# Electron vs. Hole In-Plane Dispersion — Study Guide

## What this slide is trying to show

This slide is testing an approximation introduced on the previous slide.

The previous assumption was that the in-plane energy of every electron and hole state could be described using a simple constant-effective-mass parabola:

\[
\boxed{
E(k_\parallel)
=
E(0)
+
\frac{\hbar^2 k_\parallel^2}{2m^*}
}
\]

Your boss then used an Optel \(k\cdot p\) calculation to check whether the actual calculated states really follow that form.

The main result is:

\[
\boxed{
\text{Electron states are approximately parabolic}
}
\]

but

\[
\boxed{
\text{Hole states are not sufficiently parabolic}.
}
\]

Therefore:

- a simple effective-mass model is probably acceptable for electron states,
- a more accurate non-parabolic \(E_{hh}(k_\parallel)\) relation is needed for hole states.

This matters because the electron-hole transition energy enters directly into the resonance denominators of the \(\chi^{(2)}\) calculation.

---

# 1. The simplest interpretation

The slide asks:

> Can we represent the in-plane motion using a simple free-particle-like parabola?

For electrons:

\[
\boxed{\text{approximately yes}}
\]

For holes:

\[
\boxed{\text{not accurately enough}}
\]

So the previous simple model must now be refined.

---

# 2. The model being tested

The assumed dispersion relation is

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

This is a parabolic relation in \(k_\parallel\).

Here:

- \(E_{b,m}(0)\) is the confined-state energy at the zone center,
- \(k_\parallel\) is the in-plane wavevector,
- \(m_{b,m}^{*}\) is an effective mass.

If this equation matches the calculated \(E(k_\parallel)\) data, then one can describe the entire state using just \(E(0)\) and \(m^*\).

---

# 3. What the plots are showing

The horizontal axis is

\[
\boxed{k_\parallel}.
\]

The vertical axes show calculated state energies.

Each colored set of points represents an energy dispersion

\[
\boxed{
E_n(k_\parallel).
}
\]

At

\[
k_\parallel=0,
\]

the state is at the Brillouin-zone center.

Moving away from zero means increasing in-plane momentum.

The figure compares the calculated data with polynomial/parabolic fits.

---

# 4. What a simple parabolic dispersion looks like

If

\[
E(k)
=
E(0)
+
\frac{\hbar^2k^2}{2m^*},
\]

then the energy depends on

\[
k^2.
\]

That produces a symmetric parabola.

For a conduction-band electron state, this normally looks like an upward-opening curve with a minimum at

\[
k=0.
\]

Therefore, if the calculated data follow a smooth symmetric parabola, a constant-effective-mass approximation is reasonable.

---

# 5. Why fitting the parabola determines \(m^*\)

Write the dispersion as

\[
E(k)=E(0)+Ak^2.
\]

Compare with

\[
E(k)=E(0)+\frac{\hbar^2k^2}{2m^*}.
\]

Therefore,

\[
\boxed{
A=\frac{\hbar^2}{2m^*}.
}
\]

Solving for effective mass:

\[
\boxed{
m^*=\frac{\hbar^2}{2A}.
}
\]

So the curvature of the fitted parabola determines the effective mass.

## Strong curvature

Large \(A\)

\[
\Rightarrow
m^*\text{ is small}.
\]

## Weak curvature

Small \(A\)

\[
\Rightarrow
m^*\text{ is large}.
\]

This is what your boss means by saying that fitting the energies with a parabolic term allows \(m^*\) to be determined.

---

# 6. Conclusion for the electron states

The slide states:

> Electron states are more-or-less parabolic. Effective mass approximation should work.

That means the electron dispersions can probably be represented as

\[
\boxed{
E_{e,n}(k_\parallel)
=
E_{e,n}(0)
+
\frac{\hbar^2k_\parallel^2}{2m_{e,n}^{*}}.
}
\]

For example, one could fit separate masses for

\[
e_1
\]

and

\[
e_2.
\]

Then Python can evaluate the electron energy continuously at any required \(k_\parallel\).

This is much simpler than carrying a full discrete table of electron energies for every \(k\)-point.

