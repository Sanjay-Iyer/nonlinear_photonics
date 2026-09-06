# 27F: the one controlled change

**Declared change.** One numerical knob per deck, against the shared Demo 23 baseline. The sub-demo owns several knobs because the question is about the numerical domain as a whole, but no single deck turns more than one of them - except the state-count deck, where raising the number of states written requires raising the number solved.

**Fields this sub-demo is permitted to change:** `active_spacing_nm`, `boundary`, `num_electrons`, `num_holes`, `output_state_count`, `period_barrier_nm`, `quantum_region_padding_nm`

Everything else is inherited verbatim from the Demo 23 baseline. `registry.resolve`
raises if a deck changes a field that is not in the list above, so this document
cannot drift from what was actually generated.

## mesh_fine_0p025nm.in

*Is the 0.05 nm active mesh converged?*

Changed deck fields:

| field | baseline | this deck |
|---|---|---|
| active_spacing_nm | 0.05 | 0.025 |

Structural deck lines that differ from the baseline deck: **8**

```diff
-line{ pos = 9.1 spacing = 0.05 }
-line{ pos = 16.2 spacing = 0.05 }
-line{ pos = 18.0 spacing = 0.05 }
-line{ pos = 20.9 spacing = 0.05 }
+line{ pos = 9.1 spacing = 0.025 }
+line{ pos = 16.2 spacing = 0.025 }
+line{ pos = 18.0 spacing = 0.025 }
+line{ pos = 20.9 spacing = 0.025 }
```

## mesh_coarse_0p100nm.in

*How far does a coarser mesh move the states? (sets the convergence slope)*

Changed deck fields:

| field | baseline | this deck |
|---|---|---|
| active_spacing_nm | 0.05 | 0.1 |

Structural deck lines that differ from the baseline deck: **8**

```diff
-line{ pos = 9.1 spacing = 0.05 }
-line{ pos = 16.2 spacing = 0.05 }
-line{ pos = 18.0 spacing = 0.05 }
-line{ pos = 20.9 spacing = 0.05 }
+line{ pos = 9.1 spacing = 0.1 }
+line{ pos = 16.2 spacing = 0.1 }
+line{ pos = 18.0 spacing = 0.1 }
+line{ pos = 20.9 spacing = 0.1 }
```

## padding_4nm.in

*Do the states depend on where the Dirichlet walls are placed?*

Changed deck fields:

| field | baseline | this deck |
|---|---|---|
| quantum_region_padding_nm | 2.0 | 4.0 |

Structural deck lines that differ from the baseline deck: **0**

## padding_8nm.in

*Same question, further out - a physical state must stop moving*

Changed deck fields:

| field | baseline | this deck |
|---|---|---|
| quantum_region_padding_nm | 2.0 | 8.0 |

Structural deck lines that differ from the baseline deck: **0**

## outer_barrier_28p2nm.in

*Does a thicker outer barrier change the high states or the continuum onset?*

Changed deck fields:

| field | baseline | this deck |
|---|---|---|
| period_barrier_nm | 18.2 | 28.2 |

Structural deck lines that differ from the baseline deck: **24**

```diff
-line{ pos = 9.1 spacing = 0.05 }
-line{ pos = 16.2 spacing = 0.05 }
-line{ pos = 18.0 spacing = 0.05 }
-line{ pos = 20.9 spacing = 0.05 }
-line{ pos = 30.0 spacing = 0.5 }
+line{ pos = 14.1 spacing = 0.05 }
+line{ pos = 21.2 spacing = 0.05 }
+line{ pos = 23.0 spacing = 0.05 }
+line{ pos = 25.9 spacing = 0.05 }
+line{ pos = 40.0 spacing = 0.5 }
-region{ line{ x = [0.0, 30.0] } contact{ name = qw_contact } }
-region{ line{ x = [9.1, 16.2] } binary{ name = "GaAs" } }
-region{ line{ x = [18.0, 20.9] } binary{ name = "GaAs" } }
-region{ line{ x = [8.6, 9.6] } ternary_linear{ name = "Al(x)Ga(1-x)As" alloy_x = [0.55, 0.0] x = [8.6, 9.6] } }
-region{ line{ x = [15.7, 16.7] } ternary_linear{ name = "Al(x)Ga(1-x)As" alloy_x = [0.0, 0.55] x = [15.7, 16.7] } }
-region{ line{ x = [17.5, 18.5] } ternary_linear{ name = "Al(x)Ga(1-x)As" alloy_x = [0.55, 0.0] x = [17.5, 18.5] } }
-region{ line{ x = [20.4, 21.4] } ternary_linear{ name = "Al(x)Ga(1-x)As" alloy_x = [0.0, 0.55] x = [20.4, 21.4] } }
+region{ line{ x = [0.0, 40.0] } contact{ name = qw_contact } }
+region{ line{ x = [14.1, 21.2] } binary{ name = "GaAs" } }
+region{ line{ x = [23.0, 25.9] } binary{ name = "GaAs" } }
+region{ line{ x = [13.6, 14.6] } ternary_linear{ name = "Al(x)Ga(1-x)As" alloy_x = [0.55, 0.0] x = [13.6, 14.6] } }
+region{ line{ x = [20.7, 21.7] } ternary_linear{ name = "Al(x)Ga(1-x)As" alloy_x = [0.0, 0.55] x = [20.7, 21.7] } }
+region{ line{ x = [22.5, 23.5] } ternary_linear{ name = "Al(x)Ga(1-x)As" alloy_x = [0.55, 0.0] x = [22.5, 23.5] } }
+region{ line{ x = [25.4, 26.4] } ternary_linear{ name = "Al(x)Ga(1-x)As" alloy_x = [0.0, 0.55] x = [25.4, 26.4] } }
```

## states_24.in

*Does simply asking for more states create new levels below the ones we use?*

Changed deck fields:

| field | baseline | this deck |
|---|---|---|
| num_electrons | 6 | 10 |
| num_holes | 8 | 14 |
| output_state_count | 14 | 24 |

Structural deck lines that differ from the baseline deck: **0**

## boundary_neumann.in

*Is any state an artifact of the Dirichlet wall rather than of the barriers?*

Changed deck fields:

| field | baseline | this deck |
|---|---|---|
| boundary | dirichlet | neumann |

Structural deck lines that differ from the baseline deck: **0**
