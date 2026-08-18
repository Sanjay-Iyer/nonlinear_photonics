# Demo 19 physics/model audit

## Executive finding and evidence boundary

Demo 19 is a controlled composition-profile study of one fixed, undoped, zero-field GaAs/AlGaAs asymmetric coupled quantum well. Every case uses the same 30.0 nm simulation domain and the same single-band Γ-electron and heavy-hole Schrödinger calculation. The only intended independent variable is the Al mole-fraction function at the four interfaces.

The repository contains licensed-solver summary values for all 13 cases. Every row says `solver_pass = True` but `physical_valid = False`, with the recorded reason “Demo 11/14 physical QC did not pass.” Consequently, the numerical spectra in the copied master table must not be presented as validated Demo 19 results. The raw licensed output tree and the proprietary material database used for that run are not present in this checkout, so the exact failed QC sub-check and database coefficients cannot be audited here.

Evidence used:

- the fixed case definitions and grading renderer;
- the generated Nextnano++ decks and imported composition tables;
- the inherited Demo 14 material, mesh, state, and optical configuration;
- the inherited Demo 11 analysis and shared χ² equation;
- the tracked work-machine configuration;
- the copied Demo 19 master results.

Anything not established by those artifacts is labeled **UNKNOWN**.

## 1. Structure

The growth coordinate is called `x` in the Nextnano++ deck and `z` in plots and equations. This audit uses (z).

| Nominal interval (nm) | Material | Al fraction |
|---:|---|---:|
| $0.0 \le z < 9.1$ | left outer barrier, Al\(_{0.55}\)Ga\(_{0.45}\)As | 0.55 |
| $9.1 \le z \le 16.2$ | thick GaAs well | 0 |
| $16.2 < z < 18.0$ | tunnel barrier, Al\(_{0.55}\)Ga\(_{0.45}\)As | 0.55 |
| $18.0 \le z \le 20.9$ | thin GaAs well | 0 |
| $20.9 < z \le 30.0$ | right outer barrier, Al\(_{0.55}\)Ga\(_{0.45}\)As | 0.55 |

The exact fixed dimensions are:

- left outer barrier: **9.1 nm**;
- thick well: **7.1 nm**;
- tunnel barrier: **1.8 nm**;
- thin well: **2.9 nm**;
- right outer barrier: **9.1 nm**;
- total outer/period barrier material: (9.1+9.1=18.2) nm;
- total simulation length: $18.2+7.1+1.8+2.9=\mathbf{30.0\ nm}$.

The nominal interfaces are:

| Interface | Physical transition | Position |
|---|---|---:|
| I1 | outer AlGaAs → thick GaAs well | **9.1 nm** |
| I2 | thick GaAs well → tunnel AlGaAs | **16.2 nm** |
| I3 | tunnel AlGaAs → thin GaAs well | **18.0 nm** |
| I4 | thin GaAs well → outer AlGaAs | **20.9 nm** |

In a graded case, the “nominal interval” coordinates above do not move, but portions on both sides of an interface cease to be pure material and instead carry intermediate $x_{\rm Al}$.

## 2. Grading geometry

“Grading width = 0.7 nm” means the **full start-to-end transition width** over which $x_{\rm Al}$ reaches both exact endpoints 0 and 0.55. It is not a half-width. A width $W$ is centered on the nominal abrupt interface $z_i$, so the grade occupies

\[
[z_i-W/2,\;z_i+W/2].
\]

For (W=0.7) nm, (W/2=0.35) nm. The four exact intervals are:

| Interface | Grade interval (nm) | Direction |
|---|---:|---|
| I1 | **8.75–9.45** | 0.55 → 0 |
| I2 | **15.85–16.55** | 0 → 0.55 |
| I3 | **17.65–18.35** | 0.55 → 0 |
| I4 | **20.55–21.25** | 0 → 0.55 |

The nominal well widths, tunnel-barrier width, outer-barrier allocation, interface centers, and 30.0 nm domain all remain fixed. Equal lengths (W/2) of the two adjacent nominal regions are replaced by graded alloy.

When all four interfaces have the same width $W$, the pure-material plateau lengths are:

