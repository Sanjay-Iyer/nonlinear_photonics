"""Minimal signed-component plots; amplitudes never independently normalized."""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def axes(xlabel='fundamental wavelength (nm)',ylabel=r'$\chi^{(2)}$ (pm/V)',zero_line=True):
    fig,ax=plt.subplots(figsize=(9,4.5))
    ax.set(xlabel=xlabel,ylabel=ylabel)
    ax.spines[['top','right']].set_visible(False)
    if zero_line: ax.axhline(0,color='.75',lw=.7,zorder=0)
    return fig,ax


def save(fig,ax,out,name,legend=True):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    if legend: ax.legend(frameon=False,fontsize=9,loc='best')
    fig.tight_layout()
    fig.savefig(out/(name+'.png'),dpi=220)
    fig.savefig(out/(name+'.svg'))
    plt.close(fig)


def baseline(out,wl,c,paper):
    for name,y,color,label in [('28A_real',c.real,'crimson',r'Re $\chi^{(2)}$'),
                               ('28A_imag',c.imag,'steelblue',r'Im $\chi^{(2)}$')]:
        fig,ax=axes();ax.plot(wl,y,color=color,lw=1.8,label=label);ax.set_xlim(wl[0],wl[-1]);save(fig,ax,out,name)
    fig,ax=axes()
    ax.plot(wl,c.real,color='crimson',lw=1.8,label=r'Re $\chi^{(2)}$')
    ax.plot(wl,c.imag,color='steelblue',lw=1.8,label=r'Im $\chi^{(2)}$')
    ax.set_xlim(wl[0],wl[-1]);save(fig,ax,out,'28A_real_imag')
    fig,ax=axes()
    ax.plot(wl,abs(c.real),color='crimson',label=r'$|\mathrm{Re}\,\chi^{(2)}|$')
    ax.plot(wl,abs(c),color='darkgreen',ls=':',label=r'$|\chi^{(2)}|$')
    ax.set_xlim(wl[0],wl[-1]);save(fig,ax,out,'28A_abs_real_vs_abs')
    fig,ax=axes(ylabel=r'normalized $\chi^{(2)}$')
    ax.plot(paper[:,0],paper[:,1]/max(paper[:,1]),'ko--',ms=3,lw=1.1,label='paper Fig. 2d')
    ax.plot(wl,abs(c.real)/max(abs(c.real)),color='crimson',lw=1.8,label=r'$|\mathrm{Re}\,\chi^{(2)}|$')
    ax.plot(wl,abs(c)/max(abs(c)),color='darkgreen',ls=':',lw=1.8,label=r'$|\chi^{(2)}|$')
    ax.set_xlim(wl[0],wl[-1]);save(fig,ax,out,'28A_paper_comparison')


def sweep(out,wl,cases,selected):
    for component,label in [('real','Re'),('imag','Im')]:
        for only_selected in [False,True]:
            chosen=[c for c in cases if not only_selected or any(np.isclose(c['fraction'],f,rtol=0,atol=1e-12) for f in selected)]
            fig,ax=axes()
            colors=plt.cm.viridis(np.linspace(.1,.85,len(chosen)))
            for case,color in zip(chosen,colors):
                values=getattr(case['chi'],component)
                ax.plot(wl,values,color=color,lw=1.5,label=rf"{case['fraction']:.3g} $\pi/a$")
            ax.set_xlim(wl[0],wl[-1])
            suffix='selected' if only_selected else 'kmax_overlay'
            save(fig,ax,out,f'28B_{component}_{suffix}')
    x=[c['fraction'] for c in cases]
    for tag,field in [('real','Re'),('imag','Im')]:
        fig,ax=axes(xlabel=r'requested $k_{max}/(\pi/a)$',ylabel='dominant feature wavelength (nm)',zero_line=False)
        ax.scatter(x,[c['features'][f'dominant_abs_{field}_wavelength_nm'] for c in cases],s=22,color='steelblue')
        # No connecting line: a global maximum may switch between distinct peaks.
        save(fig,ax,out,f'28B_{tag}_peak_wavelength',legend=False)
        target=cases[0]['features']['target_wavelength_nm']
        for which,key,ylabel in [('target',f'{field}_at_target_pm_per_V',rf'{field} $\chi^{{(2)}}$ at {target:g} nm (pm/V)'),
                                ('amplitude',f'max_abs_{field}_pm_per_V',rf'max $|{field}\,\chi^{{(2)}}|$ (pm/V)')]:
            fig,ax=axes(xlabel=r'requested $k_{max}/(\pi/a)$',ylabel=ylabel)
            ax.plot(x,[c['features'][key] for c in cases],'-o',ms=3,color='steelblue',lw=1.4)
            save(fig,ax,out,f'28B_{tag}_{which}',legend=False)
    fig,ax=axes(xlabel=r'requested $k_{max}/(\pi/a)$',ylabel='Re zero-crossing wavelength (nm)',zero_line=False)
    for case in cases:
        roots=case['features']['Re_zero_crossings']
        ax.scatter([case['fraction']]*len(roots),[r['wavelength_nm'] for r in roots],s=20,color='black')
    save(fig,ax,out,'28B_zero_crossings',legend=False)
