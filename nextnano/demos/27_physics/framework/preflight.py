"""Preflight: resolve, generate, diff, parse, and state the cost.

Preflight is the only stage that touches nextnano++ without being a physics
stage, and it does so with ``--parse``, which validates grammar and exits. It
never solves anything, so it is safe on a Free build and on any machine.

A sub-demo that has not passed preflight cannot run its physics stage.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from . import Demo27Error
from . import decks as deck_module
from .registry import Resolved, SubDemo
from .report import markdown_table, write_csv, write_json, write_text


def cost_statement(sub: SubDemo, resolved: Resolved) -> dict:
    """The declared cost, cross-checked against what was actually generated."""
    cost = dict(sub.cost)
    generated = len(resolved.decks)
    declared = cost.get("decks")
    k_points = [int(d.spec.k_points) if d.spec.k_mode != "none" else 0 for d in resolved.decks]
    states = [int(d.spec.output_state_count) for d in resolved.decks]
    low, high = sub.runtime_range()
    volume = cost.get("output_gb") or [None, None]
    statement = {
        "sub_demo": sub.demo_id,
        "tier": sub.tier,
        "professional_required": sub.professional_required,
        "decks_declared": declared,
        "decks_generated": generated,
        "k_points_per_deck": k_points,
        "total_k_point_solves": sum(k_points),
        "states_per_deck": states,
        "max_states": max(states) if states else 0,
        "runtime_hours_low": low,
        "runtime_hours_high": high,
        "runtime_text": sub.runtime_text(),
        "output_gb_low": volume[0] if len(volume) > 0 else None,
        "output_gb_high": volume[1] if len(volume) > 1 else None,
        "basis": cost.get("basis", ""),
    }
    if declared is not None and int(declared) != generated and generated:
        statement["warning"] = (
            "config.yaml declares %s decks but %d were generated; the estimate below is "
            "scaled to the declared count and should be corrected." % (declared, generated))
    return statement


def cost_markdown(sub: SubDemo, statement: Mapping) -> str:
    # A delegated sub-demo generates no decks of its own, so the figures come
    # from what it declares. They are labelled so the two cannot be confused.
    delegated = not statement["k_points_per_deck"]
    source = " (declared; decks belong to %s)" % sub.delegate.get("demo", "the delegate") \
        if delegated else ""
    decks = statement["decks_generated"] or statement["decks_declared"] or 0
    k_points = statement["k_points_per_deck"] or sub.cost.get("k_points_per_deck") or "n/a"
    total_k = statement["total_k_point_solves"] or (
        (sub.cost.get("k_points_per_deck") or 0) * (sub.cost.get("decks") or 0))
    states = statement["states_per_deck"] or sub.cost.get("states_per_deck") or "n/a"
    lines = [
        "# %s cost statement" % sub.demo_id,
        "",
        "**Read this before launching the physics stage.** These are planning estimates.",
        "",
        "| Item | Value |",
        "|---|---|",
        "| Tier | %s |" % statement["tier"],
        "| nextnano++ Professional required | %s |"
        % ("yes" if statement["professional_required"] else "no"),
        "| Decks | %s%s |" % (decks, source),
        "| k points per deck | %s |" % k_points,
        "| Total k-point solves | %s |" % total_k,
        "| States solved/output per deck | %s |" % states,
        "| Estimated wall time | %s |" % statement["runtime_text"],
        "| Estimated output volume | %s |" % _volume_text(statement),
        "",
        "**Basis for the estimate.** %s" % (statement.get("basis") or "not stated"),
        "",
    ]
    if statement.get("warning"):
        lines += ["> WARNING: %s" % statement["warning"], ""]
    return "\n".join(lines)


def _volume_text(statement: Mapping) -> str:
    low, high = statement.get("output_gb_low"), statement.get("output_gb_high")
    if low is None or high is None:
        return "not estimated"
    return "%.3g - %.3g GB" % (float(low), float(high))


def run(sub: SubDemo, resolved: Resolved, machine: Mapping | None,
        *, parse: bool = True) -> dict:
    """Generate the decks, diff them against the baseline, and parse them."""
    outputs = sub.outputs_dir
    inputs = sub.inputs_dir
    kind = sub.stage_kind("preflight")

    statement = cost_statement(sub, resolved)
    write_json(outputs / "COST_STATEMENT.json", statement)
    write_text(outputs / "COST_STATEMENT.md", cost_markdown(sub, statement))
    write_json(outputs / "RESOLVED_CONFIG.json", {
        "sub_demo": sub.demo_id,
        "title": sub.title,
        "question": sub.question,
        "tier": sub.tier,
        "prerequisites": list(sub.prerequisites),
        "pass_condition": sub.pass_condition,
        "stages": sub.stages,
        "delegate": sub.delegate,
        "controlled_change": sub.controlled_change,
        "baseline": {"source": "23_k_resolved_dispersion_validation/demo23_config.yaml"},
        "decks": [{"name": d.spec.name, "question": d.question,
                   "changes": {k: {"baseline": v[0], "deck": v[1]}
                               for k, v in d.changes.items()}}
                  for d in resolved.decks],
    })

    if kind == "delegated":
        result = _run_delegated_preflight(sub)
        write_text(outputs / "PREFLIGHT.md",
                   _no_deck_report(sub, statement, delegated=result))
        return {"status": result["status"], "decks": [], "parse": [], "cost": statement,
                "delegated": result}

    if kind != "generate_and_parse":
        write_text(outputs / "PREFLIGHT.md", _no_deck_report(sub, statement))
        return {"status": "PASS", "decks": [], "parse": [], "cost": statement,
                "note": "no decks: preflight kind is %r" % kind}

    if not resolved.decks:
        raise Demo27Error(
            "%s declares preflight kind 'generate_and_parse' but its config lists no decks"
            % sub.demo_id)

    baseline_text = deck_module.render(resolved.baseline, sub_demo="23-baseline")
    rows = []
    written = []
    for entry in resolved.decks:
        summary = sub.controlled_change.get("summary", "")
        path = deck_module.write(entry.spec, inputs, sub_demo=sub.demo_id,
                                 controlled_change=summary)
        written.append((entry, path))
        diff = deck_module.diff_against_baseline(baseline_text,
                                                 path.read_text(encoding="utf-8"))
        rows.append({
            "deck": path.name,
            "question": entry.question,
            "band_model": entry.spec.band_model,
            "k_mode": entry.spec.k_mode,
            "k_points": entry.spec.k_points,
            "kmax_per_nm": round(float(entry.spec.kmax_per_nm), 6),
            "states_out": entry.spec.output_state_count,
            "electrostatics": entry.spec.electrostatics,
            "interface_model": entry.spec.interface_model,
            "changed_fields": ";".join(sorted(entry.changes)) or "none",
            "structural_diff_lines": len(diff),
            "path": str(path),
        })
    write_csv(outputs / "DECK_MANIFEST.csv", rows)
    write_text(outputs / "CONTROLLED_CHANGE_DIFF.md",
               _diff_report(sub, resolved, baseline_text, written))

    parse_rows = []
    parse_status = "SKIPPED"
    if parse and machine is not None:
        from .solver import parse_deck  # noqa: PLC0415

        scratch = resolved.results_root / "syntax_check"
        for _, path in written:
            parse_rows.append(parse_deck(machine, path, scratch))
        write_csv(outputs / "DECK_SYNTAX_VALIDATION.csv", parse_rows)
        failures = [r["deck"] for r in parse_rows if not r["parse_ok"]]
        parse_status = "FAIL" if failures else "PASS"
    status = "FAIL" if parse_status == "FAIL" else "PASS"
    write_text(outputs / "PREFLIGHT.md",
               _preflight_report(sub, statement, rows, parse_rows, parse_status))
    return {"status": status, "decks": rows, "parse": parse_rows,
            "parse_status": parse_status, "cost": statement}


def _run_delegated_preflight(sub: SubDemo) -> dict:
    """Run the owning demo's own preflight. Deck generation and ``--parse`` only.

    Delegation is how Demo 27 obeys its reuse rule: where an existing demo
    already implements a calculation, Demo 27 runs that demo rather than forking
    its code, and records exactly what it ran.
    """
    import subprocess  # noqa: PLC0415
    import sys  # noqa: PLC0415

    from .registry import DEMOS_DIR, REPO_ROOT  # noqa: PLC0415

    delegate = dict(sub.delegate or {})
    for key in ("demo", "runner", "commands"):
        if key not in delegate:
            raise Demo27Error("%s has a delegated preflight but no delegate.%s"
                              % (sub.demo_id, key))
    command = (delegate["commands"] or {}).get("preflight")
    if not command:
        raise Demo27Error("%s has no delegate command mapped for preflight" % sub.demo_id)
    runner = DEMOS_DIR / str(delegate["demo"]) / str(delegate["runner"])
    if not runner.is_file():
        raise Demo27Error("%s delegates to %s, which does not exist. Demo 27 will not "
                          "reimplement it." % (sub.demo_id, runner))
    argv = [sys.executable, str(runner)] + str(command).split()
    done = subprocess.run(argv, cwd=str(REPO_ROOT), check=False)
    return {"status": "PASS" if done.returncode == 0 else "FAIL",
            "argv": argv, "returncode": done.returncode,
            "delegate": str(delegate["demo"]), "runner": str(runner)}


def _no_deck_report(sub: SubDemo, statement: Mapping,
                    delegated: Mapping | None = None) -> str:
    kind = sub.stage_kind("preflight")
    reason = {
        "delegated": "this sub-demo delegates its solver work to another demo, which owns "
                     "the decks; see the delegate block in config.yaml",
        "python": "this sub-demo is analysis-only and generates no nextnano++ deck",
        "none": "this sub-demo has no preflight work",
        "external": "this sub-demo requires tooling outside nextnano and has no deck",
    }.get(kind, kind)
    lines = ["# %s preflight" % sub.demo_id, "",
             "**No decks of its own.** %s" % reason, ""]
    if delegated:
        lines += ["## Delegated preflight", "",
                  "Ran: `%s`" % " ".join(delegated["argv"][1:]),
                  "",
                  "Result: **%s** (exit %s)" % (delegated["status"], delegated["returncode"]),
                  "",
                  "The decks, their syntax validation and their gate belong to `%s`."
                  % delegated["delegate"],
                  "Demo 27 does not fork them.",
                  ""]
    lines.append(cost_markdown(sub, statement))
    return "\n".join(lines)


def _diff_report(sub: SubDemo, resolved: Resolved, baseline_text: str, written: list) -> str:
    declared = sorted(sub.controlled_change.get("fields") or [])
    lines = [
        "# %s: the one controlled change" % sub.demo_id,
        "",
        "**Declared change.** %s" % sub.controlled_change.get("summary", "(none stated)"),
        "",
        "**Fields this sub-demo is permitted to change:** %s"
        % (", ".join("`%s`" % f for f in declared) or "none"),
        "",
        "Everything else is inherited verbatim from the Demo 23 baseline. `registry.resolve`",
        "raises if a deck changes a field that is not in the list above, so this document",
        "cannot drift from what was actually generated.",
        "",
    ]
    for entry, path in written:
        diff = deck_module.diff_against_baseline(baseline_text, path.read_text(encoding="utf-8"))
        lines += ["## %s" % path.name, "",
                  "*%s*" % entry.question, "",
                  "Changed deck fields:", ""]
        if entry.changes:
            lines.append(markdown_table(
                [{"field": key, "baseline": before, "this deck": after}
                 for key, (before, after) in sorted(entry.changes.items())],
                ["field", "baseline", "this deck"]))
        else:
            lines.append("_none - this deck reproduces the Demo 23 baseline exactly._")
        lines += ["", "Structural deck lines that differ from the baseline deck: **%d**"
                  % len(diff), ""]
        if diff:
            lines += ["```diff", *diff[:80], "```", ""]
            if len(diff) > 80:
                lines += ["_(%d further differing lines omitted)_" % (len(diff) - 80), ""]
    return "\n".join(lines)


def _preflight_report(sub: SubDemo, statement: Mapping, rows: list,
                      parse_rows: list, parse_status: str) -> str:
    lines = [
        "# %s preflight" % sub.demo_id,
        "",
        "**%s**" % sub.title,
        "",
        "Question: %s" % sub.question,
        "",
        "Pass condition: %s" % sub.pass_condition,
        "",
        "## Generated decks",
        "",
        markdown_table(rows, ["deck", "band_model", "k_mode", "k_points", "kmax_per_nm",
                              "states_out", "electrostatics", "interface_model",
                              "changed_fields", "structural_diff_lines"]),
        "",
        "## Syntax validation (`nextnano++ --parse`)",
        "",
    ]
    if parse_status == "SKIPPED":
        lines += ["No nextnano++ executable is configured on this machine, so grammar was",
                  "not validated. Preflight still resolved the configuration and wrote the",
                  "decks; run it again where nextnano++ is installed before the physics stage.",
                  ""]
    else:
        lines += [markdown_table(parse_rows, ["deck", "parse_ok", "message"]), "",
                  "`--parse` validates grammar only. A deck that parses can still be",
                  "physically wrong, which is why every physics stage writes a manifest and",
                  "audits the files that actually appear.",
                  ""]
    lines.append(cost_markdown(sub, statement))
    return "\n".join(lines)