\[
\begin{aligned}
L_{\rm left\ outer,pure}&=9.1-W/2,\\
L_{\rm thick\ well,pure}&=7.1-W,\\
L_{\rm tunnel,pure}&=1.8-W,\\
L_{\rm thin\ well,pure}&=2.9-W,\\
L_{\rm right\ outer,pure}&=9.1-W/2.
\end{aligned}
\]

For (W=0.7) nm, these are **8.75, 6.4, 1.1, 2.2, and 8.75 nm**, respectively. At the largest symmetric linear case, (W=1.4) nm, they are **8.4, 5.7, 0.4, 1.5, and 8.4 nm**. No Demo 19 grading intervals overlap.

## 3. Grading mathematics

For a nonzero grade centered at (z_i), define

\[
z_- = z_i-W/2,\qquad z_+=z_i+W/2,\qquad
u(z)=\operatorname{clip}\!\left(\frac{z-z_-}{W},0,1\right).
\]

Let $x_L$ and $x_R$ be the Al fractions immediately to the left and right. I1 and I3 use $(x_L,x_R)=(0.55,0)$; I2 and I4 use $(0,0.55)$. Inside the grade,

\[
x_{\rm Al}(z)=x_L+(x_R-x_L)f[u(z)].
\]

Outside the finite grade interval, the function is constant at the appropriate adjacent pure-material value. Thus “0.7 nm” enters only through $W=0.7$ nm in $z_\pm=z_i\pm0.35$ nm and in the normalization of $u$.

### Abrupt

The abrupt case bypasses a smooth ramp. The implemented whole-device helper starts with $x_{\rm Al}=0.55$ and overwrites the two closed well intervals with zero:

\[
x_{\rm Al}^{\rm abrupt}(z)=
\begin{cases}
0, & 9.1\le z\le16.2\ \text{or}\ 18.0\le z\le20.9,\\
0.55, & \text{otherwise on }[0,30].
\end{cases}
\]

Equivalently, each nominal interface is a step. The value assigned at the mathematical discontinuity is a zero-measure convention and has no physical effect on the continuum eigenproblem.

### Linear

\[
f_{\rm linear}(u)=u.
\]

It reaches 0 and 1 exactly at the finite interval endpoints; no tail or cutoff is needed beyond clipping (u) to ([0,1]).

### Fermi-like

This is an endpoint-normalized logistic, not a thermodynamic Fermi–Dirac occupation. Define

\[
L(u)=\frac{1}{1+\exp[-10(u-1/2)]},
\]

then

\[
f_{\rm Fermi}(u)=\frac{L(u)-L(0)}{L(1)-L(0)}
=\frac{L(u)-[1+e^5]^{-1}}{[1+e^{-5}]^{-1}-[1+e^5]^{-1}}.
\]

The raw logistic is truncated at the finite arguments (-5) and (+5), then affinely normalized so the finite endpoints are exactly 0 and 1. Temperature does not enter this grading function.

### Error function

\[
f_{\rm erf}(u)=
\frac{\operatorname{erf}[3(u-1/2)]-\operatorname{erf}(-1.5)}
{\operatorname{erf}(1.5)-\operatorname{erf}(-1.5)}.
\]

The raw error function is truncated at arguments (-1.5) and (+1.5), corresponding to the configured span parameter 3 across the normalized interval, and endpoint-normalized to exactly 0 and 1.

### Cosine

\[
f_{\rm cosine}(u)=\frac{1-\cos(\pi u)}{2}.
\]

This raised-cosine ramp already reaches 0 and 1 exactly. It is clipped to the finite grade through $u\in[0,1]$.

For all four smooth/linear forms, multiplication by $x_R-x_L=\pm0.55$ and addition of $x_L$ maps the normalized fraction exactly to the required 0↔0.55 composition range.

### Imported-profile sampling

The Fermi-like, erf, and cosine whole-device profiles are sampled from 0 to 30 nm at **0.05 nm intervals**, including the domain endpoints and explicit interface/grade endpoints. The symmetric 0.7 nm profiles have exactly **601 DAT rows** because all relevant points already lie on that grid. Nextnano++ linearly interpolates between consecutive rows, so the function actually solved is the piecewise-linear interpolation of the tabulated smooth profile. The preflight comparison evaluates the analytic profile on a 0.0025 nm audit grid (20× finer) and records the interpolation error; this fine grid is validation only, not a Nextnano input grid.

