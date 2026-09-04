# Equation 2 Simplified Study Guide

## Purpose

This guide breaks down **every major term, subscript, symbol, and mathematical part** of Equation 2 from the Ramesh et al. coupled-quantum-well paper, then connects those terms to the changes introduced in the boss's derivation and to a practical Nextnano workflow.

The goal is to understand each piece in the simplest possible way before worrying about implementation details.

---

# 1. The whole equation

The paper's Equation 2 can be written approximately as

$$
\begin{aligned}
\chi^{(2)}_{xzx}(\omega_1,\omega_2)
&=
\frac{N_z e^3 r_{e,hh}^{2}}{6\epsilon_0\hbar^2}
\sum_{k_\parallel}\sum_{m,n}\sum_l
\Bigg[
\\[2pt]
&\quad
\frac{
\langle hh_m|e_n\rangle
\langle e_n|z|e_l\rangle
\langle e_l|hh_m\rangle
}{
(\omega^{e,n}_{hh,m}-\omega_1-\omega_2+i\Gamma)
(\omega^{e,l}_{hh,m}-\omega_1+i\Gamma)
}
\\[4pt]
&\quad-
\frac{
\langle e_n|hh_m\rangle
\langle hh_m|z|hh_l\rangle
\langle hh_l|e_n\rangle
}{
(\omega^{e,n}_{hh,m}-\omega_1-\omega_2+i\Gamma)
(\omega^{e,n}_{hh,l}-\omega_1+i\Gamma)
}
\Bigg].
\end{aligned}
$$

Do not try to memorize the full expression yet. The easiest mental model is

$$
\boxed{
\chi^{(2)}
=
\text{overall constants}
\times
\sum
\left[
\frac{\text{electron pathway}}{\text{resonance terms}}
-
\frac{\text{hole pathway}}{\text{resonance terms}}
\right].
}
$$

---

# 2. $\chi^{(2)}_{xzx}$

## What is it?

$$
\boxed{\chi^{(2)}_{xzx}}
$$

is the quantity being calculated.

It is the **second-order nonlinear optical susceptibility** of the quantum-well structure.

Simple meaning:

> It tells you how strongly the material can perform a second-order nonlinear optical process such as second-harmonic generation.

Large

$$
|\chi^{(2)}|
$$

means a strong nonlinear response.

Small

$$
|\chi^{(2)}|
$$

means a weak nonlinear response.

## What does the superscript $(2)$ mean?

It means **second-order** optical nonlinearity.

For second-harmonic generation (SHG),

$$
\omega+\omega\rightarrow 2\omega.
$$

---

# 3. What does $xzx$ mean?

The subscripts

$$
\boxed{xzx}
$$

tell you the directions of the three dipole interactions.

Think:

$$
x\rightarrow z\rightarrow x.
$$

The quantum wells are grown along the

$$
z
$$

direction, so the $z$-interaction is especially important because it probes the spatial asymmetry of the quantum well.

For now, remember:

$$
\boxed{xzx=\text{the particular polarization/tensor component being calculated}.}
$$

---

# 4. $\omega_1$ and $\omega_2$

$$
\boxed{\omega_1,\omega_2}
$$

are the angular frequencies of the two incoming photons.

For SHG,

$$
\boxed{\omega_1=\omega_2=\omega.}
$$

Therefore,

$$
\omega_1+\omega_2=2\omega.
$$

For the 1550 nm case,

$$
1550\ \mathrm{nm}+1550\ \mathrm{nm}\rightarrow775\ \mathrm{nm}.
$$

---

# 5. $N_z$

$$
\boxed{N_z}
$$

is the number of quantum wells per unit length.

Simple meaning:

> How much quantum-well material exists per unit length of the structure?

It is part of the overall scaling of the susceptibility.

Very roughly,

$$
\boxed{N_z\uparrow\Rightarrow \chi^{(2)}\text{ tends to increase}.}
$$

---

# 6. $e^3$

$$
\boxed{e}
$$

is the elementary charge.

The expression contains

$$
e^3.
$$

Why three powers? Because the second-order process contains three electric-dipole interactions.

This is a physical constant, not a design variable.

---

# 7. $\epsilon_0$

$$
\boxed{\epsilon_0}
$$

is the vacuum permittivity.

It appears as part of the electromagnetic normalization of susceptibility.

It is a physical constant and is not changed by the quantum-well design.

---

# 8. $\hbar$

