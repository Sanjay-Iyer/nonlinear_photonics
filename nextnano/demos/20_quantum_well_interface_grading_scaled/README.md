# Demo 20 — Quantum-Well Interface Grading with a Configurable (2π)² k-Space Normalization

Demo 20 is **Demo 19, reorganized, plus one explicit normalization experiment**.
The structure, the 13 grading cases, the profile mathematics, the state counts,
the broadening, `N_z`, `r_e,hh`, `k_max`, the wavelength grid and the material
settings are all unchanged. Nothing about the physics model was retuned.

```
Demo 20 = organized Demo 19 + configurable (2π)² normalization experiment
(2π)² = 39.47841760435743
```

---

## 1. What Demo 20 investigates

The published target for this structure is **≈ 2500 pm/V**, and the calculation
returns **31.04 pm/V** for the abrupt reference. A missing or differently defined
2D k-space normalization would produce a discrepancy of exactly (2π)² ≈ 39.48, so
Demo 20 makes that factor switchable and measures what it does.

### The audit result — read this before enabling the switch

**Demo 19 already contains the 1/(2π)² normalization.** It is not missing.

`nextnano/demos/_shared/chi2.py::_k_grid` builds the in-plane weights as

```python
radial  = k / (2.0 * math.pi)        # <- the normalization, already reduced
weights = radial * trapezoidal_dk * spin_degeneracy
```

which is the isotropic reduction of ∫d²k/(2π)²:

```
(1/A) Σ_k f(k)  →  1/(2π)² ∫ d²k f(k)
                =  1/(2π)² · 2π ∫₀^kmax k f(k) dk     (angular integral, exact)
                =  1/(2π)  ∫₀^kmax k f(k) dk          ← what the code computes
```

Two independent confirmations, both machine-checked in `tests/test_demo20.py`:

| Check | Result |
|---|---|
| Weights sum vs closed form `g_s·k_max²/(4π)` | matches, relative 1.4e-16 |
| Independent Cartesian ∫dk_x dk_y/(2π)² over the disc (never uses isotropy) | matches |

**Therefore multiplying by (2π)² does not restore a missing factor — it cancels
an existing denominator**, switching the measure from

```
d2k_over_2pi_squared :  (1/A) Σ_k → ∫ d²k/(2π)²      w_i = g_s · k_i·dk_i / (2π)     [Demo 19]
bare_d2k             :        Σ_k → g_s · ∫ d²k       w_i = g_s · 2π·k_i·dk_i        [Demo 20 experiment]
```

Both leave χ² in pm/V — the k measure has units nm⁻² either way — so this is a
factor of exactly (2π)² in **magnitude**, not a change of units and not a
dimensional bug fix.

> **Enabling the factor does not prove that the scaled convention is physically
> correct.** It is an experimental normalization comparison until the source
> paper's own k-space measure is independently verified. Nothing in this demo
> labels `bare_d2k` as a correction.

The factor is applied **in the k measure** (`s06_chi2.k_grid`) — the one place the
normalization mathematically belongs — not as a post-hoc multiplier buried in an
empirical scale. Because the factor is k-independent, the two placements are
numerically identical; `test_scaling_placement_is_equivalent_to_post_multiplication`
verifies that rather than assuming it.

---

## 2. How Demo 20 differs from Demo 19

| | Demo 19 | Demo 20 |
|---|---|---|
| k-space convention | fixed `∫d²k/(2π)²` | switchable; **both always computed** |
| Values retained | one χ² per case | `chi2_raw_*`, `chi2_scaled_*`, `chi2_reported_*` |
| Architecture | 4 modules + cross-demo `sys.path` inserts at the top of the runner | 10 numbered stages, one config file, cross-demo imports isolated to `s04_solver` |
| Config | Demo 14's `demo.yaml`, deep-copied and patched at runtime | one `demo20_config.yaml` |
| Runnable without a licence | preflight only | preflight **and** full χ²/QC/plots/reports |
| Physics model | — | **identical** (byte-identical decks, exact χ² reproduction) |

Demo 19 itself is **not modified**. No file outside
`nextnano/demos/20_quantum_well_interface_grading_scaled/` was changed.

---

## 3. File architecture

Stages are numbered in execution order. The `s` prefix keeps them importable —
`import 01_cases` is a Python syntax error, so a bare numeric prefix would force
`importlib` gymnastics in every module.

