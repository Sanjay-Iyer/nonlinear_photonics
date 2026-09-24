# Demo 30 results

Generated 2026-09-24 on the HOME laptop by `scripts/run_demo30.py`. **No licensed nextnano
run was needed or made.** Every number below is read from `outputs/` (mainly
`outputs/summary.json`), and a rerun reproduces it.

**Raw data** (local only, hash-verified through `inputs/raw_data.lock.json`):

- `D020_2026-08-20_sb-case04-graded-300K`: single band.
- `D023_2026-09-04_kp8-disp-k0p10pia-n301-300K`: 8-band, **control k_max = 0.1·π/a**.
- `D023_2026-09-04_kp8-disp-k0p125pia-n301-300K`: optional, used by 30F only.

## Answer to the key question

**Does including absorption move the predicted spectrum toward the measured Fig. 2d
response? Barely.**

- **Absorption is large.** For the 80-period sample (2.4 µm) it removes about half of the
  SH intensity near the resonance: |A|² ≈ 0.41–0.51 across 1500–1600 nm in the primary model.
- **But it is nearly uniform across the resonance.** The χ(2) resonance is only a few nm
  wide, while |A|² changes slowly with wavelength, so the spectral shape hardly changes.
- **The predicted SH peak moves by 0–1 nm** (1503 → 1503–1504 nm). The gap to the measured
  peak at 1560 nm is 57 nm. The shift is also 0 nm when our absorption is applied to the
  paper's own simulated χ(2), which peaks at 1520 nm.
- **Shape agreement at the measured points barely improves.** nRMSE falls from 0.659
  (transparent) to 0.627 at best (expanded states + tail). The correlation stays negative
  (−0.36 → −0.31).
- **What absorption cannot explain.** It cannot produce the measured peak at 1560 nm or the
  strong measured shoulder at 1600–1700 nm. The resonance position (set by the transition
  energies) and the unmodeled propagation effects (phase mismatch, standing waves, bulk
  SH) dominate the mismatch.
- **Where absorption does matter:** absolute SH levels and any χ_eff extraction from the
  thick sample (30D).

## 30A — inputs

- **Raw packages.** All three verify fully against their `SHA256SUMS.txt`
  (50, 738 and 738 files). The consumed files are byte-identical to Demo 28A's inputs
  (`PROVENANCE.md`).
- **Measured Fig. 2d digitization** (`reference/paper_fig2d_measured.csv`,
  `plots/30A_fig2d_digitization_overlay.png`, method in `reference/FIG2D_DIGITIZATION.md`):
  - 11 points per series (80 pd sample, AlGaAs control, GaAs control) at 1400, 1500,
    1530–1580 (10 nm steps), 1600, 1700 and 1800 nm;
  - all within 0.18 nm of the 10 nm grid;
  - uncertainty about ±0.3 nm and ±0.3 arb. u.;
  - the measured peak is 199.8 arb. u. at 1560 nm.
- **Paper simulation, traced.** Peaks at 538.7, 760.2, 1079.5 and 1519.8 nm. The older
  45-point eye digitization deviates from the trace by 92 pm/V RMS (304 pm/V at most).

## 30B — χ(2) control (comparison A)

- Demo 28A is reproduced from the registered raw data with a maximum complex error of
  **0.0 pm/V**. The error against the historical Demo 26 reference is 7.0×10⁻¹⁰ pm/V.
  Re-zero positions are exact.
- `equation2.py` is byte-identical to Demo 28's.
- Comparison A reproduces Demo 28J:
  - |Re χ(2)| nRMSE **0.2379** (r 0.31), |χ(2)| nRMSE **0.2624** (r 0.25);
  - against the traced curve: 0.2310 and 0.2589.
- Plot: `plots/30B_chi2_vs_paper_simulation.png`.

## 30C — χ(1) and absorption

**Method.** χ(1)_xx uses Eq. 2's own energies, overlaps, k weights, Γ = 5 meV and +iΓ
convention, with prefactor C₁ = N_z e r² ×10¹⁸/ε₀ = **0.34019** (units in
`demo30/chi1.py`). α_E = (ω/2nc)(−s)Im χ(1) and α_I = 2α_E. The background indices are
n_ω = 3.197 and n_2ω = 3.436 (MQW TE average of the literature values in the config).

**SH absorption α_I(2ω) at 1550 nm (cm⁻¹):**

| 2×2 strict (primary) | 2×2 + tail | expanded strict | expanded + tail |
|---:|---:|---:|---:|
| 6740 | 6899 | 7071 | 7312 |

