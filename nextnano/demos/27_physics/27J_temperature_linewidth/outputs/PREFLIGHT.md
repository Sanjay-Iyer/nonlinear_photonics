# 27J preflight

**Temperature-dependent parameters and physically motivated linewidths**

Question: Do temperature-dependent material parameters or improved linewidths explain the remaining peak shifts?

Pass condition: Two things are reported separately. (a) The measured band-gap and state-energy shift per kelvin, converted into a wavelength shift per feature using Demo 24's measured dLambda/dE, so the temperature effect is compared against the actual paper-model gaps rather than asserted. (b) A linewidth study in which every Gamma model is PHYSICALLY MOTIVATED - state-dependent, energy-dependent or k-dependent from a stated mechanism. Demo 26 already found that no single Gamma repairs all features (its hypothesis 8, "NOT SUFFICIENT", high confidence), so using Gamma as a free fitting parameter is out of scope and a fitted Gamma is not an acceptable conclusion here.

## Generated decks

| deck | band_model | k_mode | k_points | kmax_per_nm | states_out | electrostatics | interface_model | changed_fields | structural_diff_lines |
|---|---|---|---|---|---|---|---|---|---|
| T_077K.in | kp8 | dispersion | 301 | 0.555714 | 14 | flat_band | linear_graded | temperature_K | 2 |
| T_200K.in | kp8 | dispersion | 301 | 0.555714 | 14 | flat_band | linear_graded | temperature_K | 2 |

## Syntax validation (`nextnano++ --parse`)

| deck | parse_ok | message |
|---|---|---|
| T_077K.in | True | parsed |
| T_200K.in | True | parsed |

`--parse` validates grammar only. A deck that parses can still be
physically wrong, which is why every physics stage writes a manifest and
audits the files that actually appear.

# 27J cost statement

**Read this before launching the physics stage.** These are planning estimates.

| Item | Value |
|---|---|
| Tier | 2 |
| nextnano++ Professional required | yes |
| Decks | 2 |
| k points per deck | [301, 301] |
| Total k-point solves | 602 |
| States solved/output per deck | [14, 14] |
| Estimated wall time | 18 min - 1 h |
| Estimated output volume | 0.6 - 1.6 GB |

**Basis for the estimate.** Two decks at the measured Demo 23 production cost of 10 min 20 s each. The 300 K arm is reused from demo_results/demo23/raw/production_y_n301_k0100. The linewidth half of this sub-demo adds no solver cost at all.
