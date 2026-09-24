# Demo 29 results

**300 K matched Professional pair acquired; 29C mixed control computed.** The
original work-run folder was returned outside Git at
`nextnano_raw/demo29_300K_original_solver/300K`. The executed decks, both job
statuses, 301-point 0.10π/a dispersion, k=0 composition, and single-band
anchors/envelopes passed local validation. The resulting 300 K historical
mixed-model spectrum is in `outputs/29C_mixed_control/300K/` on HOME.

| 300 K mixed-control quantity | Value |
|---|---:|
| Re χ² at 1550 nm | +26.4702 pm/V |
| Im χ² at 1550 nm | +0.7973 pm/V |
| Dominant \|Re χ²\| | 71.3106 pm/V at 1505 nm |
| Dominant \|Im χ²\| | 57.8979 pm/V at 1496 nm |

The selected k=0 8-band doublets were electron indices `(11,12)` and `(13,14)`
at 2.952511679 and 3.091148452 eV, and valence indices `(5,6)` and `(3,4)`
at 1.443772122 and 1.416747842 eV. `(5,6)` is HH dominated; `(3,4)` is
97.6% LH. The latter is deliberately retained only in the historical mixed
control, not silently labeled HH in the new primary model.

**29A full 8-band remains blocked.** The Professional `output_states` export
has only k=0 envelopes/composition despite 301 dispersion points. The attempted
full-8-band packer correctly rejected the run, and no finite-k position matrix
or full-8-band χ² spectrum was produced. The interband optical operator/spin
mapping also remains unresolved. The current 100/500 K acquisition is paused
until a supported full-8-band data path is established.

The control result is a same-temperature **mixed** calculation and retains
single-band k=0 matrix elements with `M(k)=M(0)`. It is not evidence that the
full-8-band model is complete. The old Demo 28 mixed 300 K curve can be added
only as a labeled historical comparison; no numerical match is required.

After the same frozen workflow processes new 100 K and 500 K data, add signed
Re/Im and |Re| temperature overlays, χ² at 1550 nm, key transition energies,
major feature locations, and a concise primary-versus-control trend summary.
