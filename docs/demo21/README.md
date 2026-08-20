# Demo 21 — Demo 20, Explained: an End-to-End Mathematical Walkthrough

Demo 21 **calculates nothing new**. It is a teaching layer over Demo 20:
an audit of what Demo 20 actually computes, a single file collecting every
equation, and a runnable trace that follows one case from its definition all
the way to the χ⁽²⁾ number Demo 20 already stored.

```
Demo 21 = Demo 20's own calculation, narrated number by number
Worked example = case 04, "Linear 1.0 nm"
```

Demo 20 is **not modified**. No file outside
`nextnano/demos/21_demo20_mathematical_walkthrough/` is changed by this demo,
and no Demo 20 result changes.

---

## 1. Files

```
21_demo20_mathematical_walkthrough/
├── DEMO20_MATH_WALKTHROUGH_LINEAR_1NM.md   READ FIRST — the full walkthrough
├── demo20_math_physics_reference.py        every equation in one file
├── trace_demo20_linear_1nm.py              the runnable numbered trace
├── trace_linear_1nm/                       checkpoint CSV/JSON (written by the trace)
├── tests/test_demo21.py                    55 licence-free tests
└── README.md
```

| Goal | Where to go |
|---|---|
| **Read first** | `DEMO20_MATH_WALKTHROUGH_LINEAR_1NM.md` |
| **Learn the maths** | `demo20_math_physics_reference.py` |
| **Run the numbers** | `python trace_demo20_linear_1nm.py` |

---

## 2. Commands

Everything here runs **without a nextnano++ licence**.

The full trace — 22 numbered steps, every intermediate value, ending in a
verification against the stored Demo 20 result:

```bash
python nextnano/demos/21_demo20_mathematical_walkthrough/trace_demo20_linear_1nm.py
```

A guided tour of the equation reference, including a self-check that every
educational reproduction agrees with production:

```bash
python nextnano/demos/21_demo20_mathematical_walkthrough/demo20_math_physics_reference.py
```

The tests:

```bash
python -m pytest nextnano/demos/21_demo20_mathematical_walkthrough/tests -q
```

Useful trace options:

| Flag | Effect |
|---|---|
| `--k-index N` | expose a different k point term-by-term (default 40, range 0–95) |
| `--all-k` | print all 96 k contributions instead of a representative set |
| `--outdir PATH` | write checkpoints somewhere else |
| `--no-files` | print only, write nothing |

---

## 3. What the trace prints

Every stage uses one fixed format:

```
INPUT       what went in (values, shapes, units)
FUNCTION    the production function, with file:line
EQUATION    the mathematics that function implements
OUTPUT      what came out (values, shapes, units)
MEANING     what it means physically
CHANGED     what is different because of this step
NEXT        what consumes this output
```

and is tagged with **who** does it:

| Tag | Meaning |
|---|---|
| **[A]** | user-defined physical input — a number you chose |
| **[B]** | deterministic Python transformation — geometry, grading, deck |
| **[C]** | nextnano++ physics — band structure, eigenstates |
| **[D]** | Python nonlinear-optical post-processing — matrix elements → χ⁽²⁾ |

The 22 steps:

| Step | Subject | Actor |
|---|---|---|
| 00 | what we are calculating, and why it is not zero | — |
| 01 | case definition | A |
| 02 | geometry → interface positions I1–I4 | B |
| 03 | grade windows | B |
| 04 | apply the linear grading → x_Al(z) | B |
| 05 | render the nextnano++ deck | B |
| 06 | what nextnano++ solves (black box) | C |
| 07 | eigenenergies back in Python — e1, e2, hh1, hh2 | C→D |
| 08 | what happens to the wavefunctions — case 04's own ψ(z) | D |
| 09 | overlap integrals O_nm | D |
| 10 | position matrix elements z^e, z^hh | D |
| 11 | the DFT / bulk Bloch quantity r_e,hh | external |
| 12 | transition energies at k = 0 | D |
| 13 | wavelength → photon energy | D |
| 14 | in-plane k grid and integration weights | D |
| 15 | transition energies disperse with k | D |
| 16 | one k point, all 16 terms | D |
| 17 | sum over all k | D |
| 18 | prefactor and unit conversion to pm/V | D |
| 19 | the whole spectrum χ⁽²⁾(λ) | D |
| 20 | select the value at 1550 nm | D |
| 21 | verification against the existing Demo 20 result | D |
| 22 | the causal chain, end to end | — |