$$
\boxed{\hbar}
$$

is the reduced Planck constant.

The most important relationship for this project is

$$
\boxed{E=\hbar\omega.}
$$

This connects the paper's frequency notation to the energy values obtained from Nextnano.

The boss later uses this relationship to rewrite the resonance denominators in terms of energies instead of angular frequencies.

---

# 9. $r_{e,hh}$

$$
\boxed{r_{e,hh}}
$$

is the **atomic-scale electron-heavy-hole interband matrix element**.

The paper defines it approximately as

$$
r_{e,hh}=\langle u_e^*|r|u_{hh}\rangle.
$$

Simple meaning:

> How intrinsically strong is the optical transition between the conduction-band and heavy-hole states at the crystal/unit-cell level?

This is **not** the same as the quantum-well envelope overlap.

Important distinction:

$$
\boxed{r_{e,hh}=\text{atomic-scale optical strength}}
$$

while

$$
\boxed{\langle\psi_{hh}|\psi_e\rangle=\text{QW-scale spatial overlap}.}
$$

In the paper,

$$
\boxed{r_{e,hh}\rightarrow\text{DFT/VASP HSE06}}
$$

while

$$
\boxed{\psi\rightarrow\text{Nextnano}.}
$$

---

# 10. Why is $r_{e,hh}$ squared?

Equation 2 contains

$$
\boxed{r_{e,hh}^2}.
$$

There are two interband electron-heavy-hole optical interactions in each pathway, so the atomic interband strength appears twice.

---

# 11. $\psi$: the envelope wavefunction

$$
\boxed{\psi}
$$

means an **envelope wavefunction**.

Examples:

$$
\psi_{e,1},\quad
\psi_{e,2},\quad
\psi_{hh,1},\quad
\psi_{hh,2}.
$$

Simple meaning:

> $\psi(z)$ tells you where the electron or hole state is located along the quantum-well growth direction.

These are the wavefunctions associated with the nanometer-scale heterostructure.

---

# 12. What does the $e$ subscript mean?

For

$$
\boxed{\psi_{e,n}},
$$

the $e$ means

$$
\boxed{\text{electron / conduction-band state}.}
$$

So

$$
\psi_{e,1}
$$

is electron state 1, and

$$
\psi_{e,2}
$$

is electron state 2.

---

# 13. What does $hh$ mean?

For

$$
\boxed{\psi_{hh,m}},
$$

$hh$ means

$$
\boxed{\text{heavy hole}.}
$$

So

$$
\psi_{hh,1}
$$

is heavy-hole state 1, and

$$
\psi_{hh,2}
$$

is heavy-hole state 2.

---

# 14. What do $m,n,l$ mean?

$$
\boxed{m,n,l}
$$

are simply **state labels**.

For this paper, the important state values are mainly 1 and 2.

A useful interpretation is:

- $n$: often selects an electron state,
- $m$: often selects a heavy-hole state,
- $l$: selects an intermediate electron or hole state.

The letters themselves do not have a deeper physical meaning. They are indices that tell the computer which state is being used.

Example:

If

$$
n=2,
$$

then

$$
\psi_{e,n}=\psi_{e,2}.
$$

If

$$
m=1,
$$

then

$$
\psi_{hh,m}=\psi_{hh,1}.
$$

---

# 15. The bracket notation $\langle A|B\rangle$

A term such as

$$
\boxed{\langle\psi_{hh,m}|\psi_{e,n}\rangle}
$$

is quantum-mechanical bra-ket notation.

In this case it corresponds to an integral such as

$$
\boxed{
\langle hh_m|e_n\rangle
=
\int
\psi_{hh,m}^{*}(z)
\psi_{e,n}(z)
\,dz.
}
$$

Simple meaning:

> How much do these two wavefunctions overlap in space?

---

# 16. $\langle hh_m|e_n\rangle$

This is an **electron-heavy-hole envelope overlap**.

If the electron and hole live in the same spatial region,

$$
\boxed{\text{overlap is large}.}
$$

If they are localized in different regions or wells,

$$
\boxed{\text{overlap is small}.}
$$

This controls how strongly that particular interband pathway contributes.

---

# 17. Why are there two overlap terms?

The first numerator contains

$$
\langle hh_m|e_n\rangle
\langle e_n|z|e_l\rangle
\langle e_l|hh_m\rangle.
$$

Think of this as a loop:

