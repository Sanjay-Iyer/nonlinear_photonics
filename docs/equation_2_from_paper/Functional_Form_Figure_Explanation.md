# Functional Form Figure — Simple and Detailed Explanation

## What this figure is trying to show

The main point of the figure is:

> **When the nonlinear-susceptibility equation says “sum over everything,” what exactly is being summed over physically?**

The figure breaks the large equation into four main choices:

\[
\boxed{
\text{polarization}
\rightarrow
\text{bands}
\rightarrow
\text{confined states}
\rightarrow
\text{in-plane }k
}
\]

That is the central idea.

---

# 1. The sums in the equation

The general equation contains

\[
\sum_P
\sum_{b_1,b_2,b_3}
\sum_{l,m,n}
\sum_{k_\parallel}.
\]

Each sum has a physical meaning:

| Sum | Figure label | Simple meaning |
|---|---|---|
| \(\sum_P\) | polarization states | Which optical-field directions are involved |
| \(\sum_{b_1,b_2,b_3}\) | bands | Which semiconductor bands participate |
| \(\sum_{l,m,n}\) | confined states | Which quantum-well states such as \(e_1,e_2,hh_1,hh_2\) are used |
| \(\sum_{k_\parallel}\) | free direction | What in-plane momentum the carrier has |

So the equation is essentially saying:

\[
\boxed{
\text{Try every allowed optical pathway and add its contribution to }\chi^{(2)}.
}
\]

---

# 2. Why there are both confined states and free states

A quantum well confines carriers in one direction:

\[
\boxed{z}
\]

but the carriers are still free to move sideways in the plane:

\[
\boxed{x,y}.
\]

So the same electron or heavy hole has two different kinds of quantum behavior.

## Along \(z\): confined

The carrier is trapped by the quantum-well potential.

Therefore only certain discrete states are allowed, such as

\[
e_1,\quad e_2
\]

and

\[
hh_1,\quad hh_2.
\]

## Along \(x-y\): free

The carrier can move continuously in the plane.

Therefore it can have many possible momenta:

\[
k_x,\quad k_y.
\]

These two ideas are what the bottom-left and center parts of the figure are showing.

---

# 3. The bottom-left plot: the confined direction

The bottom-left plot is a band-edge diagram along the growth direction \(z\).

The horizontal axis is

\[
z.
\]

The black curves/steps represent approximately the conduction- and valence-band edges.

Typical labels are:

- \(E_C\): conduction-band edge
- \(E_V\): valence-band edge

The colored curves show the confined quantum states / wavefunctions.

Nextnano solves this confinement problem and gives states such as

\[
\boxed{e_1,e_2}
\]

and

\[
\boxed{hh_1,hh_2}.
\]

These are the discrete quantum-well states.

---

# 4. What the 1.49 eV and 1.62 eV arrows mean

The arrows show interband transition energies.

For example,

\[
\boxed{
\Delta E_{11}=E_{e1}-E_{hh1}\approx1.49\ \mathrm{eV}
}
\]

and another important transition is around

\[
\boxed{1.62\ \mathrm{eV}}.
\]

The important point is that the optical transition energy is not just \(E_{e1}\) or \(E_{hh1}\).

It is the energy difference

\[
\boxed{
E_e-E_{hh}.
}
\]

That energy difference determines the optical resonance.

---

# 5. What the confined-state indices \(l,m,n\) mean

The label

\[
\sum_{l,m,n}
\]

means:

> Try different combinations of the discrete quantum-well states.

For example, a pathway might involve

\[
hh_1,\ e_1,\ e_2
\]

while another might involve

\[
hh_2,\ e_2,\ e_2.
\]

In the simplified coupled-QW Equation 2 calculation, the important states are mainly

\[
\boxed{
e_1,e_2,hh_1,hh_2.
}
\]

The indices \(l,m,n\) simply identify which state participates at each step of the three-dipole process.

---

# 6. The center drawing: free motion in the plane

The center of the figure shows something different from the confinement plot.

The quantum well confines the carrier through the layer stack, but the carrier remains free to move laterally.

So the three spatial directions behave differently:

\[
x,\quad y,\quad z.
\]

The QW strongly confines

\[
\boxed{z}
\]

while

\[
\boxed{x,y}
\]

are approximately free directions.