---

# 7. Conclusion for the hole states

The second conclusion on the slide is:

> Hole state energies are not parabolic in the free dimension.

This means the hole energies do not follow one simple quadratic function in \(k_\parallel\) over the relevant range.

So the expression

\[
\boxed{
E_{hh}(k)
=
E_{hh}(0)
+
\frac{\hbar^2k^2}{2m_{hh}^{*}}
}
\]

is not accurate enough.

The important practical conclusion is:

\[
\boxed{
\text{one constant hole effective mass is insufficient}.
}
\]

---

# 8. Why the hole dispersion needs a different functional relation

The slide says:

> \(E(k_\parallel)\) needs a functional relation other than parabolic for integration.

That means the \(\chi^{(2)}\) calculation still needs a usable function

\[
E_{hh}(k_\parallel),
\]

but the function must be more flexible than

\[
E(0)+Ak^2.
\]

Possible representations could include:

\[
\boxed{
E_{hh}(k)
=
E_{hh}(0)
+
Ak^2
+
Bk^4
+\cdots
}
\]

or direct interpolation of the calculated \(k\cdot p\) data.

The slide itself does not specify the final fitting method. Its main conclusion is only that the simple parabolic model is not good enough for the holes.

---

# 9. How this changes the previous model

## Previous assumption

Use a constant effective mass for both electrons and holes:

\[
E_e(k)
=
E_e(0)
+
\frac{\hbar^2k^2}{2m_e^*}
\]

and

\[
E_{hh}(k)
=
E_{hh}(0)
+
\frac{\hbar^2k^2}{2m_{hh}^*}.
\]

## New conclusion after checking the \(k\cdot p\) results

For electrons:

\[
\boxed{
E_e(k)
\approx
E_e(0)
+
\frac{\hbar^2k^2}{2m_e^*}.
}
\]

For holes:

\[
\boxed{
E_{hh}(k)
=
F_{hh}(k)
}
\]

where \(F_{hh}(k)\) is a more accurate non-parabolic relation obtained from the calculated dispersion.

---

# 10. Why this matters for Equation 2

A key quantity in Equation 2 is the interband transition energy

\[
\boxed{
\Delta E_{nm}(k)
=
E_{e,n}(k)
-
E_{hh,m}(k).
}
\]

This energy difference appears directly inside the optical resonance denominator.

For example,

\[
\boxed{
D_{2\omega}(k)
=
E_{e,n}(k)
-
E_{hh,m}(k)
-
E_1
-
E_2
+
i\Gamma.
}
\]

Therefore, if the hole energy is modeled incorrectly, the transition energy is also wrong.

That directly changes the predicted resonance and therefore changes the calculated \(\chi^{(2)}\).

---

# 11. Why a hole-energy error can matter a lot

Suppose the true transition energy is

\[
1.600\ \mathrm{eV},
\]

but a poor parabolic hole model predicts

\[
1.630\ \mathrm{eV}.
\]

For a 1550 nm fundamental,

\[
E_1+E_2
\approx
1.60\ \mathrm{eV}.
\]

The true two-photon detuning is approximately

\[
1.600-1.600=0.
\]

The inaccurate model gives

\[
1.630-1.600=0.030\ \mathrm{eV}.
\]

Those correspond to very different resonance conditions.

Because the susceptibility contains factors roughly like

\[
\frac{1}{D_1D_2},
\]

even a modest energy error near resonance can create a large error in \(\chi^{(2)}\).

---

# 12. Why this is especially important near 1550 nm

At a 1550 nm fundamental,

\[
E_\omega\approx0.80\ \mathrm{eV}.
\]

For SHG,

\[
2E_\omega\approx1.60\ \mathrm{eV}.
\]

The coupled-QW transitions are intentionally designed to be near this energy.

Therefore the calculation is very sensitive to errors in

\[
\Delta E_{eh}(k).
\]

A small change in hole dispersion can shift where the system becomes resonant in \(k_\parallel\)-space.

That can substantially change the \(k\)-integrated nonlinear susceptibility.

---

# 13. What the zoomed inset is doing

