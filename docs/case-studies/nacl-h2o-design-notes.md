# NaCl case study: design notes

The running record of the study `nacl-h2o`, written for whoever finishes the Claude Design canvas at the end. It holds what the study did, step by step, with the numbers the tools returned, and what the canvas still needs. Read the study's own files for anything more: `runs/nacl-h2o/summary.md`, `report.md`, `trace.jsonl`, `geometries/`.

| Item | Where |
|---|---|
| Canvas | https://claude.ai/artifact/AXterX9qo6BUSRkS9mRy9C, board `NaCl.dc.html`, "4 · Case study: H₂O on NaCl(100)" |
| Design system | Chalk Research + Aalto, installed on the canvas as `ds/chalkaalto/` |
| Canvas source, local | the scratchpad copy of `project/NaCl.dc.html`; read the board from the canvas before editing if that copy is gone |
| Inputs | `h2o_system/`: `surface.xyz`, `h2o.xyz`, `oh.xyz`, `h.xyz`, `system.xyz` as the initial state |
| Run by | the user, in an interactive Claude Code chat with the plugin |

## The system

H₂O\* → OH\* + H\* on NaCl(001), an ionic substrate. Five relaxed .xyz files with energies; no DFT in the study, protocol `mlip`.

## Progress, step by step

| Step | What the tools returned | Who acted |
|---|---|---|
| Prompt | 2 published values: E_ads(H₂O) = −0.39 eV, PBE, flat NaCl(001), O over Na, Klimeš, Bowler, Michaelides, JCP 2013; d = 0.958 Å from experiment. CatApp has nothing for NaCl. The human checked 1 of the 2 | literature-reader; human |
| Interview | First check: gas reference consistency. Distrusted default: potentials trained on metals. Trust a potential only if it gets the gas fragments right | computational-chemist drafted, human chose |
| 1 · Inputs and cell | H₂O cut into A = OH, which keeps the binding O, and B = H. Cell 2 × 2 of the slab: 22.74 × 22.74 Å, 192 atoms | computational-chemist |
| 1 · Lock | Protocol mlip: no DFT runs; the potential computes every energy. Found: OH and H files carry free_energy ≠ energy, which moves the gas O–H dissociation from 7.004 to 6.857 eV | computational-chemist |
| 1 · approve settings | passed | human |
| 1\* · Potential | Candidates uma-s-1p2p1, mace-mpa-0, chgnet. First run: only mace-mpa-0 loaded, so escalated. After the human installed chgnet 0.4.2: chgnet, E_ads error −0.072 eV against −0.293 eV for mace-mpa-0, trusted provisionally, doubt carried to step 7. Committee: mace-mpa-0, chgnet; UMA cannot run, no fairchem-core | mlip-specialist; human installed chgnet |
| 1\* · Compute plan | 0.32 s per chgnet force call on 195 atoms. Relaxation: auto, batch above 70 min, 16 CPUs, 32 GB, 3 h, a pool of 4. Screen and gate: auto, 4 CPUs | hpc-specialist |
| 1\* · approve the plan | passed | human |
| 2 · Sites | 4 inequivalent of 256 in the cell, P4mm: top Cl, top Na, bridge Na–Cl, hollow; Burnside agrees; pymatgen finds 6 | tool |
| 3.2 · Pairs | A on its top-Na site 12. d = 0.973 Å measured on the vacuum H₂O; B from 1.459 to 5 Å. 6 symmetry-distinct pairs; nearest B on a hollow, 2.01 Å in plane | tool |
| 3.2 · Placement | 6 candidates, not yet relaxed | tool |
| 3.3 · Pull-force screen | 6 screened; none pulled back above the threshold; none dropped | tool |
| 5 · Gate before relaxation | 6 of 6 pass checks 1, 9, 10, 11 | tool |
| 3.4 · Ordering | Order B001, B016, B018, B048, B051, B009. Reason: on ionic NaCl the O–H bond breaks heterolytically, OH⁻ on Na⁺ and H⁺ on Cl⁻: top Cl first, then Na–Cl bridges next to Cl, then hollows, top Na, hydride-like, last; within a site type the larger A–B separation first. It warned that B001, top Cl at A–B 1.35 Å, may recombine into H₂O\* | surface-chemist, from cards only |
| 4 · Relaxation | 6 relaxed with chgnet, 6 converged. Energies: B018 −711.794 eV, lowest; B001 and B051 +0.003; B009 +0.007; B016 +0.025; B048 +4.552 eV. Contact sheet `geometries/4-relaxed/sheet.png` | tool |