This is why the figure says:

> **2 free dimensions (1 free dimension shown)**

Only one free direction is drawn to keep the picture simple, but physically there are two in-plane directions.

---

# 7. What is \(k_\parallel\)?

\[
\boxed{k_\parallel}
\]

is the wavevector parallel to the quantum-well layers.

It is defined as

\[
\boxed{
k_\parallel=\sqrt{k_x^2+k_y^2}.
}
\]

It tells you the amount of in-plane momentum carried by the electron or hole.

This is different from the confined-state label.

For example, an electron can be in the confined subband

\[
e_1
\]

while having many different values of

\[
k_\parallel.
\]

So the energy is more accurately written as

\[
\boxed{
E_{e1}(k_\parallel)
}
\]

rather than simply \(E_{e1}\).

Likewise,

\[
\boxed{
E_{hh1}(k_\parallel).
}
\]

---

# 8. A state really has two labels

A very useful way to think about the system is

\[
\boxed{
\text{state}
=
(\text{confined subband},k_\parallel).
}
\]

For example,

\[
e_1,\ k_\parallel=0
\]

and

\[
e_1,\ k_\parallel=0.05\ \mathrm{nm}^{-1}
\]

belong to the same confined subband \(e_1\), but they are different in-plane momentum states.

---

# 9. Why the red curves are parabolas

The right side of the figure explains the free-electron-like dispersion.

Classically,

\[
E_{\mathrm{kinetic}}
=
\frac12 mv^2.
\]

Momentum is

\[
p=mv.
\]

Therefore,

\[
E=\frac{p^2}{2m}.
\]

Quantum mechanics gives

\[
\boxed{
p=\hbar k.
}
\]

Substituting,

\[
E
=
\frac{(\hbar k)^2}{2m}
\]

so

\[
\boxed{
E(k)=\frac{\hbar^2k^2}{2m}.
}
\]

That is a parabola in \(k\).

So the red curves in the center of the figure are showing

\[
\boxed{
E\propto k_\parallel^2.
}
\]

---

# 10. What this means for a quantum-well state

Suppose a confined electron state has energy

\[
E_{e1}(0)
\]

at the zone center.

As the electron gains in-plane momentum,

\[
k_\parallel>0,
\]

its energy rises approximately as

\[
\boxed{
E_{e1}(k_\parallel)
=
E_{e1}(0)
+
\frac{\hbar^2k_\parallel^2}{2m_e^*}.
}
\]

So each discrete confined level becomes an in-plane subband.

The same idea applies to

\[
e_2,\quad hh_1,\quad hh_2.
\]

---

# 11. Effective mass

In semiconductor calculations, the mass used is usually an effective mass

\[
m^*.
\]

The dispersion is approximately

\[
E(k)
=
E(0)
+
\frac{\hbar^2k^2}{2m^*}.
\]

The effective mass controls the curvature.

If

\[
m^*\downarrow,
\]

the parabola rises more quickly with \(k\).

If

\[
m^*\uparrow,
\]

the parabola is flatter.

Electrons and heavy holes can therefore have different \(k_\parallel\)-dependence.

---

# 12. Why \(k_\parallel\) matters to Equation 2

The optical transition energy depends on \(k_\parallel\):

\[
\boxed{
\Delta E_{eh}(k_\parallel)
=
E_e(k_\parallel)-E_{hh}(k_\parallel).
}
\]

At

\[
k_\parallel=0,
\]

a particular transition might be close to 1.62 eV.

At a different \(k_\parallel\), both the electron and heavy-hole energies can shift.

Therefore the transition energy changes too.

This matters because Equation 2 contains resonance denominators that depend on these transition energies.

---

# 13. Connection to the resonance denominator

For SHG, an important energy-domain denominator is approximately

\[
\boxed{
\Delta E_{eh}(k_\parallel)
-
2E_\omega
+
i\Gamma.
}
\]

At a 1550 nm fundamental,

\[
E_\omega\approx0.80\ \mathrm{eV}.
\]

Therefore,

\[
2E_\omega\approx1.60\ \mathrm{eV}.
\]

If

\[
\Delta E_{eh}(k_\parallel)
\approx1.60\ \mathrm{eV},
\]

the system is close to resonance and the nonlinear contribution becomes large.