$$
\boxed{hh_m\rightarrow e_n\rightarrow e_l\rightarrow hh_m.}
$$

The first and last steps are electron-heavy-hole interactions, so there are two electron-heavy-hole overlap factors.

---

# 18. What is $z$?

$$
\boxed{z}
$$

is the position operator along the quantum-well growth direction.

The GaAs and AlGaAs layers are stacked along $z$, so the $z$-operator probes the spatial arrangement of the wavefunctions through the layer structure.

---

# 19. $\langle e_n|z|e_l\rangle$

$$
\boxed{\langle\psi_{e,n}|z|\psi_{e,l}\rangle}
$$

is the electron-side $z$-matrix element.

It can be written as

$$
\int
\psi_{e,n}^{*}(z)
z
\psi_{e,l}(z)
\,dz.
$$

Simple meaning:

> How strongly are these electron states coupled through their position along the quantum-well growth direction?

This quantity is strongly influenced by quantum-well asymmetry.

---

# 20. $\langle hh_m|z|hh_l\rangle$

$$
\boxed{\langle\psi_{hh,m}|z|\psi_{hh,l}\rangle}
$$

is the analogous heavy-hole-side $z$-matrix element.

It represents the heavy-hole dipole contribution along the growth direction.

---

# 21. What does diagonal mean?

Suppose

$$
n=l.
$$

Then

$$
\langle e_n|z|e_l\rangle
$$

becomes

$$
\boxed{\langle e_n|z|e_n\rangle.}
$$

This is called a **diagonal matrix element**.

Example:

$$
\boxed{\langle e_2|z|e_2\rangle.}
$$

It is closely related to the average spatial position of that state:

$$
\boxed{\langle z\rangle.}
$$

The paper identifies diagonal intersubband matrix elements as especially important because many other pathway contributions cancel.

---

# 22. The first large numerator: electron-side pathway

The first numerator is

$$
\boxed{
\langle hh_m|e_n\rangle
\langle e_n|z|e_l\rangle
\langle e_l|hh_m\rangle.
}
$$

Call this the **electron-side pathway**.

Why? Because the middle $z$-interaction occurs between electron states:

$$
e_n\rightarrow e_l.
$$

Simple sequence:

$$
\boxed{hh\rightarrow e\rightarrow e\rightarrow hh.}
$$

---

# 23. The second large numerator: heavy-hole-side pathway

The second numerator is

$$
\boxed{
\langle e_n|hh_m\rangle
\langle hh_m|z|hh_l\rangle
\langle hh_l|e_n\rangle.
}
$$

Call this the **heavy-hole-side pathway**.

Why? Because the middle interaction occurs between heavy-hole states:

$$
hh_m\rightarrow hh_l.
$$

Simple sequence:

$$
\boxed{e\rightarrow hh\rightarrow hh\rightarrow e.}
$$

---

# 24. Why is there a minus sign?

Equation 2 contains

$$
\boxed{\text{electron contribution}-\text{heavy-hole contribution}.}
$$

Therefore the two pathways can cancel.

For example,

$$
100-90=10.
$$

Even if the two individual contributions are large, the final result can be much smaller because of cancellation.

---

# 25. $\omega^{e,n}_{hh,m}$

$$
\boxed{\omega^{e,n}_{hh,m}}
$$

means the transition frequency between heavy-hole state $m$ and electron state $n$.

The upper labels

$$
e,n
$$

mean electron state $n$.

The lower labels

$$
hh,m
$$

mean heavy-hole state $m$.

For example,

$$
\omega^{e,2}_{hh,1}
$$

means the transition between

$$
hh_1
$$

and

$$
e_2.
$$

---

# 26. How is the transition frequency calculated?

In energy form,

$$
\boxed{\Delta E_{nm}=E_{e,n}-E_{hh,m}.}
$$

Then

$$
\boxed{\omega^{e,n}_{hh,m}=\frac{\Delta E_{nm}}{\hbar}.}
$$

This is one of the main places where the Nextnano energy output enters the susceptibility calculation.

---

# 27. Absolute eigenenergy versus optical transition energy

Suppose Nextnano gives

$$
E_{e1}=2.941\ \mathrm{eV}
$$

and

$$
E_{hh1}=1.448\ \mathrm{eV}.
$$

Neither number alone is the optical transition energy.

The transition energy is

$$
\boxed{2.941-1.448=1.493\ \mathrm{eV}.}
$$

