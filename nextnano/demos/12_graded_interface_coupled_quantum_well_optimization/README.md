# Demo 12 — Graded-Interface Coupled Quantum Wells

This demo asks how compositional grading changes the electronic structure,
interband relative χ(2), state anticrossings, and fabrication tolerance of the
Demo 11 asymmetric coupled GaAs/Al0.55Ga0.45As quantum well (ACQW). It is ready
for the first licensed smoke run; it contains **no new licensed result**.

## Scientific baseline and controlled change

The abrupt reference is Demo 11's accepted geometry: 7.1 nm and 2.9 nm GaAs
wells, a 1.8 nm Al0.55Ga0.45As central barrier, 18.2 nm total outer period
barrier, 300 K, a 0.10 nm active mesh, four Γ-electron and four HH states, a
5 meV linewidth, and a 1550 nm application wavelength. Demo 11's extraction,
Eq. 2 relative χ(2), corrected near-zero origin-independence test,
orthonormality checks, and quasi-bound-state policy are called directly.

Demo 12 changes only the alloy transition near selected interfaces and the
variables explicitly swept in `demo.yaml`. Each case stores a resolved YAML and
a complete case-definition table, so inheritance and changes cannot be mixed.

An abrupt interface changes alloy fraction discontinuously. A graded interface
spreads that transition over a finite width. The default width is the **full
start-to-end transition width centered on the nominal abrupt interface**. Thus
half replaces the adjacent well and half replaces the adjacent barrier. Total
device length and nominal layer centers remain fixed. If wide centered grades
overlap in the thin 1.8 nm central barrier, the generated/requested profile
retains that fact and validation flags any lost endpoint; the code does not
silently widen the barrier.

## Representation in nextnano++

The repository-confirmed native linear form is:

```text
region{
  line{ x = [z0, z1] }
  ternary_linear{
    name = "Al(x)Ga(1-x)As"
    alloy_x = [x0, x1]
    x = [z0, z1]
  }
}
```

This is nextnano++ syntax inherited from Demo 11, not nextnano3 syntax. It has
passed the installed 3.0.0 parser, but the repository has not yet captured a
licensed alloy-composition output from it. Therefore Tier A is a mandatory
gate. Smooth functions use explicit `ternary_constant` sublayers because no
native nonlinear analytical grammar has been confirmed for this solver.

For normalized coordinate `u=(z-z0)/(z1-z0)` clipped to `[0,1]`, the profiles
are:

- linear: `f(u)=u`;
- sigmoid: endpoint-normalized `L(u)=1/(1+exp[-k(u-1/2)])`, with
  `f=(L-L(0))/(L(1)-L(0))`;
- error function: endpoint-normalized `f=[erf(a(u-1/2))-erf(-a/2)] /
  [erf(a/2)-erf(-a/2)]`;
- cosine: `f(u)=[1-cos(πu)]/2`;
- staircase-linear: endpoint-preserving samples `j/(N-1)` in `N` equal sublayers;
- asymmetric: linear upward and downward interfaces with separately configured
  widths;
- one-sided/location variants: the same formula at only the named interfaces.

All symmetric normalized shapes have mean `f=1/2`, so centered ramps compare at
equal thickness **and** equal integrated Al content. Requested profiles are
always saved. Licensed runs must also find the solver's alloy table and write
`realized_composition_profile.csv`; an absent or ambiguous file fails Stage 1.

Fine mesh is essential because a grade represented by one or two points is an
accidental staircase. The renderer inserts grade-boundary mesh lines and limits
the local spacing to `thickness/minimum_grid_points_per_grade` (10 by default).

## Why grading changes the physics

Smoothing Al composition smooths Γ conduction and HH/LH valence offsets. That
can shift confinement energies, move probability between the two wells, change
tunnelling splittings, and move an avoided crossing. Interband overlaps and
intraband position matrix elements then change the numerator of Eq. 2, while
transition energies move its resonant denominators. A design can therefore
have a larger intrinsic peak but a smaller value at 1550 nm, or vice versa.
Both metrics, the peak wavelength, detuning, integrated response, and optional
half-maximum bandwidth are reported separately.

Grading may also trade peak strength for tolerance: a smooth profile can make
small interface-placement errors less important, while a too-wide grade can
weaken confinement or couple to quasi-bound states. The robustness stage uses
paired finite differences, standard deviation, worst-case drift, wavelength
drift, and acceptance probability. It never calls a lower peak “better” without
showing the individual objective values.

## Seven stages and solver cost

| stage | purpose | cases in full design |
|---|---|---:|
| 1 | abrupt/native-linear/sigmoid/staircase implementation gate | 4 |
| 2 | linear thickness sweep, including 0–4 nm | 8 |
| 3 | seven profile families at 2 nm | 7 |
| 4 | eight interface-location modes | 8 |
| 5 | 11 asymmetries × 6 grading widths; track both grid directions | 66 |
| 6 | four nominal designs plus deterministic fabrication perturbations | 153 |
| 7 | constraints, rankings, and Pareto analysis of completed data | 0 new |

