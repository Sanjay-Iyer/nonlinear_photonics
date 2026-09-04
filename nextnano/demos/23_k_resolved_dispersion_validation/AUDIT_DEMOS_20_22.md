# Demo 23 reuse audit: Demos 20–22

This audit was completed before Demo 23 implementation. Demo 23 does not
modify Demos 20, 21, or 22.

| Existing function | File | Responsibility | Demo 23 decision |
|---|---|---|---|
| `CaseStates`, `absolute_prefactor`, `chi2_spectrum` | `../20_quantum_well_interface_grading_scaled/s06_chi2.py` | Validated Equation 2 constants, units, 16 pathways, cancellation, and pm/V conversion | Reuse constants/prefactor and regression target unchanged |
| `transition_energies_eV` | Demo 20 `s06_chi2.py` | Shared reduced-mass parabolic transition shift | Reproduce exactly in 23A only |
| `k_grid` | Demo 20 `s06_chi2.py` | `g_s k dk/(2 pi)` production measure and explicit bare diagnostic | Preserve production convention |
| envelope normalization, overlap and position matrices | `../_shared/chi2.py`, Demo 20 extraction | Builds `O`, `z_e`, and `z_hh` from licensed states | Reuse stored validated k=0 values |
| Demo 21 reference and trace | `../21_demo20_mathematical_walkthrough/` | Imports and explains Demo 20; no new physics | 23A comparison target |
| `deck22`, `kp8_acqw22.in.j2` | `../22_k_resolved_8band_chi2_validation/` | Professional 8-band geometry and finite-k output requests | Reused by `deck23.py` |
| `kp8io22.extract_state_grid` | Demo 22 | Requires explicit k vectors and inventories actual output | Reuse unchanged |
| `state_tracking22.track_states` | Demo 22 | Adjacent-k character-overlap assignment with energy tie-breaker | Reuse with fail-loud target-state gate |
| `chi2_22.chi2_from_k_inputs` | Demo 22 | Validated generalized 16-pathway evaluator for explicit `Ee(k)` and `Ehh(k)` | Reuse unchanged for A–D |
| `professional_probe`, `solver14.execute_real` | Demo 22 / Demo 14 | Licensed execution gate and timeout/failure handling | Reuse; no synthetic fallback |

## Frozen baseline

- `Gamma = 5 meV` in energy-domain denominators.
- `r_e,hh = 0.751 nm`.
- `Nz = 1/(30 nm)`, one coupled-well period per 30 nm.
- Spin degeneracy `g_s = 2`.
- Two electron and two heavy-hole states.
- `M(k) = M(0)` for every A–D mode.
- `kmax = 0.1 pi/a`, `a = 0.565325 nm`.
- Production normalization `d^2k/(2 pi)^2`, radially `g_s k dk/(2 pi)`.
- No residual `1/hbar` is introduced.

## Audit risk carried into Demo 23

Demo 22 can sort arbitrary k vectors by magnitude, while its radial evaluator
requires unique increasing radii. Demo 23 therefore uses one explicit
Gamma-origin path for production and keeps the second direction separate as an
isotropy diagnostic. A failed isotropy gate requires a future/direct physical
2D integration rather than silently forcing radial reduction.

