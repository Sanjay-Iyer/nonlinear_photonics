# Demo 29 results

| Section | Result | Status |
|---|---|---|
| 29A1 | Five aligned 300 K finite-k spinor frames | Preserved diagnostic |
| 29A2 | 300 K tracking, matrices, optical and sampling analysis | Complete for present data; gates below |
| 29A3 | Dense 300 K validation | Prepared; paused under current priority |
| 29A4 | Full-8-band 300 K χ² | **Not calculated** |
| 29B | Full-8-band temperature electronic-structure comparison | 100/500 K acquisition prepared; no new WORK solve yet |
| 29C | Historical mixed 100/300/500 K χ² | Complete, reference only |

## Current 29B acquisition decision

The user selected temperature acquisition as the next priority. The 100 K
and 500 K full-8-band decks are byte-identical to the **executed successful
300 K pilot deck** except for the global temperature assignment. The original
deck hash and run ID are frozen in `config/29b_reference.json`; the new
`--check-29b` report verifies this mechanically. The finite-k acquisition
remains `relative_size = 0.03`, `num_points = 5`, `num_subpoints = 1`,
`symmetry = none`, `force_k0_subspace = no`, with 301 dispersion points to
`0.10·π/a`. The existing 300 K raw is the 29B reference; it is not rerun.
The 100/500 K licensed runs have **not** been performed on HOME. They will
compare solver-temperature effects on energies, character, localization,
tracking and envelope position/dipole/momentum matrices. No full-8-band χ²
temperature result is implied while the optical mapping remains unresolved.

## 29A2 five-point physics decision (2026-09-24)

The replacement 300 K pilot raw passed all 9,991 SHA-256 checks. Its 301-point
dispersion retains `0.10·π/a = 0.555714439232 nm⁻¹`; five complete spinor
frames are on the positive Γ→y target path. HOME analysis is in
`outputs/29A_full8band_300K/29A2_physics_debug/`: `tracking.csv` has every
selected state at every on-path point, `pilot_analysis.json` has flags and
localization, `matrix_blocks/` contains complex 8-band position and
component-overlap tensors, and `sampling.json` has interpolation tests.

| k (nm⁻¹) | hh2 previous-step overlap | hh2 next-best overlap | hh1 HH/LH | hh1–hh2 position block (nm) |
|---:|---:|---:|---:|---:|
| 0 | seed | — | 100.0% / 0.0% | 0.9569 |
| 0.1160865 | **0.4096, flagged** | 0.1345 | 98.1% / 1.8% | 0.2998 |
| 0.2321730 | 0.6941 | 0.0025 | 84.7% / 14.8% | 0.3852 |
| 0.3482595 | 0.9630 | 0.0040 | 58.3% / 41.3% | 0.2929 |
| 0.4643460 | 0.9317 | 0.0027 | 46.2% / 53.3% | 0.1666 |

At the first finite-k step, hh2's best continuation is still solver states
`(1,2)`; the next-best `(3,4)` LH-rich candidate scores only 0.1345. Its
localization stays high (0.952→0.934). Thus the observed candidate pool does
not show a better replacement, but the 0.4096 overlap is too weak to certify
tracking over that 0.116 nm⁻¹ jump. A rapid change/crossing or sparse
sampling remains possible. The pool remains 14 states for 29B. A future denser
adjacent-k study may determine whether it must expand. Fixed solver
indices alone are not accepted.

The e1–e2 position block varies 0.9160→0.9096 nm. Its maximum interior
leave-one-out relative error is 0.055% for linear and 0.024% for PCHIP.
The hh1–hh2 block is **nonmonotonic**; its maximum errors are **124%**
(linear) and **100%** (PCHIP). These are tests on gauge-invariant doublet
Frobenius strengths. Raw individual complex phases are doublet-gauge
dependent and cannot be safely interpolated without phase alignment. The
interband optical matrix is unresolved, so its k-dependence cannot yet be
tested. Five-point interpolation onto 301 dispersion points is **rejected**.

Spinor normalization errors on the five path frames are below 4×10⁻¹³;
composition agrees with integrated component probabilities. The computed
off-diagonal growth-position elements match nextnano's native growth-dipole
table to at most 4.1×10⁻⁶ nm. These checks validate envelope position
matrices, **not** the missing interband Bloch optical operator. The paper and
nextnano definitions, spin and scalar-prefactor questions are documented in
`OPTICAL_MAPPING.md`; the gate remains closed. 29A3 is paused. 29B electronic
structure acquisition can proceed, but 29A4/full-8-band χ² is not ready.

**300 K matched Professional pair acquired; 29C mixed control computed.** The
original work-run folder was returned outside Git at
`nextnano_raw/demo29/demo29_300K_original_solver/300K`. The executed decks, both job
statuses, 301-point 0.10π/a dispersion, k=0 composition, and single-band
anchors/envelopes passed local validation. The resulting 300 K historical
mixed-model spectrum is in `outputs/29C_mixed_control/300K/` on HOME.

| 300 K mixed-control quantity | Value |
|---|---:|
| Re χ² at 1550 nm | +26.4702 pm/V |
| Im χ² at 1550 nm | +0.7973 pm/V |
| Dominant \|Re χ²\| | 71.3106 pm/V at 1505 nm |
| Dominant \|Im χ²\| | 57.8979 pm/V at 1496 nm |

The selected k=0 8-band doublets were electron indices `(11,12)` and `(13,14)`
at 2.952511679 and 3.091148452 eV, and valence indices `(5,6)` and `(3,4)`
at 1.443772122 and 1.416747842 eV. `(5,6)` is HH dominated; `(3,4)` is
97.6% LH. The latter is deliberately retained only in the historical mixed
control, not silently labeled HH in the new primary model.

