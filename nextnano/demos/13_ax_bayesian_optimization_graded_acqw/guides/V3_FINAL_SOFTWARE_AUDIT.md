# v3 final software audit

**Verdict: PASS WITH WARNINGS.**

## Immutability — verified, not asserted

All four protected files byte-identical before and after reanalysis; all 23
terminal ledger records hash-identical; `Experiment(read_only=True)` refuses
checkpoint, generate, complete, fail and abandon; the surrogate is refit on a
separate `Client` that is never serialized.

## Single source of truth

`accounting13` is the only classifier and counter. `axsearch13.budget_accounting`
and `demo13._lifecycle` delegate to it. `accounting_identity_holds` is computed
and emitted, so an inconsistent ledger is reported rather than producing
plausible wrong totals.

## Guide synchronization — the anti-drift mechanism

The requirement was that the catalogue must not be "a second hardcoded list that
can drift independently". It is not authoritative about anything the code
already knows:

| Guide content | Validated against |
|---|---|
| plot filenames | `plots13.PLOT_SET` — the list the renderer iterates |
| plot descriptions | `report13.PLOT_GUIDE` |
| plot CSV paths | **derived** from the figure filename |
| table names | `tables13.TABLE_CATALOGUE` |
| metric units | `tables13.unit_for` — never restated |
| parameter paths | resolved against real dotted paths in `demo.yaml` |
| the files themselves | regenerated and compared byte-for-byte |

A documented setting that no longer exists fails the suite — which is how the
missing `grading_fraction_spans_feasible_interval` was caught.

⚠️ The catalogue still owns *prose* — purpose, caveats, v3 interpretation — which
code cannot derive. That prose can go stale without failing a test. Mitigated by
requiring an entry for every rendered plot, but not eliminated.

## Raw-bundle helper

Read-only with respect to the source, asserted by hashing every source file
before and after; refuses a non-empty destination without `--overwrite`;
`--include all` requires `--force`; and it **names what it could not find**
rather than silently omitting it — the failure that produced a v3 package with
no alloy profiles.

## Stage 5 isolation

`validation_study.output_state_dir` defaults to `<experiment>_stage5`, is
rejected at startup if it equals the experiment directory, and
`run_validation_study` re-checks after path resolution.

## The failure mode this pass exposed

Both classes of surviving defect have the same shape: **a statement that was
true of v2, restated for v3 without recomputation.**

- `maximum_boundary_probability` was described as "nearly constant with NaN
  sensitivity indices". True of v2. In v3 it spans 107× and **caught a real
  violation at t0006 (1.91e-3)**. The recommendation to stop modelling it would
  have removed a working constraint. Withdrawn.
- `chi2_units` was "fixed" last pass at write time, but every v3 record predates
  the fix, so the reports stayed blank.

The stale-code audit catches stale *strings*. Nothing was catching stale
*numbers*. That gap is now recorded; closing it properly needs assertions that
recompute a claimed statistic from the current ledger.

## Warnings

1. `tracking13.py` discards real hole energies (`np.arange` placeholder) — see
   physics audit P3. **Not fixed.**
2. `demo.yaml` Stage 5 perturbation ranges (±0.2 nm barrier, ±0.25 nm grading)
   disagree with the execution plan (±0.05 nm, no grading perturbation on abrupt
   designs). The plan is right; the config was not updated.
3. `mesh_convergence_nm: [0.05, 0.10]` omits the 0.025 nm the plan's gate needs.
4. `state_tracking.anchor_case` is configured but **read by no Python code**, so
   Stage 5 §E cannot run as written.
5. Catalogue prose is untested (above).

Warnings 2–4 must be resolved before Stage 5 is authorized.