That energy difference controls the optical resonance.

---

# 28. $k_\parallel$

$$
\boxed{k_\parallel}
$$

is the in-plane wavevector.

The quantum well confines carriers along $z$, but the carriers can move approximately freely along $x$ and $y$.

Therefore,

$$
\boxed{k_\parallel=\sqrt{k_x^2+k_y^2}.}
$$

Each confined state is therefore really a subband:

$$
\boxed{E_n(k_\parallel).}
$$

---

# 29. Why does Equation 2 sum over $k_\parallel$?

There are many possible in-plane momentum states.

So the paper writes

$$
\boxed{\sum_{k_\parallel}.}
$$

Simple meaning:

> Add the nonlinear contribution from all relevant in-plane momentum states.

The paper states that this sum was converted numerically into an integral over $(k_x,k_y)$.

---

# 30. The first denominator

The first denominator contains

$$
\boxed{
\omega^{e,n}_{hh,m}(k_\parallel)
-
\omega_1
-
\omega_2
+
i\Gamma.
}
$$

This is the **two-photon / second-harmonic detuning**.

For SHG,

$$
\omega_1=\omega_2=\omega,
$$

so it becomes

$$
\boxed{\omega_{eh}(k_\parallel)-2\omega+i\Gamma.}
$$

Simple meaning:

> Is the electron-heavy-hole transition close to the total energy of two incoming photons?

If yes, the system is close to a strong resonance.

---

# 31. The second denominator

The second denominator contains a term such as

$$
\boxed{
\omega^{e,l}_{hh,m}(k_\parallel)
-
\omega_1
+
i\Gamma.
}
$$

This is the **one-photon / intermediate-state detuning**.

Simple meaning:

> How close is the intermediate state to the energy of one photon?

Equation 2 therefore contains both:

$$
\boxed{\text{two-photon resonance}}
$$

and

$$
\boxed{\text{one-photon intermediate resonance}.}
$$

---

# 32. $\Gamma$

$$
\boxed{\Gamma}
$$

is the line broadening.

The paper uses

$$
\boxed{\Gamma=5\ \mathrm{meV}.}
$$

Simple meaning:

> Real optical transitions are not infinitely sharp.

The broadening gives the resonance a finite width.

---

# 33. What does $i\Gamma$ mean?

$$
i
$$

is the imaginary unit.

For now, the easiest interpretation is

$$
\boxed{i\Gamma=\text{the mathematical damping/linewidth term}.}
$$

It prevents the resonance denominator from becoming an ideal infinite singularity and makes the susceptibility complex.

---

# 34. The sums $\sum_{m,n}\sum_l$

These sums mean:

> Try every allowed combination of the retained confined states.

For the simplified model, the important states are mainly

$$
e_1,e_2,hh_1,hh_2.
$$

The computer evaluates the different pathways and then adds them together.

---

# 35. The boss's general equation

The boss often starts from the more general Equation 1 form containing

$$
\sum_P
\sum_{b_1,b_2,b_3}
\sum_{l,m,n}
\sum_{k_\parallel}.
$$

Equation 2 has already simplified many of these choices.

---

# 36. $P$

$$
\boxed{P}
$$

means a polarization combination.

Simple meaning:

> Which directions of the optical electric field are being used?

For the specialized susceptibility component of interest,

$$
\boxed{xzx}
$$

has already selected the important tensor directions.

---

# 37. $b_1,b_2,b_3$

$$
\boxed{b_1,b_2,b_3}
$$

are **band labels**.

Examples include:

- conduction band,
- heavy-hole valence band,
- light-hole valence band,
- other bands in a more general multiband model.

Simple meaning:

> Which semiconductor band does each participating state belong to?

Equation 2 simplifies the problem mainly to electron/conduction and heavy-hole states.

---

# 38. Difference between a band label and a state label

$$
\boxed{b}
$$

tells you the **band**.

Example:

$$
\text{conduction band}.
$$

$$
\boxed{n}
$$

tells you the **confined state inside that band**.

Example:

$$
e_1
$$

is state 1 inside the conduction band.

Therefore,

$$
\boxed{\text{band}\neq\text{confined state}.}
$$

---

# 39. $\phi$ in the boss's general equation

The general equation uses

$$
\boxed{\phi}.
$$

This represents the full quantum state/wavefunction in the general formulation.

The paper then separates that wavefunction into a unit-cell part and an envelope part. That is what allows Equation 2 to contain

