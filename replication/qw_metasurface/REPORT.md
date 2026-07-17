# Replication Report — Quantum-Well-Metasurface to Maximize Nonlinear Polarization

Replicating the computational results of **Fathi et al., arXiv:2604.15476 (2026)**
via three independent routes: **aestimo** (Schrödinger–Poisson envelope
functions), **kdotpy** (8-band k·p), and a **BNN surrogate**, then comparing all
three against each other and the paper.

Living document — updated at the end of each phase.

---

## Documentary evidence base

Three papers inform this replication (all from the same UT-Austin/Harvard group):

| Ref | Citation | Role |
|-----|----------|------|
| **Main** | Fathi et al., arXiv:2604.15476 (2026) | The paper being replicated (MQW + metasurface) |
| **APL2023** | Ramesh et al., APL **123**, 251111 (2023) | χ⁽²⁾ dipole-matrix formalism (Eqs. 2–3), r_ehh = 7.51 Å (HSE06) |
| **Ref38** | Ramesh et al., arXiv:2602.23246 (2026) | *Same* 16-period 18.2/7.1/1.8/2.9 nm structure; states Al₀.₅₅Ga₀.₄₅As, E11=1.49 eV, E22=1.62 eV, graded-interface χ⁽²⁾ |

Key facts extracted:
- **Structure** (Main Methods): 16 periods of AlGaAs **18.2** / GaAs **7.1** /
  AlGaAs **1.8** / GaAs **2.9** nm. Asymmetry s = (7.1−2.9)/(7.1+2.9) = **0.42**.
- **Al fraction**: not stated in Main; Ref38 (same structure) uses **x = 0.55**.
  The plan treats x as a calibration free parameter (Phase 2).
- **χ⁽²⁾ formalism**: Main Eqs. (2)–(3) = APL2023 Eqs. (5)–(6); electron + hole
  susceptibilities, Γ = 5 meV, k∥ integral to BZ/10, r_ehh Bloch dipole pulled out.
- **Selection rule** (Ref38 Eqs. 4–5): χ_xzx ∝ ⟨e2|x|hh2⟩⟨hh2|z|hh2⟩⟨hh2|x|e2⟩ ≠ 0,
  while χ_xxz ∝ ⟨hh2|x|hh2⟩ ≈ 0 → the two are *not* equal here (the "½ factor").
- **Metasurface** (Main Methods): TiO₂ pillars h=390 nm r=230 nm, periods
  891×650 nm, GRCWA, MQW as one homogeneous layer with ellipsometry index,
  n(780 nm)=3.39+0.11i. Three GMRs A/B/C; B has Q=1124 (exp), 1567 nm (exp)/1580 nm (sim).
- **Results**: χ⁽²⁾_eff,MQW = **1.6 nm/V** @ 1.57 µm; with metasurface **≈14 nm/V**
  (17 without SH-absorption correction); ExEz enhancement ~57× vs 45°, ~11.5× vs normal ExEx.

### Prior-session assets reused
A previous effort (under `git/aestimo/paper/`) already built an aestimo+kdotpy+BDD
comparison of this exact ACQW and froze a **solver-consensus release**
(`reference_data/acqw_solver_consensus_v1/`). Its headline numbers (x=0.55, abrupt):

| Solver | E11 (eV) | E22 (eV) | HH2 wide% | HH2 narrow% | \|Δz₂₂\| (nm) |
|--------|---------:|---------:|----------:|------------:|-------------:|
| Aestimo 3×3 | 1.4955 | 1.6557 | 24.2 | 67.8 | 1.183 |
| BDD (single-band) | 1.4941 | 1.6490 | 20.8 | 71.1 | 0.931 |
| kdotpy 8-band | 1.5071 | 1.6694 | 28.7 | 64.2 | 0.791 |

This is a strong head start: the electronic-structure machinery and band-parameter
alignment already exist and are documented in
`acqw_solver_consensus_v1/docs/BAND_PARAMETER_MANIFEST.md`. This replication builds
on that but re-runs everything under the versioned-checkpoint discipline of the plan.

**Note on E22:** consensus E22 ≈ 1.656 eV (abrupt, x=0.55) is ~76 meV above the
1.58 eV target. Interface grading (Ref38: linear over ~1 nm) redshifts transitions,
and Phase 2 will calibrate x on the *abrupt* model to hit 1.58 eV, documenting the
grading effect separately.

