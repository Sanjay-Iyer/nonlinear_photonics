"""Lossless numerical transfer, not a physics calculation or a text-file archive.

Float64/complex128 values are preserved exactly after the standard text parser.
Original solver text is never modified. One compressed block per k bounds memory.
"""
import hashlib
import json
from pathlib import Path
import shutil
from zipfile import BadZipFile
import numpy as np
from . import parse_nextnano as io
from .artifacts import write_json,manifest

FORMAT='demo28-8band-numeric-v1'


def source_frames(source):
    """Yield (k, energies, z, complex spinors, composition) from either format."""
    source=Path(source)
    if (source/'compact.json').is_file():
        meta=json.loads((source/'compact.json').read_text())
        for i in range(meta['Nk']):
            with np.load(source/'frames'/f'k{i:05d}.npz',allow_pickle=False) as d:
                yield float(d['k_per_nm']),d['energy_eV'],d['z_nm'],d['psi'],d['composition']
        return
    k,e,_=io.read_dispersion(source/'raw');lookup={}
    for p in (source/'raw').rglob('*'):
        if p.is_file():lookup.setdefault(p.name,[]).append(p)
    def one(name):
        paths=lookup.get(name,[])
        if len(paths)!=1:raise ValueError('Missing/ambiguous raw file '+name)
        return paths[0]
    zref=None
    for i,ki in enumerate(k):
        parts=[]
        for s in range(1,e.shape[1]+1):
            block=[]
            for tag in io.KP8_COMPONENTS:
                _,d=io.read_table(one(f'envelope_k{i:05d}_{s:04d}_{tag}.dat'))
                if d.shape[1]!=3:raise ValueError('Expected z, real, imaginary envelope columns')
                if zref is None:zref=d[:,0].copy();io.trapezoid_weights(zref)
                if not np.array_equal(zref,d[:,0]):raise ValueError('Spatial grids differ; refusing lossy common-grid packing')
                block.append(d[:,1]+1j*d[:,2])
            parts.append(block)
        cp=one(f'spinor_composition_k{i:05d}_CbHhLhSo.dat')
        ep=one(f'energy_spectrum_k{i:05d}.dat')
        for path in (cp,ep):
            if not np.array_equal(io.read_table(path)[1][:,0],np.arange(1,e.shape[1]+1)):
                raise ValueError('Unexpected solver state IDs in '+path.name)
        comp=io.read_composition(cp)
        energy=io.read_energy_spectrum(ep)
        if not np.allclose(energy,e[i],atol=1e-7,rtol=0):raise ValueError('Per-k energy/dispersion mismatch')
        # Preserve BOTH printed energy representations (dispersion is separately copied).
        yield ki,energy,zref,np.asarray(parts,dtype=np.complex128),np.column_stack([comp[t] for t in io.KP8_COMPONENTS])


def validate_compact(root,c,check_hashes=True):
    root=Path(root);problems=[];nk=0;n=c['num_electrons']+c['num_holes']
    try:
        meta=json.loads((root/'compact.json').read_text())
        if meta['format']!=FORMAT:raise ValueError('Unsupported compact format')
        if meta['limit_bytes']!=c.get('transfer_limit_bytes',1000000000):raise ValueError('Transfer limit differs from source configuration')
        nk=meta['Nk']
        if nk!=c['k_points'] or meta['state_count']!=n:raise ValueError('Compact grid/state count mismatch')
        if json.loads((root/'run_configuration.json').read_text())!=c:raise ValueError('Configuration mismatch')
        record=json.loads((root/'run_metadata.json').read_text())
        if not record.get('professional_execution_performed') or record.get('return_code')!=0:raise ValueError('No successful recorded solve')
        for required in ('solver.log','decks/extended_8band.in','source_checksums.json','requested_k_grid.csv','dispersion.npz'):
            if not (root/required).is_file():raise ValueError('Missing '+required)
        expected=np.linspace(0,c['kmax_pi_over_a']*np.pi/c['lattice_constant_nm'],nk)
        with np.load(root/'dispersion.npz',allow_pickle=False) as d:
            dk,de,direction=d['k_per_nm'],d['energy_eV'],d['direction']
        if dk.shape!=(nk,) or de.shape!=(nk,n) or not np.isfinite(de).all() or not np.allclose(dk,expected,atol=5e-10,rtol=0):raise ValueError('Invalid saved dispersion')
        if not np.allclose(direction,[0,1,0],atol=1e-7,rtol=0):raise ValueError('Wrong radial direction')
        if set(p.name for p in (root/'frames').iterdir())!={f'k{i:05d}.npz' for i in range(nk)}:raise ValueError('Missing/extra k blocks')
        zref=None
        for i in range(nk):
            with np.load(root/'frames'/f'k{i:05d}.npz',allow_pickle=False) as d:
                if int(d['k_index'])!=i or not np.array_equal(d['solver_state'],np.arange(1,n+1)):raise ValueError('Wrong k/state IDs')
                if tuple(d['components'])!=io.KP8_COMPONENTS:raise ValueError('Wrong component basis/order')
                if abs(float(d['k_per_nm'])-expected[i])>5e-10:raise ValueError('k-grid mismatch')
                z,psi,e,comp=d['z_nm'],d['psi'],d['energy_eV'],d['composition']
                if psi.dtype!=np.complex128 or any(a.dtype!=np.float64 for a in (z,e,comp)):raise ValueError('Precision/type mismatch')
                if z.ndim!=1 or psi.shape!=(n,8,len(z)) or e.shape!=(n,) or comp.shape!=(n,8):raise ValueError('Block shape mismatch')
                if not all(np.isfinite(a).all() for a in (z,psi,e,comp)):raise ValueError('Nonfinite block')
                io.trapezoid_weights(z)
                if zref is None:zref=z.copy()
                if not np.array_equal(z,zref):raise ValueError('Spatial grid mismatch')
                if not np.allclose(e,de[i],atol=1e-7,rtol=0):raise ValueError('Energy/dispersion mismatch')
                if np.any(comp< -2e-5) or not np.allclose(comp.sum(axis=1),1,atol=2e-5,rtol=0):raise ValueError('Composition invalid')
        # Check the copied exact deck against the source manifest, not today's renderer.
        original={r['file']:r['sha256'] for r in json.loads((root/'source_checksums.json').read_text())}
        for name in ('decks/extended_8band.in','run_configuration.json','run_metadata.json','solver.log','requested_k_grid.csv'):
            if original.get(name)!=hashlib.sha256((root/name).read_bytes()).hexdigest():raise ValueError('Source provenance mismatch '+name)
        if check_hashes:
            rows=json.loads((root/'checksums.json').read_text())
            actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p.name not in ('checksums.json','return_validation.json')}
            if {r['file'] for r in rows}!=actual or len(rows)!=len(actual):raise ValueError('Incomplete/duplicate compact checksum manifest')
            for r in rows:
                p=(root/r['file']).resolve()
                if not p.is_relative_to(root.resolve()) or not p.is_file():raise ValueError('Unsafe/missing manifest path')
                if hashlib.sha256(p.read_bytes()).hexdigest()!=r['sha256']:raise ValueError('Checksum mismatch '+r['file'])
        size=sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
        if size>meta['limit_bytes']:problems.append(f'Transfer is {size} bytes, exceeds {meta["limit_bytes"]}-byte budget; no data discarded')
    except (ValueError,OSError,KeyError,TypeError,IndexError,EOFError,BadZipFile) as exc:problems.append(str(exc))
    return {'study':'28K_compact_return_validation','status':'FAIL' if problems else 'PASS','problems':problems,
            'Nk':nk,'state_count':n,'source':str(root.resolve()),'new_physics_analysis_performed':False}


