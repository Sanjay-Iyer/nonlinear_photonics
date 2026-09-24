"""Wavefunction-derived quantities for the unchanged historical baseline."""
import numpy as np


def from_envelopes(parsed):
    """Normalized real single-band envelopes (nz,2) -> O, Ze, Zh (2,2).

    z is nm; wavefunctions are nm^-1/2; integrals use the spatial trapezoid rule.
    This is the historical mixed-model baseline, not a full kp8 optical operator.
    """
    z,e,h=parsed['z_nm'],parsed['electron_env'],parsed['hole_env']
    if np.any(np.diff(parsed['electron_eV'])<=0) or np.any(np.diff(parsed['hole_eV'])>=0):
        raise ValueError('Electron levels must ascend; valence electron energies descend')
    def m(a,b,position=False):
        return np.array([[np.trapezoid(a[:,i]*b[:,j]*(z if position else 1),z) for j in range(2)] for i in range(2)])
    return {'overlap':m(e,h),'ze_nm':m(e,e,True),'zh_nm':m(h,h,True),
            'gram_error':max(float(np.max(abs(m(p,p)-np.eye(2)))) for p in (e,h))}
