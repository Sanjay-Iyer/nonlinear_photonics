"""28L/M returned-data preparation. No historical anchors or inferred optical operator.

Individual-state assignment is provisional near degeneracy. The component tensor
is retained so a reviewed Bloch operator can be applied without another solve.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.optimize import linear_sum_assignment
from . import parse_nextnano as io
from .artifacts import csv, write_json
from .extended8band import ROOT, load_config, inventory
from .compact8band import source_frames


def matrix_data(z, psi):
    """psi=(states,8,z); return normalized spinors, component overlaps and z.

    T[a,b,mu,nu]=integral conj(F[a,mu])*F[b,nu] dz. Identity
    contraction is the full-state Gram matrix, NOT interband optical overlap.
    """
    w=io.trapezoid_weights(z)
    if psi.ndim!=3 or psi.shape[1:]!=(8,len(z)) or not np.isfinite(psi).all():
        raise ValueError('Require finite complex (states,8,z) envelopes')
    norms=np.einsum('acz,acz,z->a',psi.conj(),psi,w).real
    if np.any(abs(norms-1)>.02):raise ValueError('Spinor normalization differs from unity by >2%; inspect units/grid')
    psi=psi/np.sqrt(norms)[:,None,None]
    tensor=np.einsum('amz,bnz,z->abmn',psi.conj(),psi,w,optimize=True)
    zm=np.einsum('acz,bcz,z->ab',psi.conj(),psi,w*z,optimize=True)
    return psi,tensor,zm,norms


def assign(previous,current,w,min_overlap=.5,margin=.05):
    score=abs(np.einsum('acz,bcz,z->ab',previous.conj(),current,w,optimize=True))**2
    row,col=linear_sum_assignment(-score)
    order=col[np.argsort(row)]
    best=score[np.arange(len(order)),order]
    competitor=score.copy();competitor[np.arange(len(order)),order]=-np.inf
    gap=best-competitor.max(axis=1)
    return order,best,gap,(best<min_overlap)|(gap<margin)


def ingest(source,out,c):
    if c.get('pilot'):raise ValueError('Pilot is for output coverage only, not production state/chi2 analysis')
    report=inventory(source,c)
    if report['status']!='PASS':raise ValueError('Returned-data validation failed: '+str(report['problems'][:8]))
    out=Path(out)
    if out.exists():raise ValueError('Refusing existing analysis output')
    n=c['num_electrons']+c['num_holes']
    out.mkdir(parents=True);(out/'operator_blocks').mkdir()
    rows=[];previous=None;zref=None;ambiguous_total=0
    for i,(ki,energy,z,parts,comp) in enumerate(source_frames(source)):
        if zref is None:zref=z
        if not np.array_equal(zref,z):raise ValueError('Spatial grid mismatch')
        psi,tensor,zm,norm=matrix_data(zref,parts);w=io.trapezoid_weights(zref)
        gram=np.einsum('abmm->ab',tensor)
        if np.max(abs(gram-np.eye(n)))>.02:raise ValueError(f'Nonorthogonal spinors at k index {i}')
        char=np.einsum('acz,acz,z->ac',psi.conj(),psi,w).real
        if not np.allclose(char,comp,atol=.02,rtol=0):
            raise ValueError(f'Envelope/composition mismatch at k index {i}')
        if previous is None:order=np.arange(n);score=np.ones(n);gap=np.full(n,np.nan);flags=np.zeros(n,bool)
        else:order,score,gap,flags=assign(previous,psi,w,c['tracking_min_overlap'],c['tracking_margin'])
        # A small energy separation also marks a basis-dependent individual label.
        separation=abs(energy[:,None]-energy[None,:]);np.fill_diagonal(separation,np.inf)
        flags|=(separation.min(axis=1)[order]<1e-6)
        ambiguous_total+=int(flags.sum())
        for branch,s in enumerate(order):
            blocks=char[s].reshape(4,2).sum(axis=1)
            rows.append([i,ki,branch+1,s+1,energy[s],*blocks,score[branch],gap[branch],int(flags[branch])])
        np.savez_compressed(out/'operator_blocks'/f'k{i:05d}.npz',k_per_nm=ki,energy_eV=energy,
            solver_state=np.arange(1,n+1),branch_to_solver=order+1,component_overlap=tensor,z_nm=zm,
            components=np.array(io.KP8_COMPONENTS),normalization_before=norm,ambiguous=flags)
        previous=psi[order]
    csv(out/'tracked_candidates.csv',rows,'k_index,k_per_nm,candidate_branch,solver_state,energy_eV,CB,HH,LH,SO,adjacent_overlap,assignment_margin,ambiguous')
    write_json(out/'metadata.json',{'study':'28L_28M_preparation','source':str(Path(source).resolve()),'Nk':c['k_points'],
        'ambiguous_assignments':ambiguous_total,'assignment':'maximum adjacent overlap, all candidate states; NOT certified e1/e2/hh1/hh2',
        'review_required':'Inspect flagged crossings/degenerate subspaces before selecting branches; supply reviewed optical operator and spin convention',
        'chi2_evaluated':False,'historical_inputs_used':False})


def eq2_inputs(blocks,electron_branches,valence_branches,optical_operator,review):
    """Explicit reviewed adapter; no default Bloch operator or spin reduction.

    The dimensionless 8x8 operator is factored relative to r_e_hh in Eq2.
    This adapter is a selected two-by-two model, not a general 24-state response.
    """
    if not review.get('approved') or not all(review.get(x) for x in ('operator_source','basis_convention','branch_selection','spin_convention','model_scope')):
        raise ValueError('Reviewed optical operator, branch and spin conventions required')
    b=np.asarray(optical_operator,complex)
    if b.shape!=(8,8) or not np.isfinite(b).all() or np.allclose(b,np.eye(8)):
        raise ValueError('Require reviewed non-identity finite dimensionless 8x8 interband operator')
    if len(electron_branches)!=2 or len(valence_branches)!=2 or len(set(electron_branches+valence_branches))!=4:
        raise ValueError('Choose four distinct candidate branches (zero-based)')
    result={key:[] for key in ('k_per_nm','electron_eV','valence_eV','overlap','ze_nm','zh_nm')}
    for path in blocks:
        with np.load(path,allow_pickle=False) as d:
            branches=electron_branches+valence_branches
            if np.any(d['ambiguous'][branches]) and not review.get('degeneracy_resolution'):
                raise ValueError('Selected branches have unresolved degeneracy/assignment flags')
            ix=d['branch_to_solver'].astype(int)-1;e=ix[electron_branches];v=ix[valence_branches]
            optical=np.einsum('abmn,mn->ab',d['component_overlap'],b)
            for key,value in [('k_per_nm',d['k_per_nm']),('electron_eV',d['energy_eV'][e]),('valence_eV',d['energy_eV'][v]),
                              ('overlap',optical[np.ix_(e,v)]),('ze_nm',d['z_nm'][np.ix_(e,e)]),('zh_nm',d['z_nm'][np.ix_(v,v)])]:
                result[key].append(value)
    return {key:np.stack(value,axis=-1) for key,value in result.items()}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,default=ROOT/'outputs/28L_state_tracking/returned_data')
    a=p.parse_args();ingest(a.input,a.output,load_config(a.input/'run_configuration.json'))
