# 27H preflight

**In-plane crystal-direction anisotropy**

Question: Is the radial (isotropic) in-plane assumption valid for these states and matrix elements?

Pass condition: E_n(k), state character, HH/LH mixing and the optical matrix elements are compared across the in-plane angles. PASS is reached when the maximum angular spread is quantified against an explicit tolerance and the recommendation for 27L is stated. If the spread is negligible, the correct outcome is to record 27L as NOT NEEDED - that is a successful result, not a failure.

## Generated decks

| deck | band_model | k_mode | k_points | kmax_per_nm | states_out | electrostatics | interface_model | changed_fields | structural_diff_lines |
|---|---|---|---|---|---|---|---|---|---|
| dir_yz15.in | kp8 | dispersion | 301 | 0.555714 | 14 | flat_band | linear_graded | direction;direction_name | 0 |
| dir_yz30.in | kp8 | dispersion | 301 | 0.555714 | 14 | flat_band | linear_graded | direction;direction_name | 0 |
| dir_yz60.in | kp8 | dispersion | 301 | 0.555714 | 14 | flat_band | linear_graded | direction;direction_name | 0 |

## Syntax validation (`nextnano++ --parse`)

| deck | parse_ok | message |
|---|---|---|
| dir_yz15.in | True | parsed |
| dir_yz30.in | True | parsed |
| dir_yz60.in | True | parsed |

`--parse` validates grammar only. A deck that parses can still be
physically wrong, which is why every physics stage writes a manifest and
audits the files that actually appear.

# 27H cost statement

**Read this before launching the physics stage.** These are planning estimates.

| Item | Value |
|---|---|
| Tier | 2 |
| nextnano++ Professional required | yes |
| Decks | 3 |
| k points per deck | [301, 301, 301] |
| Total k-point solves | 903 |
| States solved/output per deck | [14, 14, 14] |
| Estimated wall time | 30 min - 1.5 h |
| Estimated output volume | 0.9 - 2.5 GB |

**Basis for the estimate.** Three decks at the measured Demo 23 production cost of 10 min 20 s each, plus margin. The two endpoint directions are reused rather than recomputed.
