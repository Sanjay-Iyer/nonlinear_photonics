# Demo 13 — work-laptop final handoff

Run these **in order**. Every command carries one of three labels:

| Label | Meaning |
|---|---|
| **SAFE — no solver** | Reads or copies only. No nextnano process starts. |
| **PAID SOLVER — two-case Stage 5 gate** | Launches exactly two licensed nextnano++ runs. |
| **DO NOT RUN UNTIL GATE REVIEW** | Blocked until the gate result has been reviewed and authorized. |

There is deliberately **no command here for the full Stage 5 campaign.**

---

## 1. Pull the commit — SAFE — no solver

```bash
git pull
```

## 2. Activate the licensed environment — SAFE — no solver

```bash
conda activate NMIP
```

## 3. Verify the commit and a clean tree — SAFE — no solver

```bash
git rev-parse HEAD; git status --porcelain
```

`git status --porcelain` must print nothing. The v3 campaign was run from a
dirty tree, so its recorded commit does not fully describe the code that
produced it. Do not repeat that.

## 4. Confirm the pinned versions — SAFE — no solver

```bash
python -c "import ax, botorch, torch; print(ax.__version__, botorch.__version__, torch.__version__)"
```

Expect Ax `1.3.1`.

## 5. Run the focused tests — SAFE — no solver

```bash
python -m pytest nextnano/tests/test_demo13_state_energies_and_anchor.py nextnano/tests/test_demo13_failure_modes_and_gate.py nextnano/tests/test_demo13_bundle_and_stage5.py nextnano/tests/test_demo13_v3_reporting.py nextnano/tests/test_demo13_v3_accounting.py nextnano/tests/test_demo13_guides.py -q
```

## 6. Run the whole suite — SAFE — no solver

```bash
python -m pytest nextnano/tests/ -q
```

## 7. Record protected-file hashes BEFORE — SAFE — no solver

```bash
python -c "import hashlib,pathlib;d=pathlib.Path('nextnano/results/demo_runs/13_ax_bayesian_optimization_graded_acqw/demo13_ax_experiment_v3');[print(n, hashlib.sha256((d/n).read_bytes()).hexdigest()) for n in ('ax_experiment_snapshot.json','trial_ledger.jsonl','experiment_schema.json','demo_yaml_snapshot.yaml')]"
```

Save this output. Step 12 must reproduce it exactly.

## 8. Dry-run the raw collection — SAFE — no solver

```bash
python nextnano/scripts/bundle_raw_trials.py --experiment demo13_ax_experiment_v3 --dry-run
```

Read the `OK`/`!!` source-verification line for each trial and every
`UNAVAILABLE` line. `!!` means the run directory's resolved geometry disagrees
with the ledger — stop and find out why before copying anything.

## 9. Collect the raw alloy and state files — SAFE — no solver

```bash
python nextnano/scripts/bundle_raw_trials.py --experiment demo13_ax_experiment_v3
```

Copies, for `t0021`, `t0022`, `t0017`, `t0005` and every genuinely graded trial:
the generated input, the resolved configuration, console and solver logs,
electron and heavy-hole state energies, the envelopes needed for tracking, and
the native alloy-composition profile. Writes `raw_bundle_manifest.json` naming
everything copied **and everything missing, with the check each absence blocks.**

This is read-only with respect to the experiment. `source_modified` in the
manifest is **measured** (a size/mtime fingerprint taken before and after), not
asserted — it must read `false`.

`extracted/requested_composition_profile.csv` is reported as
`expected: false`: Demo 13 analyses trials with `demo11.analyse_case`, which
never writes it. Its absence is structural, **not** a solver failure. The
realized alloy profile has to come from the native solver output.

**This step is not a prerequisite for the gate.** The gate reads
`demo13_ax_experiment_v3/runs/t0021/extracted/` *in place*; this step copies
*out of* that directory and cannot create it. If step 13 reports the anchor
output missing, the campaign's raw output is not on this machine and the gate
cannot run here at all.

## 10. Analysis-only reanalysis — SAFE — no solver

First confirm the mode:

```bash
python -c "import yaml;c=yaml.safe_load(open('nextnano/demos/13_ax_bayesian_optimization_graded_acqw/demo.yaml'));print(c['workflow']['mode'])"
```

Must print `analyze_existing_results`. Then:

```bash
python nextnano/demos/13_ax_bayesian_optimization_graded_acqw/run_demo13.py
```

Expect exit 0 and a console block reporting 23 proposals, 7 refused, 16
completed, 3 feasible, and `experiment state : unchanged after reanalysis`.

## 11. Verify zero solver calls — SAFE — no solver

```bash
grep -E "Executing|Generated new trial" "$(ls -d nextnano/results/demo_runs/13_ax_bayesian_optimization_graded_acqw/2026* | tail -1)/console.log"
```

Must return nothing.

## 12. Verify protected hashes AFTER — SAFE — no solver

Rerun step 7. All four hashes must be identical to what you saved.

## 13. Inspect the Stage 5 gate — SAFE — no solver

```bash
python nextnano/demos/13_ax_bayesian_optimization_graded_acqw/run_demo13.py --stage5-check
```

