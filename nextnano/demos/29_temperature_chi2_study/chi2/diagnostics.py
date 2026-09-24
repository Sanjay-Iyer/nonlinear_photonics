"""Features are measured from calculated arrays, not assigned from paper targets."""
import numpy as np
from scipy.signal import find_peaks
from scipy.optimize import brentq


def features(wl,chi,evaluator=None,target_nm=1550.):
    roots=[]
    for i in np.flatnonzero(chi.real[:-1]*chi.real[1:]<0):
        if evaluator is not None:
            x=brentq(lambda x:evaluator(np.array([x]))[0].real,wl[i],wl[i+1],xtol=1e-10)
            c=evaluator(np.array([x]))[0]
        else:
            x=wl[i]-chi.real[i]*(wl[i+1]-wl[i])/(chi.real[i+1]-chi.real[i])
            c=complex(0,np.interp(x,wl,chi.imag))
        roots.append({'wavelength_nm':float(x),'real_pm_per_V':float(c.real),'imag_pm_per_V':float(c.imag)})
    # A zero exactly on a wavelength sample should also be recorded.
    for i in np.flatnonzero(chi.real==0):
        if 0<i<len(wl)-1 and chi.real[i-1]*chi.real[i+1]<0:
            roots.append({'wavelength_nm':float(wl[i]),'real_pm_per_V':0.,'imag_pm_per_V':float(chi.imag[i])})
    roots.sort(key=lambda r:r['wavelength_nm'])
    def peaks(values):
        ix=find_peaks(abs(values),prominence=.02*max(abs(values)))[0]
        return [{'wavelength_nm':float(wl[i]),'signed_value_pm_per_V':float(values[i])} for i in ix]
    return {'dominant_abs_Re_wavelength_nm':float(wl[np.argmax(abs(chi.real))]),
            'dominant_abs_Im_wavelength_nm':float(wl[np.argmax(abs(chi.imag))]),
            'max_abs_Re_pm_per_V':float(max(abs(chi.real))),'max_abs_Im_pm_per_V':float(max(abs(chi.imag))),
            'Re_peaks':peaks(chi.real),'Im_peaks':peaks(chi.imag),'Re_zero_crossings':roots,
            'target_wavelength_nm':target_nm,
            'Re_at_target_pm_per_V':float(np.interp(target_nm,wl,chi.real)) if wl[0]<=target_nm<=wl[-1] else None,
            'Im_at_target_pm_per_V':float(np.interp(target_nm,wl,chi.imag)) if wl[0]<=target_nm<=wl[-1] else None,
            'feature_policy':'maxima refer to absolute component amplitude; labels do not track physical branches across peak switches'}


def paper_metrics(wl,chi,paper):
    mask=(wl>=paper[0,0])&(wl<=paper[-1,0])
    if mask.sum()<2: return {'status':'NOT_APPLICABLE: no overlapping wavelength range'}
    ref=np.interp(wl[mask],paper[:,0],paper[:,1]);ref=ref/max(ref)
    out={}
    for name,values in [('abs_real',abs(chi.real[mask])),('magnitude',abs(chi[mask]))]:
        normalized=values/max(values)
        out[name]={'nRMSE':float(np.sqrt(np.mean((normalized-ref)**2))),
                   'correlation':float(np.corrcoef(normalized,ref)[0,1])}
    return out