## 4. Nextnano++ representation

### Abrupt

The structure is initialized everywhere as constant Al\(_{0.55}\)Ga\(_{0.45}\)As. Two GaAs regions then overwrite 9.1–16.2 nm and 18.0–20.9 nm. There is no grading keyword.

### Linear: native `ternary_linear`

`ternary_linear` tells Nextnano++ that the named ternary alloy has a mole fraction varying linearly between two endpoint values over the specified spatial interval. `alloy_x` is the Al mole fraction for `Al(x)Ga(1-x)As`; the nested `x=[...]` is the growth-coordinate span in nm.

The exact I1 block for the 0.7 nm case is:

```text
region{
    line{ x = [8.750000, 9.450000] }
    ternary_linear{ name = "Al(x)Ga(1-x)As"  alloy_x = [0.550000, 0.000000]  x = [8.750000, 9.450000] }
}
```

The four endpoint pairs are 0.55→0 at I1, 0→0.55 at I2, 0.55→0 at I3, and 0→0.55 at I4.

### Fermi-like, erf, and cosine: `ternary_import`

The imported file is a two-column ASCII DAT table:

1. column 1: position (z) in nm;
2. column 2: dimensionless Al mole fraction $x_{\rm Al}$.

The exact input representation is:

```text
import{
    file{ name = "al_profile"  filename = "al_profile.dat"  format = DAT  number_of_dimensions = 1 }
    output_imports{}
}

region{
    line{ x = [0.000000, 30.000000] }
    ternary_import{ name = "Al(x)Ga(1-x)As"  import_from = "al_profile" }
}
```

`ternary_import` applies the imported local alloy fraction to `Al(x)Ga(1-x)As` across the complete domain. Nextnano++ uses linear interpolation between DAT rows. For example, the Fermi-like I1 samples include $x_{\rm Al}(8.75)=0.55$, $x_{\rm Al}(9.10)=0.275$, and $x_{\rm Al}(9.45)=0$.

## 5. Material model

| Item | Actual Demo 19 setting or audit result |
|---|---|
| Temperature | **300 K** |
| Selected database | Configured as `C:/Code/optics/nextnano/2026_07_03/nextnano++/database/database.nnp` |
| Database availability here | **UNKNOWN** coefficients: the configured proprietary file is not in this checkout |
| GaAs representation | Nextnano binary material named **`GaAs`** |
| Alloy representation | Nextnano ternary named **`Al(x)Ga(1-x)As`**, with local `alloy_x=x_Al(z)` |
| Band-gap model and numerical parameters | **UNKNOWN**; no deck override and database file absent |
| Γ conduction-band offset rule/value | **UNKNOWN**; inherited from database, no explicit offset ratio in the deck |
| HH/LH/SO valence-band offset rule/value | **UNKNOWN**; inherited from database, no explicit offset ratio in the deck |
| Γ electron effective-mass formula | **UNKNOWN** database formula; no mass override in the deck |
| HH growth-direction effective-mass formula | **UNKNOWN** database formula; no mass override in the deck |
| Local composition dependence | The deck passes local $x_{\rm Al}(z)$ to the ternary material, so band edges and any database-defined alloy-interpolated parameters are evaluated locally. Exactly which parameters and mixing/bowing rules vary is **UNKNOWN** without `database.nnp`. |
| Dielectric model | Nextnano database value/formula **UNKNOWN** and unused by this non-Poisson solve. The optical χ² prefactor separately uses vacuum permittivity $\epsilon_0$, not a semiconductor relative dielectric constant. |
| Strain | **Not included**: no strain model is configured or run. `substrate{GaAs}` and crystal axes are present, but `run{ quantum{} }` contains no strain solve. |
| Nonparabolicity | **UNKNOWN**: no explicit enable/disable or parameter appears in the deck; the solver/database default is not available here. |
| Bowing parameters | **UNKNOWN**: no explicit bowing coefficient is present and the selected database is absent. |

The deck sets the simulation crystal axes to $x_{hkl}=[1,0,0]$ and $y_{hkl}=[0,1,0]$. Its one-dimensional coordinate is simulation `x` (therefore [100]); the repository relabels that same coordinate as growth `z` in plots and optical notation. The requested “growth_z” dipole polarization is `re=[1,0,0]`, along the one-dimensional simulation axis.

