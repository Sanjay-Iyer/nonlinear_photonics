# 27K: the one controlled change

**Declared change.** Many more states than the structure binds, solved on three different numerical domains. The state count is the sub-demo's subject; the domain is varied because that is the only way to tell a real quasi-bound resonance from a Dirichlet box level, and holding it fixed would make the question unanswerable rather than controlled.

**Fields this sub-demo is permitted to change:** `num_electrons`, `num_holes`, `output_state_count`, `period_barrier_nm`, `quantum_region_padding_nm`

Everything else is inherited verbatim from the Demo 23 baseline. `registry.resolve`
raises if a deck changes a field that is not in the list above, so this document
cannot drift from what was actually generated.

## continuum_pad2_outer18.in

*What lies above the barrier edge on the Demo 23 domain?*

Changed deck fields:

| field | baseline | this deck |
|---|---|---|
| num_electrons | 6 | 28 |
| num_holes | 8 | 36 |
| output_state_count | 14 | 64 |

Structural deck lines that differ from the baseline deck: **0**

## continuum_pad8_outer18.in

*Which of those states move when the Dirichlet walls move?*

Changed deck fields:

| field | baseline | this deck |
|---|---|---|
| num_electrons | 6 | 28 |
| num_holes | 8 | 36 |
| output_state_count | 14 | 64 |
| quantum_region_padding_nm | 2.0 | 8.0 |

Structural deck lines that differ from the baseline deck: **0**

## continuum_pad2_outer34.in

*Which of them move when the outer barrier gets thicker?*

Changed deck fields:

| field | baseline | this deck |
|---|---|---|
| num_electrons | 6 | 28 |
| num_holes | 8 | 36 |
| output_state_count | 14 | 64 |
| period_barrier_nm | 18.2 | 34.2 |

Structural deck lines that differ from the baseline deck: **24**

```diff
-line{ pos = 9.1 spacing = 0.05 }
-line{ pos = 16.2 spacing = 0.05 }
-line{ pos = 18.0 spacing = 0.05 }
-line{ pos = 20.9 spacing = 0.05 }
-line{ pos = 30.0 spacing = 0.5 }
+line{ pos = 17.1 spacing = 0.05 }
+line{ pos = 24.2 spacing = 0.05 }
+line{ pos = 26.0 spacing = 0.05 }
+line{ pos = 28.9 spacing = 0.05 }
+line{ pos = 46.0 spacing = 0.5 }
-region{ line{ x = [0.0, 30.0] } contact{ name = qw_contact } }
-region{ line{ x = [9.1, 16.2] } binary{ name = "GaAs" } }
-region{ line{ x = [18.0, 20.9] } binary{ name = "GaAs" } }
-region{ line{ x = [8.6, 9.6] } ternary_linear{ name = "Al(x)Ga(1-x)As" alloy_x = [0.55, 0.0] x = [8.6, 9.6] } }
-region{ line{ x = [15.7, 16.7] } ternary_linear{ name = "Al(x)Ga(1-x)As" alloy_x = [0.0, 0.55] x = [15.7, 16.7] } }
-region{ line{ x = [17.5, 18.5] } ternary_linear{ name = "Al(x)Ga(1-x)As" alloy_x = [0.55, 0.0] x = [17.5, 18.5] } }
-region{ line{ x = [20.4, 21.4] } ternary_linear{ name = "Al(x)Ga(1-x)As" alloy_x = [0.0, 0.55] x = [20.4, 21.4] } }
+region{ line{ x = [0.0, 46.0] } contact{ name = qw_contact } }
+region{ line{ x = [17.1, 24.2] } binary{ name = "GaAs" } }
+region{ line{ x = [26.0, 28.9] } binary{ name = "GaAs" } }
+region{ line{ x = [16.6, 17.6] } ternary_linear{ name = "Al(x)Ga(1-x)As" alloy_x = [0.55, 0.0] x = [16.6, 17.6] } }
+region{ line{ x = [23.7, 24.7] } ternary_linear{ name = "Al(x)Ga(1-x)As" alloy_x = [0.0, 0.55] x = [23.7, 24.7] } }
+region{ line{ x = [25.5, 26.5] } ternary_linear{ name = "Al(x)Ga(1-x)As" alloy_x = [0.55, 0.0] x = [25.5, 26.5] } }
+region{ line{ x = [28.4, 29.4] } ternary_linear{ name = "Al(x)Ga(1-x)As" alloy_x = [0.0, 0.55] x = [28.4, 29.4] } }
```
