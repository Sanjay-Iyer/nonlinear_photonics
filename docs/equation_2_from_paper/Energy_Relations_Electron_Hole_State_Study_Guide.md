# Energy Relations for Electron and Hole States — Study Guide

## What this figure is trying to show

The main idea of the figure is:

> **Nextnano gives the confined quantum-well states and wavefunctions near \(k_\parallel=0\). The matrix elements can be evaluated there, while the state energies are allowed to vary with in-plane momentum \(k_\parallel\). Those \(k_\parallel\)-dependent energies are then used inside the susceptibility integral.**

The calculation is being split into two kinds of quantities:

### Quantities treated as approximately fixed at \(k_\parallel=0\)

The wavefunctions and dipole matrix elements, such as

\[
\boxed{
\langle\phi_1|r_i|\phi_2\rangle
\langle\phi_2|r_j|\phi_3\rangle
\langle\phi_3|r_k|\phi_1\rangle
}
\]

### Quantities that vary with \(k_\parallel\)

The band/subband energies:

\[
\boxed{
E_{b,m}(k_\parallel)
}
\]

So conceptually the calculation becomes

\[
\boxed{
\text{fixed matrix elements}
\times
\int
\frac{
\text{\(k\)-space weighting}
}{
\text{\(k\)-dependent resonance denominators}
}
dk.
}
\]

---

# 1. What your boss wants Nextnano to do

The numbered list on the figure is essentially a computational recipe.

## Step 1 — Solve the confined quantum-well problem

Use Nextnano to calculate the confined electron and hole states, for example

\[
e_1,\quad e_2,\quad hh_1,\quad hh_2
\]

and their associated wavefunctions

\[
\psi_{e1}(z),\quad
\psi_{e2}(z),\quad
\psi_{hh1}(z),\quad
\psi_{hh2}(z).
\]

These are solutions of the confinement problem along the growth direction

\[
\boxed{z}.
\]

---

# 2. Step 2 — Calculate the matrix elements

Use the confined-state wavefunctions to calculate quantities such as

\[
\langle\phi_1|r_i|\phi_2\rangle,
\]

\[
\langle\phi_2|r_j|\phi_3\rangle,
\]

and

\[
\langle\phi_3|r_k|\phi_1\rangle.
\]

In the specialized coupled-QW Equation 2, these ultimately correspond to quantities such as

\[
\boxed{
\langle hh_m|e_n\rangle
}
\]

and

\[
\boxed{
\langle e_n|z|e_l\rangle
}
\]

or

\[
\boxed{
\langle hh_m|z|hh_l\rangle.
}
\]

These matrix elements tell you how strongly the states participate in the nonlinear optical process.

---

# 3. Step 3 — Determine the energies in the free-motion directions

The carrier is confined along \(z\), but it is free to move parallel to the quantum-well plane.

Therefore its total energy depends on the in-plane wavevector

\[
\boxed{k_\parallel}.
\]

So instead of using only

\[
E_n(0),
\]

you need

\[
\boxed{
E_n(k_\parallel).
}
\]

This describes the in-plane dispersion of each confined subband.

---

# 4. Step 4 — Fit the energy dependence

Your boss suggests describing the energy as a function of \(k_\parallel\).

A simple approximation is a parabolic, free-electron-like dispersion:

\[
\boxed{
E_{b,m}(k_\parallel)
=
E_{b,m}(0)
+
\frac{\hbar^2 k_\parallel^2}
{2m_{b,m}^{*}}.
}
\]

This is the most important equation on the bottom half of the slide.

---

# 5. What the dispersion equation means

The equation is

\[
\boxed{
E_{b,m}(k_\parallel)
=
\frac{\hbar^2k_\parallel^2}
{2m_{b,m}^{*}}
+
E_{b,m}(k_\parallel=0).
}
\]

It says:

> **The energy at finite in-plane momentum equals the confined-state energy at the zone center plus the kinetic energy associated with moving parallel to the quantum-well plane.**

Break it apart:

## \(E_{b,m}(k_\parallel)\)

Energy of state \(m\) in band \(b\) at an in-plane momentum \(k_\parallel\).

## \(E_{b,m}(0)\)

Energy of that confined quantum-well state at the zone center.

This is the quantity closely associated with the confinement solution from Nextnano.

## \(k_\parallel\)

The in-plane wavevector:

\[
\boxed{
k_\parallel=\sqrt{k_x^2+k_y^2}.
}
\]

## \(m_{b,m}^{*}\)

The effective mass associated with the band/state.