Do not substitute the optical postprocessor’s fixed in-plane masses (0.067 and 0.112 $m_0$) for Nextnano’s confinement masses. They belong to a separate parabolic $k_\parallel$ dispersion added after the solver.

## 6. Quantum model

The deck explicitly requests separate **single-band effective-mass** models:

- Γ conduction electrons: `Gamma{ num_ev=6 }`;
- heavy holes: `HH{ num_ev=6 }`.

It does not request 6-band or 8-band $k\cdot p$. The conceptual continuum equation for band $b\in\{\Gamma,HH\}$ is

\[
\hat H_b\psi_{b,n}(z)=E_{b,n}\psi_{b,n}(z),
\qquad
\hat H_b=\hat T_b[m_b^*(z)]+V_b(z),
\]

with the commonly used position-dependent-mass representation

\[
\hat T_b=-\frac{\hbar^2}{2}\frac{d}{dz}
\left[\frac{1}{m_b^*(z)}\frac{d}{dz}\right].
\]

The repository establishes “single-band effective-mass Schrödinger,” but it does **not** establish the proprietary solver’s exact heterointerface operator ordering or finite-difference/eigensolver implementation. Therefore the second equation is the physical continuum representation of the configured model, while the exact internal discretization is **UNKNOWN**.

$V_\Gamma(z)$ is the local Γ conduction-band edge. The HH problem uses the local heavy-hole valence-band edge and the solver’s HH mass/sign convention; hole eigenvalues are reported on Nextnano’s common electron-energy scale, so interband transitions are computed as $E_{e,n}-E_{hh,m}$.

This is a **Schrödinger-only**, non-self-consistent calculation:

- `run{ quantum{} }`, not Poisson or Schrödinger–Poisson;
- `no_density = yes`, so quantum charge density is not computed or fed back;
- no doping regions;
- no free-carrier charge density;
- no applied electric field;
- no electrostatic boundary conditions, because Poisson is not solved;
- a nominal zero-bias Fermi contact is declared but does not create an electrostatic problem in this run.

The quantum region is **7.1–22.9 nm**, i.e. the 9.1–20.9 nm active stack plus 2.0 nm of outer barrier on each side. Quantum boundary conditions are **Dirichlet at both ends** of that region. Six Γ states and six HH states are requested and up to six of each are output. Only the first two of each band are used in χ².

## 7. Numerics

The exact grid control lines supplied to Nextnano++ are:

```text
line{ pos = 0.000000  spacing = 0.500000 }
line{ pos = 9.100000  spacing = 0.050000 }
line{ pos = 20.900000 spacing = 0.050000 }
line{ pos = 30.000000 spacing = 0.500000 }
```

Thus the configured active-region spacing is **0.05 nm**, the configured outer-domain spacing is **0.5 nm**, and the domain is **0–30 nm**. These are grid-control values; the exact list of realized mesh nodes produced between control lines is not preserved in the copied Demo 19 results.

Other exact numerical settings are:

- quantum domain: 7.1–22.9 nm;
- requested eigenvalues: 6 Γ and 6 HH;
- output state cap: 6;
- solver threads: 1;
- wall-clock timeout: 3600 s per case;
- explicit Nextnano eigensolver algorithm/tolerance/iteration limits: **UNKNOWN/not specified**, so executable defaults apply;
- explicit Schrödinger convergence loop: none, because there is no self-consistent Poisson loop;
- envelope orthonormality acceptance tolerance in post-analysis: $10^{-3}$;
- maximum allowed boundary probability: $10^{-3}$, measured in the outermost 5% of the quantum grid;
- minimum confined probability diagnostic: 0.5;
- origin-independence check: 100 nm coordinate shift, relative limit $10^{-6}$, absolute tolerance $10^{-12}$, scale floor $10^{-9}$;
- $k_\parallel$ convergence probes: 48, 96, 192, and 384 points, compared with the finest grid at relative tolerance $10^{-3}$; production uses 96 points.

All 13 cases use exactly the same deck-level temperature, domain, grid controls, quantum region, boundary conditions, requested states, and optical settings. Smooth imported composition profiles are always tabulated at 0.05 nm even in the outer barriers.

## 8. Which Demo 19 quantities are direct solver outputs?