```
20_quantum_well_interface_grading_scaled/
├── demo20_config.yaml          Layer 1  every setting, in one file
├── config20.py                 Layer 1  config load, CLI overrides, path resolution
├── s01_cases.py                Layer 1  the 13 frozen grading cases
├── s02_grading.py              Layer 2  geometry, profile maths, solver-free validation
├── s03_inputs.py               Layer 2  nextnano++ decks + imported DAT tables
├── graded_acqw20.in.j2         Layer 2  deck template (Demo 19's, header comment aside)
├── s04_solver.py               Layer 3  licensed solver interface — the ONLY cross-demo importer
├── s05_extract.py              Layer 4  solver data → one standard CaseStates type
├── s06_chi2.py                 Layer 5  THE PHYSICS + the k-space normalization
├── s07_analysis.py             Layer 5  drives both conventions over all 13 cases
├── s08_qc.py                   Layer 6  status separation, normalization audit, invariance gates
├── s09_plots.py                Layer 7  figures 01–10 (Demo 19's set) + 11–13 (new)
├── s10_report.py               Layer 8  CSV / JSON / Markdown
├── run_demo20.py                        CLI orchestrator
├── tests/test_demo20.py                 45 tests, all licence-free
└── README.md
```

You can read `s06_chi2.py` on its own to check the susceptibility mathematics. It
imports only `numpy` — no solver, no plotting, no I/O.

### Cross-demo dependencies

`s04_solver.py` is the only module that imports from another demo, and every
import is named with its reason in `SHARED_DEPENDENCIES`. It reuses
`demo_workflow` (machine config), `solver14` (the licensed invocation),
`demo16b` (post-solve output and composition readback) and `demo14`
(`analyse_real_trial`, the Demo 11 parser chain) — deliberately, so a Demo 20
solve is the *same* calculation as a Demo 19 solve rather than a similar one.
The home-laptop analysis path never calls `enable_shared_imports()`.

---

## 4. Turning the scaling ON and OFF

In `demo20_config.yaml`:

```yaml
chi2:
  apply_kspace_2pi_squared_scaling: false   # Demo 19 original convention
```

```yaml
chi2:
  apply_kspace_2pi_squared_scaling: true    # (2π)²-scaled experiment
```

Or per execution, overriding the YAML without editing it:

```bash
python nextnano/demos/20_quantum_well_interface_grading_scaled/run_demo20.py --analysis-only --kspace-scale off
```

```bash
python nextnano/demos/20_quantum_well_interface_grading_scaled/run_demo20.py --analysis-only --kspace-scale on
```

**Both conventions are computed and written to the output tables on every run.**
The switch only chooses which one carries the `reported` label and which one
populates Demo 19's own column names (`chi2_1550_pm_per_V`, `peak_chi2_pm_per_V`).
`chi2_raw_*` and `chi2_scaled_*` are byte-for-byte identical between an
`--kspace-scale off` run and an `--kspace-scale on` run.

---

## 5. Commands

Local checks and analysis (no licence needed):

```bash
python nextnano/demos/20_quantum_well_interface_grading_scaled/run_demo20.py --preflight --verbose
```

```bash
python nextnano/demos/20_quantum_well_interface_grading_scaled/run_demo20.py --analysis-only --kspace-scale off
```

```bash
python nextnano/demos/20_quantum_well_interface_grading_scaled/run_demo20.py --analysis-only --kspace-scale on
```

```bash
python -m pytest nextnano/demos/20_quantum_well_interface_grading_scaled/tests -q
```

Later, on the licensed work laptop — 13 real nextnano++ solves:

```bash
python nextnano/demos/20_quantum_well_interface_grading_scaled/run_demo20.py --physics --kspace-scale off --verbose
```

`--physics` runs the complete solver-free gate first and refuses to consume a
licence if any deck or grading profile fails. On a machine with no licensed
installation it exits with the reason instead of degrading to a placeholder.

Useful extras: `--master-table <path>` to analyse a different results CSV,
`--results-root <path>` to redirect output, `--no-plots` to skip figures,
`--config <path>` for an alternative YAML.

---

## 6. Running the analysis without a solver

`--analysis-only` needs the electron/hole energies and the O / z matrices. Those
come from `analysis.master_table`, which defaults to Demo 19's own results:

```yaml
analysis:
  source: master_table
  master_table: demo_results/demo19/tables/demo19_master_results.csv
```

