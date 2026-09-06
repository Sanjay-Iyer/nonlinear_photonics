# 27J: the one controlled change

**Declared change.** The lattice temperature, which drives nextnano's temperature-dependent band parameters. Nothing else moves, so any energy shift is attributable to the material model rather than to the structure.

**Fields this sub-demo is permitted to change:** `temperature_K`

Everything else is inherited verbatim from the Demo 23 baseline. `registry.resolve`
raises if a deck changes a field that is not in the list above, so this document
cannot drift from what was actually generated.

## T_077K.in

*How far do the states and the gap move at liquid-nitrogen temperature?*

Changed deck fields:

| field | baseline | this deck |
|---|---|---|
| temperature_K | 300.0 | 77.0 |

Structural deck lines that differ from the baseline deck: **2**

```diff
-temperature = 300.0
+temperature = 77.0
```

## T_200K.in

*Intermediate point, so the shift is measured as a slope rather than from two ends*

Changed deck fields:

| field | baseline | this deck |
|---|---|---|
| temperature_K | 300.0 | 200.0 |

Structural deck lines that differ from the baseline deck: **2**

```diff
-temperature = 300.0
+temperature = 200.0
```
