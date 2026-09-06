# 27C: the one controlled change

**Declared change.** The number of states solved and written. Geometry, mesh, temperature, k range and k sampling are all the Demo 23 baseline, so any new state is a property of the structure and not of a changed calculation.

**Fields this sub-demo is permitted to change:** `num_electrons`, `num_holes`, `output_state_count`

Everything else is inherited verbatim from the Demo 23 baseline. `registry.resolve`
raises if a deck changes a field that is not in the list above, so this document
cannot drift from what was actually generated.

## extended_states_e20_h28.in

*Which states exist between the Demo 23 window and the barrier continuum?*

Changed deck fields:

| field | baseline | this deck |
|---|---|---|
| num_electrons | 6 | 20 |
| num_holes | 8 | 28 |
| output_state_count | 14 | 48 |

Structural deck lines that differ from the baseline deck: **0**
