# Demo 17 — paper absolute χ⁽²⁾ reproduction, corrected

Demo 16E's **ten structures, unchanged**, re-solved with three named corrections
to the absolute scale, reported against the paper's **2340 pm/V** ideal-abrupt
value (arXiv:2602.23246v1 §3.1).

Holding the structures fixed is the design. The per-case ratio Demo 17 / Demo
16E then measures *the corrections* rather than ten different geometries, and
`cases17.assert_matches_baseline` makes that an error rather than a footnote if
any geometry drifts.

## The three corrections

| | changed | from → to | worth | why it is allowed to change |
|---|---|---|---|---|
| **A** | `chi2.nz_mode` | `period_density` → `well_density`<br>N_z 3.333e7 → **6.667e7 m⁻¹** | **×2, exactly** | Ramesh 2023 Eq. 1: "N_z is the number of quantum **wells** per unit length". Fig. 1a puts **two** GaAs wells (7.1 nm, 2.9 nm) in each 30 nm period. χ⁽²⁾ is linear in N_z. |
| **B** | `k_parallel.zone_edge_convention` | `legacy_pi_over_a` → `crystallographic_two_pi_over_a`<br>k_max 0.5557 → **1.1114 nm⁻¹** | measured (~×1.36) | GaAs is zincblende (FCC): X = (1,0,0) in units of 2π/a, so the Γ→X zone edge is **2π/a**. π/a is the *simple-cubic* edge and does not describe this lattice. The paper's stated 1/10 of the zone is unchanged — only *which* edge it is a tenth of. |
| **C** | `geometry.domain_padding_nm`<br>`geometry.quantum_region_padding_nm` | 20.0 → **35.0 nm**<br>2.0 → **30.0 nm** | **unmeasured before this demo** | `boundary{ x = dirichlet }` puts ψ = 0 at the quantum-region edge, so at 2.0 nm padding the hard wall quantizes the states as much as the wells do. 16E recorded 7.3 % of E2 outside the wells, boundary probabilities up to 3.1e-3 against a 1.0e-3 constraint, and `physical_qc_valid = False` on **all ten** cases. |

**Nothing is fitted.** There is no `absolute_scale_factor`. `r_e_hh = 0.751 nm`,
Γ = 5 meV, the 0.10 zone fraction and the two-states-per-band truncation are
published values and all of them stay.

### Correction C is not "18.2 → 35 nm"

`period_barrier_nm: 18.2` is **not** the simulation cladding — it is the AlGaAs
barrier of the *physical* 30 nm period (18.2 + 7.1 + 1.8 + 2.9), and it is what
correction A counts wells inside. Changing it would contradict A, so it stays at
the paper value. The numbers correction C actually moves are `domain_padding_nm`
(the flat AlGaAs slab the renderer puts on each side — it was **20.0** nm, not
18.2) and `quantum_region_padding_nm` (where the Dirichlet wall sits — **2.0**
nm, and the load-bearing one).

The rendered deck, verified by preflight:

```
domain          0.0 → 81.8 nm      (35.0 + 11.8 + 35.0)
active region  35.0 → 46.8 nm
quantum region  5.0 → 76.8 nm      Dirichlet walls, 30 nm clear of the wells
```

### How correction B reaches Eq. 2 without editing shared code

`chi2.Chi2Settings.k_max_per_nm` hardcodes the π/a edge, and that module is
shared with Demos 11, 13, 14 and 16B–16E — Demo 17 does not get to move their
results. The correct radius is therefore requested through the only knob that
reaches it:

```
fraction_of_bz × (π/a)  ==  fraction_of_brillouin_zone_physical × (2π/a)
0.20            × (π/a)  ==  0.10                                × (2π/a)
```

So `fraction_of_bz: 0.20` is a *fraction of the legacy π/a edge*, not a physical
claim; the physical statement is the two keys beside it.
`demo17.verify_k_space_convention` recomputes the identity and raises if the
three numbers ever disagree, preflight asserts the resulting k_max equals
0.10 × 2π/a to 1e-12, **and** cross-checks it against `physics14.k_max_per_nm`,
which implements both conventions explicitly. A preflight check also confirms
the guard rejects a revert to `0.10` — a check that cannot fail is not one.

## How each correction is measured

A and B are post-processing conventions: they can be switched on and off on one
set of solved wavefunctions. C changes the deck, so it only exists as a
difference between two solves. That splits the total cleanly:

```
chi2_17_corrected      chi2_17_legacy_settings       chi2_17_corrected
-----------------  =   -----------------------   ×   -----------------------
chi2_16E_recorded      chi2_16E_recorded              chi2_17_legacy_settings
                                 |                              |
                                 C                            A × B
```

`demo17.correction_ablation` evaluates three rungs on *this run's own envelopes*
— no re-solve, so no structural difference can leak into the ratio — and asserts
factor A comes out at exactly 2.0, since N_z enters Eq. 2 linearly and anything
else means the settings never reached the evaluator. `versus_baseline` supplies
C from the committed Demo 16E summary; with no baseline it reports "unavailable"
rather than guessing, because an absent baseline is not a baseline of 1.

## Expected outcome, stated in advance

**This is not expected to reach 2340 pm/V, and it is not supposed to.**

Demo 16F already measured A and B independently on 16E's licensed `case_02`
envelopes, with a second implementation of Eq. 2 built on `kspace16f`/`eq16f`
rather than on the shared `chi2` module:

| rung | χ⁽²⁾(1550) pm/V |
|---|---:|
| legacy | 30.99 |
| `paper_Nz` (A) | 61.99 — exactly ×2 |
| `paper_Nz_and_zone` (A+B) | 84.04 — ×1.356 from the zone edge |

Against 2340 pm/V that leaves **27.8×** for correction C to supply, which a
cladding change is very unlikely to deliver: 16E's boundary probabilities were
~3e-3, so the truncation is real but not catastrophic. What Demo 17 produces is
the **first measurement of C on solved structures**, and a per-case budget that
says how much of the remaining gap is domain truncation and how much is not.

Two open factors are recorded and **never applied**: the factor of 3 between the
paper's Eq. 1 and Eq. 2 as printed, and the heavy-hole m_j multiplicity the paper
does not state. Even granting both (3 × 2 = 6) the gap would not close, so
neither is a hidden answer.

## What must not happen

* No `absolute_scale_factor`. Fitting one answers the question by assuming it.
* `r_e_hh_nm = 0.751` stays — independent basis (Ramesh 2023 APL, VASP/HSE06),
  corroborated by the GaAs Kane value r_cv = ħp_cv/(m₀E_g) = 0.738 nm.
* Γ = 5 meV, two states per band and the 0.10 zone fraction stay: the paper
  states all three in Methods §5.1.
* The ten structures stay Demo 16E's. `assert_matches_baseline` enforces it.

## Files

| file | what it owns |
|---|---|
| `demo.yaml` | the three corrections, and every convention they touch |
| `graded_acqw17.in.j2` | the deck; identical grammar to Demo 14's, wider box |
| `cases17.py` | the ten fixed structures + the baseline-identity check |
| `demo17.py` | corrections, verification guards, ablation, verdicts |
| `preflight17.py` | 20 solver-free checks, 6 of them on the corrections |
| `run_demo17.py` | CLI, run tree, tables, figures |
| `validation_cases.yaml` | the frozen case list (`--write-cases` regenerates) |

Everything structural is reused, not copied: `demo16e.render_blocks` for the
three deck representations, `demo16e.run_case` for the parser and
realized-composition gates, `demo16b.solve_case` for the licensed solve,
`demo11.analyse_case` through `demo14.analyse_real_trial` for Eq. 2, and
`plots16e` for the figures. The one edit to Demo 16E is a `build=` parameter on
`run_case`, backward compatible and defaulted, mirroring the injection point
`demo16b.solve_case` already had.

## Commands

Solver-free, runs anywhere:

```bash
python nextnano/demos/17_paper_chi2_reproduction_corrected/run_demo17.py --preflight
```

Print the three corrections and exit:

```bash
python nextnano/demos/17_paper_chi2_reproduction_corrected/run_demo17.py --corrections
```

Parse all ten decks (needs any nextnano++ build, free included):

```bash
python nextnano/demos/17_paper_chi2_reproduction_corrected/run_demo17.py --syntax
```

The licensed run — ten solves, gates, ablation, correction budget, paper
comparison:

```bash
python nextnano/demos/17_paper_chi2_reproduction_corrected/run_demo17.py --physics --verbose
```

Rebuild every table and figure from an existing run, no solver:

```bash
python nextnano/demos/17_paper_chi2_reproduction_corrected/run_demo17.py --analyze-existing <RUN_DIR>
```