---

## 4. Checkpoint files

Written to `trace_linear_1nm/`, numbered in transformation order:

| File | Contents |
|---|---|
| `01_inputs.json` | every configured input for case 04 |
| `02_geometry.csv` | I1–I4, positions, Al fractions either side |
| `03_grading_profile.csv` | x_Al(z), 601 deck points |
| `04_nextnano_input_summary.txt` | what nextnano++ receives + the complete deck |
| `05_subband_energies.csv` | E_e1, E_e2, E_hh1, E_hh2 |
| `06_case04_envelopes.csv` | case 04's own ψ(z), raw and normalized, plus the two integrands (see §6) |
| `07_matrix_elements.csv` | O, z^e, z^hh, r_e,hh — with who computed each |
| `08_transition_energies_zero_k.csv` | ΔE_nm(0) and hc/ΔE |
| `09_k_grid.csv` | k, dk, both conventions' weights, all 96 points |
| `10_transition_energies_vs_k.csv` | ΔE_nm(k), all 96 points |
| `11_triple_sum_terms_at_1550nm.csv` | all 16 terms with numerators and both denominators |
| `12_k_contributions.csv` | S(k_i), w_i, w_i·S_i, all 96 points |
| `13_chi2_spectrum.csv` | χ⁽²⁾(λ), both conventions, 401 points |
| `14_final_result.json` | the result and all five verification comparisons |

`trace_linear_1nm/` is a scratch output directory and is not tracked.

---

## 5. Nothing here overrides Demo 20

The reference module labels every callable:

| Label | Meaning |
|---|---|
| `# ACTUAL PRODUCTION FUNCTION` | Demo 20's own function, re-exported. This determines Demo 20's results. |
| `# EDUCATIONAL WRAPPER AROUND PRODUCTION FUNCTION` | calls production, adds explanation and extra intermediates |
| `# EDUCATIONAL REPRODUCTION OF THE EQUATION` | written out here for readability; **not** used by Demo 20 |

Every reproduction names the production implementation it mirrors, and
`demo20_math_physics_reference.self_check()` asserts they agree:

```
interface_positions                  max|diff| = 0.000e+00
linear_profile_at_I1                 max|diff| = 0.000e+00
k_grid_nodes                         max|diff| = 0.000e+00
k_grid_weights                       max|diff| = 0.000e+00
absolute_prefactor                   max|diff| = 7.105e-15   (1 ULP, re-association)
photon_energy_1550nm                 max|diff| = 0.000e+00
transition_energy_dE11_at_k40        max|diff| = 0.000e+00
triple_sum_unrolled_vs_direct        max|diff| = 0.000e+00
```

If a reproduction ever disagrees, the reproduction is wrong — the fix goes in
Demo 21, never in Demo 20.

---

## 6. Where the numbers come from

Demo 21 uses the same home-laptop path Demo 20 uses: the electron and hole
energies and the O / z matrices are read back out of Demo 19's master results
CSV, which is **real licensed nextnano++ output**. Only the χ⁽²⁾ postprocessing
is re-evaluated. Nothing is fabricated, mocked, or approximated.

**STEP 08 additionally re-runs the envelope → matrix-element step on case 04's
own wavefunctions**, from

```text
demo_results/demo20/data/case_04/optical/parsed/envelopes.csv
demo_results/demo20/data/case_04/optical/parsed/matrix_elements.json
```

