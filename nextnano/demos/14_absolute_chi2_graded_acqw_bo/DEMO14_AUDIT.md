# Demo 14 — pre-implementation audit

_Spec §0 (repository audit) and the verifiable part of §1 (documentation audit).
Written before any Demo 14 implementation. No licensed solver was run. No Demo 13
file was modified._

---

## Headline: the spec's central premise needs one revision

> "The purpose of Demo 14 is to advance Demo 13 from a relative arbitrary-unit
> χ(2) optimization to a physically normalized absolute second-order nonlinear
> susceptibility in SI units."

**The absolute model already exists and is already tested.** It is not a thing to
be built; it is a thing to be *unblocked*. `nextnano/demos/_shared/chi2.py`
(966 lines) implements the Ramesh Eq. 2 density-matrix model with three modes —
`relative`, `absolute`, `calibrated` — selected by `Chi2Settings.mode`.

`mode="absolute"` already produces pm/V through this prefactor
([chi2.py:650](../_shared/chi2.py:650)):

```
chi2 = N_z e^3 r_e_hh^2 / (6 eps0) * SUM   ->  m/V, then *1e12 -> pm/V
```

It refuses to run without the two quantities the paper does not publish, by
design ([chi2.py:298](../_shared/chi2.py:298)):

```
absolute mode needs r_e_hh_nm and n_wells_per_metre, and the paper publishes
neither. Supply them from a documented source, or use mode='relative' ... or
mode='calibrated' (one fitted scale factor).
```

So Demo 14's real scientific task is narrower and sharper than the spec assumes:

> **Source, justify, and validate two physical constants — `r_e_hh_nm` (§4) and
> `n_wells_per_metre` (§8) — then flip `metric.mode` to `absolute`.**

Everything else in §3, §5, §6, §7 is already implemented and under test.

---

## §0.3 — where each thing the spec asks about actually lives

| Spec asks | Location | Status |
|---|---|---|
| relative χ(2) calculation | [`_shared/chi2.py:474`](../_shared/chi2.py:474) `chi2_spectrum` | Full Eq. 2 triple sum, conduction + valence terms |
| what equation | Ramesh Eq. 2, SHG (ω₁=ω₂), two-photon and one-photon denominators | Documented in the docstring |
| wavefunction normalization | `BandStates.__post_init__`, `gram_matrix`, `orthonormality_error` | Refuses non-orthonormal bases above 1e-3 |
| state tracking | `tracking11.py`, `tracking13.py`, `anchor13.py` | Overlap-first, energy-continuity secondary |
| intersubband z matrix elements | `position_matrix` ([chi2.py:220](../_shared/chi2.py:220)) | In nm; `<e_n\|z\|e_l>` and `<hh_m\|z\|hh_l>` |
| origin independence | `origin_independence` ([chi2.py:830](../_shared/chi2.py:830)) | 100 nm shift, relative + absolute residual |
| grading rendering | `grading13.py`, `demo12.py:271`, `graded_acqw_bo.in.j2` | `ternary_linear` native; everything else = 16-sublayer `ternary_constant` staircase |
| reusable plots | `plots13.py` (54 kB, 47 figures) | Substantial reuse available |
| **k∥ integration** | **`_k_grid` ([chi2.py:432](../_shared/chi2.py:432)), `Chi2Settings.k_max_per_nm`** | **Already implemented** |

### §6 (k∥) is already done

The spec says "Demo 14 must not use only k_parallel = 0". Demo 13 never did.
`demo.yaml` already carries:

```yaml
k_parallel_fraction_of_bz: 0.10     # the paper's one-tenth of the zone
k_parallel_points: 96
lattice_constant_nm: 0.565325       # zone edge taken as pi/a
electron_mass_m0: 0.067
heavy_hole_inplane_mass_m0: 0.112
spin_degeneracy: 2
```

with parabolic in-plane dispersion at the reduced mass, and the assumption set
recorded in every artifact via `chi2.ASSUMPTIONS`. What is genuinely **missing**
is the §6 convergence *reporting*: there is no
`k_parallel_integration_converged` / `k_parallel_relative_error` output and no
cutoff-sweep test. That is a real gap, but a small one.