| Quantity | Classification in the Demo 19 reported pipeline | Explanation |
|---|---|---|
| Γ conduction-band edge $E_c(z)$ | **DIRECT NEXTNANO OUTPUT** | From requested band-edge output. |
| HH/valence band edge $E_{HH}(z)$ | **DIRECT NEXTNANO OUTPUT** | HH, LH, and SO classical edges are requested; Demo 19 uses HH. |
| $E_1,E_2$ | **DIRECT NEXTNANO OUTPUT** | Parsed from Γ energy spectrum. |
| $HH_1,HH_2$ | **DIRECT NEXTNANO OUTPUT** | Parsed from HH energy spectrum. |
| Envelope wavefunctions/probability densities | **DIRECT NEXTNANO OUTPUT** | Both envelopes and probabilities are requested. |
| State centroids $\langle z\rangle$ | **CALCULATED IN PYTHON FROM NEXTNANO OUTPUT** | $\int z\rho_n(z)dz/\int\rho_n(z)dz$, using solver probability density. |
| Reported $O_{nm}$ overlaps | **CALCULATED IN PYTHON FROM NEXTNANO OUTPUT** | $O_{nm}=\int\psi_{e,n}\psi_{hh,m}dz$ from parsed envelopes. Native `overlap_integrals{Gamma_HH{}}` is also requested, but the master-table $O_{ij}$ comes from the Python χ² matrix calculation. |
| Reported electron $z^e_{nl}$ | **CALCULATED IN PYTHON FROM NEXTNANO OUTPUT** | $\int\psi_{e,n}z\psi_{e,l}dz$. |
| Reported HH $z^{hh}_{ml}$ | **CALCULATED IN PYTHON FROM NEXTNANO OUTPUT** | $\int\psi_{hh,m}z\psi_{hh,l}dz$. |
| Native dipole/position matrices | **DIRECT NEXTNANO OUTPUT exists** | Requested for Γ and HH with growth-axis polarization, but those native values are not the source of the Demo 19 master-table matrices or χ² calculation. |
| $E_{e,n}-E_{hh,m}$ transition table used by χ² | **CALCULATED IN PYTHON FROM NEXTNANO OUTPUT** | Differences of solver eigenenergies; a native Γ–HH transition-energy output is also requested but is not the arithmetic source used by the postprocessor. |

## 9. Optical postprocessing

### Inputs and fixed settings

- Solver states supplied: up to 6 Γ and 6 HH.
- States entering every $m,n,l$ sum: **first 2 Γ and first 2 HH only**.
- Zero-$k$ transition energy:
  \[
  \Delta E_{nm}(0)=E_{e,n}-E_{hh,m}.
  \]
- In-plane dispersion:
  \[
  \Delta E_{nm}(k)=\Delta E_{nm}(0)+\frac{\hbar^2k^2}{2\mu},\qquad
  \mu^{-1}=m_e^{-1}+m_{hh,\parallel}^{-1}.
  \]
- Optical-dispersion masses: $m_e=0.067m_0$, $m_{hh,\parallel}=0.112m_0$, hence $\mu=0.0419218m_0$.
- Envelope overlap:
  \[
  O_{nm}=\langle\psi_{e,n}|\psi_{hh,m}\rangle
  =\int\psi_{e,n}(z)\psi_{hh,m}(z)\,dz.
  \]
- Intrasubband position matrices:
  \[
  z^e_{nl}=\int\psi_{e,n}(z)z\psi_{e,l}(z)\,dz,
  \qquad
  z^{hh}_{ml}=\int\psi_{hh,m}(z)z\psi_{hh,l}(z)\,dz.
  \]
- Bloch interband position matrix element: $r_{e,hh}=0.751$ nm = 7.51 Å. It is a position, not $e r$.
- Broadening: $\Gamma=5.0$ meV = 0.005 eV in the energy-form denominators.
- $N_z$: `period_density`, one coupled-well period per 30.0 nm, so
  \[
  N_z=(30.0\times10^{-9}\ \mathrm m)^{-1}=3.3333333\times10^7\ \mathrm{m^{-1}}.
  \]
  The configured alternative two-wells-per-period convention is only a sensitivity, not the production value.