both resolved against `REPO_ROOT`. It selects `z_nm, psi_e1, psi_e2, psi_hh1,
psi_hh2` **by header name** out of the 13 columns present, normalizes through
the production `BandStates`, reports ∫|ψ|² dz before and after and both
orthonormality errors, recomputes O / z^e / z^hh, and asserts all twelve
elements against the recorded `matrix_elements.json`.

That `case_04/optical/parsed/` subtree only exists where a licensed
`--physics` run wrote it. When it is absent STEP 08 says so and falls back to
Demo 11's `s1_ref` — **a different structure**, labelled as a fallback and used
nowhere else — so the mechanism can still be watched on genuine licensed
wavefunctions. χ⁽²⁾ is byte-identical either way: §12 and §13 take O, z^e and
z^hh from the results table, not from STEP 08.

---

## 7. Result

```text
Case              04 — "Linear 1.0 nm" (linear grading, W = 1.0 nm at I1–I4)
Target wavelength 1550 nm

chi^(2)(1550 nm)  18.047520507860781 pm/V    [raw    — k measure ∫d²k/(2π)²]
chi^(2)(1550 nm)  712.487551332532917 pm/V   [scaled — k measure g_s ∫d²k]
peak              45.106579094356526 pm/V at 1502.0 nm   [raw]
relative to the abrupt reference (case 00)   0.5815
```

Verification, from the trace's own STEP 21:

| Comparison | Relative difference | Tolerance |
|---|---:|---|
| traced raw vs stored Demo 20 `chi2_raw_1550_pm_per_V` | 0.000e+00 | `rtol = 0` |
| traced scaled vs stored Demo 20 `chi2_scaled_1550_pm_per_V` | 0.000e+00 | `rtol = 0` |
| traced peak vs stored Demo 20 `raw_peak_chi2_pm_per_V` | 0.000e+00 | `rtol = 1e-15` |
| traced raw vs Demo 19 recorded `chi2_1550_pm_per_V` | 1.969e-16 | `rtol = 1e-15` |
| independent hand reconstruction vs traced raw | 5.906e-16 | `rtol = 1e-14` |

The hand reconstruction is the one genuinely independent path: it rebuilds
χ⁽²⁾ from the 16 unrolled terms at each of 96 k points and never calls
`chi2_spectrum`.

---

## 8. Validation caveat, inherited from Demo 20

`solver_pass` and `physical_valid` are **separate concepts** and Demo 21
propagates both:

```
solver_pass    = True      the nextnano++ process exited 0
physical_valid = False     inherited Demo 11/14 physical QC did not pass
```

This holds for all 13 Demo 19 cases. The specific failing sub-check cannot be
identified from this checkout — it needs the raw licensed run tree and the
proprietary `database.nnp`. Treat every number here as a **controlled
comparison between grading cases**, not as validated absolute physics, and note
that neither k-space convention reproduces the published ≈2500 pm/V target.

---

## 9. One bug found, reported not fixed

`run_demo20.py --analysis-only --no-plots` ends in a `KeyError: 'skip_reasons'`
(`run_demo20.py:235` vs `s09_plots.py:366-368`). It fires **after** every table,
spectrum, QC file and report has been written correctly — no scientific output
is affected — but the terminal summary is lost and the exit code is non-zero.
The default path is unaffected: `--analysis-only` with plots on exits 0, and
re-running it reproduces the committed `demo20_master_results.csv` with **zero**
differing cells across all 13 cases and all 74 columns.

Left unchanged, per Demo 21's brief. Details in
`DEMO20_MATH_WALKTHROUGH_LINEAR_1NM.md` §28.

---

## 10. Relationship to the other demos

```
Demo 11   the parser chain and the shared chi2 module        (equations)
Demo 14   the licensed solver invocation, r_e,hh provenance  (constants)
Demo 19   the 13-case interface-grading study                (the licensed run)
Demo 20   Demo 19 reorganized + the (2π)² normalization experiment
Demo 21   ── explains Demo 20 ──                             (this demo)
```

Demo 21 imports Demo 20 and `_shared/chi2.py` read-only. It never calls
`s04_solver.enable_shared_imports()`, so it pulls in no other demo.