The large plot shows the overall electron and hole energy dispersions.

The inset zooms in near

\[
k_\parallel=0.
\]

This makes subtle curvature easier to inspect.

The electron data appear close to smooth parabolic behavior.

The hole states show more complicated shapes and are not represented well by a single simple parabola over the range shown.

This visual comparison is the basis for the two conclusions on the right side of the slide.

---

# 14. Why use an Optel \(k\cdot p\) calculation first

Rather than assuming the effective-mass form, your boss calculated the actual dispersion

\[
\boxed{
E_n(k_\parallel)
}
\]

using a \(k\cdot p\)-type model.

Then the calculated results were used to test whether a simpler approximation is acceptable.

This gives the reasoning sequence:

\[
\boxed{
\text{calculate real dispersion}
}
\]

\[
\downarrow
\]

\[
\boxed{
\text{test parabolic approximation}
}
\]

\[
\downarrow
\]

Electron:

\[
\boxed{\text{simple model acceptable}}
\]

Hole:

\[
\boxed{\text{simple model inadequate}}.
\]

This is a better approach than assuming both carrier types are parabolic from the beginning.

---

# 15. How this applies to the Nextnano workflow

The analogous Nextnano workflow would be:

## Step 1 — Run a multiband calculation

Obtain

\[
E_{e1}(k_i),
\quad
E_{e2}(k_i),
\quad
E_{hh1}(k_i),
\quad
E_{hh2}(k_i)
\]

over a set of in-plane \(k\)-points.

---

## Step 2 — Test the electron dispersions

Fit the electron states to

\[
E_e(k)=E_e(0)+Ak^2.
\]

If the fit is good, calculate

\[
\boxed{
m_e^*=\frac{\hbar^2}{2A}.
}
\]

Then use the fitted electron dispersion in the \(\chi^{(2)}\) calculation.

---

## Step 3 — Test the heavy-hole dispersions

Try the same form:

\[
E_{hh}(k)=E_{hh}(0)+Ak^2.
\]

If the fit is poor, do not force a constant-effective-mass model.

Instead retain a more accurate representation of

\[
\boxed{
E_{hh}(k).
}
\]

---

## Step 4 — Build transition energies

For every relevant electron-heavy-hole pair,

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

## Step 5 — Put the transition energies into Equation 2

Use

\[
\Delta E_{nm}(k)
\]

inside the resonance denominators.

Then perform the \(k_\parallel\)-integral.

---

# 16. What happens to the matrix elements

This slide does not appear to change the previous approximation that the dipole matrix elements are evaluated at

\[
k_\parallel=0.
\]

So the model remains approximately

\[
\boxed{
M(k_\parallel)\approx M(0).
}
\]

The refinement introduced here concerns the energies:

\[
\boxed{
E_e(k)\approx\text{parabolic}
}
\]

while

\[
\boxed{
E_{hh}(k)\approx\text{non-parabolic}.
}
\]

The \(k\)-integral therefore becomes conceptually

\[
\boxed{
M(0)
\int
\frac{
2\pi k\,dk
}{
D_1[
E_e^{\mathrm{parab}}(k),
E_{hh}^{\mathrm{accurate}}(k)
]
D_2[
E_e^{\mathrm{parab}}(k),
E_{hh}^{\mathrm{accurate}}(k)
]
}.
}
\]

---

# 17. Before and after comparison

## Before testing

Assume:

\[
\boxed{
E_e(k)
=
E_e(0)
+
\frac{\hbar^2k^2}{2m_e^*}
}
\]

and

\[
\boxed{
E_{hh}(k)
=
E_{hh}(0)
+
\frac{\hbar^2k^2}{2m_{hh}^*}.
}
\]

## After testing

Electron:

\[
\boxed{
\text{parabolic approximation is reasonable}.
}
\]

Hole:

\[
\boxed{
\text{parabolic approximation is not sufficient}.
}
\]

So use

\[
\boxed{
E_{hh}(k)=F_{hh}(k)
}
\]

instead of one constant \(m_{hh}^*\).

---

# 18. Boss's reasoning step by step

## Step 1

Equation 2 requires integration over