$$
r_{e,hh}
$$

for the microscopic interband contribution and

$$
\psi(z)
$$

for the quantum-well envelope contribution.

---

# 40. $r_i,r_j,r_k$

The general numerator contains

$$
\langle\phi_1|r_i|\phi_2\rangle
\langle\phi_2|r_j|\phi_3\rangle
\langle\phi_3|r_k|\phi_1\rangle.
$$

The $r$'s are position/dipole operators.

The subscripts

$$
i,j,k
$$

tell you the coordinate direction.

For $xzx$,

$$
\boxed{i=x,\quad j=z,\quad k=x.}
$$

---

# 41. Boss change 1: $\sum_k\rightarrow\iint dk_xdk_y$

The paper uses

$$
\boxed{\sum_{k_\parallel}.}
$$

The boss makes the continuum integration explicit:

$$
\boxed{\sum_{k_\parallel}\rightarrow\iint dk_xdk_y.}
$$

Simple meaning:

> Instead of symbolically adding discrete momentum states, integrate through the continuous two-dimensional in-plane momentum space.

---

# 42. Why are there two free dimensions?

The quantum well is confined along

$$
\boxed{z},
$$

but approximately free along

$$
\boxed{x,y}.
$$

So:

$$
\boxed{z=\text{confined}}
$$

and

$$
\boxed{x,y=\text{free}.}
$$

---

# 43. Boss change 2: $\iint dk_xdk_y\rightarrow\int2\pi k\,dk$

If the system is rotationally symmetric in the plane,

$$
\boxed{
\iint dk_xdk_y
\rightarrow
\int 2\pi k_\parallel\,dk_\parallel.
}
$$

Simple meaning:

> Instead of integrating every $(k_x,k_y)$ point separately, integrate over circular rings in momentum space.

The factor

$$
2\pi k
$$

comes from the circumference weighting of each ring.

---

# 44. Why does $k$ multiply the integral?

At $k=0$, there is only the center point.

At larger $k$, there is an entire circular ring of possible $(k_x,k_y)$ combinations.

Therefore larger $k$ corresponds to more available in-plane momentum states.

This gives the geometric factor

$$
\boxed{2\pi k\,dk.}
$$

---

# 45. Boss change 3: frequency to energy

The original form uses angular frequency $\omega$.

The boss uses

$$
\boxed{E=\hbar\omega}
$$

to rewrite the denominators in energy form.

So a term such as

$$
\omega_{eh}-\omega_1-\omega_2
$$

becomes something like

$$
\boxed{E_{eh}-E_1-E_2.}
$$

The physical resonance condition is unchanged. The energy form is simply easier to compare with Nextnano outputs.

---

# 46. $E_1,E_2$

In the boss's rewritten equation,

$$
\boxed{E_1,E_2}
$$

are the photon energies.

For SHG,

$$
\boxed{E_1=E_2.}
$$

At 1550 nm,

$$
E_1\approx E_2\approx0.80\ \mathrm{eV}.
$$

Therefore,

$$
\boxed{E_1+E_2\approx1.60\ \mathrm{eV}.}
$$

---

# 47. $E_{b,m}(k_\parallel)$

$$
\boxed{E_{b,m}(k_\parallel)}
$$

means:

> Energy of confined state $m$, in band $b$, at in-plane momentum $k_\parallel$.

At $k_\parallel=0$, you have the zone-center confined-state energy.

At finite $k_\parallel$, the energy changes because of in-plane motion and multiband dispersion.

---

# 48. Boss's parabolic electron approximation

For electron states, the boss tested

$$
\boxed{
E_e(k)
=
E_e(0)
+
\frac{\hbar^2k^2}{2m_e^*}.
}
$$

Simple meaning:

$$
\boxed{\text{total electron energy}=\text{confined energy}+\text{in-plane kinetic energy}.}
$$

The Optel calculation suggested that the electron states are approximately parabolic, so this approximation may work reasonably well.

---

# 49. $m^*$

$$
\boxed{m^*}
$$

is the effective mass.

It controls the curvature of the energy-versus-$k$ dispersion.

Small $m^*$: stronger curvature.

Large $m^*$: flatter dispersion.

---

# 50. Why the hole states need something different

The boss's Optel results showed that the hole states are not accurately represented by one simple parabola over the relevant range.

So for holes,

