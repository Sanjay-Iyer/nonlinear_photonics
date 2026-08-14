# Demo 17D — prefactor estimation ensemble sweep

Pure Python. **No solver, no licence, no network.** Reads Demo 17's saved
artifacts, compounds **ten declared multiplier combinations** across the
1400–1800 nm window for the abrupt and graded structures, and measures each one
against every published absolute value.

**Nothing here is fitted to a published number.** Demo 17c fits one scalar and
labels it; Demo 17D fits nothing and instead asks what each *hypothesis about
the prefactor* would imply if it were true.

```bash
python nextnano/demos/17d_prefactor_ensemble_sweep/run_demo17d.py
```

## The ensemble matrix

| ID | combination | N_z | perm | tensor | dipole | total | evidence |
|---|---|---:|---:|---:|---:|---:|---|
| 01 | Raw Baseline | 1.0 | 1.0 | 1.0 | 1.0 | **1.00×** | established |
| 02 | Conservative Active Density | 3.0 | 1.0 | 1.0 | 1.0 | **3.00×** | ~ reported |
| 03 | Standard SHG Permutation | 1.0 | 2.0 | 1.0 | 1.0 | **2.00×** | ~ reported |
| 04 | Density + Standard Permutation | 3.0 | 2.0 | 1.0 | 1.0 | **6.00×** | ~ reported |
| 05 | Density + Boyd Full Permutation | 3.0 | 3.0 | 1.0 | 1.0 | **9.00×** | ~ reported |
| 06 | Tensor Inversion Only | 1.0 | 1.0 | 2.8 | 1.0 | **2.80×** | ? speculative |
| 07 | Density + Tensor Inversion | 3.0 | 1.0 | 2.8 | 1.0 | **8.40×** | ? speculative |
| 08 | Full Permutation + Tensor Inversion | 1.0 | 3.0 | 2.8 | 1.0 | **8.40×** | ? speculative |
| 09 | Combined Standard | 3.0 | 2.0 | 2.8 | 1.0 | **16.80×** | ? speculative |
| 10 | Full Reconciliation Budget | 3.0 | 3.0 | 2.8 | 1.1 | **27.72×** | ! contradicted |

`evidence` is the **weakest** status among the factors a row actually raises
above 1.0, carried forward from Demo 17b:

| mark | status | meaning |
|---|---|---|
| | `established` | a cited source requires it |
| `~` | `reported` | Demo 17b computed it and declined to promote it |
| `?` | `speculative` | no source in this repository establishes it |
| `!` | `contradicted` | a measurement in this repository points the other way |

Each declared `total` is **checked against the product** of its four factors at
load time, and a factor value the table does not define is refused rather than
silently applied.

## Result

Demo 17 raw: `case_02` (abrupt) **84.70 pm/V @ 1550 nm**, peak **145.78 pm/V @
1520 nm**. `case_01` (graded) **53.83** and **106.09 @ 1508 nm**.

| ID | combination | mult | abrupt @1550 | abrupt peak | graded peak | RMS err |
|---|---|---:|---:|---:|---:|---:|
| 01 | Raw Baseline | 1.00× | 84.7 | 145.8 | 106.1 | 92.5 % |
| 02 | Conservative Active Density | 3.00× | 254.1 | 437.3 | 318.3 | 77.6 % |
| 03 | Standard SHG Permutation | 2.00× | 169.4 | 291.6 | 212.2 | 85.1 % |
| 04 | Density + Standard Permutation | 6.00× | 508.2 | 874.7 | 636.5 | 55.5 % |
| 05 | Density + Boyd Full Permutation | 9.00× | 762.3 | 1312.0 | **954.8** | 34.1 % |
| 06 | Tensor Inversion Only | 2.80× | 237.2 | 408.2 | 297.0 | 79.1 % |
| 07 | Density + Tensor Inversion | 8.40× | 711.5 | 1224.6 | 891.1 | 38.2 % |
| 08 | Full Permutation + Tensor Inversion | 8.40× | 711.5 | 1224.6 | 891.1 | 38.2 % |
| 09 | **Combined Standard** | 16.80× | 1423.0 | **2449.1** | 1782.3 | **31.3 %** |
| 10 | Full Reconciliation Budget | 27.72× | 2347.9 | 4041.1 | 2940.7 | 111.3 % |