### §7 (units) is already resolved

The spec asks us to choose formulation A (angular frequency) or B (energy) and
derive the prefactor. **B is already chosen**, and the reason is documented at
[chi2.py:624](../_shared/chi2.py:624): the paper's ħ² cancels against the two
frequency denominators once those are written in energy rather than angular
frequency. Γ = 5 meV enters directly as an energy — exactly the eV/rad·s
confusion the spec warns about, already avoided.

---

## §16 validation targets already exist, with provenance

`11_paper_validation_interband_chi2_acqw/paper_targets.yaml` already holds every
benchmark §16 lists, each tagged `structural` / `spectral` / `simulated` /
`measured` / `reference` / `qualitative` and cited to a paper section:

| Quantity | Value | kind |
|---|---|---|
| ideal abrupt χ(2) @1550 | 2340 pm/V | simulated |
| EDS Al-profile χ(2) | 1200 pm/V | simulated |
| EDS Ga-profile χ(2) | 1363 pm/V | simulated |
| 4-period measured | 2750 pm/V | measured |
| 80-period measured | 1730 pm/V | measured |
| growth-interrupted | 1345 pm/V | measured |
| bulk GaAs | 377 pm/V | reference |
| simulated resonance | 1520 nm | spectral |
| measured resonance | 1560 nm | spectral |

These reconcile with the numbers in the spec (ideal "a few nm/V" = 2.34 nm/V;
graded "~1.2–1.4 nm/V" = 1200–1363 pm/V; best measured 2750 pm/V). The file
already separates `measured` from `simulated` and states that Demo 11 does not
attempt to reproduce the measured values — which is precisely the §9 distinction
the spec asks for.

**The §2 publication-inconsistency check has already been done and found one.**
`paper_targets.yaml` records that Fig. 1a's caption and the layer arithmetic both
give a 30 nm period (10 + 1.8 + 18.2), while the Section 2.2 body text says
"Each period is 20 nm" in the same sentence. It is treated as a typo — and the
file already flags *why it matters*: N_z sets the absolute χ(2) scale.

A `missing_for_absolute_scale:` block already names all four gaps: `r_e_hh_nm`,
`n_wells_per_metre`, `k_parallel_quadrature`, `full_input_deck`. On N_z it
already states the §8 ambiguity precisely:

> Ambiguous even given the period: 1/(30 nm) counting coupled-well pairs, or
> 2/(30 nm) counting individual wells.

Both source papers are present in the repo root (`2602.23246v1.pdf`;
`Interband second-order nonlinear optical susceptibility of asymmetric coupled
quantum wells.pdf`), so §8's "if the two papers differ, document both" is
actionable.

Existing tests already lock this down: `test_absolute_mode_refuses_without_the_unpublished_inputs`,
`test_absolute_scale_is_linear_in_Nz_and_quadratic_in_r`,
`test_relative_mode_never_claims_pm_per_V`.

---

## §10 — nextnano++ grading: what I verified, and what I could not

Two documentation links in the brief point at the **wrong solver**. The NEGF link
is nextnano.NEGF; reference [2] (`nextnano.com/nextnano3/input_parser/keywords/alloy-function.htm`)
is legacy **nextnano³**. Demo 13 drives **nextnano++**, a third input language.
So rather than trust either page, I queried the authoritative grammar for the
exact installed build — `keywords_nnp.xml`, nextnano++ 3.0.0 — and ran probe
decks through the parser.

### Alloy keywords that exist in nextnano++ 3.0.0

```
ternary_constant   ternary_linear   ternary_import
ternary_pyramid    ternary_trumpet  ternary_zb / ternary_wz
```

plus a top-level `import{}` block offering `file{ filename format=AVS|DAT }` and
`analytic_function{ function = "..." }`.

### Findings