That CSV's `E1_eV`, `E2_eV`, `HH1_eV`, `HH2_eV`, `O11..O22`, `z_e11..z_e22` and
`z_hh11..z_hh22` columns are **real licensed solver output**. Demo 20 re-runs only
the χ² postprocessing on top of them. This is why the whole physics/QC/plot chain
is testable at home, and it is verified rather than asserted:
`test_chi2_reproduces_demo19_recorded_value` recomputes χ²(1550) from those matrix
elements and compares it against the value Demo 19 recorded, for every case.

**Nothing is faked.** If the source table has no solver states — a pending
Demo 19 preflight table, for instance — those cases come back with
`states=None` and their recorded `failure_reason` intact.

---

## 7. Where results are written

```
demo_results/demo20/
├── tables/     master + presentation + scaling comparison + case tables + summary.md
├── plots/      figures 01–13
├── data/       per-case spectra (both conventions, side by side) and solver output
├── qc/         normalization audit (txt + json), QC report, preflight report
├── logs/       solver logs (licensed runs only)
├── inputs/     generated case.in and al_profile.dat per case
└── demo20_run_record.json
```

Figures 01–10 keep Demo 19's filenames so the two output directories can be
diffed. Figures 11–13 are new:

| Figure | Content |
|---|---|
| `11_raw_vs_scaled_chi2_1550.png` | both conventions per case, log axis, with the paper target |
| `12_scaling_ratio_by_case.png` | the ratio, on a ±0.1 % window around (2π)² |
| `13_reference_raw_vs_scaled_spectrum.png` | magnitude and normalized lineshape, reference case |

`03_abrupt_vs_graded_wavefunctions.png` needs per-state envelope data, which only
exists beside a raw licensed run. On the home path it is skipped and the skip is
reported — it is never drawn from something else.

---

## 8. Results

Reference case 00 (abrupt), |χ²| at 1550 nm:

| Quantity | Value |
|---|---|
| Demo 19 recorded | 31.036041396587407 pm/V |
| Demo 20, `off` (raw) | 31.036041396587414 pm/V |
| Relative difference | **2.3 × 10⁻¹⁶** |
| Demo 20, `on` (scaled) | 1225.2538030406026 pm/V |
| Ratio scaled / raw | 39.47841760435743 (exact) |
| Paper target | ≈ 2500 pm/V |
| Ratio to paper, raw | 0.0124 (98.8 % below) |
| Ratio to paper, scaled | 0.490 (51.0 % below) |
| **Residual after scaling** | **2.04×** |

Invariance gates, all passing across all 13 cases and 5213 wavelength points:

| Gate | Result |
|---|---|
| ratio = (2π)² everywhere | max deviation 2.1e-14 |
| peak wavelength unchanged | 0 nm shift |
| normalized lineshape unchanged | 5.6e-16 |
| case ranking unchanged | identical |
| grading trend unchanged | 3.3e-16 |

### The residual — a lead, not a result

The leftover **2.04×** is close to the documented `N_z` counting ambiguity, which
is a factor of exactly 2 (`period_density`, one coupled pair per 30 nm period, vs
`well_density`, its two individual wells — see `s06_chi2.n_z_for`). Combining both
gives ≈ 2450 pm/V, within 2 % of the published number.

That is recorded in `paper_comparison.residual_analysis` **as a lead only**. Two
independent convention changes that happen to multiply to roughly the published
value is not evidence that either is the paper's choice, and Demo 20 does not
fit to the target. Settling it needs the paper's own k-space measure *and* its own
`N_z` definition.

---

## 9. Physical-validation caveat

Demo 19's copied run records, for all 13 cases:

```
solver_pass    = True
physical_valid = False        reason: "Demo 11/14 physical QC did not pass"
```

Demo 20 keeps these as **separate concepts** and propagates both. A zero solver
return code means the process finished; it says nothing about whether the physics
is trustworthy.

The specific failed QC sub-check **cannot be identified from this checkout**: it
needs the raw licensed run tree and the proprietary `database.nnp`, neither of
which is present on this machine. That is reported as unknown rather than guessed.

`demo20_summary.md` and `qc/demo20_qc_report.json` carry an explicit per-level
verdict:

| Level | Status |
|---|---|
| code validated | yes — 45 local tests, including exact Demo 19 reproduction |
| numerics validated | yes — k measure matches closed form, grid converged, factor exact |
| solver validated | **no** — no licensed solve ran here |
| physical model validated | **no** — inherited physical QC did not pass |
| paper reproduction validated | **no** — neither convention reproduces the target |

Treat the numbers as a **controlled comparison between grading cases**, not as
validated absolute physics.
