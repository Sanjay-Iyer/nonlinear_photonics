"""28F: full-line diagonal-frequency dispersion audit, not an absorption model.

No Equation 2 denominators are duplicated here. Signed energy evaluation uses
the authoritative equation2.calculate_chi2_energy. See CAUSALITY_AUDIT.md.
"""
import argparse
import csv
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import numpy as np
from scipy.signal import hilbert
from .equation2 import Settings, calculate_chi2_energy
from .input_builder import build_inputs
from .artifacts import write_json, manifest
from .plotting import axes, save

ROOT = Path(__file__).resolve().parents[1]


def uniform_energy_grid(half_width, step):
    if not np.isfinite(half_width) or not np.isfinite(step) or half_width <= 0 or step <= 0:
        raise ValueError('Positive finite energy extent and step required')
    count = int(round(2 * half_width / step))
    if count < 8 or not np.isclose(count * step, 2 * half_width, atol=1e-10, rtol=0):
        raise ValueError('Energy range must contain an integer number of steps')
    # Both endpoints retained so reversal exactly represents E -> -E.
    return np.linspace(-half_width, half_width, count + 1)


def kk_reconstruct(energy, chi, gamma_sign=1, padding_multiple=3):
    """Full-line H f(x)=PV integral f(t)/(x-t) dt/pi, approximated by FFT.

    +iGamma: analytic lower half plane (inverse time convention exp(+iwt));
    Re=H(Im), Im=-H(Re). Minus Gamma reverses both signs. Zero padding reduces
    periodic-image error, but does not restore unavailable spectral tails.
    """
    x = np.asarray(energy, float)
    c = np.asarray(chi, complex)
    if x.ndim != 1 or len(x) < 8 or c.shape != x.shape or not np.isfinite(c).all():
        raise ValueError('Finite complex 1D spectrum on at least 8 points required')
    dx = np.diff(x)
    if not np.isfinite(x).all() or np.any(dx <= 0) or not np.allclose(dx, dx[0], rtol=1e-9, atol=1e-12):
        raise ValueError('KK requires a strictly increasing uniform energy grid')
    if gamma_sign not in (-1, 1) or not isinstance(padding_multiple, int) or padding_multiple < 1:
        raise ValueError('Invalid Fourier sign or padding multiple')
    pad = (padding_multiple - 1) * len(x) // 2
    def transform(y):
        y = np.pad(y, (pad, pad))
        return hilbert(y).imag[pad:pad + len(x)]
    return gamma_sign * transform(c.imag), -gamma_sign * transform(c.real)


def analytic_shg(energy, resonance=1.5, damping=.1, gamma_sign=1):
    """Known causal oscillator SHG: 1/[D(2E) D(E)^2], arbitrary units.

    D(E)=Omega^2-E^2+i gamma E for inverse exp(+iwt). Upper-half-plane poles,
    lower-half-plane analytic, O(E^-6), and F(-E)=F(E)*. Not the QW model.
    """
    e = np.asarray(energy)
    def d(x): return resonance**2 - x**2 + 1j * gamma_sign * damping * x
    return 1 / (d(2*e) * d(e)**2)


def error_metrics(reference, reconstructed, mask):
    a, b = np.asarray(reference)[mask], np.asarray(reconstructed)[mask]
    if not len(a): raise ValueError('Metric region has no samples')
    rms = float(np.sqrt(np.mean((a-b)**2)))
    scale = float(np.sqrt(np.mean(a**2)))
    return {'rms_error': rms, 'max_abs_error': float(np.max(abs(a-b))),
            'reference_rms': scale, 'relative_rms_error': rms/scale if scale else None}


def evaluate_signed(energy, inputs, settings, chunk_size=2048):
    if not isinstance(chunk_size, int) or chunk_size < 1: raise ValueError('Invalid chunk size')
    return np.concatenate([calculate_chi2_energy(energy[start:start+chunk_size], inputs, settings).chi2_complex
                           for start in range(0, len(energy), chunk_size)])


