"""Local discrete Equation 2 for both Demo 29 calculation paths.

Preserves all sixteen pathways, conjugations, signs, units and complex broadening.
Momentum selection/weights live in k_integration.py. All studies call this module.
"""
from dataclasses import dataclass
import numpy as np
from .k_integration import radial_weights

HC_EV_NM=1239.841984
E_C=1.602176634e-19
EPS0=8.8541878128e-12


@dataclass(frozen=True)
class Settings:
    gamma_meV: float=5.
    spin_degeneracy: int=2
    period_nm: float=30.
    r_e_hh_nm: float=.751
    gamma_sign: int=1

    def __post_init__(self):
        for value in (self.gamma_meV,self.period_nm,self.r_e_hh_nm):
            if not np.isfinite(value) or value<=0: raise ValueError('Require positive finite broadening, period and interband length')
        if self.gamma_sign not in (-1,1) or self.spin_degeneracy not in (1,2):
            raise ValueError('gamma_sign must be +/-1 and spin degeneracy 1 or 2')

    @property
    def gamma_eV(self): return self.gamma_meV*1e-3


def photon_energy(wavelength_nm):
    w=np.asarray(wavelength_nm,float)
    if w.ndim!=1 or not len(w) or not np.all(np.isfinite(w)) or np.any(w<=0):
        raise ValueError('Fundamental wavelength must be a positive finite 1D array')
    return HC_EV_NM/w


def prefactor(settings):
    """Historical pm/V convention: Nz=1/period, r=0.751 nm, 1/6.

    Nz e^3 r^2/(6 eps0). Two hbar factors cancel in the energy-domain equation.
    Conversion: z[nm]*1e-9, k[nm^-2]*1e18, denominator[eV^2]*e^2,
    final m/V*1e12 -> pm/V. This does not establish the paper's absolute scale.
    """
    nz=1/(settings.period_nm*1e-9)
    return nz*E_C**3*(settings.r_e_hh_nm*1e-9)**2/(6*EPS0)*(1e-9*1e18/E_C**2)*1e12


def expand_matrices(inputs,nk):
    arrays=[]
    for key in ('overlap','ze_nm','zh_nm'):
        a=np.asarray(inputs[key],complex)
        if a.shape==(2,2): a=np.repeat(a[:,:,None],nk,axis=2)
        if a.shape!=(2,2,nk) or not np.all(np.isfinite(a)):
            raise ValueError(f'{key} must be finite (2,2) or (2,2,nk)')
        arrays.append(a)
    return arrays


@dataclass
class Spectrum:
    wavelength_nm: np.ndarray
    chi2_complex: np.ndarray
    pathways_complex: np.ndarray
    pathway_labels: list
    k_weights_nm_minus2: np.ndarray
    summed_integrand: np.ndarray


def calculate_chi2(wavelength_nm, inputs, settings=Settings()):
    """Evaluate Eq2 on supplied electronic-structure arrays.

    wavelength_nm: (n_lambda,), FUNDAMENTAL light wavelength in nm.
    inputs['k_per_nm']: (nk,), nonnegative increasing radial momentum, nm^-1.
    electron_eV / valence_eV: (2,nk), both on one electron-energy reference, eV.
    overlap: O[n,m]=<e_n|h_m>, dimensionless; (2,2) or (2,2,nk).
    ze_nm: <e_n|z|e_ell>; zh_nm: <h_m|z|h_ell>, nm; same allowed shapes.
    Constant matrices are explicitly broadcast: M(k)=M(0), not new finite-k data.
    m indexes valence, n electron; ell electron in C terms, valence in V terms.

    Returns Spectrum: complex integrated chi2 (n_lambda,) in stated pm/V,
    pathways (16,n_lambda), labels, integration weights (nk,) in nm^-2,
    and unweighted summed_integrand (n_lambda,nk) in nm/eV^2.
    No occupation factors or carrier-population dynamics are added.
    """
    return calculate_chi2_energy(photon_energy(wavelength_nm),inputs,settings,wavelength_nm)


def calculate_chi2_energy(photon_energy_eV,inputs,settings=Settings(),wavelength_nm=None):
    """Same Eq2 algebra on signed fundamental energies for analytic audits.

    Negative energies extend the written resonant expression mathematically;
    this does NOT add omitted antiresonant terms or assert physical validity.
    Zero energy has wavelength infinity. Use audit-specific output, not save_spectrum.
    """
    energy=np.asarray(photon_energy_eV,float)
    if energy.ndim!=1 or not len(energy) or not np.all(np.isfinite(energy)):
        raise ValueError('Photon energies must be a nonempty finite 1D array')
    if wavelength_nm is None:
        wavelength_nm=np.divide(HC_EV_NM,energy,out=np.full_like(energy,np.inf),where=energy!=0)
    k=np.asarray(inputs['k_per_nm'],float)
    weights=radial_weights(k,settings.spin_degeneracy)
    hw=energy[:,None]
    g=1j*settings.gamma_sign*settings.gamma_eV
    terms,labels=[],[]
    summed=np.zeros((len(hw),len(k)),complex)
    for pathway in pathway_definitions(inputs):
        d2=pathway['two_transition_eV']-2*hw+g
        d1=pathway['one_transition_eV']-hw+g
        value=pathway['numerator']/(d2*d1)
        summed+=value
        terms.append(prefactor(settings)*(value@weights))
        labels.append(pathway['label'])
    terms=np.asarray(terms)
    return Spectrum(np.asarray(wavelength_nm),terms.sum(axis=0),terms,labels,weights,summed)


def pathway_definitions(inputs):
    """Yield all 16 gauge-invariant products and transition arrays (nk,).

    Indices m,n,ell are zero-based. C uses intermediate electron ell;
    V uses intermediate valence ell and includes the Equation 2 minus sign.
    """
    nk=len(inputs['k_per_nm'])
    ee,hh=(np.asarray(inputs[key],float) for key in ('electron_eV','valence_eV'))
    if ee.shape!=(2,nk) or hh.shape!=ee.shape: raise ValueError('Energies must be (2,nk)')
    transition=ee[:,None,:]-hh[None,:,:]
    if not np.all(np.isfinite(transition)) or np.any(transition<=0): raise ValueError('Ee-Eh must be positive finite eV')
    o,ze,zh=expand_matrices(inputs,nk)
    for m in range(2):
        for n in range(2):
            for kind in ('C','V'):
                for ell in range(2):
                    numerator=(np.conj(o[n,m])*ze[n,ell]*o[ell,m] if kind=='C'
                               else -o[n,m]*zh[m,ell]*np.conj(o[n,ell]))
                    yield {'label':f'{kind}_m{m+1}_n{n+1}_l{ell+1}', 'm':m,'n':n,'ell':ell,'kind':kind,
                           'numerator':numerator,'two_transition_eV':transition[n,m],
                           'one_transition_eV':transition[ell,m] if kind=='C' else transition[n,ell]}
