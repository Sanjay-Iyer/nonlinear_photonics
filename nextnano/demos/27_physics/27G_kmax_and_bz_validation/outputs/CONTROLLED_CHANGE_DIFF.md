# 27G: the one controlled change

**Declared change.** The in-plane cutoff only. The k-point count moves with it so that the k spacing stays at the Demo 23 value - widening the range while holding the point count fixed would confound a cutoff effect with a sampling effect, and Demo 24 has already shown this spectrum is sensitive to both.

**Fields this sub-demo is permitted to change:** `k_points`, `kmax_per_nm`, `relative_size`

Everything else is inherited verbatim from the Demo 23 baseline. `registry.resolve`
raises if a deck changes a field that is not in the list above, so this document
cannot drift from what was actually generated.

## bz_0p15_pi_over_a.in

*Intermediate cutoff - does the 1250-1450 nm feature keep marching?*

Changed deck fields:

| field | baseline | this deck |
|---|---|---|
| k_points | 301 | 451 |
| kmax_per_nm | 0.5557144392322634 | 0.8335716588483951 |
| relative_size | 0.1 | 0.15 |

Structural deck lines that differ from the baseline deck: **0**

## bz_0p10_gamma_x.in

*The competing reading of the paper - 0.1 |Gamma-X| = 0.2 pi/a*

Changed deck fields:

| field | baseline | this deck |
|---|---|---|
| k_points | 301 | 601 |
| kmax_per_nm | 0.5557144392322634 | 1.1114288784645268 |

Structural deck lines that differ from the baseline deck: **0**

## bz_0p30_pi_over_a.in

*Past both readings - has the response actually saturated?*

Changed deck fields:

| field | baseline | this deck |
|---|---|---|
| k_points | 301 | 901 |
| kmax_per_nm | 0.5557144392322634 | 1.6671433176967903 |
| relative_size | 0.1 | 0.3 |

Structural deck lines that differ from the baseline deck: **0**