$$
\boxed{
E_{hh}(k)
\neq
E_{hh}(0)
+
\frac{\hbar^2k^2}{2m_{hh}^*}
}
$$

over the relevant range.

Instead, the hole energy should be represented more accurately as

$$
\boxed{E_{hh}(k)=F_{hh}(k),}
$$

where $F_{hh}(k)$ is a better fit or a direct interpolation of the multiband calculation.

---

# 51. Why does the hole dispersion matter?

Equation 2 needs the transition energy

$$
\boxed{E_e(k)-E_{hh}(k).}
$$

If $E_{hh}(k)$ is wrong, then the transition energy is wrong.

That means the optical detuning is wrong.

Therefore the predicted

$$
\boxed{\chi^{(2)}}
$$

can also be wrong, especially near resonance.

---

# 52. The boss's matrix-element approximation

The boss's slide indicates that the matrix elements may be evaluated at the zone center,

$$
\boxed{k_\parallel=0,}
$$

and treated as approximately independent of $k_\parallel$.

This is the approximation

$$
\boxed{M(k)\approx M(0).}
$$

Then

$$
\int M(k)F(k)\,dk
$$

becomes approximately

$$
\boxed{M(0)\int F(k)\,dk.}
$$

This makes the calculation much simpler.

---

# 53. What remains inside the $k$-integral?

The energies remain inside because they vary with $k$:

$$
\boxed{E_e(k),\quad E_{hh}(k).}
$$

Therefore the resonance denominators remain $k$-dependent.

Conceptually,

$$
\boxed{
M(0)
\int
\frac{2\pi k\,dk}{D_1(k)D_2(k)}.
}
$$

---

# 54. Full practical connection to Nextnano

## Step 1 - Define the heterostructure

Specify quantities such as:

- GaAs well widths,
- AlGaAs barrier widths,
- tunneling barrier,
- material compositions,
- interface grading.

## Step 2 - Nextnano constructs the band-edge potentials

Obtain the conduction and valence/heavy-hole confinement potentials.

## Step 3 - Nextnano solves the confined states

Obtain zone-center quantities such as

$$
\boxed{E_{e1}(0),E_{e2}(0)}
$$

and

$$
\boxed{E_{hh1}(0),E_{hh2}(0)}
$$

plus the corresponding envelope wavefunctions

$$
\boxed{\psi_{e1},\psi_{e2},\psi_{hh1},\psi_{hh2}.}
$$

## Step 4 - Calculate overlaps

From the wavefunctions,

$$
\boxed{O_{mn}=\langle hh_m|e_n\rangle.}
$$

## Step 5 - Calculate $z$-matrix elements

$$
\boxed{z^e_{nl}=\langle e_n|z|e_l\rangle}
$$

and

$$
\boxed{z^{hh}_{ml}=\langle hh_m|z|hh_l\rangle.}
$$

## Step 6 - Determine the in-plane dispersion

For electrons,

$$
\boxed{
E_e(k)
\approx
E_e(0)+\frac{\hbar^2k^2}{2m_e^*}.
}
$$

For heavy holes,

$$
\boxed{E_{hh}(k)=\text{a more accurate non-parabolic relation}.}
$$

## Step 7 - Construct transition energies

$$
\boxed{
\Delta E_{nm}(k)
=
E_{e,n}(k)-E_{hh,m}(k).
}
$$

## Step 8 - Compare with the photon energies

For a 1550 nm fundamental,

$$
E_\omega\approx0.80\ \mathrm{eV}
$$

and

$$
2E_\omega\approx1.60\ \mathrm{eV}.
$$

The two-photon detuning becomes approximately

$$
\boxed{
D_{2\omega}(k)
=
\Delta E_{nm}(k)
-
1.60\ \mathrm{eV}
+
i\Gamma.
}
$$

## Step 9 - Calculate the pathway strength

Use

$$
\boxed{\text{overlap}\times z\text{-matrix element}\times\text{overlap}}
$$

divided by the resonance denominators.

## Step 10 - Integrate over $k$

Conceptually,

$$
\boxed{
\int
(\text{pathway contribution})
\,2\pi k\,dk.
}
$$

The exact state-counting normalization must remain consistent with the chosen implementation.

## Step 11 - Sum the state combinations

Add all retained combinations of

$$
e_1,e_2,hh_1,hh_2.
$$

## Step 12 - Electron pathway minus heavy-hole pathway

$$
\boxed{A_e-A_{hh}.}
$$

