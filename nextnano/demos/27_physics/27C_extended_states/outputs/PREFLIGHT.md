# 27C preflight

**Extended state capture - are e1, e2, hh1, hh2 enough?**

Question: Are the four states Equation 2 currently uses sufficient, or do other states carry optical weight?

Pass condition: E_n(k) is available for every requested state over the whole k path, each state carries a physical identity (CB/HH/LH/SO fractions, localization, confinement) rather than an energy index, and every candidate transition in the search window is classified bound / quasi-bound / continuum. The ~2.296 eV question is answered with evidence, not assumed: Demo 24 showed no bound-bound transition in this structure can exceed the 2.145 eV barrier gap, so a bound candidate there would contradict that and needs the stronger evidence.

## Generated decks

| deck | band_model | k_mode | k_points | kmax_per_nm | states_out | electrostatics | interface_model | changed_fields | structural_diff_lines |
|---|---|---|---|---|---|---|---|---|---|
| extended_states_e20_h28.in | kp8 | dispersion | 301 | 0.555714 | 48 | flat_band | linear_graded | num_electrons;num_holes;output_state_count | 0 |

## Syntax validation (`nextnano++ --parse`)

| deck | parse_ok | message |
|---|---|---|
| extended_states_e20_h28.in | True | parsed |

`--parse` validates grammar only. A deck that parses can still be
physically wrong, which is why every physics stage writes a manifest and
audits the files that actually appear.

# 27C cost statement

**Read this before launching the physics stage.** These are planning estimates.

| Item | Value |
|---|---|
| Tier | 2 |
| nextnano++ Professional required | yes |
| Decks | 1 |
| k points per deck | [301] |
| Total k-point solves | 301 |
| States solved/output per deck | [48] |
| Estimated wall time | 30 min - 2 h |
| Estimated output volume | 1 - 3 GB |

**Basis for the estimate.** Demo 23 solved 301 k points for 14 states in 10 min 20 s. The eigenvalue cost grows faster than linearly in the state count, so 48 states is taken as 3-10x that. Envelopes are written at k=0 only unless 27A unlocks per-k output, which is why 27C is cheap compared with 27B.