It determines how quickly the state energy changes with \(k_\parallel\).

## \(\hbar^2k_\parallel^2/(2m^*)\)

The additional energy associated with free motion in the plane.

---

# 6. Physical picture using one electron state

Suppose Nextnano gives

\[
E_{e1}(0)=2.94\ \mathrm{eV}.
\]

That is the energy of \(e_1\) at

\[
k_\parallel=0.
\]

If the electron moves sideways through the QW plane, then

\[
k_\parallel>0.
\]

Its energy becomes approximately

\[
\boxed{
E_{e1}(k_\parallel)
=
E_{e1}(0)
+
\frac{\hbar^2k_\parallel^2}{2m_e^*}.
}
\]

So the confined state \(e_1\) is not really one single energy.

It becomes a subband

\[
\boxed{
E_{e1}(k_\parallel).
}
\]

The same applies to

\[
e_2,\quad hh_1,\quad hh_2.
\]

---

# 7. Why this matters for \(\chi^{(2)}\)

The nonlinear-susceptibility denominator contains transition energies such as

\[
\boxed{
E_e(k_\parallel)-E_{hh}(k_\parallel).
}
\]

The optical transition energy is therefore

\[
\boxed{
\Delta E_{eh}(k_\parallel)
=
E_e(k_\parallel)-E_{hh}(k_\parallel).
}
\]

As \(k_\parallel\) changes:

\[
E_e(k_\parallel)
\]

changes and

\[
E_{hh}(k_\parallel)
\]

changes.

Therefore

\[
\Delta E_{eh}(k_\parallel)
\]

also changes.

That changes how close the system is to optical resonance.

---

# 8. The top equation split into three pieces

The equation at the top can be thought of schematically as

\[
\chi^{(2)}
\sim
\sum
f
\int
\frac{
\text{matrix-element product}
}{
D_1(k_\parallel)
D_2(k_\parallel)
}
2\pi k_\parallel dk_\parallel.
\]

There are three main pieces:

1. the matrix-element product,
2. the \(k_\parallel\)-dependent energy denominators,
3. the \(2\pi k_\parallel dk_\parallel\) state-counting factor.

---

# 9. Piece A — The matrix elements

The highlighted numerator is

\[
\boxed{
\langle\phi_1|r_i|\phi_2\rangle
\langle\phi_2|r_j|\phi_3\rangle
\langle\phi_3|r_k|\phi_1\rangle.
}
\]

These tell you how strongly the three states couple through the optical process.

The yellow annotation on the slide says essentially:

> **Calculate these at \(k_\parallel=0\), the zone center, so they can come outside the \(k\)-integral.**

---

# 10. Why the matrix elements can come outside the integral

Suppose the original integral contains

\[
\int
M(k_\parallel)
F(k_\parallel)
\,dk_\parallel.
\]

Here

\[
M(k_\parallel)
\]

is the matrix-element product.

If you assume

\[
\boxed{
M(k_\parallel)\approx M(0),
}
\]

then the matrix element is treated as a constant.

Therefore,

\[
\int
M(0)
F(k_\parallel)
\,dk_\parallel
=
\boxed{
M(0)
\int
F(k_\parallel)
\,dk_\parallel.
}
\]

This means the wavefunction matrix elements only have to be evaluated once at the zone center.

That simplifies the calculation substantially.

---

# 11. The approximation being made

The physical assumption is approximately

\[
\boxed{
\text{matrix elements vary weakly with }k_\parallel
}
\]

compared with the importance of the \(k_\parallel\)-dependent energies.

So the modeling choice is:

\[
\boxed{
M(k_\parallel)\approx M(0)
}
\]

but

\[
\boxed{
E(k_\parallel)\neq E(0).
}
\]

This is an approximation, not an exact identity.

---

# 12. Piece B — The energy denominators

A denominator contains terms such as

\[
\boxed{
E_{b_2,m}(k_\parallel)
-
E_{b_1,l}(k_\parallel)
-
E_1
-
E_2.
}
\]

This asks:

> How close is the material transition energy to the total energy of the two incoming photons?

The material transition energy is

\[
E_{b_2,m}(k_\parallel)-E_{b_1,l}(k_\parallel).
\]

The photons provide

\[
E_1+E_2.
\]

So the detuning is

\[
\boxed{
\Delta E_{\text{material}}
-
\Delta E_{\text{photons}}.
}
\]

---

# 13. For SHG, \(E_1=E_2\)

For second-harmonic generation,

\[
\boxed{
E_1=E_2=E_\omega.
}
\]