---

## Phase 0 — Environment and parameter capture ✅ GATE PASSED

**Date:** 2026-07-17 · **commit tag:** `qwms-phase0`

- Directory tree created under `replication/qw_metasurface/`.
- `config/paper_params.yaml` initialized (all plan parameters + documentary
  anchors from APL2023 and Ref38). Validates against `config/check_config.py`.
- All required packages import cleanly in conda env **NMIP**
  (`C:\Users\iyer95\miniconda3\envs\NMIP\python.exe`):

  | package | version | package | version |
  |---------|---------|---------|---------|
  | python | 3.11.15 | torch | 2.12.1+cpu |
  | numpy | 2.4.6 | kdotpy | 1.4.0 |
  | scipy | 1.17.1 | grcwa | 0.1.2 (pip-installed this phase) |
  | matplotlib | 3.11.0 | h5py | 3.16.0 |
  | aestimo | 3.0.0 | pandas | 3.0.3 |

  Full list in `logs/env.txt`.

**Gate:** ✅ all imports succeed; `paper_params.yaml` validates.

**Environment gotchas** (from memory + this session):
- `conda` is not on PATH; invoke `C:\Users\iyer95\miniconda3\envs\NMIP\python.exe` directly.
- numpy is 2.x → use `np.trapezoid` not `np.trapz`.
- Some prior scripts print Unicode; set `PYTHONIOENCODING=utf-8` when piping.
- Root repo newly `git init`-ed; nested `git/aestimo` (own repo) is `.gitignore`-d.

---

## Phase 1 — Structure definition and material parameters ✅ GATE PASSED

**Date:** 2026-07-17 · script `phase1_structure/build_structure.py`

Single-period stack (growth z, left→right): outer barrier **18.2** / wide well
GaAs **7.1** / coupling barrier **1.8** / narrow well GaAs **2.9** / outer barrier
**18.2** nm. Asymmetry s = 0.42. Wide well left, narrow well right (matches Fig. 2a).

Band edges computed from the aestimo database (shared with Phase 2), GaAs VB = 0:

| Quantity | Value | Source |
|----------|------:|--------|
| Barrier Al fraction (pre-calibration) | 0.55 | Ref38 anchor; calibrated in Phase 2 |
| GaAs Eg (300 K) | 1.4223 eV | aestimo database |
| Al₀.₅₅Ga₀.₄₅As Eg | 1.9268 eV | bowing-interpolated |
| Conduction band offset | 0.5045 eV | CBO fraction 0.65 |
| Valence band offset | 0.2717 eV | 1 − CBO |

These reproduce the frozen `acqw_solver_consensus_v1` manifest values (ΓCBO 0.504504,
VBO 0.271656 eV) exactly.

**Two variants** implemented:
- `ideal`: abrupt square wells (grading 0 nm).
- `graded`: piecewise-linear interfaces, grading width **1.0 nm** (Ref38 EDS:
  "gradients were mostly linear across 1 nm"). Modeled by moving-average
  convolution of the abrupt Al profile.

**Known thickness issue (documented):** 16 × 30.0 nm = 480 nm, but the paper
states 595 nm film. The ~115 nm difference is unitemized cap/buffer/terminating
layers (Ref38 mentions a 10 nm GaAs cap + removed etch stops). The electronic
problem is solved on **one period** with thick (18.2 nm) outer barriers as
confining walls; **595 nm** is used only for the optical/metasurface thickness (Phase 5).

Outputs: `structure_{ideal,graded}.npz` + `.csv`, `fig2a_bandedges.png/.svg`.

**Gate:** ✅ band-edge plot visually consistent with Fig. 2a — two coupled wells,
correct asymmetry (wide left, thin right), graded variant shows sloped interfaces.

## Phase 2 — aestimo envelope states and matrix elements
_(pending)_

## Phase 3 — kdotpy multiband k·p cross-check
_(pending)_

## Phase 4 — χ⁽²⁾ spectrum
_(pending)_

## Phase 5 — Metasurface GMR simulation
_(pending)_

## Phase 6 — BNN surrogate + uncertainty
_(pending)_

## Phase 7 — Three-way comparison and report
_(pending)_
