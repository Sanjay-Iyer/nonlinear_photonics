# 27I: the one controlled change

**Declared change.** The quantum model. The single-band deck also drops the k path, because a decoupled Gamma/HH model has no in-plane k dependence to sample in this deck form - that is the second field, and it is a consequence of the first rather than an independent choice.

**Fields this sub-demo is permitted to change:** `band_model`, `k_mode`

Everything else is inherited verbatim from the Demo 23 baseline. `registry.resolve`
raises if a deck changes a field that is not in the list above, so this document
cannot drift from what was actually generated.

## model_kp6_valence.in

*Which features survive a 6-band valence treatment with a decoupled conduction band?*

Changed deck fields:

| field | baseline | this deck |
|---|---|---|
| band_model | kp8 | kp6 |

Structural deck lines that differ from the baseline deck: **0**

## model_single_band.in

*Which features survive a decoupled parabolic Gamma/HH treatment?*

Changed deck fields:

| field | baseline | this deck |
|---|---|---|
| band_model | kp8 | single_band |
| k_mode | dispersion | none |

Structural deck lines that differ from the baseline deck: **0**