At 1550 nm,

\[
E_\omega\approx0.80\ \mathrm{eV}.
\]

Therefore,

\[
E_1+E_2
\approx
1.60\ \mathrm{eV}.
\]

So the important two-photon denominator becomes approximately

\[
\boxed{
E_e(k_\parallel)
-
E_{hh}(k_\parallel)
-
1.60\ \mathrm{eV}.
}
\]

If

\[
E_e(k_\parallel)-E_{hh}(k_\parallel)
\approx1.60\ \mathrm{eV},
\]

the system is close to resonance.

---

# 14. Why the \(k_\parallel\)-dependence matters

Imagine that at

\[
k_\parallel=0
\]

the transition energy is

\[
1.62\ \mathrm{eV}.
\]

Then the detuning for 1550 nm SHG is approximately

\[
1.62-1.60
=
0.02\ \mathrm{eV}.
\]

At another finite \(k_\parallel\), the transition could shift to

\[
1.60\ \mathrm{eV}.
\]

Then the detuning becomes

\[
0.
\]

That \(k_\parallel\)-state can contribute much more strongly.

This is why the energy dependence must remain inside the \(k_\parallel\) integral.

---

# 15. Piece C — The \(2\pi k_\parallel dk_\parallel\) factor

The integral contains

\[
\boxed{
2\pi k_\parallel dk_\parallel.
}
\]

This comes from integrating over the two-dimensional in-plane \(k\)-space.

Originally,

\[
\iint dk_x\,dk_y.
\]

Using radial symmetry,

\[
dk_xdk_y
=
k_\parallel dk_\parallel d\theta.
\]

Integrating around the full angle gives

\[
\int_0^{2\pi}d\theta
=
2\pi.
\]

Therefore,

\[
\boxed{
\iint dk_xdk_y
=
\int
2\pi k_\parallel dk_\parallel.
}
\]

Physically, at each \(k_\parallel\) there is a ring of equivalent in-plane momentum states.

The ring circumference grows as

\[
2\pi k_\parallel,
\]

so larger \(k_\parallel\) corresponds to more available states.

---

# 16. What “fit the energy dependence” means

Suppose a calculation gives data such as:

| \(k_\parallel\) | \(E_{e1}\) |
|---:|---:|
| 0.00 | 2.941 |
| 0.01 | 2.943 |
| 0.02 | 2.949 |
| 0.03 | 2.959 |

You can fit these points to

\[
\boxed{
E(k)
=
E(0)+Ak^2.
}
\]

Then identify

\[
\boxed{
A=\frac{\hbar^2}{2m^*}.
}
\]

That gives an effective mass.

Then you can represent the dispersion continuously as

\[
\boxed{
E(k)
=
E(0)+\frac{\hbar^2k^2}{2m^*}.
}
\]

---

# 17. Why the figure mentions Optel, Nextnano, or NRL Multibands

The figure suggests performing a \(k\cdot p\) calculation using tools such as:

- Optel,
- Nextnano,
- NRL Multibands.

The purpose is to obtain the electronic structure, especially

\[
\boxed{
E_n(k_\parallel)
}
\]

and the corresponding wavefunctions.

For the current workflow, Nextnano is the relevant tool.

---

# 18. What \(k\cdot p\) is doing here

At a simple level, \(k\cdot p\) theory describes how semiconductor bands and states change as one moves away from the Brillouin-zone center.

At

\[
k_\parallel=0,
\]

you have the zone-center confined states.

The \(k\cdot p\) model describes how those states evolve for

\[
k_\parallel>0.
\]

That is precisely the information needed for the \(k_\parallel\)-dependent denominators in \(\chi^{(2)}\).

---

# 19. How this maps to the Nextnano workflow

## Stage 1 — Define the structure

Specify:

- GaAs/AlGaAs layers,
- QW widths,
- tunneling barrier,
- compositions,
- interface grading.

---

## Stage 2 — Solve the confined problem

Use Nextnano to obtain

\[
\boxed{
E_{e1}(0),E_{e2}(0),E_{hh1}(0),E_{hh2}(0)
}
\]

and

\[
\boxed{
\psi_{e1}(z),\psi_{e2}(z),
\psi_{hh1}(z),\psi_{hh2}(z).
}
\]

---

## Stage 3 — Calculate matrix elements

From the wavefunctions, calculate quantities such as

\[
\boxed{
\langle hh_m|e_n\rangle
}
\]

and

\[
\boxed{
\langle e_n|z|e_l\rangle
}
\]

and