- Spin degeneracy: **2**.
- Radial $k_\parallel$ grid: **96 linearly spaced points**, including 0 and $k_{\max}$.
- Cutoff convention: $k_{\max}=0.1\pi/a$, with $a=0.565325$ nm, giving **0.55571444 nm⁻¹**.
- $k$-space normalization:
  \[
  \frac1A\sum_{\mathbf k}\rightarrow\int\frac{d^2k}{(2\pi)^2}
  =\frac1{2\pi}\int_0^{k_{\max}}k\,dk,
  \]
  evaluated by trapezoidal radial weights and multiplied by spin factor 2.
- Envelope matrix elements are assumed independent of $k_\parallel$; only transition energies disperse.
- Fermi/occupation factor: **unity**—full valence band and empty conduction band. There is no optical Fermi-level or finite-temperature occupation integration. The 300 K solver temperature affects the material model, not this occupation factor.
- Focused wavelength grid used for Demo 19 reporting: **1400–1800 nm, 401 points**, i.e. 1 nm increments.
- A broad grid is also configured: **400–1800 nm, 701 points**, i.e. 2 nm increments.
- The photon energy in the spectrum is the fundamental, $E_\omega=hc/\lambda$, and SHG sets $\omega_1=\omega_2=\omega$.

### Implemented χ² equation

In the repository’s angular-frequency notation,

\[
\chi^{(2)}_{xzx}(\omega_1,\omega_2)=
\frac{N_z e^3r_{e,hh}^2}{6\epsilon_0\hbar^2}
\sum_{k_\parallel}\sum_{m,n}\sum_l
\left[
\frac{O_{nm}\,z^e_{nl}\,O_{lm}}
{(\omega^{e,n}_{hh,m}-\omega_1-\omega_2+i\Gamma)
 (\omega^{e,l}_{hh,m}-\omega_1+i\Gamma)}
-
\frac{O_{nm}\,z^{hh}_{ml}\,O_{nl}}
{(\omega^{e,n}_{hh,m}-\omega_1-\omega_2+i\Gamma)
 (\omega^{e,n}_{hh,l}-\omega_1+i\Gamma)}
\right].
\]

The production code evaluates the algebraically equivalent energy form for SHG:

\[
\chi^{(2)}_{xzx}(E_\omega)=
\frac{N_z e^3r_{e,hh}^2}{6\epsilon_0}
\int\frac{d^2k}{(2\pi)^2}
\sum_{m,n,l}
\left[
\frac{O_{nm}z^e_{nl}O_{lm}}
{[\Delta E_{nm}(k)-2E_\omega+i\gamma]
 [\Delta E_{lm}(k)-E_\omega+i\gamma]}
-
\frac{O_{nm}z^{hh}_{ml}O_{nl}}
{[\Delta E_{nm}(k)-2E_\omega+i\gamma]
 [\Delta E_{nl}(k)-E_\omega+i\gamma]}
\right],
\]

where $\gamma=0.005$ eV. In the angular-frequency form, the corresponding rate is $\Gamma_\omega=\gamma/\hbar$. The explicit $\hbar^{-2}$ disappears because both angular-frequency denominators are rewritten as energy denominators. Length, $k$-measure, and eV-to-joule conversions are then applied explicitly, and the result is converted from m/V to pm/V. No fitted scale factor is used.

The postprocessor normalizes parsed envelopes before integration and refuses χ² when the within-band Gram matrices differ from identity by more than $10^{-3}$. It also checks that translating the coordinate origin leaves χ² unchanged.

This section describes the fixed model only. It does not revisit any Demo 18 discrepancy analysis.

## 10. Causal chain for a meeting

**Grading input → $x_{\rm Al}(z)$.** A case specifies a profile family and one full transition width for each of I1–I4. Those widths are centered on the fixed nominal interfaces and mapped to a bounded, endpoint-normalized Al-fraction function from 0 to 0.55.

**$x_{\rm Al}(z)$ → local material parameters/band edges.** Nextnano receives either native linear alloy regions or a tabulated ternary alloy fraction. At each position it uses the selected material database to construct the local Γ and valence band edges and any composition-dependent effective masses; the exact database interpolation coefficients are unavailable in this checkout.

