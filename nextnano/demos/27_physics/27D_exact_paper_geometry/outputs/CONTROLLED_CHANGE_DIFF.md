# 27D: the one controlled change

**Declared change.** The interface model, and nothing else. Layer widths, Al fractions, mesh, temperature, state count, k range and k sampling are the Demo 23 baseline, so the only thing that can move a spectral feature is the interface abruptness. The geometry is NOT optimized here; 27D asks whether the paper's structure explains the disagreement, not which structure fits best.

**Fields this sub-demo is permitted to change:** `interface_model`

Everything else is inherited verbatim from the Demo 23 baseline. `registry.resolve`
raises if a deck changes a field that is not in the list above, so this document
cannot drift from what was actually generated.

## abrupt_paper_geometry.in

*Does the ideal abrupt structure move P1/Z1/P2/P3/Z2/P4 towards the paper?*

Changed deck fields:

| field | baseline | this deck |
|---|---|---|
| interface_model | linear_graded | abrupt |

Structural deck lines that differ from the baseline deck: **4**

```diff
-region{ line{ x = [8.6, 9.6] } ternary_linear{ name = "Al(x)Ga(1-x)As" alloy_x = [0.55, 0.0] x = [8.6, 9.6] } }
-region{ line{ x = [15.7, 16.7] } ternary_linear{ name = "Al(x)Ga(1-x)As" alloy_x = [0.0, 0.55] x = [15.7, 16.7] } }
-region{ line{ x = [17.5, 18.5] } ternary_linear{ name = "Al(x)Ga(1-x)As" alloy_x = [0.55, 0.0] x = [17.5, 18.5] } }
-region{ line{ x = [20.4, 21.4] } ternary_linear{ name = "Al(x)Ga(1-x)As" alloy_x = [0.0, 0.55] x = [20.4, 21.4] } }
```
