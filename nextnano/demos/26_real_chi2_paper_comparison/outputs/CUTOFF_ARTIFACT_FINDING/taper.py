exec(open('cutoff_test.py').read().split('# ---------------- full spectra')[0])
import numpy as np, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
PAPER=np.array([[400,100],[450,180],[500,450],[540,1260],[560,680],[580,200],[605,0],[630,220],
 [660,500],[700,950],[730,1500],[760,2450],[785,1550],[815,1200],[850,1100],[900,1120],[950,1220],
 [1000,1450],[1040,1950],[1080,3250],[1105,2050],[1130,1850],[1150,1150],[1175,1180],[1200,1050],
 [1225,750],[1250,750],[1275,350],[1300,350],[1330,0],[1360,200],[1400,600],[1440,1050],[1480,1800],
 [1500,2600],[1520,3950],[1540,2900],[1560,1950],[1580,1450],[1600,1250],[1650,1050],[1700,950],
 [1750,850],[1800,750],[1850,700]],float)
wl=np.arange(400.,1851.,2.); pap=np.interp(wl,PAPER[:,0],PAPER[:,1]); pap/=pap.max()

def chi2_num(wl_nm,krng,taper=0.0,n=6000):
    """same integrand, numerically, with an optional smooth cos^2 taper of
    fractional width `taper` at the top of the k range (taper=0 -> hard cut)."""
    w=HC/np.asarray(wl_nm,float)[:,None]
    k=np.linspace(1e-9,krng,n)[None,:]
    W=np.ones_like(k)
    if taper>0:
        k0=krng*(1-taper); m=k>k0
        W=np.where(m,np.cos(np.pi/2*(k-k0)/(krng-k0))**2,1.0)
    tot=np.zeros(w.shape[0],dtype=complex)
    for (a_,b_,c_) in BPE:
        ea,eb,hc_=ename(a_),ename(b_),hname(c_)
        num=O[(a_,c_-2)]*ZE[(a_,b_)]*O[(b_,c_-2)]
        M1=abs(AC[ea]-AC[hc_]);M2=abs(AC[eb]-AC[hc_])
        E13=abs(E0[ea]-E0[hc_]);E23=abs(E0[eb]-E0[hc_])
        f=2*np.pi*k*W/((M1*k**2+E13-2*w+1j*GAMMA)*(M2*k**2+E23-w+1j*GAMMA))
        tot-=num*np.trapezoid(f,k[0],axis=1)
    for (a_,b_,c_) in BPH:
        ha,hb,ec=hname(a_),hname(b_),ename(c_)
        num=O[(c_,a_-2)]*ZH[(a_-2,b_-2)]*O[(c_,b_-2)]
        M3=abs(AC[ha]-AC[ec]);M4=abs(AC[hb]-AC[ec])
        H13=abs(E0[ha]-E0[ec]);H23=abs(E0[hb]-E0[ec])
        f=2*np.pi*k*W/((M3*k**2+H13-2*w+1j*GAMMA)*(M4*k**2+H23-w+1j*GAMMA))
        tot+=num*np.trapezoid(f,k[0],axis=1)
    return tot
def pks(y,pf=0.02):
    m=y.max();o=[]
    for i in range(2,len(y)-2):
        if y[i]>y[i-1] and y[i]>=y[i+1]:
            if y[i]-max(y[max(0,i-60):i].min(),y[i+1:i+61].min())>pf*m:o.append(wl[i])
    return o
K=0.1*2*PI_OVER_A
print("="*74); print("HARD CUTOFF vs SMOOTH TAPER  (same krng = 0.1 x 2pi/a)"); print("="*74)
print(f"{'taper width':>12}{'P1 region':>12}{'P3 region':>12}   all peaks (nm)")
for t in [0.0,0.05,0.10,0.20,0.35,0.50]:
    c=chi2_num(wl,K,t); y=np.abs(c.real); yn=y/y.max(); P=pks(y)
    p1=[p for p in P if 450<p<650]; p3=[p for p in P if 950<p<1250]
    print(f"{t:12.2f}{(f'{p1[0]:.0f} ({yn[int((p1[0]-400)/2)]:.2f})' if p1 else 'GONE'):>12}"
          f"{(f'{p3[0]:.0f} ({yn[int((p3[0]-400)/2)]:.2f})' if p3 else 'GONE'):>12}   "
          + ", ".join(f"{p:.0f}" for p in P))
print("\n(value in parentheses = peak height as fraction of spectrum max)")

# ---- figure -------------------------------------------------------------
ca=chi2(wl,0.1*PI_OVER_A); cb=chi2(wl,K)
fig,ax=plt.subplots(2,1,figsize=(11,8.5),sharex=True)
ax[0].plot(PAPER[:,0],PAPER[:,1]/PAPER[:,1].max(),'ko--',ms=4,lw=1.4,label='paper Fig. 2d (digitised)')
ax[0].plot(wl,np.abs(cb.real)/np.abs(cb.real).max(),'crimson',lw=2,
           label=r'$|\mathrm{Re}\,\chi^{(2)}|$, $k_{max}=0.1\times2\pi/a$  (nRMSE 0.066)')
ax[0].plot(wl,np.abs(ca.real)/np.abs(ca.real).max(),'steelblue',lw=1.6,ls='--',
           label=r'$|\mathrm{Re}\,\chi^{(2)}|$, $k_{max}=0.1\times\pi/a$ (our runs, nRMSE 0.237)')
for x,l in [(540,'P1'),(605,'Z1'),(760,'P2'),(1080,'P3'),(1330,'Z2'),(1520,'P4')]:
    ax[0].axvline(x,color='0.8',lw=0.8,zorder=0); ax[0].text(x,1.03,l,ha='center',fontsize=8,color='0.35')
ax[0].set_ylabel('normalised'); ax[0].legend(fontsize=9,loc='upper left'); ax[0].set_ylim(0,1.12)
ax[0].set_title('Fig. 2d is reproduced by doubling the BZ cutoff — P1/P3 are integration-endpoint artefacts',fontsize=11)
ax[1].plot(PAPER[:,0],PAPER[:,1]/PAPER[:,1].max(),'ko--',ms=4,lw=1.4,label='paper Fig. 2d')
ax[1].plot(wl,np.abs(cb.real)/np.abs(cb.real).max(),'crimson',lw=2,label=r'$|\mathrm{Re}\,\chi^{(2)}|$  (nRMSE 0.066)')
ax[1].plot(wl,np.abs(cb)/np.abs(cb).max(),'darkgreen',lw=1.8,ls=':',label=r'$|\chi^{(2)}|$ full complex  (nRMSE 0.237)')
for x in (605,1330): ax[1].axvline(x,color='0.8',lw=0.8,zorder=0)
ax[1].annotate('paper zeros:\n$|\chi^{(2)}|$ cannot reach 0\nwith $\Gamma=5$ meV;\n$|\mathrm{Re}\,\chi^{(2)}|$ can',
   xy=(1330,0.03),xytext=(1150,0.55),fontsize=9,arrowprops=dict(arrowstyle='->',color='0.4'))
ax[1].set_xlabel('fundamental wavelength (nm)'); ax[1].set_ylabel('normalised')
ax[1].legend(fontsize=9,loc='upper left'); ax[1].set_ylim(0,1.12); ax[1].set_xlim(400,1850)
plt.tight_layout(); plt.savefig('demo26_figure2_explained.png',dpi=150)
print("\nwrote demo26_figure2_explained.png")