1. **There is no Fermi-function alloy keyword in nextnano++.** The interdiffusion
   `Fermi-function` the brief describes belongs to nextnano³'s alloy-function
   syntax. In nextnano++, a Fermi/sigmoid profile must go through
   `ternary_import` or `analytic_function` exactly like erf and cosine. This does
   not block anything — but §10's "use Nextnano's documented Fermi-function
   interface profile when supported" is **not supported here**, and should be
   dropped rather than searched for.

2. **`ternary_import` + `import{file{}}` parses cleanly.** Verified:

   ```
   import{ file{ name="al_profile" filename="x_al.dat" format=DAT
                 number_of_dimensions=1 }
           output_imports{} }
   structure{ region{ everywhere{}
       ternary_import{ name="Al(x)Ga(1-x)As" import_from="al_profile" } } }
   ```
   → `*** PARSING COMPLETED ***`

   This is the §10/§11 route for erf, cosine and Fermi, and it removes the
   16-sublayer staircase. Note `output_imports{}` belongs inside `import{}`, not
   `structure{}` (the parser rejects the latter).

3. **The free build cannot execute imports.** `--structure` gets past the grammar
   and then stops:

   > `ERROR: This version of nextnano++ does not allow importing files or
   > analytical functions.`

   **Consequence for the plan:** the home laptop can validate *syntax* of an
   imported-profile deck but can never confirm the profile is *realized*
   correctly. §11's "always calculate the realized width from the final
   mesh-sampled x_Al(z)" and §12's realized-geometry diagnostics therefore
   require a **licensed smoke run** before they can be trusted — this is new
   licensed work that the spec's execution order does not currently budget for.

4. **`analytic_function` with `exp` and with `erf` both parse — but this proves
   nothing.** I tested a deliberately meaningless function string
   (`totally_not_a_function(x)+zzz(3)`) and it *also* parsed. `--parse` does not
   validate function-string contents. So whether nextnano++ actually implements
   `erf` in its expression language is **unverified**, and can only be settled on
   the licensed machine. Do not let a passing `--parse` be read as support.

5. The existing deck already requests `output_alloy_composition` and
   `dipole_moment_matrix_elements{ polarization Gamma HH }`, so §12's realized
   profile and §5's dipole cross-check both already have a data source.

---

## §10A–10E addendum — findings against the grading brief

### §10A growth coordinate: it is `x`, confirmed two ways

`ternary_linear` carries `alloy_x` plus `x`/`y`/`z` real vectors. The repo's 1D
decks declare `simulate1D{}` with `grid{ xgrid{} }`, and the validated Demo 13
template already uses `ternary_linear{ alloy_x=[a,b] x=[z0,z1] }`. Growth
coordinate = **x**. Established from the grammar and an existing validated input,
not inferred from an example.

### §10A "do not invent ternary_fermi/erf/cosine" — confirmed, they do not exist

The complete ternary keyword set in nextnano++ 3.0.0 is `ternary_constant`,
`ternary_linear`, `ternary_import`, `ternary_pyramid`, `ternary_trumpet`,
`ternary_zb`, `ternary_wz`. There is no Fermi, erf or cosine alloy keyword. The
`ternary_import` route the brief specifies is therefore the only one available
for all three, which matches §10C.

### §10E native-vs-import equivalence: agreed, and it is the missing budget line

§10E's A/B test (same linear well via `ternary_linear` and via a high-resolution
`ternary_import`, compared on band edges, energies, wavefunctions, matrix
elements and χ(2)) is the right gate. It is also **licensed-only work**: the free
home build parses import decks but refuses to execute them
(`does not allow importing files or analytical functions`). §10E cannot be run
here at all, and must be added to the licensed budget before any Fermi/erf/cosine
trial.

### §10B: the 10–90 definition is undefined over ~19% of the beta search space

§10B pins 10% and 90% to the *nominal* transition — x_Al = 0.055 and 0.495 for a
0 ↔ 0.55 interface. But §12 and §13A deliberately allow the two graded interfaces
to **overlap** at thin barriers, and an overlapped barrier never reaches 0.55.

Modelling an interdiffused interface as a box convolved with a Gaussian (which
makes the erf profile exact), the barrier peak is
`x_peak = 0.55 * erf(t / (2*sigma*sqrt2))`, with `sigma = w_10_90 / (2*sqrt2*erfinv(0.8))`.
Sampling 20 000 points uniformly from the §13 beta ranges (barrier 0.85–2.50 nm,
each width 0.40–1.40 nm):

