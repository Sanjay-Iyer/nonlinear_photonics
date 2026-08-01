# Experiment v3 — search-space design

**Status: designed, not launched.** No v3 experiment directory has been created
and no v3 configuration has been committed as the active `demo.yaml`. v2's
checkpoint is not reused, altered, or resumed under a v3 space: v3 gets its own
`experiment_state_dir: demo13_ax_experiment_v3`, and
`Experiment._check_schema_compatible` refuses to load a v2 snapshot under a
changed search space anyway.

v3 exists to fix two scientific limitations of v2 that no amount of reanalysis
can repair, because they are properties of what v2 *sampled*.

---

## Limitation A — the winner sits on the lower barrier bound

v2's best design has `central_barrier_thickness_nm = 0.5`, exactly the lower
bound. That is the optimizer reporting that the bound is binding. The optimum is
at or below 0.5 nm, and 0.5 nm may not be a physically meaningful structure.

### Deriving a defensible new lower bound

Zero is not the answer: at zero the two wells merge into one and the "coupled
quantum well" is a different device. Six constraints, evaluated:

| Constraint | Value | Implied minimum barrier |
|---|---|---|
| **Spatial mesh** | `active_region_grid_spacing_nm: 0.10` | — |
| **Cells across the barrier** | want ≥ 10 for a resolved potential step | **1.0 nm** at 0.10 nm mesh; **0.5 nm** at 0.05 nm mesh |
| **Growth-layer realism** | GaAs a = 0.565325 nm ⇒ 1 ML along [001] = **0.2827 nm** | A barrier must be an integer ML count. 0.5 nm = **1.77 ML**, which is not growable as specified. 2 ML = **0.565 nm**; 3 ML = **0.848 nm** |
| **Interdiffusion scale** | AlGaAs/GaAs interdiffusion is typically 0.3–1 nm | A 2 ML barrier is comparable to the interdiffusion length and would be substantially washed out |
| **Geometry feasibility** | `minimum_flat_region_nm: 0.10` per layer outside any grade | Not binding for abrupt designs |
| **State-tracking stability** | thinner barrier ⇒ stronger coupling ⇒ near-degenerate doublet ⇒ least discriminating overlap assignment | Argues against going thinner without §2.5 of the Stage 5 plan passing |

### Recommendation

**Primary: `lower: 0.85` nm (3 monolayers, 0.848 nm), with
`active_region_grid_spacing_nm: 0.05`.**

That gives **17 mesh cells** across the thinnest barrier, an integer monolayer
count, and a thickness comfortably above the interdiffusion scale. It is
defensible as a *grown structure*, which 0.5 nm is not.

**Contingency, decided by Stage 5 §2.1:** if mesh convergence shows the
objective at 0.5 nm is stable to < 2 % between 0.10 and 0.05 nm, and state
tracking §2.5 passes, then `lower: 0.565` nm (2 ML) is admissible at 0.05 nm
mesh (11 cells). Below 2 ML the envelope-function model with an abrupt Al₀.₅₅
step is being applied to a layer thinner than the scale on which the alloy
potential is defined, and no bound should be set there.

**Do not run v3 before Stage 5 decides this.** Choosing the bound from the
result is the point; choosing it first would repeat v2's mistake with a
different number.

The upper bound stays at 2.5 nm: v2 sampled it and found nothing there.

---

## Limitation B — grading collapses to abrupt

Under `parameterization: fraction`, a small fraction at a thin barrier produces
a realized width that mesh-snaps to zero. The design is then abrupt, but it
entered the surrogate's training data carrying a profile label — so the model
learned about "cosine grading" from a structure with no grading in it.

### Deriving `minimum_mesh_resolvable_nonzero_grading_nm`

| Input | Value | Implied minimum |
|---|---|---|
| `active_region_grid_spacing_nm` | 0.05 (v3) | a grade must span several cells to be a ramp rather than a step |
| `minimum_grid_points_per_grade` | 10 | **0.50 nm** at 0.05 nm mesh |
| `staircase_sublayers` | 16 | the fallback implementation subdivides the grade into 16 layers; each must exceed the mesh ⇒ **0.80 nm** |
| `mesh_snap_nm` | 0.01 | snapping granularity only; not a resolution limit |
| `minimum_flat_region_nm` | 0.10 | flat material each layer must retain outside the grade |

**Finding: v2's `minimum_graded_thickness_nm: 0.10` is inconsistent with its own
`minimum_grid_points_per_grade: 10`,** which at a 0.10 nm mesh demands 1.0 nm.
A 0.10 nm "grade" is one mesh cell — a step, not a ramp. This is why v2 was able
to accept nominally graded designs that carry no grading information.

**v3 value: `minimum_mesh_resolvable_nonzero_grading_nm: 0.80 nm`**, the binding
staircase requirement at a 0.05 nm mesh. It keeps the native and staircase
implementations mutually consistent, which Demo 12 validates against each other.

### Enforcement

For the graded branch, require

```
realized_grading_thickness_nm >= minimum_mesh_resolvable_nonzero_grading_nm
```

and handle a violation in the preflight, **before** the candidate reaches
nextnano, in this order:

1. **Reject and regenerate** — the proposal is invalid geometry, exactly as an
   over-wide grade already is. It consumes an attempt, not a BO iteration
   (`invalid_preflight_counts_as_bo_iteration: false`).
2. If regeneration exhausts `max_candidate_regeneration_attempts`,
   **canonicalize to abrupt** and record it as such: `realized_interface_mode:
   abrupt`, `collapsed_to_abrupt: true`, and the profile label dropped, so it
   trains the model as the abrupt design it actually is.

