# 27H: the one controlled change

**Declared change.** The in-plane direction of the dispersion path, and nothing else. Growth is along [100] throughout, so [010] and [001] are symmetry-equivalent and the physically distinct sweep is from [010] to [011].

**Fields this sub-demo is permitted to change:** `direction`, `direction_name`

Everything else is inherited verbatim from the Demo 23 baseline. `registry.resolve`
raises if a deck changes a field that is not in the list above, so this document
cannot drift from what was actually generated.

## dir_yz15.in

*15 degrees off [010] - where does the anisotropy first appear?*

Changed deck fields:

| field | baseline | this deck |
|---|---|---|
| direction | (0.0, 1.0, 0.0) | (0.0, 0.9659258262890683, 0.25881904510252074) |
| direction_name | y | yz15 |

Structural deck lines that differ from the baseline deck: **0**

## dir_yz30.in

*30 degrees off [010]*

Changed deck fields:

| field | baseline | this deck |
|---|---|---|
| direction | (0.0, 1.0, 0.0) | (0.0, 0.8660254037844387, 0.49999999999999994) |
| direction_name | y | yz30 |

Structural deck lines that differ from the baseline deck: **0**

## dir_yz60.in

*60 degrees off [010] - past the [011] diagonal Demo 23 already has*

Changed deck fields:

| field | baseline | this deck |
|---|---|---|
| direction | (0.0, 1.0, 0.0) | (0.0, 0.49999999999999994, 0.8660254037844387) |
| direction_name | y | yz60 |

Structural deck lines that differ from the baseline deck: **0**
