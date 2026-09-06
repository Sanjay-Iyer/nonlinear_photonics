# Schrödinger-Poisson audit

The paper Methods explicitly describes Schrödinger-Poisson calculations with nextnano. The copied Demo23 results contain `fixed charges: 0 e/cm^2`, and the Demo23 configuration/deck audit does not document doping, carrier density, or a self-consistent Poisson loop matching the paper. Therefore the implementations are **UNCERTAIN / NOT DEMONSTRABLY MATCHED**.

Charge, doping, occupations, built-in fields, and Hartree potential can shift subbands and alter asymmetric-well wavefunctions. Their importance cannot be quantified from the copied data. A like-for-like electrostatic rerun is **REQUIRES_PROFESSIONAL_DATA**, but the colleague's deck/charge settings should be obtained first.