Against targets 2340 pm/V (abrupt peak), 1150 pm/V (abrupt @1550) and 1200 pm/V
(graded peak):

| published target | value | closest combo | got | error |
|---|---:|---|---:|---:|
| abrupt, spectral peak | 2340 | 09 Combined Standard | 2449.1 | **+4.7 %** |
| abrupt, at 1550 nm | 1150 | 09 Combined Standard | 1423.0 | +23.7 % |
| graded, spectral peak | 1200 | 05 Density + Boyd Full Perm. | 954.8 | −20.4 % |

**Combo 09 (16.80×) is closest overall at 31.3 % RMS** — outside the 15 % match
threshold, so the run exits 1. It gets there with the *contradicted* dipole tweak
left at 1.0×, but still rests on the speculative 2.8× tensor factor.

**The three published numbers do not agree on one combination.** That
disagreement is the result, not a tie to be broken, and the next section is why.

## The part no multiplier in this ensemble can fix

Every combination here is a **scalar**, and a scalar cannot change a ratio.
Wherever the paper pins two quantities on the same structure, their ratio is a
fixed prediction of Demo 17's converged lineshape, and the whole sweep is
powerless over it:

| case | ours | published | mismatch | floor on both |
|---|---:|---:|---:|---:|
| case_02 (peak / 1550 nm) | 1.721 | 2.035 | **−15.4 %** | **8.0 %** |

"Floor on both" is the error a *perfectly chosen* scalar still leaves on each
quantity after splitting the difference. No combination in this ensemble beats
it, and no ensemble of pure scalars ever could. **About 8 % of the residual is
not a scale question at all** — it is lineshape, and closing it needs different
physics (broadening, the in-plane mass pair, or a resonance the two-state
truncation omits), not a bigger prefactor.

## Two readings of the paper, two different winners

`demo17c.yaml` reads the published 2340 pm/V as a value **at 1550 nm** and
anchors its fitted K there. This demo's default profile reads it as the
**spectral peak**, with ~1150 pm/V at 1550 nm. Both readings are run:

```bash
python nextnano/demos/17d_prefactor_ensemble_sweep/run_demo17d.py --targets-profile demo17c
```

| profile | targets | closest | RMS | inside 15 %? |
|---|---|---|---:|---|
| `paper` (default) | 2340 peak / 1150 @1550 / 1200 graded peak | **09** at 16.80× | 31.3 % | no |
| `demo17c` | 2340 @1550 / 4000 peak / 1200 graded @1550 | **10** at 27.72× | 14.1 % | yes |

The two readings cannot both hold — that is exactly the 1.72-vs-2.03 contrast
above — and **which one is right changes which hypothesis wins**. Reporting one
winner without the other would be reporting an artifact of the reading.

## What this demo does not show

1. **It resolves the product, never the factors.** Combos 07 and 08 both total
   8.40× by different routes and produce identical spectra. They are in the
   ensemble as a control on exactly this point, and the figure draws the
   coincidence as a coincidence (wide translucent band under a dashed line)
   rather than letting one paint over the other.

2. **Combo 10 was constructed from the answer.** Its factors multiply to 27.72
   against Demo 17's measured residual of 27.63 — 0.3 % apart. Landing on
   2340 pm/V is arithmetic, the same arithmetic as Demo 17c's fitted K, and is
   not evidence.

3. **Only the baselines are established.** The 2.8× tensor inversion has no
   source in this repository — no audit here has measured a tensor-inversion
   ratio at all, and its value looks reverse-engineered from the gap. The 1.1×
   dipole tweak runs *against* Demo 17b's Kane measurement, which put
   `r_e,hh` at 0.736 nm versus the published 0.751 — a multiplier of **0.96**,
   slightly below one, not 1.1.

## Where the curves come from

The two numbers this demo **reports** per case — χ⁽²⁾ at 1550 nm, and the
spectral peak — are read straight out of Demo 17's stored scalars and
multiplied. They are exact, and the table is complete even for a hand-off that
carries no spectrum at all.