Because \(\Delta E_{eh}\) depends on \(k_\parallel\), one generally cannot use only the \(k_\parallel=0\) state.

The calculation must include the range of relevant \(k_\parallel\).

---

# 14. What the bands sum means

The figure labels

\[
\boxed{
\sum_{b_1,b_2,b_3}
}
\]

as **bands**.

The general semiconductor system can contain different bands such as:

- conduction band,
- heavy-hole valence band,
- light-hole valence band,
- split-off band.

The indices \(b_1,b_2,b_3\) ask:

> Which semiconductor band does each participating state belong to?

For the specialized Equation 2 in this paper, the calculation is simplified mainly to conduction-band and heavy-hole-band states.

---

# 15. Important terminology: band vs confined state

These are not the same thing.

## Band

Examples:

\[
\text{conduction band},\quad
\text{heavy-hole band}.
\]

These are represented by indices such as

\[
b_1,b_2,b_3.
\]

## Confined state or QW subband

Examples:

\[
e_1,\quad e_2,\quad hh_1,\quad hh_2.
\]

These are represented by

\[
l,m,n.
\]

So:

\[
\boxed{
\text{band}
\neq
\text{confined state}.
}
\]

For example,

\[
e_1
\]

means the first confined state within the conduction band.

---

# 16. What the polarization sum means

The figure labels

\[
\boxed{\sum_P}
\]

as **polarization states**.

The general susceptibility is

\[
\chi^{(2)}_{ijk}.
\]

For the important coupled-QW component,

\[
\boxed{
\chi^{(2)}_{xzx}.
}
\]

This corresponds to dipole interactions in the directions

\[
x,\quad z,\quad x.
\]

The general numerator contains

\[
\langle\phi_1|r_i|\phi_2\rangle
\langle\phi_2|r_j|\phi_3\rangle
\langle\phi_3|r_k|\phi_1\rangle.
\]

For \(xzx\),

\[
i=x,\qquad
j=z,\qquad
k=x.
\]

So the interaction sequence is roughly

\[
\boxed{
x\text{-interaction}
\rightarrow
z\text{-interaction}
\rightarrow
x\text{-interaction}.
}
\]

---

# 17. What the large numerator means

The numerator is

\[
\langle\phi_1|r_i|\phi_2\rangle
\langle\phi_2|r_j|\phi_3\rangle
\langle\phi_3|r_k|\phi_1\rangle.
\]

A simple interpretation is

\[
\boxed{
\text{transition 1 strength}
\times
\text{transition 2 strength}
\times
\text{transition 3 strength}.
}
\]

It measures how strongly the system can execute the three-step optical pathway.

If one matrix element is nearly zero, the whole product becomes very small.

---

# 18. What the denominators mean

The first denominator is essentially

\[
\boxed{
\text{transition energy}
-
(\omega_1+\omega_2).
}
\]

The second denominator is essentially

\[
\boxed{
\text{intermediate transition energy}
-
\omega_2.
}
\]

They measure how far the pathway is from optical resonance.

If the denominator is small,

\[
\boxed{
\text{close to resonance}
}
\]

and the contribution can be large.

If the denominator is large,

\[
\boxed{
\text{far from resonance}
}
\]

and the contribution is smaller.

---

# 19. Put all four sums together

The general calculation does the following.

## Step 1: choose a polarization pathway

\[
P.
\]

For example,

\[
xzx.
\]

## Step 2: choose the bands

\[
b_1,b_2,b_3.
\]

For the specialized Eq. 2, this mostly becomes conduction and heavy-hole bands.

## Step 3: choose the confined QW states

\[
l,m,n.
\]

For example,

\[
e_1,e_2,hh_1,hh_2.
\]

## Step 4: choose the in-plane momentum

\[
k_\parallel.
\]

## Step 5: calculate that pathway's contribution

\[
\frac{
\text{three matrix elements}
}{
\text{two resonance denominators}
}.
\]

## Step 6: add all contributions

The result is

\[
\boxed{
\chi^{(2)}.
}
\]

---

# 20. The figure as an algorithm

```text
FOR each allowed polarization:
    FOR each allowed combination of bands:
        FOR each allowed combination of confined QW states:
            FOR each in-plane momentum k_parallel:

                determine the state energies

                determine the transition energies

                calculate the dipole matrix elements

                calculate how close the pathway is to resonance

                calculate that pathway's contribution to chi^(2)

            add all k_parallel contributions

        add all confined-state contributions

    add all band contributions

add all polarization contributions
```