| | |
|---|---|
| peak x_Al, min / median / max | 0.317 / 0.541 / 0.550 |
| reaches x_Al = 0.495 | **80.6%** |
| **never reaches 0.495** | **19.4%** |

| barrier | width 0.4 | width 0.9 | width 1.4 |
|---|---|---|---|
| 0.85 nm | 0.546 | **0.426** | **0.310** |
| 1.00 nm | 0.549 | **0.465** | **0.352** |
| 1.40 nm | 0.550 | 0.525 | **0.440** |
| 1.80 nm | 0.550 | 0.544 | 0.495 |
| 2.50 nm | 0.550 | 0.550 | 0.538 |

Bold = the profile never crosses 0.495, so a nominal-referenced
`realized_grading_width_10_90_nm` **has no value to measure**.

Two things make this matter more than a bookkeeping detail:

1. **It concentrates exactly where the paper puts the optimum.** The brief keeps
   the 0.85 nm floor because "the paper says the expected optimum is around
   ~1 nm". At 0.85–1.0 nm with realistic ≥0.9 nm grading, peak Al is 0.43–0.47 —
   the metric is undefined across the most scientifically interesting region.
2. **It would reintroduce the failure §13A exists to abolish.** §13A's success
   criterion is that `subresolution_grade`-style rejection becomes impossible by
   construction. The *geometry* does stay perfectly bounded and well defined —
   nothing needs rejecting — but §10E requires "realized 10-90 widths are
   measured correctly", and an unmeasurable width would fail that check on ~1 in 5
   designs. The rejection would come back under a new name.

**Recommended fix — reference the realized peak, and record both.** Measure the
10–90 width against the profile's own achieved maximum
(`0.10 * realized_peak_al_fraction` to `0.90 * realized_peak_al_fraction`), which
is always defined and is what an experimentalist reading a STEM/EDS line scan
would measure anyway. Keep the nominal-referenced value beside it as a separate,
explicitly nullable field, because the two answer different questions:

```
requested_grading_width_10_90_nm          # what the optimizer asked for, vs nominal 0.55
realized_grading_width_10_90_nm           # vs realized peak -- ALWAYS defined
realized_grading_width_10_90_nominal_nm   # vs 0.055/0.495 -- null when never reached
realized_peak_al_fraction                 # already required by 10A/12
grading_interfaces_overlap                # already required by 12/13A
```

Reporting only the peak-referenced number would hide that a design never became
AlGaAs; reporting only the nominal one throws away a fifth of the space. Both,
with the null made explicit, is the honest option — and it keeps §13A's
"feasible by construction" promise intact.

---

## Demo 13 Stage 5 (§0 and §17): confirmed NOT run

The spec says not to assume. Checked:

- no `demo13_stage5_v3_validation` directory exists;
- no `nextnano/results/transfer/` directory exists;
- no file under `nextnano/` is newer than 2026-08-03; last commit is 2026-08-02.

The two-case mesh gate (t0021 at 0.025 nm and 0.10 nm) is implemented, isolated
and blocked behind `--stage5-check`, but **has never been executed**. Demo 13's
0.05 nm mesh is therefore still unvalidated, and §17's warning stands: Demo 14
inherits an unproven mesh if it simply adopts 0.05 nm for continuity.

---

## Corrections to the brief

| Brief says | Actually |
|---|---|
| "advance Demo 13 from relative to absolute χ(2)" | Absolute mode already implemented and tested; blocked only on 2 constants |
| §6 "must not use only k∥ = 0" | Demo 13 already integrates to 0.1 BZ with 96 points |
| §7 "choose formulation A or B and derive the prefactor" | Already B (energy), with the ħ² cancellation documented |
| §10 "use Nextnano's documented Fermi-function" | No such keyword in nextnano++ — nextnano³ only |
| §4 "Demo 13 explicitly omitted the interband Kane/Bloch element" | Correct, and it is the genuine blocker |
| §2 "layer numbers must be checked mathematically" | Already done — 30 nm vs "20 nm" typo recorded |
| ref [2] alloy-function page | nextnano³ documentation, not nextnano++ |

