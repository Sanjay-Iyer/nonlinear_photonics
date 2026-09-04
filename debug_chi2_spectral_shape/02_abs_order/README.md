EXPERIMENT: 02_ABS_ORDER
HYPOTHESIS: A premature magnitude operation may be hiding destructive interference.
RESULT: The production A ordering is coherent. Every early-magnitude ordering B-D destroys cancellation and produces more filled nodes.
NODE 1 EFFECT: A remains 0.2545; early-magnitude variants do not recover zero.
NODE 2 EFFECT: A remains 0.5028; early-magnitude variants do not recover zero.
1520-NM EFFECT: The A peak remains 1045 nm.
RMSE CHANGE: A remains 0.2038.
INTERPRETATION: Use abs(integral(sum(terms))) only when reporting magnitude. Early abs is nonphysical here.
KEEP / REJECT / INCONCLUSIVE: KEEP A; REJECT B-D
