# Equation 2 term-by-term audit

| Printed element | Independent code expression | Match? | Notes |
|---|---|---|---|
| Common two-photon denominator | `Delta[n,m]-2E+iGamma` | YES | E=hc/lambda |
| Electron one-photon denominator | `Delta[l,m]-E+iGamma` | YES | Correct l,m transition |
| HH one-photon denominator | `Delta[n,l]-E+iGamma` | YES | Correct n,l transition |
| Electron numerator | `conj(O[n,m])*ze[n,l]*O[l,m]` | YES | Explicit bra/ket orientation |
| HH numerator | `O[n,m]*zh[m,l]*conj(O[n,l])` | YES | Explicit bra/ket orientation |
| Relative family sign | electron minus HH | YES | Printed minus retained |
| m,n,l ranges | 0,1 for each | YES | 8 electron + 8 HH pathways |
| SH permutation | omega1=omega2=omega | YES | 2E and E denominators |
| Occupation | occupied HH / empty electron implicit | YES/ASSUMED | Same low-density interband reduction as paper |
| Broadening | +i Gamma in both denominators | YES | 5 meV baseline |
| Energy conversion | E=hc/lambda, Gamma in eV | YES | No mixed angular-frequency units |
| hbar | absent in energy-domain evaluator | YES | The printed hbar^-2 cancels the two hbar factors from frequency denominators |

Every one of 16 pathways, both subtotals, and the final 1,451 complex wavelength samples were compared with the stored engine. Maximum final complex error: **5.326e-10 pm/V**. Per-denominator shapes and finiteness are recorded separately.