- **Sanity.** On the e1–hh1 plateau (1.543 eV), 1.7% is absorbed per 30 nm period. That is
  inside the 0.3–3% sanity band, and about 2× typical single-well values; this is
  plausible if r_e,hh = 0.751 nm is the full ⟨S|x|X⟩ matrix element rather than its
  heavy-hole projection.
- **Fundamental absorption is negligible.** α_I(ω) at 1550 nm is 1.9 to 22 cm⁻¹ (upper
  bounds from the Lorentzian tails). The largest α_E(ω)·L over the window is 3.3×10⁻³, below
  the 0.01 threshold. α_ω stays in Eq. 5 anyway.
- **Onsets sit at their transition energies.** The dIm/dE peaks are at T(0) + 0.05 meV
  (e1–hh1) and −0.48 meV (e2–hh2).
- **Validity window.** The SH is below the bound-to-continuum onset (1.7616 eV) for
  fundamentals ≥ **1407.6 nm**.
- **Strict-cutoff trust limit ≥ 1492.7 nm.** The stored 0.1·π/a states end the e1–hh1
  absorption at 1.676 eV, so below 1492.7 nm the strict result loses absorption, down to
  −85% at 1408 nm.

**Strict vs tail** (α_I(2ω), 2×2): the tail adds 6.1% at 1500 nm, 2.3% at 1550 nm and
1.6% at 1600 nm. It differs by more than 10% only in two places: at 1408–1491 nm (the
truncation) and at 1676–1800 nm, where α is tiny.

**2×2 vs expanded** (tail): the expanded model absorbs ×1.34 at 1500 nm (e2–hh3 turns on
at 1499 nm), ×1.06 at 1550 nm, ×1.03 at 1600 nm and ×1.33 at 1700 nm. The maximum is
×2.48 at 1408 nm (e3–hh2). Varying the assumed slope of the extra pairs by ×0.7 or ×1.3
changes the expanded α by −14% to +26%.

Plots: `plots/30C_absorption_coefficients.png`, `plots/30C_diagnostic_chi1_re_im.png`.

## 30D — absorptive SH propagation (1994 Eq. 5)

**SH intensity factor |A|² for 80 periods (2.4 µm):**

| λ (nm) | 2×2 strict | 2×2 + tail | expanded strict | expanded + tail |
|---:|---:|---:|---:|---:|
| 1500 | 0.414 | 0.392 | 0.316 | 0.297 |
| 1550 | 0.470 | 0.461 | 0.454 | 0.440 |
| 1560 | 0.475 | 0.467 | 0.461 | 0.449 |
| 1600 | 0.514 | 0.508 | 0.507 | 0.496 |
| 1700 | 0.975 | 0.968 | 0.971 | 0.956 |

**At 1550 nm by sample (2×2 strict):**

| Periods | \|A\| (field) | \|A\|² (intensity) | Paper χ_eff (pm/V) |
|---:|---:|---:|---:|
| 4 | 0.980 | 0.960 | 2750 |
| 12 | 0.942 | 0.887 | 1170 |
| 16 | 0.923 | 0.852 | 1170 |
| 80 | 0.686 | 0.470 | 1730 |

- **Conditional reading only.** *If* an extraction ignored MQW absorption, its χ_eff would
  be low by the field factor |A|. We do not know whether the paper's field simulation
  included absorption.
- **Numerical check.** The closed form agrees with direct ODE integration and with the
  field-overlap integral to 4.5×10⁻¹⁴.
- **Phase mismatch (limitation, not applied).** L_c = 1.62 µm against L = 2.4 µm at 1550 nm.
  A transparent slab would show sinc² ≈ **0.099**. That is a larger effect than absorption,
  and the reason for Demo 31.

Plot: `plots/30D_absorption_factor.png`.

## 30E — SH intensity vs measured Fig. 2d (comparison B)

The window is 1492.7–1800 nm and uses 10 measured points (1500–1800 nm). The 1400 nm point
is outside the validity window. Each curve is normalized to its own maximum.

| Model SH intensity | nRMSE | Pearson r | Peak (nm) |
|---|---:|---:|---:|
| transparent (control) | 0.659 | −0.36 | 1503 |
| 2×2 strict (primary) | 0.648 | −0.35 | 1503 |
| 2×2 + tail | 0.645 | −0.35 | 1503 |
| expanded strict | 0.630 | −0.32 | 1504 |
| expanded + tail | 0.627 | −0.31 | 1504 |
| *measured (80 periods)* | | | *1560* |
| *paper simulated \|χ(2)\| (a susceptibility)* | | | *1519.8* |

