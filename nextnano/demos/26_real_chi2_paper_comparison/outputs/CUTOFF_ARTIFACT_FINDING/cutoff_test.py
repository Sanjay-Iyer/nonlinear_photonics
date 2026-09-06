"""
Faithful re-implementation of the author's Xi2.m algorithm, with an ANALYTIC
k-integral, to test whether the paper's P1 (540 nm) / P3 (1080 nm) peaks are
k-cutoff artifacts of the parabolic-extrapolation + finite-krng scheme.

Author's integrand (Xi2.m):
    integral_0^krng  2*pi*k dk / ((M1 k^2 + E13 - w1 - w2 + i g)(M2 k^2 + E23 - w1 + i g))
Substituting u = k^2 gives  pi * int_0^K2 du /((M1 u + a)(M2 u + b)),
which integrates EXACTLY to
    (pi/C) * [ log((M2 K2 + b)/b) - log((M1 K2 + a)/a)],   C = M2*a - M1*b
Both log terms diverge twice: at the BAND EDGE (a->0 or b->0) and at the
CUTOFF (M*K2 + a -> 0). The second family is pure numerics.
"""
import numpy as np, csv, json

HC = 1239.841984  # eV*nm
A_LAT = 0.56533   # nm  (GaAs)
PI_OVER_A = np.pi / A_LAT   # nm^-1

# ---- aligned parabolic fits (demo24 parabolic_fit_report.csv) --------------
E0 = {'e1': 2.9411581380879994, 'e2': 3.0610228581580006,
      'h1': 1.447805442384,     'h2': 1.4127914221860003}
AC = {'e1': 0.523019419858308,  'e2': 0.4492704548603311,
      'h1': -0.09578794643000983,'h2': -0.05376779479500629}   # eV nm^2

# ---- frozen matrix elements (demo19 case_00 abrupt reference) --------------
O  = {(1,1):0.9825659268894466, (1,2):0.024432908041949086,
      (2,1):-0.08804807050423832,(2,2):0.45711354825954503}      # <e_i|h_j>
ZE = {(1,1):12.734585435956998,(1,2):1.0340924360961732,
      (2,1):1.0340924360961732,(2,2):18.75911084155838}          # nm
ZH = {(1,1):12.65154699565089, (1,2):1.451016947195746,
      (2,1):1.451016947195746, (2,2):12.967036940337104}         # nm

GAMMA = 0.005   # eV, exactly the author's gma

EN = ['e1','e2']; HN = ['h1','h2']

# author's transition lists, 1,2 = electron ; 3,4 = hole
BPE = [(1,1,3),(1,1,4),(1,2,3),(1,2,4),(2,1,3),(2,1,4),(2,2,3),(2,2,4)]
BPH = [(3,3,1),(4,4,1),(3,4,1),(3,4,2),(4,3,1),(4,3,2),(3,3,2),(4,4,2)]

def ename(i): return EN[i-1]
def hname(i): return HN[i-3]

def logint(M1,a,M2,b,K2):
    """pi * int_0^K2 du/((M1 u + a)(M2 u + b)) -- exact."""
    C = M2*a - M1*b
    C = np.where(np.abs(C) < 1e-14, 1e-14+0j, C)
    return np.pi*(np.log((M2*K2+b)/b) - np.log((M1*K2+a)/a))/C

def chi2(wl_nm, krng, include_holes=True):
    w = HC/np.asarray(wl_nm, float)          # photon energy eV
    K2 = krng**2
    tot = np.zeros_like(w, dtype=complex)
    for (a_,b_,c_) in BPE:                                  # electron pathway
        ea,eb,hc_ = ename(a_),ename(b_),hname(c_)
        num = O[(a_,c_-2)]*ZE[(a_,b_)]*O[(b_,c_-2)]
        M1 = abs(AC[ea]-AC[hc_]); M2 = abs(AC[eb]-AC[hc_])
        E13= abs(E0[ea]-E0[hc_]); E23= abs(E0[eb]-E0[hc_])
        tot -= num*logint(M1, E13-2*w+1j*GAMMA, M2, E23-w+1j*GAMMA, K2)
    if include_holes:
        for (a_,b_,c_) in BPH:                              # hole pathway
            ha,hb,ec = hname(a_),hname(b_),ename(c_)
            num = O[(c_,a_-2)]*ZH[(a_-2,b_-2)]*O[(c_,b_-2)]
            M3 = abs(AC[ha]-AC[ec]); M4 = abs(AC[hb]-AC[ec])
            H13= abs(E0[ha]-E0[ec]); H23= abs(E0[hb]-E0[ec])
            tot += num*logint(M3, H13-2*w+1j*GAMMA, M4, H23-w+1j*GAMMA, K2)
    return tot

