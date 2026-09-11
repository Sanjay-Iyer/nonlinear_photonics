exec(open('cutoff_test.py').read().split('# ---------------- full spectra')[0])
import numpy as np
wl=np.arange(400.,1851.,1.)
def pks(y,pf=0.02):
    m=y.max();o=[]
    for i in range(2,len(y)-2):
        if y[i]>y[i-1] and y[i]>=y[i+1]:
            if y[i]-max(y[max(0,i-120):i].min(),y[i+1:i+121].min())>pf*m: o.append(wl[i])
    return o
BZ2=2*np.pi/A_LAT   # full Gamma-X, nm^-1
print("="*86)
print("EXTENDED krng SCAN -- how far have we actually gone?")
print("="*86)
print(f"{'k/(pi/a)':>9}{'k/(2pi/a)':>11}{'k nm^-1':>10}{'peak pm/V':>11}   artefact 1w/2w (nm)      real peaks")
prev=None
for f in [0.05,0.10,0.125,0.15,0.20,0.25,0.30,0.40,0.50,0.60,0.80,1.00,1.50,2.00]:
    k=f*PI_OVER_A; c=chi2(wl,k); y=np.abs(c.real); P=pks(y)
    a1=[p for p in P if p<700]; a3=[p for p in P if 900<p<1400]
    real=[p for p in P if 700<=p<=900]+[p for p in P if p>1400]
    art=f"{a1[0]:.0f} / {a3[0]:.0f}" if (a1 and a3) else ("below 400 nm" if not a1 else "-")
    print(f"{f:9.3f}{k/BZ2:11.4f}{k:10.4f}{y.max():11.1f}   {art:22s}  "
          + ", ".join(f"{p:.0f}" for p in real))
print("\n" + "="*86)
print("DOES IT EVER SATURATE?  (paper Methods claim: 'saturated by one-tenth of the BZ')")
print("="*86)
last=None
for f in [0.1,0.2,0.4,0.8,1.6,3.2,6.4]:
    v=np.abs(chi2(wl,f*PI_OVER_A).real).max()
    d="" if last is None else f"   (+{(v/last-1)*100:5.1f}% vs previous)"
    print(f"  krng={f:5.2f} pi/a   peak |Re chi2| = {v:7.1f} pm/V{d}")
    last=v
print("\n  physical ceiling: electron subbands cross the Al0.55Ga0.45As CB edge at")
print(f"  k ~ 0.73-0.85 nm^-1 = {0.73/PI_OVER_A:.3f}-{0.85/PI_OVER_A:.3f} pi/a"
      f" = {0.73/BZ2:.3f}-{0.85/BZ2:.3f} x (2pi/a)")
print("  -> beyond that the states are not bound and the parabola is fiction.")
print("\n" + "="*86)
print("WHAT '0.1 BZ' COULD MEAN")
print("="*86)
for lbl,k in [("0.1 x (pi/a)   zone edge along one axis", 0.1*PI_OVER_A),
              ("0.1 x (2pi/a)  full Gamma-X distance",    0.1*BZ2)]:
    c=chi2(wl,k); y=np.abs(c.real); P=pks(y)
    print(f"  {lbl:38s} k={k:.4f} nm^-1  peaks: " + ", ".join(f"{p:.0f}" for p in P))
print(f"  {'friend inferred (fitted, single-band mu)':38s} k=1.0000 nm^-1  "
      f"= {1.0/PI_OVER_A:.4f} pi/a = {1.0/BZ2:.4f} x (2pi/a)")
print(f"  {'ours inferred (fitted, kp8 mu)':38s} k=1.1348 nm^-1  "
      f"= {1.1348/PI_OVER_A:.4f} pi/a = {1.1348/BZ2:.4f} x (2pi/a)")