\[
\boxed{
\langle hh_m|z|hh_l\rangle.
}
\]

Under the approximation shown on the slide, evaluate them at

\[
k_\parallel=0.
\]

---

## Stage 4 — Determine the dispersion

Obtain or fit

\[
\boxed{
E_n(k_\parallel).
}
\]

For the simple constant-effective-mass model,

\[
\boxed{
E_n(k)
=
E_n(0)
+
\frac{\hbar^2k^2}{2m_n^*}.
}
\]

---

## Stage 5 — Construct transition energies

At each \(k\),

\[
\boxed{
\Delta E_{nm}(k)
=
E_{e,n}(k)
-
E_{hh,m}(k).
}
\]

---

## Stage 6 — Construct the optical detunings

For SHG at 1550 nm,

\[
\boxed{
D_{2\omega}(k)
=
\Delta E_{nm}(k)
-
1.60\ \mathrm{eV}
+
i\Gamma.
}
\]

The one-photon denominator is constructed similarly.

---

## Stage 7 — Perform the \(k\)-integral

Because the matrix elements are treated as constants,

\[
\boxed{
M(0)
\int
\frac{
2\pi k\,dk
}{
D_1(k)D_2(k)
}.
}
\]

The exact state-counting normalization must remain consistent with the implementation.

---

## Stage 8 — Sum all pathways

Repeat for the retained combinations of

\[
e_1,e_2,hh_1,hh_2
\]

and combine the electron-side and heavy-hole-side terms.

The result is

\[
\boxed{
\chi^{(2)}.
}
\]

---

# 20. What this slide adds beyond the previous slide

The previous "Functional Form" figure established that the system contains:

\[
\boxed{
\text{confined states}
+
\text{free in-plane motion}.
}
\]

This slide explains how to calculate those two pieces.

## Confined part

Get

\[
E_n(0),\psi_n
\]

from Nextnano.

## Free-motion part

Describe

\[
E_n(k_\parallel)
\]

with a dispersion relation such as

\[
\frac{\hbar^2k_\parallel^2}{2m^*}.
\]

## Combine them

\[
\boxed{
E_n(k_\parallel)
=
E_n(0)
+
E_{\text{free}}(k_\parallel).
}
\]

That is the main new concept introduced by this slide.

---

# 21. The key equation to memorize

If only one equation from this slide is memorized, use

\[
\boxed{
E_n(k_\parallel)
=
E_n(0)
+
\frac{\hbar^2k_\parallel^2}{2m_n^*}.
}
\]

In words:

> **The energy at finite in-plane momentum equals the confined-state energy at the zone center plus the kinetic energy from motion parallel to the quantum-well plane.**

---

# 22. The second key idea to memorize

The second major idea is

\[
\boxed{
\text{matrix elements at }k_\parallel=0
\quad\text{while}\quad
\text{energies depend on }k_\parallel.
}
\]

Mathematically,

\[
\boxed{
M(k_\parallel)\approx M(0)
}
\]

but

\[
\boxed{
E(k_\parallel)\neq E(0).
}
\]

Therefore the susceptibility contribution becomes approximately

\[
\boxed{
M(0)
\int
\frac{
2\pi k\,dk
}{
D_1[E(k)]D_2[E(k)]
}.
}
\]

That is the mathematical heart of the slide.

---

# 23. Study-guide checklist

You should be able to answer the following:

1. What does \(E_n(0)\) represent?
2. Why does the QW create discrete states along \(z\)?
3. What is \(k_\parallel\)?
4. Why does the energy change as \(k_\parallel\) increases?
5. What is effective mass \(m^*\)?
6. Why is the simple dispersion approximately parabolic?
7. Why are the matrix elements being evaluated at \(k_\parallel=0\)?
8. Why can they then be pulled outside the integral?
9. Which quantities remain inside the \(k_\parallel\) integral?
10. Why do the resonance denominators depend on \(k_\parallel\)?
11. Why is \(E_1=E_2\) for SHG?
12. What is \(E_1+E_2\) approximately for a 1550 nm fundamental?
13. Why does the integral contain \(2\pi k\,dk\)?
14. What information must Nextnano provide?
15. What must Python/post-processing calculate afterward?

---

# 24. One-sentence summary

\[
\boxed{
\text{Nextnano gives the confined states and wavefunctions near }k_\parallel=0;
\text{ evaluate the matrix elements there, model how the state energies disperse with }k_\parallel,\text{ and integrate the resulting resonance contributions over the in-plane }k\text{-states to obtain }\chi^{(2)}.
}
\]
