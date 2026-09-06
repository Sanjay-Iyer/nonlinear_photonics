# 27L: the one controlled change

**Declared change.** The k sampling changes from a 1D radial path to the 2D k-integration grid. The point count changes with it because 61 points along a path and 61 points across a 2D grid are not the same object; the cutoff, the structure and the state count are the Demo 23 baseline.

**Fields this sub-demo is permitted to change:** `k_mode`, `k_points`, `symmetry`

Everything else is inherited verbatim from the Demo 23 baseline. `registry.resolve`
raises if a deck changes a field that is not in the list above, so this document
cannot drift from what was actually generated.

## k2d_integration_n61.in

*Does the 2D in-plane integral differ from the radial one?*

Changed deck fields:

| field | baseline | this deck |
|---|---|---|
| k_mode | dispersion | integration |
| k_points | 301 | 61 |

Structural deck lines that differ from the baseline deck: **0**
