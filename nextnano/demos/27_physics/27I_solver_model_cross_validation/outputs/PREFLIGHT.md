# 27I preflight

**Solver and model cross-validation**

Question: Which spectral features come specifically from the 8-band k.p treatment?

Pass condition: The same physical structure is solved with three models and the state energies, transition energies and optical matrix elements are tabulated side by side. PASS means each of the six Equation 2 features is attributed to the simplest model that reproduces it. The comparison must be like-for-like: the geometry, mesh, temperature and domain are identical across arms, which is exactly what the single controlled change guarantees.

## Generated decks

| deck | band_model | k_mode | k_points | kmax_per_nm | states_out | electrostatics | interface_model | changed_fields | structural_diff_lines |
|---|---|---|---|---|---|---|---|---|---|
| model_kp6_valence.in | kp6 | dispersion | 301 | 0.555714 | 14 | flat_band | linear_graded | band_model | 0 |
| model_single_band.in | single_band | none | 301 | 0.555714 | 14 | flat_band | linear_graded | band_model;k_mode | 0 |

## Syntax validation (`nextnano++ --parse`)

| deck | parse_ok | message |
|---|---|---|
| model_kp6_valence.in | True | parsed |
| model_single_band.in | True | parsed |

`--parse` validates grammar only. A deck that parses can still be
physically wrong, which is why every physics stage writes a manifest and
audits the files that actually appear.

# 27I cost statement

**Read this before launching the physics stage.** These are planning estimates.

| Item | Value |
|---|---|
| Tier | 1 |
| nextnano++ Professional required | yes |
| Decks | 2 |
| k points per deck | [301, 0] |
| Total k-point solves | 301 |
| States solved/output per deck | [14, 14] |
| Estimated wall time | 6 min - 30 min |
| Estimated output volume | 0.1 - 0.5 GB |

**Basis for the estimate.** The single-band arm is an ordinary 1D Schroedinger solve on 600 grid points and takes seconds. The kp6 arm is the Demo 23 production cost scaled by roughly (6/8), i.e. minutes. The kp8 arm is not rerun: it is demo_results/demo23/raw/production_y_n301_k0100 on this exact structure.