Writes nothing, calls no solver. Confirm every line before going further:

- `Stage 5 destination` ends in `demo13_stage5_v3_validation` and sits **beside**
  `demo13_ax_experiment_v3`, not inside it;
- `Isolation : OK`;
- `Gate design/anchor : t0021 / t0021`;
- `Reference mesh : 0.05 nm (already computed, not re-run)`;
- `Paid solver calls : 2`;
- both cases show barrier `0.85 nm`, wide `6.937824 nm`, narrow `3.062176 nm`,
  `abrupt 0 nm`, at meshes `0.025 nm` and `0.1 nm`;
- `Anchor output` names a real directory (step 9 must have produced it);
- `Full campaign : BLOCKED`.

**If `Paid solver calls` is not exactly 2, stop.**

## 14. Launch the two-case mesh gate — PAID SOLVER — two-case Stage 5 gate

Only after step 13 reads exactly as above.

```bash
python -c "import pathlib,re;p=pathlib.Path('nextnano/demos/13_ax_bayesian_optimization_graded_acqw/demo.yaml');t=p.read_text(encoding='utf-8');p.write_text(t.replace('mode: analyze_existing_results','mode: validate_top_designs'),encoding='utf-8')"
```

```bash
python nextnano/demos/13_ax_bayesian_optimization_graded_acqw/run_demo13.py
```

This runs **two** licensed nextnano++ calculations and nothing else, then
**returns**. The full campaign is never generated in the same invocation that
produced the gate result — `run_validation_study` returns immediately after the
gate with `full_campaign_generated: false`, so a passing gate cannot fall
through into the remaining ~60 cases. Releasing those needs a separate,
separately authorized run after the result below has been reviewed.

Immediately afterwards, put the mode back:

```bash
python -c "import pathlib;p=pathlib.Path('nextnano/demos/13_ax_bayesian_optimization_graded_acqw/demo.yaml');t=p.read_text(encoding='utf-8');p.write_text(t.replace('mode: validate_top_designs','mode: analyze_existing_results'),encoding='utf-8')"
```

## 15. Locate the gate outputs — SAFE — no solver

```bash
ls -R nextnano/results/demo_runs/13_ax_bayesian_optimization_graded_acqw/demo13_stage5_v3_validation
```

## 16. Verify the campaign is still untouched — SAFE — no solver

Rerun step 7 a third time. All four hashes must still match.

## 17. Package the gate results for review — SAFE — no solver

`bundle_raw_trials.py` reads `<experiment>/runs/t####/` and Stage 5 writes
`<state dir>/<case id>/`, so the bundler does **not** apply here. Copy the
directory directly:

```bash
tar -czf nextnano/results/transfer/stage5_gate_review.tgz -C nextnano/results/demo_runs/13_ax_bayesian_optimization_graded_acqw demo13_stage5_v3_validation
```

## 18. Everything else — DO NOT RUN UNTIL GATE REVIEW

The full Stage 5 campaign (local refinement, state-count, padding and
fabrication perturbations for the top designs — roughly **69 licensed cases**)
is **not** in this document and must not be launched until the two-case gate has
been reviewed and separately authorized.

While `validation_study.gate.enabled` is `true`, `run_validation_study` runs the
gate and returns — the campaign cannot be generated by any invocation, whatever
the gate result says. Releasing it is therefore a deliberate, reviewable
configuration change (setting `gate.enabled: false`), never a side effect of
re-running a command. Do not make that change on the basis of this document.

---

## Files to return after the two-case paid run

Copy these back for review:

1. `nextnano/results/demo_runs/13_ax_bayesian_optimization_graded_acqw/demo13_stage5_v3_validation/stage5_gate_result.json`
2. `.../demo13_stage5_v3_validation/stage5_schema.json`
3. `.../demo13_stage5_v3_validation/gate_mesh_0.025nm/` — generated input, logs, `extracted/`
4. `.../demo13_stage5_v3_validation/gate_mesh_0.1nm/` — generated input, logs, `extracted/`
5. `nextnano/results/transfer/demo13_ax_experiment_v3_raw_supplement/` — the step 9 bundle, including `raw_bundle_manifest.json`
6. `nextnano/results/transfer/stage5_gate_review.tgz` — the step 17 archive
7. The step 7 / 12 / 16 hash outputs, all three
8. The console log of the step 14 run

## What the gate decides

`stage5_gate_result.json` carries a `comparison` block holding, for each new
mesh, the reference-mesh value beside the new value for: tracked state labels,
state-tracking confidence and ambiguity, the heavy-hole minimum gap, relative
χ² at 1550 nm, peak wavelength, signed and absolute detuning, maximum boundary
probability, physical QC, and Ax feasibility.

`gate_passed` is `true` only when every gate case assigns to the anchor without
ambiguity and keeps the anchor's state labels. It is `null` — never `true` —
when the gate could not be evaluated, and the reason is stated in
`gate_unavailable_reason`.

**A passing gate does not validate t0021.** It establishes that the mesh does
not change the answer. t0021 still sits on the central-barrier lower bound, and
the remaining convergence, sensitivity and robustness checks have not run.