**Local material parameters → quantum Hamiltonian.** The local band edge is the confinement potential and the local band mass enters a separate one-band Γ or HH effective-mass Schrödinger operator. There is no doping, field, carrier-density feedback, Poisson solve, strain solve, or multiband coupling.

**Hamiltonian → electron and HH eigenstates.** Nextnano solves the two 1D eigenproblems on the same 7.1–22.9 nm quantum box with Dirichlet endpoints and returns six energies plus envelopes/probability densities for each band.

**Eigenstates → energies, overlaps, and dipoles.** The first two Γ and HH energies are read directly. The reporting/optical layer integrates their normalized envelopes to obtain interband overlaps and within-band $z$ matrix elements; it also computes probability centroids from solver densities.

**Energies, overlaps, and dipoles → χ² spectrum.** The code inserts those quantities into the fixed two-band triple-sum formula, adds parabolic in-plane transition dispersion, integrates to $0.1\pi/a$ with spin factor 2, and applies $r_{e,hh}$, $N_z$, and 5 meV broadening to produce complex χ² and |χ²| versus fundamental wavelength.

## 11. Twenty likely expert questions and repository-grounded answers

1. **Does 0.7 nm mean ±0.7 nm?** No. It is the full width; the endpoints are $z_i\pm0.35$ nm.

2. **Do the interfaces move when graded?** No. I1–I4 remain at 9.1, 16.2, 18.0, and 20.9 nm; each is the grade center.

3. **Does grading change total well thickness or period length?** No. The nominal dimensions and 30.0 nm domain stay fixed; pure-material plateau lengths shrink.

4. **How much pure tunnel barrier remains at 0.7 nm symmetric grading?** 1.1 nm, because both adjacent half-grades consume 0.35 nm.

5. **Are the logistic and erf widths 10–90% widths?** No. In Demo 19 they are full, finite, endpoint-to-endpoint widths. The raw smooth functions are truncated and normalized to reach exact endpoints.

6. **Is the Fermi-like profile temperature dependent?** No. It is a logistic shape with dimensionless steepness 10; 300 K does not enter that grading equation.

7. **Why is linear native but the other shapes imported?** The actual deck uses Nextnano `ternary_linear` for a linear mole-fraction ramp. The smooth profiles are supplied as $x_{\rm Al}(z)$ DAT tables through `ternary_import`.

8. **What interpolation does an imported profile receive?** Linear interpolation between 0.05 nm-spaced DAT rows. Thus the solver sees a piecewise-linear approximation of the analytic smooth shape.

9. **Do all cases use the same numerical mesh?** Yes: identical 0.05 nm active and 0.5 nm outer grid controls. Imported tables also use the same 0.05 nm sampling.

10. **Is this Schrödinger–Poisson?** No. It is a Schrödinger-only quantum run with `no_density=yes`, no doping, and no Poisson block.

11. **Is an electric field applied by the contact?** No field is solved. A zero-bias contact is declared, but without Poisson/current it does not create an electrostatic potential profile.

12. **Are the valence states multiband $k\cdot p$?** No. The quantum deck requests a separate single-band HH effective-mass model. LH and SO band edges are output classically but not quantized for χ².

13. **How many states are converged and how many enter optics?** Six Γ and six HH eigenvalues are requested; only the first two of each enter the optical triple sum.

14. **Are overlap and $z$ matrices taken from Nextnano’s native optical outputs?** Native outputs are requested, but the reported Demo 19 matrices and χ² are recomputed from normalized Nextnano envelopes by numerical integration.

15. **Are confinement masses the same 0.067/0.112 $m_0$ used in the optical integral?** Not established. Those two fixed values are only the postprocessor’s in-plane dispersion masses. Nextnano confinement masses come from the absent material database.

16. **What band-offset ratio and alloy bowing are used?** **UNKNOWN** from this checkout. There is no explicit override; the configured `database.nnp` controls them and is not present.

17. **Is strain included?** No strain solve is configured. The GaAs substrate declaration alone does not add a `run{strain{}}` calculation.

18. **What is the $k_\parallel$ cutoff?** $0.1\pi/a=0.55571444$ nm⁻¹ using $a=0.565325$ nm, with 96 radial points and spin degeneracy 2.

19. **What sets the absolute χ² scale?** $r_{e,hh}=0.751$ nm, $N_z=1/(30\,\mathrm{nm})$, $e^3/(6\epsilon_0)$, the normalized 2D $k$-integral, and explicit SI conversions. No calibration factor is fitted.

