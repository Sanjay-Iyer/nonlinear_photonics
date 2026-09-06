# 27E: the one controlled change

**Declared change.** Whether Poisson is solved self-consistently with the Schroedinger equation. Both decks are otherwise the Demo 23 baseline structure, so the pair isolates electrostatics. Note that the flat-band arm is regenerated rather than reused from Demo 23: if 27D changes the geometry decision, both arms must move together, and a control from a different structure would not be a control.

**Fields this sub-demo is permitted to change:** `electrostatics`

Everything else is inherited verbatim from the Demo 23 baseline. `registry.resolve`
raises if a deck changes a field that is not in the list above, so this document
cannot drift from what was actually generated.

## A_flat_band_control.in

*Control - the Demo 23 flat-band quantum solve, regenerated for a like-for-like pair*

Changed deck fields:

_none - this deck reproduces the Demo 23 baseline exactly._

Structural deck lines that differ from the baseline deck: **0**

## B_self_consistent.in

*Does self-consistent electrostatics move the states or the spectrum?*

Changed deck fields:

| field | baseline | this deck |
|---|---|---|
| electrostatics | flat_band | quantum_poisson |

Structural deck lines that differ from the baseline deck: **6**

```diff
+output_carrier_densities{}
+output_ionized_dopant_densities{}
+poisson{
+output_potential{}
+output_electric_field{}
+}
```
