"""Energy-domain Eq.2, adapted from the independently audited Demo26 engine.

Reference: extended_implementation_audit.independent_eq2 (bra/ket conjugations),
Demo22 chi2_from_k_inputs (real-input baseline), Demo20 absolute_prefactor.
No runtime dependency on any prior demo. Wavelength always means fundamental.
"""
from dataclasses import dataclass
import numpy as np

HC_EV_NM = 1239.841984
E_C = 1.602176634e-19
EPS0 = 8.8541878128e-12


@dataclass(frozen=True)
class Settings:
    gamma_meV: float = 5.0
    spin_degeneracy: int = 2
    period_nm: float = 30.0
    r_e_hh_nm: float = 0.751
    gamma_sign: int = 1

    def __post_init__(self):
        if not np.isfinite(self.gamma_meV) or self.gamma_meV <= 0:
            raise ValueError("Gamma must be a positive finite broadening in meV")
        if self.gamma_sign not in (-1, 1) or self.spin_degeneracy not in (1, 2):
            raise ValueError("gamma_sign must be +/-1; spin degeneracy must be 1 or 2")
        if not np.isfinite(self.period_nm) or self.period_nm <= 0 or not np.isfinite(self.r_e_hh_nm) or self.r_e_hh_nm <= 0:
            raise ValueError("period and interband length must be positive finite nm")

    @property
    def gamma_eV(self):
        return self.gamma_meV * 1e-3


def photon_energy(wavelength_nm):
    wavelength_nm = np.asarray(wavelength_nm, float)
    if wavelength_nm.ndim != 1 or not np.all(np.isfinite(wavelength_nm)) or np.any(wavelength_nm <= 0):
        raise ValueError("fundamental wavelengths must be a positive finite 1D array")
    return HC_EV_NM / wavelength_nm


def radial_weights(k, spin=2):
    """Trapezoidal g_s*k*dk/(2*pi), i.e. isotropic int d^2k/(2*pi)^2."""
    k = np.asarray(k, float)
    if k.ndim != 1 or len(k) < 2 or not np.all(np.isfinite(k)) or k[0] < 0 or np.any(np.diff(k) <= 0):
        raise ValueError("k must be finite, nonnegative and strictly increasing")
    dk = np.empty_like(k)
    dk[0], dk[-1] = (k[1]-k[0])/2, (k[-1]-k[-2])/2
    dk[1:-1] = (k[2:]-k[:-2])/2
    return spin * k * dk / (2*np.pi)


def prefactor(settings):
    """Historical period-density convention; nm/eV/k units -> pm/V.

    Two energy denominator conversions cancel the original hbar^-2.
    Remaining conversion: z nm->m; k nm^-2->m^-2; eV^2->J^2; m/V->pm/V.
    """
    nz = 1/(settings.period_nm*1e-9)
    return nz*E_C**3*(settings.r_e_hh_nm*1e-9)**2/(6*EPS0) * (1e-9*1e18/E_C**2)*1e12


def matrices(inputs, nk):
    result = []
    for key in ("overlap", "ze_nm", "zh_nm"):
        value = np.asarray(inputs[key], complex)
        if value.shape == (2,2):
            value = np.repeat(value[:,:,None], nk, axis=2)
        if value.shape != (2,2,nk) or not np.all(np.isfinite(value)):
            raise ValueError(f"{key} must be finite (2,2) or (2,2,nk)")
        result.append(value)
    return result


