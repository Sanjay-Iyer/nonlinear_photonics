"""Raw nextnano -> parsed arrays -> historical Demo26 baseline chi2 inputs."""
import itertools
from pathlib import Path
import numpy as np
from . import parse_nextnano as io
from .matrix_elements import from_envelopes


def build_inputs(root):
    root=Path(root)
    sb=io.read_single_band(root/'singleband_case04_graded')
    matrix=from_envelopes(sb)
    anchors=np.r_[sb['electron_eV'],sb['hole_eV']]
    kp=root/'kp8'
    energy=io.read_energy_spectrum(io.find_one(kp,'kp8/energy_spectrum_k00000.dat'))
    comp=io.read_composition(io.find_one(kp,'spinor_composition_k00000_CbHhLhSo.dat'))
    k,disp,meta=io.read_dispersion(kp)
    if len(energy)%2 or not np.allclose(energy,disp[0],atol=1e-9,rtol=0):
        raise ValueError('k=0 energies disagree with dispersion or are not paired')
    spin=np.column_stack([comp[c] for c in io.KP8_COMPONENTS])
    spin=spin/np.abs(spin).sum(axis=1)[:,None]
    pairs=np.arange(len(energy)).reshape(-1,2)
    pair_energy=energy[pairs].mean(axis=1)
    cb=spin[:,:2].sum(axis=1)[pairs].mean(axis=1)
    expected=anchors[:2,None]-anchors[None,2:]
    candidates=[]
    for e in itertools.combinations(np.flatnonzero(cb>=.8),2):
        e=sorted(e,key=lambda i:pair_energy[i])
        for h in itertools.combinations(np.flatnonzero(cb<=.2),2):
            h=sorted(h,key=lambda i:pair_energy[i],reverse=True)
            score=np.sqrt(np.mean((pair_energy[e,None]-pair_energy[None,h]-expected)**2))
            candidates.append((float(score),e+h))
    if not candidates: raise ValueError('Cannot classify two electron and two valence pairs')
    candidates.sort(key=lambda x:x[0])
    if len(candidates)>1 and candidates[1][0]-candidates[0][0]<1e-10:
        raise ValueError('Ambiguous historical pair assignment')
    chosen=pairs[candidates[0][1]]
    raw=np.array([disp[:,pair].mean(axis=1) for pair in chosen])
    aligned=anchors[:,None]+raw-raw[:,0,None]  # historical operation order
    inputs={'k_per_nm':k,'electron_eV':aligned[:2],'valence_eV':aligned[2:],
            **matrix,'anchors_eV':anchors,'kp8_pair_ids':(chosen+1).tolist(),
            'model':'historical Demo26 baseline: kp8 dispersion shifts + single-band matrices',
            'matrix_treatment':'M(k)=M(0)', 'state_assignment_score_eV':candidates[0][0],
            'state_assignment_margin_eV':candidates[1][0]-candidates[0][0] if len(candidates)>1 else None,
            'limitations':['Valence pair (3,4) is light-hole dominated; retained for historical reproduction',
                          'No finite-k spinor tracking; fixed solver columns and pair averaging',
                          'Single-band overlaps and matrix elements frozen at k=0',
                          'No explicit carrier occupations, excitons or additional pathways'],
            'dispersion_metadata':meta}
    parsed={'k_per_nm':k,'all_kp8_energies_eV':disp,'selected_pair_mean_energies_eV':raw,
            'k0_all_energies_eV':energy,'composition':spin,**sb}
    return inputs,parsed
