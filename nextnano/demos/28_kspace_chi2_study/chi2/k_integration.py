"""Explicit native-grid selection and isotropic 2D momentum integration."""
import numpy as np


def radial_weights(k_per_nm, spin=2):
    """Weights in nm^-2: g_s*k*dk/(2*pi) = isotropic int g_s*d2k/(2*pi)^2.

    Endpoint dk weights are half the adjacent interval. Recompute weights AFTER
    selecting the cutoff: slicing full-grid weights would overcount its endpoint.
    """
    k = np.asarray(k_per_nm,float)
    if k.ndim!=1 or len(k)<2 or not np.all(np.isfinite(k)) or k[0]<0 or np.any(np.diff(k)<=0):
        raise ValueError("k must be finite, nonnegative, strictly increasing, with >=2 points")
    if spin not in (1,2):
        raise ValueError("spin degeneracy must be 1 or 2")
    dk=np.empty_like(k)
    dk[0],dk[-1]=(k[1]-k[0])/2,(k[-1]-k[-2])/2
    dk[1:-1]=(k[2:]-k[:-2])/2
    return spin*k*dk/(2*np.pi)


def select_range(inputs, kmax_per_nm, kmin_per_nm=0.):
    """Only retain existing samples within [kmin,kmax]. Never extrapolate.

    Requested limits between samples stop at the last available interior sample.
    Every result records requested and actual endpoints. No tolerance can admit
    a sample above the requested upper limit.
    """
    k=np.asarray(inputs['k_per_nm'],float)
    radial_weights(k)
    if not np.isfinite(kmax_per_nm) or not np.isfinite(kmin_per_nm) or not 0<=kmin_per_nm<kmax_per_nm:
        raise ValueError("Require finite 0 <= kmin < kmax")
    if kmax_per_nm>k[-1] or kmin_per_nm<k[0]:
        raise ValueError(f"Requested [{kmin_per_nm},{kmax_per_nm}] outside solved [{k[0]},{k[-1]}] nm^-1")
    keep=(k>=kmin_per_nm)&(k<=kmax_per_nm)
    if keep.sum()<2:
        raise ValueError("Cutoff retains fewer than two solved k points")
    result={**inputs,'k_per_nm':k[keep]}
    for key in ('electron_eV','valence_eV'):
        result[key]=np.asarray(inputs[key])[:,keep]
    for key in ('overlap','ze_nm','zh_nm'):
        value=np.asarray(inputs[key])
        result[key]=value[:,:,keep] if value.ndim==3 else value.copy()
    result['selection']={'requested_min_per_nm':float(kmin_per_nm),'requested_max_per_nm':float(kmax_per_nm),
                         'actual_min_per_nm':float(k[keep][0]),'actual_max_per_nm':float(k[keep][-1]),
                         'source_indices':np.flatnonzero(keep).tolist(),'points':int(keep.sum()),
                         'policy':'native samples only; no interpolation or extrapolation'}
    return result