def run(config=ROOT/'config/causality.json', raw_root=None, out=ROOT/'outputs/28F_causality', make_plots=True):
    cfg=json.loads(Path(config).read_text()); out=Path(out); out.mkdir(parents=True, exist_ok=True)
    baseline=json.loads((ROOT/cfg['baseline_config']).read_text())
    settings=Settings(**baseline['settings'])
    raw=Path(raw_root) if raw_root else ROOT/baseline['raw_input']
    inputs,_=build_inputs(raw)
    widths=cfg['energy_half_widths_eV']; step=cfg['energy_step_eV']
    if len(widths)<2 or np.any(np.diff(widths)<=0): raise ValueError('At least two increasing bandwidths required')
    lo,hi=cfg['central_window_eV']; elo,ehi=cfg['edge_fraction_window']
    if not 0<lo<hi<min(widths) or not 0<elo<ehi<1: raise ValueError('Invalid central/edge windows')
    rows=[]; reports=[]; last=None
    for width in widths:
        energy=uniform_energy_grid(width,step)
        masks={'central':(energy>=lo)&(energy<=hi), 'edge':(abs(energy)>=elo*width)&(abs(energy)<=ehi*width)}
        # Always validate numerical checker on known analytic SHG before Eq2.
        analytic=analytic_shg(energy,cfg['analytic_oscillator_energy_eV'],cfg['analytic_oscillator_gamma_eV'],settings.gamma_sign)
        ar,ai=kk_reconstruct(energy,analytic,settings.gamma_sign,cfg['padding_multiple'])
        analytic_metrics={part:error_metrics(getattr(analytic,part),v,masks['central']) for part,v in [('real',ar),('imag',ai)]}
        if any(v['relative_rms_error']>cfg['numerical_relative_rms_tolerance'] for v in analytic_metrics.values()):
            raise ValueError('Analytic KK checker failed; refusing physical-model audit')
        chi=evaluate_signed(energy,inputs,settings,cfg['chunk_size'])
        kr,ki=kk_reconstruct(energy,chi,settings.gamma_sign,cfg['padding_multiple'])
        metrics={region:{part:error_metrics(getattr(chi,part),v,mask) for part,v in [('real',kr),('imag',ki)]} for region,mask in masks.items()}
        symmetry=float(np.max(abs(chi[::-1]-chi.conj()))/np.max(abs(chi)))
        report={'half_width_eV':width,'energy_points':len(energy),'analytic_checker':analytic_metrics,
                'equation2_metrics':metrics,'reality_symmetry_max_relative_error':symmetry}
        reports.append(report)
        for region in masks:
            for component in ('real','imag'):
                rows.append({'half_width_eV':width,'energy_step_eV':step,'region':region,'component':component,**metrics[region][component]})
        np.savez_compressed(out/f'kk_bandwidth_{width:g}_eV.npz',photon_energy_eV=energy,chi2_complex=chi,
                            real_from_imag=kr,imag_from_real=ki,analytic_chi=analytic,analytic_re_from_im=ar,analytic_im_from_re=ai)
        last=(energy,chi,kr,ki,analytic,ar,ai)
        print(f'28F: +/-{width:g} eV, dE={step:g}, analytic checker PASS; central KK relative RMS {metrics["central"]["real"]["relative_rms_error"]:.4g}, {metrics["central"]["imag"]["relative_rms_error"]:.4g}')
    with (out/'bandwidth_metrics.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    energy,chi,kr,ki,analytic,ar,ai=last
    # Save a human-inspectable complete signed-frequency spectrum (not wavelength).
    np.savetxt(out/'chi2_signed_energy.csv',np.column_stack([energy,chi.real,chi.imag,abs(chi.real),abs(chi),kr,ki]),delimiter=',',
               header='photon_energy_eV,chi2_real_pm_per_V,chi2_imag_pm_per_V,chi2_abs_real_pm_per_V,chi2_abs_pm_per_V,KK_real_pm_per_V,KK_imag_pm_per_V',comments='')
    numerical=all(v['relative_rms_error']<=cfg['numerical_relative_rms_tolerance'] for v in reports[-1]['equation2_metrics']['central'].values())
    try: commit=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    except (OSError,subprocess.CalledProcessError): commit=None
    meta={'study':'28F_causality','timestamp_utc':datetime.now(timezone.utc).isoformat(),'git_commit':commit,
          'configuration':cfg,'settings':asdict(settings),'source_dataset':str(raw.resolve()),
          'k_points':len(inputs['k_per_nm']),'k_range_per_nm':[float(inputs['k_per_nm'][0]),float(inputs['k_per_nm'][-1])],
          'k_units':'nm^-1','BZ_conversion':'reported fraction = k*a/pi, radial isotropic disk approximation',
          'lattice_constant_nm':cfg['lattice_constant_nm'],'state_indices':inputs['kp8_pair_ids'],
          'integration_method':'g_s*k*dk/(2*pi), native-grid trapezoidal','normalization':'none; stated historical pm/V',
          'equation_implementation':'chi2/equation2.py::calculate_chi2_energy',
          'equation_sha256':hashlib.sha256((ROOT/'chi2/equation2.py').read_bytes()).hexdigest(),
          'wavelength_grid':None,'spectral_grid':'uniform signed photon energy; negative energies are mathematical analytic continuation, not new bands',
          'gamma_eV':settings.gamma_eV,'analytic_checker_status':'PASS','model_full_line_KK_status':'PASS' if numerical else 'INCONCLUSIVE DUE TO BANDWIDTH/TRUNCATION',
          'physical_causality_status':'INCONCLUSIVE: resonant-only extension fails real-field conjugation symmetry; full response and paper Fourier convention unresolved',
          'fourier_convention_for_plus_iGamma':'inverse exp(+i*omega*t), susceptibility forward exp(-i*omega*t), analytic lower half plane',
          'poles_energy_eV':'d1: transition+iGamma; d2: (transition+iGamma)/2; all upper half plane for gamma_sign=+1',
          'bandwidth_reports':reports,'licensed_solver_executed':False,
          'limitations':['Finite FFT domain and zero-padding introduce edge errors; see bandwidth metrics.',
                         'Broad energy extension tests rational Eq2 algebra only, not material validity across +/-32 eV.',
                         'No negative-frequency symmetrization or missing antiresonant pathways are silently added.',
                         'Causal complex-envelope analyticity is not sufficient to establish complete real-field susceptibility or measured absorption.']}
    write_json(out/'raw_manifest.json',manifest(raw));write_json(out/'metadata.json',meta)
    if make_plots:
        for part,direct,rebuilt,name in [('Re',chi.real,kr,'28F_re_from_im_KK'),('Im',chi.imag,ki,'28F_im_from_re_KK')]:
            fig,ax=axes(xlabel='fundamental photon energy (eV)',ylabel=rf'{part} $\chi^{{(2)}}$ (pm/V)')
            ax.plot(energy,direct,color='black',lw=1.8,label='Equation 2')
            ax.plot(energy,rebuilt,color='crimson' if part=='Re' else 'steelblue',ls='--',lw=1.3,label='full-line KK reconstruction')
            ax.set_xlim(lo,hi);save(fig,ax,out/'plots',name)
        fig,ax=axes(xlabel='fundamental photon energy (eV)',ylabel='analytic SHG response (arb. units)')
        ax.plot(energy,analytic.real,color='black',label='analytic Re');ax.plot(energy,ar,ls='--',color='crimson',label='KK Re')
        ax.plot(energy,analytic.imag,color='steelblue',label='analytic Im');ax.plot(energy,ai,ls=':',color='orange',label='KK Im')
        ax.set_xlim(0,2.5);save(fig,ax,out/'plots','28F_analytic_checker')
        fig,ax=axes(xlabel='fundamental photon energy (eV)',ylabel=r'$|F(-E)-F(E)^*|$ (pm/V)',zero_line=False)
        ax.plot(energy,abs(chi[::-1]-chi.conj()),color='darkmagenta',lw=1.6,label='real-field conjugation defect')
        ax.set_xlim(lo,hi);save(fig,ax,out/'plots','28F_reality_symmetry')
    return meta


def cli(argv=None):
    parser=argparse.ArgumentParser(description='28F analytic and finite-band full-line KK audit; cached data only')
    parser.add_argument('--config',type=Path,default=ROOT/'config/causality.json')
    parser.add_argument('--input',type=Path);parser.add_argument('--output',type=Path,default=ROOT/'outputs/28F_causality')
    parser.add_argument('--no-plots',action='store_true');a=parser.parse_args(argv)
    meta=run(a.config,a.input,a.output,not a.no_plots)
    print('28F physical interpretation:',meta['physical_causality_status'])
    return 0