def pack(source,out,validated=False):
    from .extended8band import load_config,inventory
    source=Path(source).resolve();out=Path(out).resolve()
    if out.exists() or out.is_relative_to(source):raise ValueError('Choose a new transfer directory outside the original run')
    if (source/'compact.json').exists():raise ValueError('Source is already compact')
    c=load_config(source/'run_configuration.json')
    if not validated:
        result=inventory(source,c)
        if result['status']!='PASS':raise ValueError('Raw validation failed: '+str(result['problems'][:8]))
    out.mkdir(parents=True);(out/'frames').mkdir();(out/'decks').mkdir()
    for name in ('run_configuration.json','run_metadata.json','solver.log','requested_k_grid.csv','decks/extended_8band.in'):
        shutil.copy2(source/name,out/name)
    shutil.copy2(source/'checksums.json',out/'source_checksums.json')
    k,e,km=io.read_dispersion(source/'raw')
    np.savez_compressed(out/'dispersion.npz',k_per_nm=k,energy_eV=e,direction=km['direction'])
    # Preserve small native run/material/optical records as cross-checks, not duplicate spatial wavefunctions.
    copied=[]
    for p in (source/'raw').rglob('*'):
        if not p.is_file():continue
        name=p.name.lower()
        if any(t in name for t in ('simulation_info','matrix_elements','oscillator','bandedge','alloy','material','bandgap')):
            target=out/'native_metadata'/p.relative_to(source/'raw');target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(p,target);copied.append(target.relative_to(out).as_posix())
    count=0;payload=0
    for i,(ki,energy,z,psi,comp) in enumerate(source_frames(source)):
        arrays=dict(k_index=np.int64(i),k_per_nm=np.float64(ki),energy_eV=energy,z_nm=z,psi=psi,composition=comp,
                    solver_state=np.arange(1,len(energy)+1),components=np.array(io.KP8_COMPONENTS))
        path=out/'frames'/f'k{i:05d}.npz';np.savez_compressed(path,**arrays)
        with np.load(path,allow_pickle=False) as saved:
            for key,value in arrays.items():
                if not np.array_equal(saved[key],value):raise ValueError('Numerical round-trip failure '+key)
        payload+=psi.nbytes;count+=1
        if count%50==0:print(f'Packed and exact-round-trip checked {count}/{len(k)} k points',flush=True)
    write_json(out/'compact.json',{'format':FORMAT,'Nk':count,'state_count':e.shape[1],'source':str(source),
        'limit_bytes':c.get('transfer_limit_bytes',1000000000),'wavefunction_uncompressed_bytes':payload,
        'precision':'float64/complex128; exact round trip of parsed numbers, not byte-identical source text',
        'round_trip_checked':True,'native_metadata':copied,'physics_evaluated':False,
        'excluded':'redundant envelope bases/shifted copies and probability text; originals retained on WORK'})
    write_json(out/'checksums.json',manifest(out))
    report=validate_compact(out,c);write_json(out/'return_validation.json',report)
    # Include the report in the final byte-budget decision.
    report=validate_compact(out,c);write_json(out/'return_validation.json',report)
    if report['status']!='PASS':raise ValueError('Compact validation failed; original raw retained: '+str(report['problems']))
    print(f'Compact transfer: {sum(p.stat().st_size for p in out.rglob("*") if p.is_file())/1e6:.1f} MB; original text retained',flush=True)
    return out
