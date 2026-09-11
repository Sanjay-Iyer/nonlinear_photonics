"""28I: evidence-limited state audit; never relabel historical Eq2 branches."""
import argparse
import datetime as dt
import json
from pathlib import Path
import numpy as np
from .input_builder import build_inputs
from . import parse_nextnano as io, plotting
from .artifacts import csv, write_json, manifest

ROOT = Path(__file__).resolve().parents[1]


def pair_subspace_fidelity(left, right, weights):
    """Mean squared principal overlap of two orthonormalized spinor subspaces.

    Invariant to arbitrary phases/unitary rotations within either doublet.
    Arrays: (pair_size, eight_components, spatial_points).
    """
    def orth(x):
        q, _ = np.linalg.qr((x * np.sqrt(weights)[None,None,:]).reshape(len(x),-1).T)
        return q
    a,b=orth(left),orth(right)
    return float(np.sum(abs(a.conj().T@b)**2)/min(a.shape[1],b.shape[1]))


def read_envelopes_at(directory, states, index):
    result=[]; z=None
    for state in states:
        parts=[]
        for component in io.KP8_COMPONENTS:
            _, data=io.read_table(directory/f'envelope_k{index:05d}_{state:04d}_{component}.dat')
            if z is None: z=data[:,0]
            if not np.allclose(z,data[:,0]): raise ValueError('Inconsistent spinor spatial grid')
            parts.append(data[:,1]+1j*data[:,2])
        result.append(parts)
    return z,np.asarray(result)


def audit(raw_root=ROOT/'nextnano/raw_results', out=ROOT/'outputs/28I_state_character'):
    raw_root=Path(raw_root);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    inputs,parsed=build_inputs(raw_root)
    k=inputs['k_per_nm'];energy=parsed['all_kp8_energies_eV']
    directory=io.find_one(raw_root/'kp8','spinor_composition_k00000_CbHhLhSo.dat').parent
    pairs=inputs['kp8_pair_ids']; labels=['e1','e2','historical h1','historical h2']
    rows=[]; pair_character=[]
    for index in range(len(k)):
        path=directory/f'spinor_composition_k{index:05d}_CbHhLhSo.dat'
        if not path.exists(): continue
        comp=io.read_composition(path)
        arr=np.column_stack([comp[c] for c in io.KP8_COMPONENTS]);arr=arr/arr.sum(axis=1)[:,None]
        for p,pair in enumerate(pairs):
            blocks=arr[np.array(pair)-1].mean(axis=0).reshape(4,2).sum(axis=1)
            rows.append([index,k[index],p,*blocks])
            if index==0: pair_character.append(dict(label=labels[p],solver_states=pair,CB=blocks[0],HH=blocks[1],LH=blocks[2],SO=blocks[3]))
    csv(out/'state_character.csv',rows,'k_index,k_per_nm,pair_index,CB,HH,LH,SO')
    csv(out/'raw_solver_energies.csv',np.column_stack([k,energy]),'k_per_nm,'+','.join(f'state_{i+1}_eV' for i in range(energy.shape[1])))
    energies=parsed['selected_pair_mean_energies_eV']
    csv(out/'selected_pair_energies.csv',np.column_stack([k,energies.T]),'k_per_nm,e1_eV,e2_eV,h1_eV,h2_eV')
    local=[];continuity=[];previous={}
    for index in range(len(k)):
        for p,pair in enumerate(pairs):
            if not all((directory/f'envelope_k{index:05d}_{s:04d}_{c}.dat').exists() for s in pair for c in io.KP8_COMPONENTS): continue
            z,psi=read_envelopes_at(directory,pair,index);w=io.trapezoid_weights(z)
            density=abs(psi)**2; density=density.sum(axis=1).mean(axis=0)
            density=density/np.dot(w,density)
            well=((z>=9.1)&(z<=16.2))|((z>=18)&(z<=20.9))
            edge=(z<z[0]+1)|(z>z[-1]-1)
            local.append([index,k[index],p,np.dot(w,density*z),np.dot(w,density*well),np.dot(w,density*edge)])
            if p in previous and previous[p][0]==index-1:
                continuity.append([index,k[index],p,pair_subspace_fidelity(previous[p][1],psi,w)])
            previous[p]=(index,psi)
    csv(out/'localization.csv',local,'k_index,k_per_nm,pair_index,mean_growth_coordinate_nm,well_probability,edge_1nm_probability')
    csv(out/'adjacent_pair_subspace_fidelity.csv',np.asarray(continuity).reshape(-1,4),'k_index,k_per_nm,pair_index,subspace_fidelity')
    unique=sorted(set(int(row[0]) for row in rows))
    meta=dict(study='28I',timestamp_utc=dt.datetime.now(dt.timezone.utc).isoformat(),source_dataset=str(raw_root.resolve()),
              k_points=len(k),k_max_per_nm=k[-1],k_units='nm^-1',k_max_pi_over_a=k[-1]*.565325/np.pi,
              BZ_definition='fraction of pi/a along Gamma-to-y; not asserted to equal paper BZ convention',
              state_pairs=pairs,k0_pair_character=pair_character,composition_k_indices=unique,
              composition_coverage=len(unique)/len(k),adjacent_pair_overlaps_available=len(continuity),
              max_adjacent_fixed_pair_energy_change_eV=np.max(abs(np.diff(energies,axis=1)),axis=1),
              state_assignment='fixed original solver columns; not an overlap-tracked relabeling',
              high_k_model_validity='UNRESOLVED: energy continuity alone cannot certify state identity or bound character',
              physical_status='historical h2 already LH dominated at k=0; not a two-HH model',
              localization_interpretation='finite-box well/edge probability is descriptive, not proof of a bound state',
              licensed_solver_executed=False,normalization='probability normalized per pair; energies unshifted raw eV',
              equation_implementation='chi2/equation2.py (not evaluated by state audit)',
              limitations=['No finite-k character inferred from energies when spinors are missing',
                           'Subspace overlap diagnoses fixed doublets only, does not perform competing-branch assignment',
                           'No model-valid high-k interval is certified by this audit'])
    write_json(out/'metadata.json',meta);write_json(out/'raw_manifest.json',manifest(raw_root))
    for selected,title in [([0,1],'electron'),([2,3],'valence')]:
        fig,ax=plotting.axes(xlabel=r'$k_{||}$ (nm$^{-1}$)',ylabel='raw pair-mean energy (eV)',zero_line=False)
        for p in selected: ax.plot(k,energies[p],label=labels[p],lw=1.6)
        plotting.save(fig,ax,out/'plots',f'28I_{title}_energies')
    fig,ax=plotting.axes(xlabel='historical pair label at k=0',ylabel='8-band probability fraction',zero_line=False)
    bottom=np.zeros(4)
    for block,color in zip(['CB','HH','LH','SO'],['#377eb8','#4daf4a','#e69f00','#999999']):
        value=np.array([r[block] for r in pair_character]);ax.bar(np.arange(4),value,bottom=bottom,label=block,color=color);bottom+=value
    ax.set_xticks(np.arange(4),labels);ax.set_ylim(0,1.04)
    ax.legend(frameon=False,ncol=4,loc='lower center',bbox_to_anchor=(.5,1.01))
    plotting.save(fig,ax,out/'plots','28I_k0_character',legend=False)
    print(json.dumps(meta,default=lambda x:x.tolist() if hasattr(x,'tolist') else x,indent=2))
    return meta


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input',type=Path,default=ROOT/'nextnano/raw_results');parser.add_argument('--output',type=Path,default=ROOT/'outputs/28I_state_character')
    args=parser.parse_args();audit(args.input,args.output)