20. **Are the copied Demo 19 numerical spectra validated?** No. All 13 summary rows record a successful solver return but failed inherited physical QC. The raw run needed to identify the specific failed sub-check is absent here.

## 12. One-page cheat sheet

### Fixed structure

- 0–9.1 nm: Al\(_{0.55}\)Ga\(_{0.45}\)As outer barrier
- 9.1–16.2 nm: 7.1 nm GaAs well
- 16.2–18.0 nm: 1.8 nm Al\(_{0.55}\)Ga\(_{0.45}\)As tunnel barrier
- 18.0–20.9 nm: 2.9 nm GaAs well
- 20.9–30.0 nm: Al\(_{0.55}\)Ga\(_{0.45}\)As outer barrier
- I1/I2/I3/I4 = 9.1/16.2/18.0/20.9 nm; total = 30.0 nm

### Grading definition and equations

- $W$ is full width centered on $z_i$: $z_\pm=z_i\pm W/2$
- $u=\operatorname{clip}[(z-z_-)/W,0,1]$
- $x_{\rm Al}=x_L+(x_R-x_L)f(u)$, with endpoints 0 and 0.55
- linear: $f=u$
- Fermi-like: $f=[L(u)-L(0)]/[L(1)-L(0)]$, $L=[1+e^{-10(u-1/2)}]^{-1}$
- erf: $f=[\operatorname{erf}(3(u-1/2))-\operatorname{erf}(-1.5)]/[\operatorname{erf}(1.5)-\operatorname{erf}(-1.5)]$
- cosine: $f=(1-\cos\pi u)/2$
- 0.7 nm intervals: 8.75–9.45, 15.85–16.55, 17.65–18.35, 20.55–21.25 nm
- smooth DAT: position nm + dimensionless $x_{\rm Al}$, 0.05 nm sampling, linear interpolation

### Nextnano material/quantum model

- 300 K; GaAs binary + local Al(x)Ga(1−x)As ternary
- external database path: `.../2026_07_03/nextnano++/database/database.nnp`
- exact gaps, offsets, masses, dielectric, nonparabolicity, bowing: **UNKNOWN** here
- no strain, doping, charge density, field, or Poisson
- separate one-band Γ electron and one-band HH effective-mass Schrödinger equations
- quantum box 7.1–22.9 nm; Dirichlet endpoints
- request/output 6 Γ + 6 HH states

### Mesh and numerical/QC controls

- domain 0–30 nm
- active control spacing 0.05 nm; outer control spacing 0.5 nm
- explicit eigen-solver tolerances: **UNKNOWN/default**
- envelope orthonormality $10^{-3}$; boundary probability $10^{-3}$
- optical $k$-convergence probes 48/96/192/384, tolerance $10^{-3}$
- same settings for every grading case

### Optical model

- use first 2 Γ + first 2 HH states in all $m,n,l$ sums
- $O_{nm}=\int\psi_{e,n}\psi_{hh,m}dz$
- $z^e_{nl}=\int\psi_{e,n}z\psi_{e,l}dz$; $z^{hh}_{ml}=\int\psi_{hh,m}z\psi_{hh,l}dz$
- $r_{e,hh}=0.751$ nm; $\Gamma=5$ meV
- $N_z=3.3333333\times10^7$ m⁻¹ (one 30 nm period)
- $m_e=0.067m_0$, $m_{hh,\parallel}=0.112m_0$; spin = 2
- 96 radial $k$ points; $k_{\max}=0.55571444$ nm⁻¹
- occupation factor = 1; envelopes $k$-independent
- focused spectrum 1400–1800 nm in 1 nm steps; broad spectrum 400–1800 nm in 2 nm steps

### Output provenance

- **Direct Nextnano:** realized alloy composition, band edges/gap, Γ and HH energies, envelopes, probabilities; native transitions/overlaps/dipoles are also requested.
- **Python from Nextnano:** centroids, reported overlaps, reported $z$ matrices, transition-energy differences, χ² spectrum, 1550 nm value, peak, and comparisons.
- **Status warning:** copied run = 13/13 solver returns succeeded, 0/13 marked physically valid; do not present its spectra as validated.