Plot: `plots/30E_fig2d_comparison.png`.

## 30F — optional k extension

**0.125·π/a (existing data).** The run's deck differs from the control only in the k
endpoint.

- **The analytical tail matches real data.** Where absorption is significant (1415–1669 nm),
  0.1·π/a strict + tail agrees with the real 0.125·π/a strict result within **6.3%** (2×2)
  and **3.6%** (expanded). The strict 0.1·π/a result alone is off by up to 85% and 48%.
- **χ(2):** the peak stays at 1503 nm, and χ(2)(1550 nm) goes from 26.47+0.80i to
  31.57+0.68i pm/V, identical to Demo 28C.
- **Comparison B improves slightly** (transparent 0.641, best 0.601), and the peaks are
  unchanged. The conclusions do not change.

**0.2·π/a: not computed; there are no registered data yet.** Two routes (details in
`work_laptop/README.md`):

- **Route A — no licensed run.** The existing 28K run reaches exactly 0.2·π/a on the same
  k spacing. Its 14 relevant states reproduce the control to 3×10⁻¹¹ eV on the 301 shared
  nodes. Registering it needs your approval.
- **Route B — clean run.** The prepared package (control deck with only the endpoint and
  point count changed) takes about 20 min on WORK and holds every other parameter fixed.

## Validation summary

All tests pass: `python -m pytest nextnano/demos/30_absorption_study/tests -q`.

| Required check | Where |
|---|---|
| 1. baseline reproduces Demo 28A | `test_control_reproduces_demo28A` (0.0 pm/V) |
| 2. Eq. 2 copy unchanged | `test_equation2_is_byte_identical_to_demo28` |
| 3. raw-data lock verification | `test_parsers_read_exactly_the_locked_files`, `test_modified_raw_data_is_rejected`, `test_failed_status_is_rejected`, `test_missing_raw_data_fails_with_instructions`, 30A full-package verification |
| 4. χ(1) analytic case | `test_strict_parabolic_band_matches_closed_form`, `test_tail_completes_the_infinite_parabola`, `test_prefactor_from_constants` |
| 5. passive absorption positive | `test_passive_absorption_is_positive_in_both_conventions` |
| 6. field vs intensity | `test_intensity_coefficient_is_twice_the_field_coefficient`, `test_alpha_units_by_hand` |
| 7. α → 0 transparent | `test_no_absorption_is_the_transparent_result` |
| 8. α_2ω → 2α_ω stable | `test_alpha_2w_equal_to_twice_alpha_w_is_stable` |
| 9. closed form vs numerical | `test_closed_form_matches_ode_and_overlap_integral` (+ 30D, 4.5×10⁻¹⁴) |
| 10. resonance positions | 30C resonance alignment; `test_strict_vs_tail_and_2x2_vs_expanded_are_quantified` |
| 11. strict vs tail quantified | 30C `alpha_I_2w_tail_vs_strict`; 30F tail check against 0.125·π/a data |
| 12. 2×2 vs expanded quantified | 30C `alpha_I_2w_expanded_vs_2x2`; 30D, 30E |
| 13. isolation audit | `test_isolation_audit_passes`, `test_isolation_guard_really_blocks` (`outputs/isolation_audit.json`) |
| 14. deterministic rerun | `test_deterministic_rerun` (byte-identical CSV/NPY) |

## Assumptions and limitations (not resolved by Demo 30)

- **Mixed model inherited from Demo 28A:**
  - 8-band dispersion shifts with single-band k = 0 anchors and envelopes;
  - matrix elements frozen at k = 0;
  - the "hh2" dispersion comes from an LH-dominated 8-band pair.
- **Absolute scale of χ(1).** It depends on r_e,hh² (a heavy-hole projection could halve it),
  on the in-plane reduced mass, and on missing excitonic enhancement at the edges.
- **Missing absorption.** No light-hole transitions, continuum or excitons. The expanded
  model is a sensitivity comparison, not an upper bound.
- **Propagation.** Only a uniform, period-averaged slab with normal-incidence thickness and
  1994 Eq. 5's phase matching. Phase mismatch, Fresnel and standing waves, oblique
  incidence and bulk GaAs/AlGaAs SH are Demo 31.
- **Background index** is constant, ±0.02.
- **Measured curve.** "Normalized SH Intensity (arb. u.)" has an unstated normalization, so
  only shapes and peak positions are compared.
- **Period.** The paper's "Each period is 20 nm" text conflicts with its layers (30 nm);
  30 nm is used.
- **Temperature.** 300 K only; temperature dependence is Demo 29.