Tier A (default) is 4 cases. Tier B is 27 cases (Stages 1–4). Tier C is 246
cases (all solver stages). Tier C is rejected unless both `tier: C` and
`enable_full_optimization: true` are set in YAML. Completed-case reuse is an
execution policy recorded in YAML; until the first licensed run establishes a
stable output bundle, retain each completed run and do not delete raw evidence.

## State identity and quasi-bound states

Energy index alone is unsafe near Demo 11's avoided crossing. Stage 5
normalizes and interpolates envelopes to a common physical grid, constructs
absolute-overlap matrices, performs one-to-one assignment, aligns arbitrary
global signs, and uses energy continuity only as a small tie-breaker. It tracks
each asymmetry row along grading and each grading column along asymmetry. Raw
index, tracked label, best/second overlap, margin, sign flip, energies,
localization, and ambiguity remain in CSV; every assignment matrix remains in
JSON. Disagreement between the two traversals is evidence of ambiguity.

Each χ(2) state retains left/right/total boundary probability, per-region
probability, bound acceptance, inclusion, and exclusion reason. `warn`,
`exclude`, and `fail_case` policies remain available; the default is `warn` and
is printed in reports.

## Outputs and interpretation

Six paired CSV/JSON tables cover case definitions, realized geometry,
electronic structure, nonlinear optics, robustness, and optimization. The 24
numbered figures requested by the study each have a matching file in
`plot_data/`. Plots show raw solver points; no smoothing is applied. On an
unlicensed machine, figure placeholders and `not run` outcomes are expected.

The final licensed comparison names four roles: Demo 11 abrupt reference,
strongest intrinsic graded design, strongest 1550 nm graded design, and most
robust graded design. It shows full geometry, grading, transitions, resonance,
both χ(2) metrics, boundary probability, tracking confidence, robustness, and
advantages/disadvantages. Constraint failures are visible and excluded from
rankings, never deleted from tables.

## Home-laptop checks

From the repository root:

```powershell
conda activate llm
python -m pytest nextnano/tests/test_demo12_graded_interfaces.py -q
python nextnano/demos/12_graded_interface_coupled_quantum_well_optimization/report12.py
python nextnano/demos/12_graded_interface_coupled_quantum_well_optimization/run_demo12.py
```

The last command generates the four Tier A decks and marks every solver result
`skipped_no_solver`. The synthetic report is prominently labelled and is only
a report-generation test.

## Exact work-laptop sequence

1. Update and activate the same environment used for Demo 11:

```powershell
git pull
conda activate llm
python -m pip install -r requirements.txt
python nextnano/scripts/run_input.py --check-config
```

The check must show the intended nextnano++ executable, database, writable
output root, and licensed configuration. It does not run the solver.

2. Keep `execution.tier: A` and `enable_full_optimization: false` in
`demo.yaml`, then generate and run the four-case smoke study:

```powershell
python nextnano/demos/12_graded_interface_coupled_quantum_well_optimization/run_demo12.py
```

3. In the printed artifact directory, inspect every
`runs/*/extracted/realized_composition_profile.csv`, especially `v_native` and
`v_stair`. Confirm `validation_report.md` does not report a missing/ambiguous
alloy file. Inspect `plots/01_alloy_composition.png` and
`plots/24_native_staircase_validation.png` before proceeding.

4. Change only YAML to `execution.tier: B`; leave the full-optimization switch
false, then run Stages 1–4 and generate extraction, tables, plots, and reports:

```powershell
python nextnano/demos/12_graded_interface_coupled_quantum_well_optimization/run_demo12.py
```

5. After Stage 1 agreement and selected mesh convergence are acceptable, set
`execution.tier: C` and `enable_full_optimization: true`. Run the joint grid,
robustness cases, extraction, bidirectional tracking, plots, final audit, and
Pareto report with the same implemented command:

```powershell
python nextnano/demos/12_graded_interface_coupled_quantum_well_optimization/run_demo12.py
```

6. Package the latest compact report bundle (raw solver fields remain local):

```powershell
python nextnano/scripts/bundle_results.py --demo 12_graded_interface_coupled_quantum_well_optimization --include-plots
git status --short
```

Transfer the resulting ZIP back to the home laptop. Routine demo runs remain
under the gitignored `nextnano/results/demo_runs/**`; do not commit licenses or
raw solver output. Commit a curated compact bundle only if repository policy is
deliberately changed or the bundle is moved to an approved tracked location.

## What can and cannot be concluded yet

The home laptop establishes formulas, deck generation, geometry preservation,
state-tracking behavior on synthetic crossings, sensitivity/Pareto logic, and
report plumbing. It cannot establish that nextnano realizes the native grade,
that band edges and energies agree with the staircase approximation, that the
mesh is converged, or that grading improves χ(2) or robustness. Those claims
remain `not run` until real licensed results support them quantitatively.
