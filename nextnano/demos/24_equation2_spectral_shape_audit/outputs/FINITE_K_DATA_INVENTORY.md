# Finite-k matrix-element data inventory

The copied output supports E(k), but not a valid finite-k M(k) reconstruction. Demo 24 therefore does not fabricate a finite-k spectrum.

| Quantity | Needed for Equation 2? | Available in copied Demo 23 raw output? | Exact file/path | Can be used directly? | Needs conversion? | Missing? |
|---|---|---|---|---|---|---|
| tracked transition energies E(k) | True | True | C:\code\nonlinear_photonics\demo_results\demo23\raw\production_y_n301_k0100\production_y_n301_k0100\bias_00000\QuantumDispersions\acqw\kp8\dispersion_Gamma_to_y.dat | True | no | False |
| k=0 envelope components | True | True | C:\code\nonlinear_photonics\demo_results\demo23\raw\production_y_n301_k0100\production_y_n301_k0100\bias_00000\Quantum\acqw\kp8\envelope_k00000_0001_cb1.dat; C:\code\nonlinear_photonics\demo_results\demo23\raw\production_y_n301_k0100\production_y_n301_k0100\bias_00000\Quantum\acqw\kp8\envelope_k00000_0001_cb2.dat; C:\code\nonlinear_photonics\demo_results\demo23\raw\production_y_n301_k0100\production_y_n301_k0100\bias_00000\Quantum\acqw\kp8\envelope_k00000_0001_hh1.dat; C:\code\nonlinear_photonics\demo_results\demo23\raw\production_y_n301_k0100\production_y_n301_k0100\bias_00000\Quantum\acqw\kp8\envelope_k00000_0001_hh2.dat; ... | False | integration and state pairing | False |
| finite-k envelope components | True | False |  | False | integration and state pairing | True |
| k=0 Cb/HH/LH/SO composition | False | True | C:\code\nonlinear_photonics\demo_results\demo23\raw\production_y_n301_k0100\production_y_n301_k0100\bias_00000\Quantum\acqw\kp8\spinor_composition_k00000_CbHhLhSo.dat | True | pair averaging | False |
| finite-k Cb/HH/LH/SO composition | False | False |  | True | pair averaging | True |
| finite-k overlap O_nm(k) | True | False |  | False | quantity-specific parser | True |
| finite-k electron z matrix z_e(k) | True | False |  | False | quantity-specific parser | True |
| finite-k heavy-hole z matrix z_hh(k) | True | False |  | False | quantity-specific parser | True |
