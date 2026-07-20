# Module 4: Experimental Metrology and MBE Growth

### 1. Molecular Beam Epitaxy (MBE) with Interface Control
The quality of the ACQW interfaces directly governs the energy level alignment and wavefunction profiles.
* **Compositional Grading:** High-resolution scanning transmission electron microscopy (STEM) and energy-dispersive X-ray spectroscopy (EDS) reveal that typical MBE growths suffer from a $\sim 1\text{ nm}$ compositional transition at the GaAs/AlGaAs interfaces. 
* **The Threat of Grading:** This $1\text{ nm}$ blur shifts the subband energy levels away from the precise resonance condition and reduces the diagonal matrix elements, dropping the theoretical $\chi^{(2)}$ from $\sim 2340\text{ pm/V}$ to $\sim 1200\text{ pm/V}$.
* **Mitigation (Growth Interruptions):** Pausing the molecular beams (shutters closed, arsenic flux maintained) for 5 to 30 seconds at each heterointerface allows surface adatoms to migrate and flatten. This successfully sharpens the interfaces, pushing the experimental $\chi^{(2)}$ back toward the idealized prediction.

### 2. Substrate Transfer (Flip-Chip)
Because the bulk GaAs growth substrate is highly non-linear (creating background interference) and strongly absorbs the generated $775\text{ nm}$ light, a precise substrate transfer workflow is required:

1. **MBE Growth:** Grow the AlGaAs etch-stop layer followed by the active ACQW multi-period stack on a sacrificial GaAs substrate.
2. **Flip-Chip Bonding:** Flip the stack upside down and epoxy-bond it to a highly transparent, weakly non-linear Sapphire Substrate.
3. **Substrate Removal:** Mechanically thin the GaAs growth substrate, then use selective chemical wet etches to clean off the remaining GaAs, stopping perfectly at the AlGaAs etch-stop layer.

### 3. Azimuthal Rotation-Angle SHG
To isolate the engineered quantum well nonlinearity from bulk and surface background signals, researchers perform **rotation-angle surface SHG**:
1. **Angle of Incidence:** The sample is tilted at a $45^\circ$ angle. This ensures that the incoming $p$-polarized light has an electric field component along the $z$-direction (growth axis), which is required to drive the out-of-plane quantum well transitions.
2. **Azimuthal Rotation:** The sample is rotated $360^\circ$ around its surface normal.
3. **Symmetry Signature:** The zincblende crystal structure of the GaAs cap and substrate remnants yields a characteristic four-lobed pattern under azimuthal rotation, reflecting its $S_4$ point-group symmetry. Deviations and resonant peaks in this pattern uniquely distinguish the engineered ACQW contribution from standard bulk background.