The 1400–1800 nm **curve** is only drawn, and comes from the best tier available:

| tier | provenance | what it is |
|---|---|---|
| 1 | `demo17_spectrum_csv` | Demo 17's own sampled spectrum, if the hand-off has one |
| 2 | `eq2_rebuilt_from_recorded_matrix_elements` | Eq. 2 re-evaluated from the per-case matrix elements in `physics_summary.json` |
| 3 | `stored_anchors_only` | neither available — the figure falls back to markers and says so on the axes |

The current `demo_results/demo_17` hand-off has no spectrum CSV, so it runs at
tier 2. Demo 17 recorded ⟨e1\|hh1⟩ and ⟨e2\|hh2⟩ but **not** the two cross
overlaps ⟨e1\|hh2⟩ and ⟨e2\|hh1⟩, so tier 2 has to say what it does about them:

| `cross_overlap_model` | case_02 @1550 | case_02 peak | case_01 @1550 | case_01 peak |
|---|---:|---:|---:|---:|
| `zero` (nothing fitted anywhere) | −0.13 % | −1.11 % | +2.98 % | −0.17 % |
| `fit_to_stored_anchors` (default) | +0.02 % | −0.03 % | +0.01 % | −0.01 % |

The fit's target is **Demo 17's own stored output**, never a published number:
two unknowns against three constraints (value at 1550 nm, peak height, peak
position), so it is over-determined and the residual above is a real check.
`--cross-overlaps zero` turns it off. **Either way no reported number moves** —
only the drawn line does.

Two checks run on the rebuilt matrices every time:

- **origin independence** — Demo 17's diagonal position elements are ~38 nm
  because its z origin sits at the domain edge, and Eq. 2's conduction and
  valence terms must cancel that exactly. Shifting the origin 100 nm and
  re-evaluating agrees to **~1e-14**.
- **kernel agreement** — the vectorised energy-form sum used here is checked
  against Demo 17b's independently written *angular-frequency* kernel (which
  keeps ħ² explicit in the prefactor) at three wavelengths per case. They agree
  to **~1e-14**.

## Files

| file | what it is |
|---|---|
| `run_demo17d.py` | CLI and master reporter |
| `ensemble17d.py` | the sweep engine |
| `demo17d.yaml` | the ten combinations, the factor table, the targets |

Reuses `_shared/plots.py` and `17b_prefactor_scale_audit/prefactor_audit17b.py`
(`resolve_results_dir`, `load_case`, `chi2_from_matrices`,
`production_prefactor_pm_per_V`).

## Artifacts

Written to `demo_results/demo_17d/`:

| artifact | contents |
|---|---|
| `estimation_ensemble_summary.csv` | `Combo_ID, Combo_Name, Multiplier, Peak_chi2_pmV, Peak_Wavelength_nm, chi2_1550nm_pmV, Target_Error_Percent`, then the factor signature, the evidence status, the graded case's three columns, the aggregate, and one error column per target |
| `chi2_10_estimation_combos_spectrum.png` | all ten curves per case — abrupt on top with the 2340 pm/V band and the 1150 pm/V line, graded below with its 1200 pm/V band; 1550 nm marked with a per-combo data point |
| `estimation_ensemble_report.json` | every combination with its factors and rationales, the full ranking, the shape-versus-scale analysis, the rebuild fidelity and both correctness checks |

The CSV's required columns are the **primary (abrupt) case**; the graded case
gets its own prefixed columns rather than extra rows, so one row stays one
combination.

## Options

```
--targets-profile paper|demo17c   which reading of the published values to score against
--cross-overlaps zero|fit_to_stored_anchors   how the rebuilt lineshape handles the
                                              two unrecorded overlaps (drawn curve only)
--results-dir DIR                 another Demo 17 hand-off or a raw run tree
--out DIR                         output directory
--no-plot                         skip the figure
```

**Exit status** is 0 when at least one combination lands inside the configured
match threshold and 1 when none does. A miss is a result, so it is reported
either way rather than suppressed — the default profile exits 1.
