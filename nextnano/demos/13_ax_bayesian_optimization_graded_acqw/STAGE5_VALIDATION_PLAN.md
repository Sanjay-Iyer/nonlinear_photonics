# Stage 5 validation plan — Demo 13 v2 top designs

**Status: prepared, not launched.** Stage 5 spends licensed solver time and must
not run until the work-laptop reanalysis has passed its checklist
(`WORK_LAPTOP_REANALYSIS.md`).

Stage 5 exists to answer one question: **is t0012 a physical optimum, or an
artifact of the mesh, the state window, the domain size, or the search bounds?**
Until it passes, t0012 is a proposed optimum and the reports say so.

---

## 1. Designs under test

| Role | Design | Why |
|---|---|---|
| **A** | t0012 — best trial. s ≈ 0.4603, barrier 0.5 nm, abrupt, realized grading 0 nm | The claim under test |
| **B** | t0011 — rank 2 | Is the *ranking* stable, or does it reorder under refinement? |
| **C** | t0010 — rank 3 | Same |
| **D** | A lower-response but valid design, well away from the barrier bound (barrier ≳ 1.5 nm) | A control. If *its* objective also moves with mesh, the problem is global, not specific to the thin barrier |
| **E** | Demo 11 abrupt reference (case `s1_ref`) | The comparison baseline. Must be re-run under identical numerics, not quoted from its own bundle |

Designs B–D are selected from the ranked table by the deterministic
`(objective, trial_index)` key, so the selection is reproducible.

## 2. Checks, in the order they must run

Cheapest-and-most-likely-to-invalidate first, so an early failure saves the rest.

### 2.1 Mesh convergence — run this first
`validation_study.mesh_convergence_nm: [0.05, 0.10]`

At 0.10 nm the 0.5 nm barrier of design A spans **5 cells**. Halving to 0.05 nm
gives 10. **Acceptance: the objective changes by < 2 % between the two meshes.**

If it does not converge, nothing downstream matters: the ranking, the grading
conclusion and the barrier optimum are all suspect, and the v3 lower bound must
rise. Extend to 0.025 nm for design A specifically if 0.05 → 0.10 is not flat.

### 2.2 State-count convergence
`state_count_convergence: [4, 6]`

Demo 11's registry entry records an **unresolved** finding: its Eq. 2
state-window convergence is marked FAILED, and the s ≈ 0.42 asymmetry optimum was
shown to be an anticrossing artifact of window truncation. Demo 13 inherits that
extraction unchanged and its winner sits at s ≈ 0.4603.

**Acceptance: the objective changes by < 2 % from 4 → 6 states, and the tracked
state labels do not permute.** A change here is inherited physics, not a Demo 13
regression, and must be reported as such.

### 2.3 Outer-domain padding
`domain_padding_nm: [0.0, 4.0]`

**Acceptance: objective change < 1 %, and `maximum_boundary_probability` stays
below 1e-3 at both paddings.** This metric is constant across the v2
observations, which is itself worth confirming rather than assuming.

### 2.4 Boundary-probability diagnostics

Report `maximum_boundary_probability` (largest per-state edge leakage) and, if
available, the per-state distribution. **These are different quantities from a
total summed over states**; the reports must not interchange them. Only the
maximum is constrained, at 1e-3, with `boundary_edge_fraction: 0.05`.

### 2.5 State-tracking stability — order independence

The v2 tracking is `nearest_neighbour_overlap_assignment` against the nearest
already-completed trial, so the reference chain depends on BO evaluation order.

**Procedure:** re-track all five designs against the fixed anchor
(`anchor_case: reference_abrupt`) rather than against nearest neighbours, and
compare the assignment to the one recorded during the campaign.
**Acceptance: identical state labels, confidence ≥ 0.8, assignment margin ≥
0.15, `ambiguous` false.** Any permutation invalidates the corresponding trial's
metrics, because the extraction picked the wrong pair of states.

Design A is the highest risk: a 0.5 nm barrier gives the strongest tunnel
coupling in the study, so the lowest two electron states are most nearly
degenerate and an overlap-based assignment is least discriminating.

### 2.6 Local refinement in asymmetry
`local_refinement.asymmetry_s: [-0.02, 0.02]` around s ≈ 0.4603.

**Acceptance:** the objective at ±0.02 is **lower** than at the centre. If a
neighbour is higher, the sampled point is not a local maximum and the campaign
stopped short. Recommend a finer ±0.005 pass for design A, because Demo 11's
anticrossing artifact appeared on exactly this axis at a similar s.

