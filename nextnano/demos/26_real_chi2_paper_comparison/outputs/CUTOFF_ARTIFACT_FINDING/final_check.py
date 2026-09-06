exec(open('cutoff_test.py').read().split('# ---------------- full spectra')[0])
import numpy as np
PAPER = np.array([[400,100],[450,180],[500,450],[540,1260],[560,680],[580,200],[605,0],
 [630,220],[660,500],[700,950],[730,1500],[760,2450],[785,1550],[815,1200],[850,1100],
 [900,1120],[950,1220],[1000,1450],[1040,1950],[1080,3250],[1105,2050],[1130,1850],
 [1150,1150],[1175,1180],[1200,1050],[1225,750],[1250,750],[1275,350],[1300,350],
 [1330,0],[1360,200],[1400,600],[1440,1050],[1480,1800],[1500,2600],[1520,3950],
 [1540,2900],[1560,1950],[1580,1450],[1600,1250],[1650,1050],[1700,950],[1750,850],
 [1800,750],[1850,700]],float)
wl=np.arange(400.,1851.,1.); pap=np.interp(wl,PAPER[:,0],PAPER[:,1]); pap/=pap.max()
def sc(y):
    n=y/y.max(); return float(np.sqrt(np.mean((n-pap)**2))),float(np.corrcoef(n,pap)[0,1])
def pks(y,pf=0.02):
    m=y.max();o=[]
    for i in range(2,len(y)-2):
        if y[i]>y[i-1] and y[i]>=y[i+1]:
            if y[i]-max(y[max(0,i-120):i].min(),y[i+1:i+121].min())>pf*m: o.append(wl[i])
    return o

print("="*76)
print('WHAT IS 0.2045 pi/a?   BZ-radius convention test')
print("="*76)
for lbl,k in [('demo23: 0.1 x (pi/a)',0.1*PI_OVER_A),
              ('paper?: 0.1 x (2pi/a)',0.1*2*PI_OVER_A),
              ('best fit scan',0.2045*PI_OVER_A)]:
    print(f"  {lbl:<24} krng = {k:.5f} nm^-1  = {k/PI_OVER_A:.4f} pi/a")

print("\n"+"="*76); print("FEATURE-BY-FEATURE at krng = 0.1 x 2pi/a (the convention swap)")
print("="*76)
k=0.1*2*PI_OVER_A; c=chi2(wl,k); y=np.abs(c.real)
re=c.real; zc=[wl[i]-re[i]*(wl[i+1]-wl[i])/(re[i+1]-re[i]) for i in range(len(re)-1) if re[i]*re[i+1]<0]
P=pks(y)
tgtP=[540,760,1080,1520]; tgtZ=[605,1330]
print(f"{'feature':<9}{'paper nm':>10}{'model nm':>10}{'err nm':>9}")
for t in tgtP:
    b=min(P,key=lambda p:abs(p-t)); print(f"{'peak':<9}{t:10.0f}{b:10.0f}{b-t:+9.0f}")
for t in tgtZ:
    b=min(zc,key=lambda p:abs(p-t)); print(f"{'zero':<9}{t:10.0f}{b:10.0f}{b-t:+9.0f}")
r,cc=sc(y); print(f"\n  |Re chi2| : nRMSE={r:.4f}  corr={cc:+.3f}")
r2,cc2=sc(np.abs(c)); print(f"  |chi2|    : nRMSE={r2:.4f}  corr={cc2:+.3f}")
print(f"  peak |Re chi2| = {y.max():.1f} pm/V   (paper peak 3950 pm/V)")

print("\n"+"="*76); print("CONTROLS"); print("="*76)
# (a) hole pathway on/off -> gauge invariance
for inc,lbl in [(True,'electron + hole (gauge-invariant)'),(False,'electron pathway ONLY')]:
    cc_=chi2(wl,k,include_holes=inc); r,co=sc(np.abs(cc_.real))
    print(f"  {lbl:<36} peak={np.abs(cc_.real).max():10.1f} pm/V  nRMSE={r:.4f}")
# (b) origin shift test
print("\n  origin-shift (z -> z + 20 nm) on full sum:")
ZE0=dict(ZE); ZH0=dict(ZH)
for kk_ in [(1,1),(2,2)]: ZE[kk_]=ZE0[kk_]+20.0; ZH[kk_]=ZH0[kk_]+20.0
cs=chi2(wl,k); ZE.update(ZE0); ZH.update(ZH0)
print(f"    max |change| = {np.abs(cs-c).max():.3e} pm/V  -> {'INVARIANT' if np.abs(cs-c).max()<1e-9 else 'ORIGIN-DEPENDENT'}")
# (c) cutoff convergence
print("\n  is the integral converged in krng? (peak |Re chi2|, pm/V)")
for f in [0.05,0.10,0.15,0.20,0.25,0.30,0.40]:
    cq=chi2(wl,f*PI_OVER_A); print(f"    krng={f:.2f} pi/a -> peak={np.abs(cq.real).max():9.1f}")