def evaluate(wavelength, inputs, settings=Settings()):
    """Return integrated complex total, sixteen pathways, labels and weights.

    m: valence state; n: electron state; ell: intermediate state in that
    pathway's band. O[n,m]=<e_n|h_m>. ZE[n,l]=<e_n|z|e_l>.
    ZH[m,l]=<h_m|z|h_l>. Occupation factors are not explicit in this model.
    """
    k = np.asarray(inputs["k_per_nm"], float)
    weights = radial_weights(k, settings.spin_degeneracy)
    ee, hh = (np.asarray(inputs[key], float) for key in ("electron_eV", "valence_eV"))
    if ee.shape != (2,len(k)) or hh.shape != ee.shape:
        raise ValueError("energies must have shape (2,nk)")
    transition = ee[:,None,:] - hh[None,:,:]
    if not np.all(np.isfinite(transition)) or np.any(transition <= 0):
        raise ValueError("all electron-minus-valence transition energies must be positive finite eV")
    o, ze, zh = matrices(inputs, len(k))
    hw = photon_energy(wavelength)[:,None]
    g = 1j*settings.gamma_sign*settings.gamma_eV
    terms, labels = [], []
    for m in range(2):
        for n in range(2):
            d2 = transition[n,m] - 2*hw + g
            for ell in range(2):
                d1 = transition[ell,m] - hw + g
                numerator = np.conj(o[n,m])*ze[n,ell]*o[ell,m]
                terms.append(prefactor(settings)*((numerator/(d2*d1))@weights))
                labels.append(f"C_m{m+1}_n{n+1}_l{ell+1}")
            for ell in range(2):
                d1 = transition[n,ell] - hw + g
                numerator = -o[n,m]*zh[m,ell]*np.conj(o[n,ell])
                terms.append(prefactor(settings)*((numerator/(d2*d1))@weights))
                labels.append(f"V_m{m+1}_n{n+1}_l{ell+1}")
    terms = np.array(terms)
    return terms.sum(axis=0), terms, labels, weights


def analytic_integral(m1, a, m2, b, cutoff):
    """Exact bare 2*pi*k dk integral used in the historical cutoff test.

    Use separate log differences to avoid a quotient branch discontinuity.
    The repository formula is identical on the supplied positive-Gamma inputs.
    Degenerate slopes/denominators use fixed Gauss quadrature, avoiding division
    by an arbitrary epsilon. No solver extrapolation is hidden here.
    """
    c = m2*a-m1*b
    result = np.empty_like(a, dtype=complex)
    regular = np.abs(c) > 1e-12
    k2 = cutoff**2
    result[regular] = np.pi*((np.log(m2*k2+b[regular])-np.log(b[regular]))
                           -(np.log(m1*k2+a[regular])-np.log(a[regular])))/c[regular]
    if np.any(~regular):
        nodes, weights = np.polynomial.legendre.leggauss(256)
        u = (nodes+1)*k2/2
        result[~regular] = np.pi*k2/2 * ((1/((m1*u+a[~regular,None])*(m2*u+b[~regular,None])))@weights)
    return result


def evaluate_parabolic(wavelength, inputs, cutoff, settings=Settings()):
    """Eq2 on explicitly extrapolated parabolas, with baseline physical units.

    Same A-B sign, +iGamma, prefactor and integration convention as evaluate().
    Historical cutoff_test returned -A+B, bare 2*pi*k dk, no prefactor. Thus
    legacy_unscaled = -total / (prefactor * g_s/(4*pi^2)).
    """
    if not np.isfinite(cutoff) or cutoff <= 0:
        raise ValueError("cutoff must be positive finite nm^-1")
    e, a = np.asarray(inputs["energy_eV"]), np.asarray(inputs["curvature_eV_nm2"])
    if e.shape != (4,) or a.shape != (4,) or not np.all(np.isfinite(e)) or not np.all(np.isfinite(a)):
        raise ValueError("four finite energies and curvatures required: e1,e2,h1,h2")
    o, ze, zh = (v[:,:,0] for v in matrices(inputs, 1))
    hw, g = photon_energy(wavelength), 1j*settings.gamma_sign*settings.gamma_eV
    factor = prefactor(settings)*settings.spin_degeneracy/(4*np.pi**2)
    terms, labels = [], []
    for m in range(2):
        for n in range(2):
            d2 = e[n]-e[m+2]-2*hw+g
            m1 = a[n]-a[m+2]
            for ell in range(2):
                d1 = e[ell]-e[m+2]-hw+g
                integral = analytic_integral(m1,d2,a[ell]-a[m+2],d1,cutoff)
                terms.append(factor*np.conj(o[n,m])*ze[n,ell]*o[ell,m]*integral)
                labels.append(f"C_m{m+1}_n{n+1}_l{ell+1}")
            for ell in range(2):
                d1 = e[n]-e[ell+2]-hw+g
                integral = analytic_integral(m1,d2,a[n]-a[ell+2],d1,cutoff)
                terms.append(-factor*o[n,m]*zh[m,ell]*np.conj(o[n,ell])*integral)
                labels.append(f"V_m{m+1}_n{n+1}_l{ell+1}")
    terms = np.array(terms)
    return terms.sum(axis=0), terms, labels
