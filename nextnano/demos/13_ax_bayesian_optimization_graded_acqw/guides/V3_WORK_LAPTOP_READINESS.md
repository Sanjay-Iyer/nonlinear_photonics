# v3 work-laptop readiness

**Verdict: READY for reanalysis. NOT ready for Stage 5.**

## Safe to run

`workflow.mode: analyze_existing_results` is now the **shipped default**. It
opens the experiment read-only, calls no solver, and was verified end-to-end:
exit 0, zero `Executing` lines, zero `Generated new trial` lines, all four
protected hashes identical before and after.

Previously the shipped mode was `closed_loop`. That was harmless *only* because
the budget was exhausted -- one `num_iterations` bump would have turned the same
command into licensed solver spend. That trap is removed.

## Command safety

Every numbered step in `WORK_LAPTOP_GUIDE.md` is marked **SAFE** or **SPENDS
SOLVER TIME**, and a test enforces the marking. No runnable Stage 5 launch
command appears anywhere; the mode is named as unsafe and the reader is directed
to the execution plan.

## Raw-bundle helper

`bundle_raw_trials.py` supports `--dry-run`, is read-only with respect to the
experiment, refuses a non-empty destination without `--overwrite`, requires
`--force` for the full raw tree, and names every requested-but-missing file.
Default selection: t0021, t0022, t0017, t0005 plus every genuinely graded trial,
read from the ledger.

## Stage 5 -- NOT authorized

Blocking items:

1. **The independent physics audit returned FAIL.** State-count convergence, not
   mesh, may be the true first gate: the inherited Demo 11 window error is
   reported as 58 nm against a 15 nm constraint.
2. **Stage 5 SS E targets a risk that does not exist** -- the "near-degenerate
   doublet at the thinnest barrier" is backwards; t0021 has one of the *largest*
   splittings (95.1 meV, verified).
3. **`state_tracking.anchor_case` is read by no code**, so SS E cannot run as
   written.
4. **Config disagrees with the plan**: `mesh_convergence_nm` lacks the 0.025 nm
   the gate requires; perturbation ranges are +/-0.2 nm where the plan says
   +/-0.05 nm and no grading perturbation on abrupt designs.
5. **No alloy profile has ever been verified**, so no realized grading claim has
   evidence behind it.

Isolation itself is ready: Stage 5 writes to `demo13_ax_experiment_v3_stage5`,
and a configuration pointing it at the optimization experiment is rejected at
startup and again after path resolution.