\[
k_\parallel.
\]

Therefore the calculation needs

\[
E_n(k_\parallel).
\]

## Step 2

The simplest possible model is

\[
E(k)
=
E(0)
+
\frac{\hbar^2k^2}{2m^*}.
\]

## Step 3

Test that approximation with a multiband \(k\cdot p\) calculation.

## Step 4

Inspect the electron states.

They look approximately parabolic.

Therefore:

\[
\boxed{
\text{fit an electron effective mass}.
}
\]

## Step 5

Inspect the hole states.

They do not look sufficiently parabolic.

Therefore:

\[
\boxed{
\text{do not force one constant hole effective mass}.
}
\]

## Step 6

Create a better functional representation of

\[
E_{hh}(k).
\]

## Step 7

Calculate

\[
\boxed{
\Delta E_{eh}(k)
=
E_e(k)
-
E_{hh}(k).
}
\]

## Step 8

Insert this transition energy into the Equation 2 denominators.

## Step 9

Integrate over \(k_\parallel\).

---

# 19. Why this slide is scientifically important

This slide is part of a sequence of progressively checking and improving the model.

The logic is:

\[
\boxed{
\text{Equation contains }\sum_{k_\parallel}
}
\]

then

\[
\boxed{
\sum_k
\rightarrow
\int 2\pi k\,dk
}
\]

then

\[
\boxed{
\text{need }E_n(k)
}
\]

then

\[
\boxed{
\text{assume parabolic }E_n(k)
}
\]

and now

\[
\boxed{
\text{test whether that assumption is actually valid}.
}
\]

The result is

\[
\boxed{
\begin{array}{c}
\text{electron model can remain simple}\\
\text{hole model needs to be more realistic}
\end{array}
}
\]

This is an example of reducing model complexity only where the numerical physics supports it.

---

# 20. Practical Nextnano interpretation

For a Nextnano-based implementation, this slide suggests:

\[
\boxed{
\text{Nextnano kp8 / multiband calculation}
}
\]

\[
\downarrow
\]

extract

\[
\boxed{
E_{e1}(k),
E_{e2}(k),
E_{hh1}(k),
E_{hh2}(k)
}
\]

\[
\downarrow
\]

fit/test each curve

\[
\boxed{
\text{parabolic?}
}
\]

Then:

## Electron states

If the fit quality is good,

\[
\boxed{
E_e(k)
=
E_e(0)
+
\frac{\hbar^2k^2}{2m_e^*}.
}
\]

## Heavy-hole states

If the fit quality is poor,

\[
\boxed{
\text{use the calculated }E_{hh}(k)
\text{ directly or a more accurate fit}.
}
\]

Then calculate

\[
\boxed{
\Delta E_{nm}(k)
=
E_{e,n}(k)
-
E_{hh,m}(k)
}
\]

and use this in the \(k\)-resolved \(\chi^{(2)}\) integral.

---

# 21. Three things to memorize

## 1. Parabolic dispersion means constant effective mass

\[
\boxed{
E(k)
=
E(0)
+
\frac{\hbar^2k^2}{2m^*}
}
\]

corresponds to a constant effective-mass approximation.

---

## 2. The calculation shows different behavior for electrons and holes

\[
\boxed{
\text{electron states: approximately parabolic}
}
\]

\[
\boxed{
\text{hole states: non-parabolic}
}
\]

over the relevant range shown.

---

## 3. The consequence for Equation 2

The transition energy should use

\[
\boxed{
\Delta E_{eh}(k)
=
E_e^{\mathrm{simple}}(k)
-
E_{hh}^{\mathrm{more\ accurate}}(k).
}
\]

That accurate transition energy matters because it appears directly inside the resonance denominators.

---

# 22. One-sentence explanation of the slide

> **The \(k\cdot p\) calculation is being used to test whether the in-plane energies required for the \(\chi^{(2)}\) integral can be simplified to a constant-effective-mass parabola; the electron subbands are approximately parabolic, but the hole subbands are not, so the hole \(E(k_\parallel)\) dispersion must be represented more accurately when calculating the optical resonance denominators.**