Never let a zero-or-sub-resolution grade enter training data wearing a profile
label. `grading13.GradingView.profile_evidence` already returns `None` for such
a design on the reporting side; v3 moves the same rule upstream into generation.

### Making the fraction bound consistent

`grading_fraction_of_feasible_max.lower: 0.05` is unsafe: at a feasible maximum
of 1.0 nm it requests 0.05 nm, far below 0.80 nm. Because the maximum varies
per candidate, no fixed fraction lower bound is correct. Two changes:

- raise the fraction lower bound to **0.35**, which is sufficient whenever the
  feasible maximum is ≥ 2.3 nm;
- keep the realized-width check as the authority, since it is the only one that
  holds for every geometry.

---

## Sampling enough genuine graded designs

v2's failure was not that grading lost. It is that **grading was never given a
fair test**: a handful of graded proposals, several of which realized zero.
Nothing in v2 can answer whether grading helps.

### Stratified initialization

| Setting | v2 | v3 | Why |
|---|---|---|---|
| `num_initial_trials` | 6 | **12** | Enough to stratify at all |
| Stratification | none | **6 abrupt, 6 graded**, enforced | Sobol on a hierarchical space does not guarantee branch balance |
| `minimum_genuine_graded_sobol_trials` | — | **6** | A graded initial trial that collapses is regenerated, not counted |
| Profile coverage in initialization | none | **linear, sigmoid, erf, cosine** × ≥ 1, remaining 2 free | No profile may be unrepresented before the model starts extrapolating |
| `num_iterations` | 10 | **14** | Two more than v2 to pay for the larger, better-conditioned initial design |

### Balanced comparison stage

After the BO campaign, run a **paired abrupt/graded stage**: for each of the top
3 abrupt designs, run the same (asymmetry, barrier) geometry with a genuine
non-zero grade of each profile. That is a controlled comparison — one variable
changed — which a scattered BO campaign can never provide, and it is the only
design that can answer "does grading help".

Cost: 3 designs × 4 profiles = **12 licensed runs**. Cheap for the only
question v2 could not touch.

### Warm-starting from v2

Warm-start **only unambiguously mapped v2 abrupt observations**:

- realized interface mode is `abrupt` (so the mapping carries no grading
  coordinate at all and cannot be misinterpreted);
- `central_barrier_thickness_nm` lies inside the **new** bounds — a v2 trial at
  0.5 nm is outside a 0.85 nm lower bound and must be dropped, not clamped;
- trial is `completed` and `trial_valid`;
- every `require_matching_physics_keys` value matches, **including the changed
  `active_region_grid_spacing_nm`** — which, if the mesh moves to 0.05 nm,
  disqualifies every v2 observation.

That last point is the honest conclusion: **if v3 refines the mesh, v2 cannot
warm-start it at all**, because the observations were computed with different
numerics. Attaching them anyway would teach the model that two different
calculations of the same design gave different answers. Every attached
observation records its provenance and `source_experiment: v2`.

**Recommendation: run v3 with no warm start.** State it plainly rather than
importing observations of uncertain comparability to save twelve solver runs.

---

## Other v3 changes

| Change | Reason |
|---|---|
| `maximum_boundary_probability` → `outcome_modelling.never_model` | Constant across v2's observations; Ax logs it as constant on every fit and its Sobol indices are NaN. A modelled constraint that carries no information risks the all-infeasible pathology of `AX_FEASIBILITY_ANALYSIS.md`. Still enforced outside Ax. |
| `metrics13.build_record` strips `PROVENANCE_FIELDS` before prefixing | Removes the `parameter__proposed_grading_fraction` double-underscore leak (`OLD_CODE_AUDIT.md` §A20). Safe in v3 because no v2 record is being written. |
| `surrogate_slices.fixed_values` re-centred on the v3 optimum region | v2's held-fixed barrier of 1.8 nm is nowhere near the 0.5 nm optimum, so its slices cut through an abandoned region. |
| Canonical hash includes `realized_interface_mode` | Two designs with the same realized geometry are the same structure; the hash must not distinguish them by a proposal label, and must not merge a genuine grade with a collapsed one. |

## Proposed v3 search space

```yaml
bo:
  num_initial_trials: 12
  num_iterations: 14
  batch_size: 1
  search_space:
    encoding: hierarchical
    parameterization: fraction
    # Derived, not chosen: 3 monolayers of AlGaAs (0.848 nm) at a 0.05 nm mesh
    # is 17 cells across the barrier and is a growable layer. Revisit only if
    # Stage 5 mesh convergence licenses 2 ML.
    central_barrier_thickness_nm: {type: range, lower: 0.85, upper: 2.5}
    asymmetry_s: {type: range, lower: 0.36, upper: 0.56}
    grading_fraction_of_feasible_max: {lower: 0.35, upper: 1.0}
    # Binding constraint is the staircase implementation: 16 sublayers, each
    # wider than the 0.05 nm mesh.
    minimum_mesh_resolvable_nonzero_grading_nm: 0.80
    minimum_graded_thickness_nm: 0.80
    reject_subresolution_grades: true
    stratify_initial_trials_by_interface_mode: true
    minimum_genuine_graded_sobol_trials: 6
    balanced_profile_initialization: true
numerical:
  active_region_grid_spacing_nm: 0.05
workflow:
  experiment_state_dir: demo13_ax_experiment_v3
```

## Claims v3 must still refuse to make

Even with this design, one sample per category is not a ranking.
`grading13.evidence_counts` keeps `profile_ranking_supportable` false until at
least two profiles have ≥ 3 genuinely graded trials each. With 6 stratified
graded initial trials plus the 12-run paired comparison stage, that threshold is
reachable — which is the point of the design.
