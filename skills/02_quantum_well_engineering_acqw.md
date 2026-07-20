# Module 2: Quantum Well Engineering and Asymmetric Coupled Quantum Wells (ACQWs)

### 1. Quantum Wells and Bandgap Engineering
When a thin layer of a narrow-bandgap semiconductor (GaAs, $E_g \approx 1.42\text{ eV}$) is sandwiched between wider-bandgap barriers ($\text{Al}_{0.55}\text{Ga}_{0.45}\text{As}$, $E_g \approx 2.1\text{ eV}$), carriers are confined along the growth axis ($z$). This 1D confinement quantizes the allowed energy levels into subbands. 

Unlike prior engineering efforts that utilized **intersubband transitions** (restricted to the mid-infrared, $\sim 10\ \mu\text{m}$, because of conduction-band offset limitations), this design leverages **interband transitions** (valence band to conduction band). This shifts the operating wavelength into the near-infrared and visible regimes ($\sim 1550\text{ nm}$ fundamental, $\sim 775\text{ nm}$ second-harmonic), unlocking telecommunications and integrated quantum optical circuits.

### 2. Wavefunction Hybridization in Asymmetric Wells
By stacking two GaAs wells of unequal widths ($d_1 = 7.1\text{ nm}$, $d_2 = 2.9\text{ nm}$) separated by an ultrathin, tunneling-allowed $\text{Al}_{0.55}\text{Ga}_{0.45}\text{As}$ barrier ($1.8\text{ nm}$), the electron and hole wavefunctions hybridize across the barrier, forming molecular-like bonding and anti-bonding envelopes.

* **Asymmetric Centroids:** Because the wells have different widths, the probability densities (centroids) of the electronic states are spatially shifted relative to one another. This physical displacement acts as a permanent dipole moment along the z-axis, keeping $\langle \psi_n | z | \psi_n \rangle \neq 0$ and bypassing the pairwise pathway cancellations that completely kill $\chi^{(2)}$ in symmetric structures.

### 3. The Asymmetry Parameter ($s$)
The structural asymmetry is mathematically defined as:

$$s = \frac{d_1 - d_2}{d_1 + d_2}$$

* If $s = 0$ (symmetric double well), the spatial centroids of the wavefunctions are symmetric, and their contributions to the second-order susceptibility cancel out ($\chi^{(2)} = 0$).
* If $s = 1$ (single quantum well), the system is centrosymmetric with respect to its center.
* Optimizing $s$ balances the transition dipole moments and the spatial asymmetry. For GaAs/AlGaAs, simulations identify **$s \approx 0.42$** as the sweet spot, yielding a $\chi^{(2)}$ of thousands of $\text{pm/V}$.