That is what the large equation is doing conceptually.

---

# 21. How this simplifies for the paper's Equation 2

The full Equation 1 is more general than the specialized Equation 2 used for the coupled-QW calculation.

For Equation 2, many choices are already restricted.

A simpler mental form is

\[
\boxed{
\chi^{(2)}_{xzx}
=
\sum_{k_\parallel}
\sum_{\substack{
e_1,e_2\\
hh_1,hh_2
}}
\left[
\text{electron-side pathway}
-
\text{heavy-hole-side pathway}
\right].
}
\]

This is much closer to the actual coupled-QW calculation.

---

# 22. Where Nextnano enters

Nextnano solves the confinement problem along \(z\).

Starting from the layer structure,

\[
\boxed{
\text{GaAs/AlGaAs geometry}
}
\]

it constructs the band-edge potentials and solves for

\[
\boxed{
E_{e1},E_{e2},E_{hh1},E_{hh2}
}
\]

and

\[
\boxed{
\psi_{e1}(z),\psi_{e2}(z),
\psi_{hh1}(z),\psi_{hh2}(z).
}
\]

These are the **confined states** shown in the bottom-left part of the figure.

---

# 23. Each confined state becomes an in-plane subband

Once the free in-plane motion is included, each confined state is not just one energy.

Instead, each becomes a function of \(k_\parallel\):

\[
\boxed{
E_{e1}(k_\parallel)
}
\]

\[
\boxed{
E_{e2}(k_\parallel)
}
\]

\[
\boxed{
E_{hh1}(k_\parallel)
}
\]

\[
\boxed{
E_{hh2}(k_\parallel).
}
\]

This is a major conceptual point.

A QW "energy level" is really the bottom of an in-plane subband.

---

# 24. The single most important new idea in this slide

The most important concept is:

\[
\boxed{
e_1\text{ is not just one energy.}
}
\]

More accurately, it is

\[
\boxed{
E_{e1}(k_\parallel).
}
\]

Why?

Because the electron is:

- confined along \(z\),
- but free to move along \(x\) and \(y\).

That is exactly why \(k_\parallel\) appears in the nonlinear-susceptibility equation and why the \(k\)-sum must later be converted into a \(k\)-space integral.

---

# 25. Entire figure in one physical sentence

> **A quantum-well carrier has a discrete state because it is confined through the layer stack, but it also has continuous in-plane momentum because it is free to move parallel to the layers. The nonlinear-susceptibility equation therefore considers all allowed polarization, band, confined-state, and in-plane-momentum combinations and weights each one by its dipole strength and optical resonance before adding everything together to obtain \(\chi^{(2)}\).**

---

# 26. Memory map

\[
\boxed{
\text{QW structure}
}
\]

\[
\downarrow
\]

### Confined along \(z\)

\[
\boxed{
e_1,e_2,hh_1,hh_2
}
\]

\[
\downarrow
\]

### Free along \(x,y\)

Each confined state becomes

\[
\boxed{
E_n(k_\parallel)
}
\]

\[
\downarrow
\]

### Choose a pathway

\[
\boxed{
P,\quad
b_1,b_2,b_3,\quad
l,m,n,\quad
k_\parallel
}
\]

\[
\downarrow
\]

### Calculate

\[
\boxed{
\frac{
\text{dipole strength}
}{
\text{resonance detuning}
}
}
\]

\[
\downarrow
\]

### Add all contributions

\[
\boxed{
\chi^{(2)}.
}
\]

---

# 27. Connection to the next derivation step

Once the role of \(k_\parallel\) is understood, the next mathematical step becomes natural.

The symbolic sum

\[
\sum_{k_\parallel}
\]

is converted into an explicit integral over in-plane momentum.

In two dimensions,

\[
\iint dk_x\,dk_y.
\]

If the system is rotationally symmetric in the plane, that can be rewritten as a radial integral

\[
\int 2\pi k_\parallel\,dk_\parallel
\]

subject to the correct \(k\)-space normalization convention.

This is why the "Functional Form" slide connects directly to the later "Adjusting the Form" slide.