**29A full 8-band remains in development.** The first finite-k pilot exported
nine complete 8-band frames, but only k=0 lies on the requested positive Γ→y
interval 0–0.10π/a. A second, target-aligned 300 K pilot produced five usable
path frames, described below. The interband optical operator/spin mapping
remains unresolved; no full-8-band χ² spectrum has been produced. **29B**
100/500 K electronic-structure acquisition is prepared. **29C** historical mixed-model
100/300/500 K controls have been computed.

The control result is a same-temperature **mixed** calculation and retains
single-band k=0 matrix elements with `M(k)=M(0)`. It is not evidence that the
full-8-band model is complete. The old Demo 28 mixed 300 K curve can be added
only as a labeled historical comparison; no numerical match is required.

Signed Re/Im, |Re| and |χ²| mixed-model temperature overlays, χ² at 1550 nm,
key transition energies, and major feature locations are available below.
A primary-versus-control trend summary awaits full-8-band χ² results.

## 2026-09-24: 29C historical mixed-model temperature controls

The returned 100 K and 500 K packages passed checksum, same-temperature deck,
job-status, 301-point Γ→positive-y dispersion and single-band input validation.
The existing 300 K matched solver pair was processed by the same mixed-model
engine. These are **29C controls**, not the new full-8-band χ² result.

| Solver T | Re χ²(1550 nm) | Im χ²(1550 nm) | \|χ²\|(1550 nm) | Dominant \|Re\| feature | E11 at k=0 |
|---:|---:|---:|---:|---:|---:|
| 100 K | +11.4995 pm/V | +0.9861 pm/V | 11.5417 pm/V | 1436 nm | 1.572158 eV |
| 300 K | +26.4702 pm/V | +0.7973 pm/V | 26.4822 pm/V | 1505 nm | 1.493353 eV |
| 500 K | +11.1015 pm/V | −52.8320 pm/V | 53.9858 pm/V | 1601 nm | 1.397429 eV |

The dominant long-wavelength \|Re χ²\| feature moves 165 nm toward longer
wavelengths from 100 to 500 K. Re χ² at 1550 nm is not monotonic. The large
500 K \|χ²\| at that wavelength comes primarily from its imaginary part as
the feature moves through the vicinity of 1550 nm. The k=0 E11 transition
falls by 0.174730 eV across the same temperature range. The selected `(3,4)`
valence pair remains LH dominated and is retained only for historical method
consistency. The model uses same-temperature 8-band dispersion plus
single-band k=0 anchors and constant matrices, `M(k)=M(0)`; it contains no
explicit thermal carrier-occupation factors.

The plots and numeric table are in `outputs/comparison/mixed/`:
`real.png`, `imag.png`, `abs_real.png`, `abs_chi2.png`, `at_1550_nm.png`,
`k0_transition_energies.png`, and `temperature_summary.csv`. Individual
temperature `metadata.json` files include peak and zero-crossing positions.

## 2026-09-24: 29A target-aligned pilot transfer status

The 300 K debug report records a successful 7 min 35 s Professional 8-band
solve, unchanged 301-point 0.10π/a dispersion, and **81 complete finite-k
frames**. Five exported state points lie exactly on the positive Γ→y target
interval: k = 0, 0.1160865, 0.2321730, 0.3482595 and 0.4643460 nm⁻¹.
This establishes target-path output coverage for testing adjacent-k state
tracking and position-matrix variation. It does **not** provide spinors at
every one of the 301 dispersion nodes. The optical operator and spin
convention remain unresolved, so no full-8-band χ² spectrum is available.

An initial HOME extraction was incomplete, but the replacement at
`nextnano_raw/demo29_300K_target_pilot_raw/pilot_target_300K_trial2/` is complete:
all 9,991 manifest files are present and all SHA-256 hashes match. Analysis of
the five target-path frames is in
`outputs/29A_full8band_baseline/target_pilot_trial2/pilot_analysis.json` and
its complex matrix blocks. The target grid and state/matrix plots are
`outputs/comparison/pilot_target_grid.png` and
`outputs/comparison/pilot_state_matrices.png`.

At k=0, the selected 8-band doublets are e1 `(11,12)`, e2 `(13,14)`, hh1
`(5,6)`, and hh2 `(1,2)`. The latter two are 100% HH at k=0; the `(3,4)` pair
used by the historical mixed calculation is 97.6% LH and must not be treated
as hh2 in the new primary model. Across the five path frames the tracked solver
indices happen to remain the same, but hh2's overlap at k=0.1160865 nm⁻¹ is
only 0.410 and is flagged as ambiguous. By k=0.464346 nm⁻¹, the tracked hh1
pair is 46.2% HH and 53.3% LH. Fixed eigenvalue indices or a permanent HH
character assumption are therefore unsafe.

The computed 8-band growth-position blocks vary with k: their two-doublet
Frobenius strengths are 0.916→0.910 nm for e1–e2, 0.957→0.167 nm for hh1–hh2,
and approximately zero→0.252 nm for e1–hh1 across the five exported frames.
These are genuine finite-k spinor-derived position blocks, but they are not by
themselves the interband optical transition operator needed for Equation 2.
There are also only five spinor frames on the requested path versus 301
dispersion points, so any future k-dependent optical calculation would need a
specified interpolation or denser spinor output. **No full-8-band χ² spectrum
or 100/300/500 K full-8-band temperature trend has been calculated.**
