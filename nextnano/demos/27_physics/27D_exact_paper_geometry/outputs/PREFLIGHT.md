# 27D preflight

**Exact paper geometry - abrupt interfaces versus 1 nm grading**

Question: Does the paper's abrupt-interface structure reproduce the spectrum better than our 1 nm graded structure?

Pass condition: The abrupt structure is solved with everything else held at the Demo 23 baseline, and the six Equation 2 features (P1 540, Z1 605, P2 760, P3 1080, Z2 1330, P4 1520 nm) are located in the normalized |chi2| for both structures and compared against the digitized paper curve. PASS means the comparison is made and the answer is stated either way. A result showing grading is NOT the explanation is a pass, and demotes hypothesis 1 in the Demo 26 ranking.

## Generated decks

| deck | band_model | k_mode | k_points | kmax_per_nm | states_out | electrostatics | interface_model | changed_fields | structural_diff_lines |
|---|---|---|---|---|---|---|---|---|---|
| abrupt_paper_geometry.in | kp8 | dispersion | 301 | 0.555714 | 14 | flat_band | abrupt | interface_model | 4 |

## Syntax validation (`nextnano++ --parse`)

| deck | parse_ok | message |
|---|---|---|
| abrupt_paper_geometry.in | True | parsed |

`--parse` validates grammar only. A deck that parses can still be
physically wrong, which is why every physics stage writes a manifest and
audits the files that actually appear.

# 27D cost statement

**Read this before launching the physics stage.** These are planning estimates.

| Item | Value |
|---|---|
| Tier | 2 |
| nextnano++ Professional required | yes |
| Decks | 1 |
| k points per deck | [301] |
| Total k-point solves | 301 |
| States solved/output per deck | [14] |
| Estimated wall time | 9 min - 30 min |
| Estimated output volume | 0.3 - 1 GB |

**Basis for the estimate.** One deck identical in cost to the Demo 23 production run (301 k points, 14 states, 10 min 20 s measured on the work laptop), plus margin. Only one deck is needed because the graded arm ALREADY EXISTS: demo_results/demo23/raw/ production_y_n301_k0100 is this exact structure and solver configuration, so rerunning it would buy nothing. See REUSE_AUDIT.md.