### 2.7 Local refinement in central-barrier thickness
`local_refinement.central_barrier_thickness_nm: [-0.2, 0.2]`

**⚠️ Design A sits on the lower bound of 0.5 nm, so −0.2 nm means 0.3 nm — outside
the search space, and about one monolayer of AlGaAs.** Run it anyway, and label
it explicitly as *outside the searched range and outside the range where the
envelope-function model is trustworthy*. Its purpose is diagnostic: if the
objective keeps rising at 0.3 nm, that confirms the bound is binding and the
optimum is not interior.

### 2.8 Fabrication perturbations
`fabrication_perturbations`: wells ±0.2 nm, central barrier ±0.2 nm, Al fraction
±0.01, grading ±0.25 nm.

**Two corrections were required here and are now implemented** (see
`OLD_CODE_AUDIT.md` §C1):

1. **Grading is not perturbed on a design that realizes none.** Design A
   realizes 0 nm of grading. A −0.25 nm perturbation is meaningless, and a
   +0.25 nm one changes the interface *mode* from abrupt to graded — a
   different structure, not a fabrication tolerance. `robustness_cases` now
   skips grading perturbations entirely when `realized_grading_thickness_nm` is
   zero, so design A gets 6 perturbations (wells, barrier, Al fraction) rather
   than 8, and none of them is a mode change.
2. **A ±0.2 nm barrier perturbation on a 0.5 nm barrier is a ±40 % change.**
   Every robustness row now carries `perturbation_fraction_of_nominal` and
   `relative_drift_per_fractional_change`, so the ±40 % barrier change is not
   averaged into the same score as a ±3 % well change.

**Acceptance:** relative objective drift < 10 % for each perturbation. Read
`relative_drift_per_fractional_change` for the barrier, not the raw drift — the
raw number will look reassuring precisely because the same 0.2 nm is a much
larger relative change there.

### 2.9 Repeated extraction and objective recalculation

Re-run extraction and the Eq. 2 objective on the **stored raw output** of each
design without re-solving. **Acceptance: bitwise-identical objective.** Any
difference is an extraction-path bug, not physics.

### 2.10 Comparison on the same relative scale

Every number above is a Demo 11 Eq. 2 **relative** susceptibility in arbitrary
units. Comparisons are ratios on that scale. No pm/V value is produced, quoted,
or implied.

## 3. The report must answer, explicitly

| Question | Passing answer |
|---|---|
| Does the ranking remain stable? | A, B, C keep their order under both mesh and state-count refinement |
| Does t0012 remain best? | Yes, at every mesh and state count tested |
| Does the objective change materially with mesh? | < 2 % from 0.10 → 0.05 nm |
| Does the state identity remain stable? | No label permutation; confidence ≥ 0.8, margin ≥ 0.15, order-independent |
| Does the response survive fabrication perturbations? | < 10 % drift, barrier sensitivity reported separately |
| Does the optimum move away from the sampled point? | No neighbour in the ±0.02 / ±0.2 refinement exceeds the centre |
| Is the 0.5 nm barrier numerically resolved? | ≥ 10 cells across it and mesh-converged — **at 0.10 nm it is 5 cells, so this almost certainly requires the 0.05 nm mesh** |
| Is the boundary metric still acceptable? | max boundary probability < 1e-3 at every padding and state count |

## 4. Cost and gating

Five designs × (2 mesh + 2 state-count + 2 padding + 2 asymmetry + 2 barrier)
= 50 validation cases, plus robustness cases: 8 per graded design and **6 per
abrupt design**, since grading perturbations are now skipped where there is no
grading. For four abrupt designs and one graded that is 6×4 + 8 = 32. Roughly
**82 licensed solver runs** — over five times the optimization campaign itself.

**Gate it:** run §2.1 mesh convergence on design A alone first (2 runs). If the
objective moves by more than 2 %, stop and fix the mesh before spending the
other 88.

## 5. How to run it

Only after the reanalysis checklist passes:

```bash
git -C C:\Code\optics\nextnano\nonlinear_photonics status --porcelain
```

The tree must be clean — a validation run from a dirty tree cannot be
attributed to a commit. Then set in `demo.yaml`:

```yaml
workflow:
  mode: validate_top_designs
  experiment_state_dir: demo13_ax_experiment_v2
```

Stage 5 writes into `<experiment_state_dir>/runs/v*` and `r*` and appends
validation rows; it does **not** open the experiment read-only, because it
legitimately adds side cases. It must never complete, fail or abandon an
optimization trial — verify afterwards that the 16 optimization trial records
are unchanged with the manifest captured before the run.