## Step 13 - Multiply by the overall constants

Combine the result with

$$
N_z,\quad e,\quad\epsilon_0,\quad r_{e,hh},\quad\text{etc.}
$$

to obtain

$$
\boxed{\chi^{(2)}.}
$$

---

# 55. Reduce the entire equation to five questions

When you see any term in Equation 2, ask which of these questions it answers.

## 1. Which quantum state?

$$
e_1,e_2,hh_1,hh_2.
$$

Represented by

$$
m,n,l.
$$

## 2. Where is the state?

Represented by

$$
\psi(z).
$$

## 3. How strongly do the states interact?

Represented by

$$
\langle hh|e\rangle
$$

and

$$
\langle\psi|z|\psi'\rangle.
$$

## 4. How close is the transition to the laser resonance?

Represented by energy or frequency detuning terms such as

$$
E_e(k)-E_{hh}(k)-E_{\text{photon total}}.
$$

## 5. How many states contribute?

Represented by

$$
\sum_{m,n,l}
$$

and the in-plane momentum sum/integral.

That is the core of Equation 2.

---

# 56. Master table

| Symbol | Plain-English meaning | Role in the calculation |
|---|---|---|
| $\chi^{(2)}_{xzx}$ | nonlinear susceptibility | final answer |
| $(2)$ | second order | identifies the nonlinear order |
| $xzx$ | tensor directions | selects optical interaction directions |
| $\omega_1,\omega_2$ | photon angular frequencies | define the input light |
| $E_1,E_2$ | photon energies | boss's energy-domain version |
| $N_z$ | QWs per unit length | scales the response |
| $e$ | elementary charge | physical constant |
| $\epsilon_0$ | vacuum permittivity | physical constant |
| $\hbar$ | reduced Planck constant | converts between energy and angular frequency |
| $r_{e,hh}$ | atomic interband matrix element | intrinsic electron-HH optical strength |
| $\psi_{e,n}$ | electron envelope wavefunction | where electron state $n$ lives |
| $\psi_{hh,m}$ | heavy-hole envelope wavefunction | where HH state $m$ lives |
| $n$ | electron-state index | selects a retained electron state |
| $m$ | HH-state index | selects a retained heavy-hole state |
| $l$ | intermediate-state index | selects the intermediate state |
| $\langle hh|e\rangle$ | envelope overlap | electron-hole spatial coupling |
| $z$ | growth-direction position operator | probes QW asymmetry |
| $\langle e|z|e\rangle$ | electron $z$-dipole | electron-side QW contribution |
| $\langle hh|z|hh\rangle$ | HH $z$-dipole | heavy-hole-side QW contribution |
| $\omega^{e,n}_{hh,m}$ | transition frequency | electron-HH energy separation in frequency units |
| $E_e-E_{hh}$ | transition energy | energy-domain form used naturally with Nextnano |
| $k_\parallel$ | in-plane wavevector | free-motion coordinate |
| $E_n(k)$ | subband dispersion | state energy at finite in-plane momentum |
| $m^*$ | effective mass | controls curvature of $E(k)$ |
| $\Gamma$ | linewidth/broadening | gives resonance a finite width |
| $i\Gamma$ | complex damping term | prevents an ideal singular resonance |
| $\sum_k$ | sum over momentum states | paper notation |
| $\iint dk_xdk_y$ | 2D momentum integral | boss's continuum form |
| $2\pi k\,dk$ | radial momentum-space weight | boss's symmetry-reduced integral |
| first fraction | electron-side pathway | middle $z$-interaction is electron-electron |
| second fraction | HH-side pathway | middle $z$-interaction is HH-HH |
| minus sign | subtraction of pathways | permits cancellation |

---

# 57. The most important conceptual split

The first branch of the calculation is

$$
\boxed{
\underbrace{\psi_n(z)}_{\text{where the state lives}}
\rightarrow
\underbrace{\text{matrix elements}}_{\text{how strongly states interact}}
}
$$

while the second branch is

$$
\boxed{
\underbrace{E_n(k)}_{\text{state energies}}
\rightarrow
\underbrace{\text{denominators}}_{\text{how close to resonance}}
}
$$

Equation 2 combines the two:

$$
\boxed{
\chi^{(2)}
\sim
\frac{\text{interaction strength}}{\text{resonance detuning}}.
}
$$

That is the foundation to understand before worrying about the exact numerical prefactors, normalization conventions, or implementation details.