# ---------- where does the code PREDICT the cutoff artifact? ----------------
print("="*74)
print("ANALYTIC PREDICTION: cutoff-artifact energy = dE(k=0) + M*krng^2")
print("="*74)
print("Paper P1=540 nm -> 2.2960 eV (1w) ; P3=1080 nm -> 2.2960 eV (2w). Same energy.")
print()
print(f"{'transition':<12}{'dE(0) eV':>10}{'M eV.nm2':>11}{'krng needed':>13}{'in pi/a':>10}")
need = HC/540.0
kk=[]
for i,en in enumerate(EN,1):
    for j,hn in enumerate(HN,1):
        dE = E0[en]-E0[hn]; M = AC[en]-AC[hn]
        k = np.sqrt((need-dE)/M); kk.append(k)
        print(f"e{i}-hh{j}      {dE:10.5f}{M:11.5f}{k:13.5f}{k/PI_OVER_A:10.4f}")
print(f"\n  --> all four cluster at krng = {np.mean(kk):.4f} nm^-1 "
      f"= {np.mean(kk)/PI_OVER_A:.4f} pi/a   (spread {np.ptp(kk)/np.mean(kk)*100:.1f}%)")
print(f"  --> demo23 production cutoff was 0.1 pi/a = {0.1*PI_OVER_A:.4f} nm^-1")
json.dump({'k_needed_mean':float(np.mean(kk)),
           'pi_over_a':float(PI_OVER_A)}, open('pred.json','w'))

# ---------------- full spectra + topology scan -----------------------------
from numpy import trapezoid
PAPER = np.array([[400,100],[450,180],[500,450],[540,1260],[560,680],[580,200],[605,0],
 [630,220],[660,500],[700,950],[730,1500],[760,2450],[785,1550],[815,1200],[850,1100],
 [900,1120],[950,1220],[1000,1450],[1040,1950],[1080,3250],[1105,2050],[1130,1850],
 [1150,1150],[1175,1180],[1200,1050],[1225,750],[1250,750],[1275,350],[1300,350],
 [1330,0],[1360,200],[1400,600],[1440,1050],[1480,1800],[1500,2600],[1520,3950],
 [1540,2900],[1560,1950],[1580,1450],[1600,1250],[1650,1050],[1700,950],[1750,850],
 [1800,750],[1850,700]],float)
FEATURES = {'P1':540,'Z1':605,'P2':760,'P3':1080,'Z2':1330,'P4':1520}
wl = np.arange(400.,1851.,1.)
pap_i = np.interp(wl, PAPER[:,0], PAPER[:,1]); pap_n = pap_i/pap_i.max()

def peaks(y, prom_frac=0.02):
    m = y.max(); out=[]
    for i in range(2,len(y)-2):
        if y[i]>y[i-1] and y[i]>=y[i+1]:
            lo=y[max(0,i-120):i].min(); hi=y[i+1:i+121].min()
            if y[i]-max(lo,hi) > prom_frac*m: out.append(wl[i])
    return out

def score(y):
    n = y/y.max() if y.max()>0 else y
    return float(np.sqrt(np.mean((n-pap_n)**2))), float(np.corrcoef(n,pap_n)[0,1])

print("\n"+"="*74); print("KRNG SCAN  (observable = |Re chi2|, the friend's reading)"); print("="*74)
print(f"{'krng/(pi/a)':>12}{'nRMSE':>9}{'corr':>8}{'npk':>5}   peaks (nm)")
rows=[]
for frac in [0.10,0.125,0.15,0.175,0.19,0.20,0.2045,0.21,0.22,0.25,0.30]:
    k = frac*PI_OVER_A
    c = chi2(wl,k); y = np.abs(c.real)
    pk = peaks(y); r,cc = score(y)
    rows.append((frac,r,cc,pk))
    ps = ", ".join(f"{p:.0f}" for p in pk[:8])
    print(f"{frac:12.4f}{r:9.4f}{cc:8.3f}{len(pk):5d}   {ps}")

print("\n"+"="*74); print("HEAD-TO-HEAD at the two cutoffs"); print("="*74)
for frac in [0.10, 0.2045]:
    k = frac*PI_OVER_A; c = chi2(wl,k)
    print(f"\n--- krng = {frac} pi/a = {k:.4f} nm^-1 ---")
    for label,y in [('|Re chi2|',np.abs(c.real)),('|chi2|',np.abs(c)),('Re chi2',c.real)]:
        yy = y/np.abs(y).max()
        s=[]
        for nm,t in FEATURES.items():
            s.append(f"{nm}={yy[int(t-400)]:+.3f}")
        r,cc = score(np.abs(y))
        print(f"  {label:<10} nRMSE={r:.4f} corr={cc:+.3f}  " + " ".join(s))
    # zero crossings of Re
    re=c.real; zc=[wl[i] for i in range(len(re)-1) if re[i]*re[i+1]<0]
    print(f"  Re[chi2] sign changes at: {', '.join(f'{z:.0f}' for z in zc)}")
    print(f"  |chi2| minima at Re-zeros (frac of max): "
          f"{', '.join(f'{np.abs(c)[int(z-400)]/np.abs(c).max():.3f}' for z in zc)}")