---

## Recommended revised execution order

The spec's §23 order is sound; these are the changes the audit forces.

1. ~~Resolve `r_e_hh_nm` and `n_wells_per_metre`~~ — **DONE**, see above.
2. **Angular-frequency implementation + cross-test** against the existing energy
   form. Independent path, not a rescaling. Home-laptop work.
3. **k∥: 2D Cartesian cross-check + convergence reporting** (§6). Home-laptop
   work on existing tested code.
4. **N_z and zone-edge sensitivity tables.** Cheap, and they bound the absolute
   scale before any licensed time is spent.
5. **ABSOLUTE PAPER-REFERENCE GATE** (§16, and point 5 of the resolution) — the
   7.1/1.8/2.9 structure against 2340 / 1200 / 1363 pm/V and the ~1520 nm
   resonance. **This now comes before the grading renderer**, per the resolution's
   point 7. Licensed.
6. **Grading renderer** — 10–90 constructor, `ternary_import` emission,
   thousands-of-samples solver-free suite (§13A, §10E part 1).
7. **NEW: licensed native-vs-import equivalence run** (§10E part 2) — the free
   home build parses import decks but refuses to execute them, so this cannot be
   done here. Must be budgeted.
8. **Mesh + k convergence gate** (§17).
9. **Only then** the 30-trial campaign.

---

## RESOLVED — both blockers closed 2026-08-07

Full provenance in [`docs/demo14_physics_sources.md`](../../../docs/demo14_physics_sources.md).

1. **`r_e_hh` = 7.51 Å = 0.751 nm.** Ramesh 2023 (APL 123, 251111), HSE06/VASP.
   **Verified verbatim from the PDF in this repo**, not taken on trust. It is a
   *position* matrix element; Eq. (3) already carries `e³`, so it must not be
   multiplied by charge again. Config: `metric.r_e_hh_nm: 0.751`.
2. **`N_z` = 1/L_period = 3.3333333e7 m⁻¹**, `Nz_mode: period_density`. Ramesh
   2023's definition — "N_z is the number of QWs per unit length" — **verified
   verbatim**, and confirmed to be genuinely ambiguous between periods and
   individual wells, so a sensitivity table over the readings is mandatory before
   the normalization is called validated. `spin_degeneracy` stays a separate
   variable and is never folded into N_z (the code already does this).
3. **§10B width reference: peak-referenced, with a nullable nominal companion.**
   Decided. `realized_grading_width_10_90_nm` is measured against
   `realized_peak_al_fraction` (always defined);
   `realized_grading_width_10_90_nominal_nm` keeps the 0.055/0.495 reading and is
   explicitly null for the ~19% of designs that never reach 0.495.

**Unit chain verified analytically**: `C J m² · m⁻² · m · J⁻² = m/V`. The `m⁻²`
comes only from the 2D k∥ measure, so "no plain unweighted average" is a
dimensional requirement, not a preference. An order-of-magnitude probe with
placeholder matrix elements gives ~350 pm/V against the paper's 2340 pm/V — same
order, and a smoke test only.

**Correction to the resolution's point 3:** `_k_grid` is *already* the radial 2D
form (`∫d²k/(2π)² = (1/2π)∫k dk`, trapezoidal, spin separate). It is not a plain
average. What is genuinely missing is the independent 2D Cartesian cross-check
and the convergence reporting.

## Open questions that need your call

1. **Demo 13's Stage 5 gate** is still unrun. Run it first (2 licensed runs,
   validates the 0.05 nm mesh Demo 14 wants to inherit), or leave Demo 13 parked
   and let Demo 14 establish its own mesh gate from scratch?
2. **Zone-edge convention.** π/a (current) or 2π/a? The papers do not state it.
   This moves `k_max` by 2× and the k-measure by 4× — a direct multiplier on
   every pm/V number, comparable in size to the N_z ambiguity.