| 5 · Gate after relaxation | 0 of 6 pass. Five re-formed the O–H bond, check 10, A–B 0.97 to 0.99 Å: H went back onto OH, so water again. Four of those are also saddle points, check 5, one imaginary mode, 64i to 178i cm⁻¹. The sixth, B048, did not recombine but the slab reconstructed, top-layer atoms up to 0.75 Å, check 4, and A migrated. Every candidate also migrated, check 2. Picture `geometries/5-gate/rejected.png` | tool |

The headline for the design: with chgnet on NaCl(001), no non-recombining OH\* + H\* survived. The five near-equal energies before the gate were one state, H₂O\* re-formed from five starts. The pipeline caught it in code, check 10, and nothing recombined slipped into the ranking. Say this plainly, in the design system's red ▲ tone: it is the result, not a failure of the run.

| 3.6 · Minima hopping | After the gate, the human asked for the alternative generator: candidates MH000 to MH003 join the queue after the six; the surface-chemist kept its order | human; surface-chemist |
| 6 and 7 · Clustering, doubt | Nothing kept, so nothing to check against the committee; 0 escalated. The step-7 block prints an empty table: a cosmetic fault to fix in summary.py | tools |

| 3.6 · Minima hopping, gated | 5 hops with chgnet found 4 minima, MH000 to MH003; all 4 rejected: O–H re-formed, check 10, 0.97 to 0.98 Å; MH000 and MH001 also saddles, 108i and 128i cm⁻¹ | tool |
| 7 · review flagged cases | passed, with nothing to review | human |
| 8 · Ranking | 0 states ranked: all 10 candidates, 6 placed and 4 from minima hopping, recombined or reconstructed | tool |

The result so far: 10 starts, two generators, 0 survivors; 9 of 10 re-formed H₂O\*. With chgnet, OH\* + H\* on NaCl(001) does not hold apart in a 2 × 2 cell.

| 8 · pick | passed with no pick: nothing was ranked | human |
| Solution | 0 final states. report.md holds the 10 rejected candidates with their reasons; 100 % of the nearest shell gated recombined. No final-state energies, so the code fixes of 22 October had nothing to act on | tools |

Faults seen in the report, to fix after the study, not during it: the head reads "Every energy below is from chgnet, mace-mpa-0, the potential that relaxed the candidates", naming the committee as the one potential; and step 1 still writes A as "HO" rather than OH.

| Interpret results | passed by the human: close the study and report the null result. The critic's review: the report's head must name chgnet alone, and the report must state the null result with its scope | human; scientific-critic |

## Status: closed, and the canvas board is done

The NaCl board shows the result, the funnel, the inputs, the sites map, the gate's rejection sheet, what each agent did and what the human decided. Nothing below is left for the design.

## Fixes the study showed, for the code, after the study

1. report.md: name the one potential that relaxed the candidates, not the committee.
2. report.md: a null-result section, with the counts, the reasons and the scope.
3. Step 1 summary: write fragment A as OH, the team's name, not HO.
4. Step 7 and 8 summaries: no empty table when nothing is kept.
5. The plan box: the human's trust rule, gas fragments right, was never tested by a tool; the critic called it blocking.

## What the canvas needed at the end, all done

1. Replace the tag "in progress" on the NaCl board with the step the study reached.
2. Replace the sticky note "Still to come" with the results: survivors, rejections with reasons, the picked final states with their A–B distance and energies.
3. Add one picture: upload `geometries/8-ranked/sheet.png`, or the picked states from `geometries/solution-final-states/`, as an asset, and place it in a Figure.
4. Add the funnel, as on the recorded-run board: pairs, placed, past the gate, relaxed, past the gate, kept, picked.
5. Keep every number as the tools returned it, units with a space; state limits plainly, in the design system's honest tone.
6. Do not change boards 1, 2, 3 and 5 unless the study showed something they contradict.
