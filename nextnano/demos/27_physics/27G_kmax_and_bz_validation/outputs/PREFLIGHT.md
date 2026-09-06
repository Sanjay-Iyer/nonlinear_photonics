# 27G preflight

**kmax and Brillouin-zone convention validation**

Question: What does the paper's "one tenth of the Brillouin zone" physically correspond to?

Pass condition: The chi2 spectrum is computed out to at least 0.2 pi/a, and every spectral feature is classified as either STABLE (its position stops moving as kmax grows) or CUTOFF ARTIFACT (its position tracks the zone-edge transition energy). Demo 24 already showed that the model's own 1250-1450 nm structure is the second kind: it marched 1502 -> 1431 -> 1376 -> 1318 nm as kmax went 0.05 -> 0.125 pi/a and tracked 2hc/DeltaE(kmax) to 9 nm, while the two real peaks moved less than 1 nm. PASS means every feature carries that label out to the Gamma-X reading of the paper's cutoff.

## Generated decks

| deck | band_model | k_mode | k_points | kmax_per_nm | states_out | electrostatics | interface_model | changed_fields | structural_diff_lines |
|---|---|---|---|---|---|---|---|---|---|
| bz_0p15_pi_over_a.in | kp8 | dispersion | 451 | 0.833572 | 14 | flat_band | linear_graded | k_points;kmax_per_nm;relative_size | 0 |
| bz_0p10_gamma_x.in | kp8 | dispersion | 601 | 1.111429 | 14 | flat_band | linear_graded | k_points;kmax_per_nm | 0 |
| bz_0p30_pi_over_a.in | kp8 | dispersion | 901 | 1.667143 | 14 | flat_band | linear_graded | k_points;kmax_per_nm;relative_size | 0 |

## Syntax validation (`nextnano++ --parse`)

| deck | parse_ok | message |
|---|---|---|
| bz_0p15_pi_over_a.in | True | parsed |
| bz_0p10_gamma_x.in | True | parsed |
| bz_0p30_pi_over_a.in | True | parsed |

`--parse` validates grammar only. A deck that parses can still be
physically wrong, which is why every physics stage writes a manifest and
audits the files that actually appear.

# 27G cost statement

**Read this before launching the physics stage.** These are planning estimates.

| Item | Value |
|---|---|
| Tier | 2 |
| nextnano++ Professional required | yes |
| Decks | 3 |
| k points per deck | [451, 601, 901] |
| Total k-point solves | 1953 |
| States solved/output per deck | [14, 14, 14] |
| Estimated wall time | 1 h - 3 h |
| Estimated output volume | 0.8 - 2.5 GB |

**Basis for the estimate.** Demo 23 measured 301 k points x 14 states at 10 min 20 s, i.e. about 2 s per k point. The k spacing is held at the Demo 23 value, so widening the range widens the point count proportionally: 451, 601 and 901 points for 0.15, 0.20 and 0.30 pi/a. That is roughly 2000 k-point solves, or 1-3 h with margin. Only three decks are new: 0.10 pi/a is demo_results/demo23/raw/ production_y_n301_k0100 and 0.125 pi/a is kmax_y_n301_k0125, both already computed on this exact structure.
