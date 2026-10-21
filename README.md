# open-science-hackathon: the nearest non-recombining final state

## The problem

Given a surface with the adsorbate AB\* and the desired product A\* + B\*, both fragments adsorbed, find the final state in which B\* sits as close to A\* as it can while the two stay fully dissociated and do not bond back. That is the whole scope, fixed by the team. Not catalysis, not kinetics, not yet the barrier: those are a later phase and no core task or measurable depends on them. The plan follows the shape of NEBscape, the closest prior work; CatTSunami is secondary. Everything a coding agent needs is in `agent.md`; the theory and the design history are in `archive/`.

## Inputs and output

Three relaxed structures and the named product go in; the nearest validated final states come out, with the pairs they rejected and why.

![The team's plan: three relaxed inputs, unique sites, the least distance before pull-back, the best configuration for both fragments, the dissociated final state](figures/plan.webp)

*Figure: the team's visualisation · 5 panels, inputs and output, schematic*

Reading the figure: panel 1, three relaxed inputs; panel 3, the unit cell and its unique sites; panel 4, how far B can sit from A before the molecule pulls it back, the stated problem; panel 5, the best configuration for both fragments; panel 2, the dissociated final state.

| Item | Content | Owner |
|---|---|---|
| Inputs | Relaxed initial state AB\* on the surface; relaxed clean surface; relaxed adsorbate in vacuum, each with its energy; the product named as A\* + B\*, both fragments adsorbed | Human |
| Input prompt | Surface, adsorbates, system description; critic and knowledge prompts as a fixed list; reasoning questions as a written skill | Human |
| Known | E_ads of the adsorbate from the literature, one or two published values with functional and site; a human verifies each | Literature |
| Settings | DFT settings locked in `PROJECT.md` by the dft-settings-protocol skill before anything is computed | Human |
| Output | The nearest non-recombining final states in order, the first few survivors, each on a card with its issues and the calibrated doubt from mlip_doubt; the human interprets them and the chosen final states go to DFT single points, P5; E(FS near) and E(FS ∞); every rejected pair with its reason; the recombination rate | Tool |

## The pipeline we will implement

The plan is a single pass from the input prompt to the solution; step 3, placing the dissociated fragment, is the stated problem. Each box carries the board's step and the tool that implements it; the amber tags are the decisions still open; the purple boxes are our agents where the board drew an agent input; the pause signs are the checkpoints where the agent waits for the human.

![The pipeline we will implement: the board's steps with their tool calls, the open decisions as amber tags, our agents in purple, the checkpoints in pink](figures/pipeline.png)

*Figure: the pipeline we will implement · 16 steps, 9 open decisions, 5 checkpoints, schematic*

Reading the figure: grey boxes are computation, each with its tool name and action; the coral box is step 3 with its six points in the board's order, 1 to 4 then 5 or 6, and a note on the order the code runs them; the purple boxes on the left are our agents at the steps where the board drew an agent input, dashed where they are extensions; the amber tags on the right are the open decisions. The panels of the team's visualisation above map onto these steps as follows.

| Panel of the visualisation | Board steps |
|---|---|
| 1 Inputs: relaxed initial state, surface, adsorbate | 1, 1\* |
| 3 Unit cell and unique adsorption sites | 2, 3.5 |
| 4 Least distance before the molecule pulls the atom back | 3.1, 3.2, 3.3, 4, 5 |
| 5 Most favourable configuration for both components | 3.4, 3.6, 6, 7, 8 |
| 2 Output: dissociated final state | Solution |

## How the plan evolved, step by step

The board is the reference: one row per board step, in the board's order and numbering, with what the board says, what the literature refined, and what we added. Nothing on the board was dropped; the ML variant of the filter in step 5 and the vision model in step 3 are recorded as not taken and as an extension.

![One row per board step: what the board says, what the literature refined, what we added](figures/board-evolution.png)

*Figure: evolution of the plan · 16 board steps, 4 columns, schematic*

Reading the figure: the left column quotes the board, with the owner line under each step; green is the refinement the literature gave, with its source; blue is what we added or decided; amber is a decision still open and dashed purple an extension. The dashed bracket marks step 3, the stated problem, with its six points in the board's order.

<!-- board:evolution -->
| Board step | What the board says | Refined by the literature | What we added or decided | Open, or an extension |
|---|---|---|---|---|
| Input prompt | surf + adsorbates (2) + a general system description; surface and adsorbate with their energies, E_ads from the literature | Get Physics Done · AutoDFT: a Formulate interview that locks scope, conventions and verification targets; compact written settings rules, such as spin for Ni and Co | the interviewer asks five fixed questions and writes PROJECT.md; the three relaxed inputs and A, B as structures are supplied | none |
| (1) Structure retriever | fed by the input prompt: surf + adsorbates (2) and a general system description; surface and adsorbate with their energies | AiiDA common workflows · SSSP · OC20: numerical settings come from a verified protocol, never from the model; OC20's RPBE and PAW if the benchmark is OC20NEB | the three relaxed inputs plus A and B as structures; settings locked in PROJECT.md; a cell wide enough for the pair | Open: one set of gas references for AB, A and B |
| (1\*) MLIP selection, AL prospect | chosen before placement so step 3 can use it; active learning as a prospect | 80-MLIP survey · CatBench · AtomisticSkills: no potential is best everywhere; CatBench classes each failure; ml-mlip-benchmark scores candidates on the system class | benchmark two or three, record why; spin for Ni and Co; the candidates become the committee of step 7 | Extension: active learning: doubt → a few DFT labels → fine-tune → re-run |
| (2) Adsorption sites with pymatgen | Python, with pymatgen | pymatgen · ACAT · spglib: pymatgen's site finder labels no fcc or hcp hollow; ACAT gives labelled sites and the site graph; spglib the symmetry operations | symmetry-complete and counted; fcc and hcp apart; pymatgen kept as the baseline | none |
| (3.1) Least distance before pull-back | estimate the minimum distance at which the dissociated atom is not pulled back | CatTSunami · NEBscape: CatTSunami treats a bond as breaking at 1.25 to 1.63× its length; NEBscape keeps fragments intact by Hookean constraint during sampling | the bond-re-formed check as code, after relaxation, with a logged reason; a pair that fails is never kept | Open: the A–B distance threshold |
| (3.2) Window [1.5 d, 5] Å | d the max vdW length of the bond to break, from the literature | NEBscape · CatTSunami: NEBscape excludes separations above 4.5 Å; CatTSunami samples a 1 to 3 Å shell, 25 pairs, one survivor at random | every symmetry-distinct pair inside the window, ordered by site-graph distance, nearest first, counted: the objective is explicit | Open: d from vacuum or from the adsorbed molecule; 5 Å or NEBscape's 4.5 Å |
| (3.3) Pull force with the MLIP | use the selected MLIP to estimate the pull force on the binding fragment | NEBscape · CatTSunami: neither screens by force; both relax every candidate they generate | one force call per pair before relaxing; a pull towards the other fragment queues the pair last, never drops it | Open: the force threshold |
| (3.4) Agentic critique of the cleavage | criticise and adjust the placement from knowledge of what the cleavage does | AdsMind · AtomWorld · ChemCrow: AdsMind: the LLM returns a site type, code places, 98.8 %; AtomWorld: LLM coordinate edits fail; an LLM judge rates fluent wrong answers well | geometry-critic reads descriptor cards, proposes a site type per fragment, orders the list; never edits coordinates, never overrides a check | Extension: a vision model to predict the sites, only after the geometry benchmark shows an image helps |
| (3.5) Site and orientation, pymatgen | agentic knowledge or a package such as pymatgen, so the binding fragment adsorbs | El Agente Potente · CatTSunami: symmetry-distinct sites and orientations enumerated by code; CatTSunami: 5 placements within 2 Å of the old binding site | code places, the LLM never does: the fragment keeping the binding atom at symmetry-distinct sites near its old site, counted | Open: the binding fragment fixed at its old site, or enumerated |
| (3.6) Or minima hopping with the MLIP | alternatively, minima hopping with the selected MLIP for the binding fragment | NEBscape: minima hopping from symmetry-inequivalent sites with Hookean constraints; 94 % of 304 OC20NEB reactions converge; MIT code | kept as the alternative generator, wrapped, and as the baseline policy our nearest-first choice is scored against | none |
| (4) Initial configurations | output of step 3: all degrees of freedom of the adsorbate × all sites | Burnside · symmetry trap: the count checked by Burnside's lemma; a small random displacement before relaxing, or a symmetric start relaxes to a saddle | every candidate pair relaxed with the chosen potential and the locked settings, displacement first | Open: the displacement amplitude |
| (5) Physics-based and anomaly filtering | physics by script; anomaly by ML and/or script; reasoning questions injected | AdsorbML in fairchem: four anomaly checks exist; the desorbed check treats A\* + B\* as one adsorbate and misses B leaving while A stays | nine checks as code, per fragment, before and after relaxation; the ML variant not taken; every rejection logged with its reason | Extension: an LLM critic reads the card and comments; it never overrides a check |
| (6) SOAP clustering | pick the 3 lowest-energy configurations from each cluster, could be more | NEBscape: deduplicates by SOAP and keeps the first two energy–distance Pareto fronts within 1.2 eV | cluster the survivors; keep the nearest and the lowest per cluster; nearest first overall | Open: how many per cluster |
| (7) Uncertainty estimation | with all relevant models from 1\*; agentic uncertainty and DFT as question marks | MACE committees · uncertainty-toolbox: committee variance is cheap; calibration metrics exist; El Agente Potente saw two MLIPs disagree in sign on a reaction energy | disagreement calibrated on a few DFT or OC20NEB labels; doubt escalates to the human instead of guessing | Extension: agentic uncertainty: N planner runs; DFT single points if D2 allows DFT |
| (8) Rank; user chooses up to 5 | optional: uncertainty estimates and potential issues; critic and knowledge prompts | AdsorbML · CatDT: top-k then DFT is AdsorbML's recipe; CatDT: a raw case bank scores 68 % against 52 to 54 % for distilled lessons | descriptor cards with rank, doubt and verdicts; the choice and reason go to the case bank; only a human promotes a case to a skill | Open: up to five, or fewer |
| Solution | final output, with uncertainty and issues alongside | OC20NEB · AtomisticSkills: OC20NEB product frames as the comparison; every parameter logged beside its output; general-peer-review reads the report | the nearest non-recombining final state with E(FS near), E(FS ∞), rejections, recombination rate, trace; two numbers and two comparisons | Open: the pass criterion against the OC20NEB product frame |
<!-- /board:evolution -->

The board's own open questions, answered as far as we can: step 3 applies to dissociative adsorption only, which is the fixed scope; the models of step 7 are the candidates benchmarked at 1\*; "phys. int." at step 8 is read as the physical issues shown on each card; the vision model feeds step 3 and is an extension. The path from AB\* to the final state and its barrier are out of scope and live in the archive, `archive/docs/adsorption-agent-workflow.md`, sections 12 and 15.

## What is ours and what is not

Ours is the nearest-first objective of 3.2, the logged gate of 3.1 and 5, the pull-force pre-filter of 3.3, and two numbers nobody reports; everything else is a wrapped tool.

- NEBscape is the closest prior work and not an LLM agent: symmetry-inequivalent sites by spglib, two adsorbates placed combinatorially, separations beyond a cut-off excluded, Hookean fragment integrity, energy–distance Pareto selection, SOAP deduplication, a converged OC20NEB benchmark. Its endpoint generator is what step 3.6 wraps and its Pareto choice is the baseline our policy is scored against.
- CatTSunami's AutoFrameDissociation, open source in fairchem, builds the same final state by sampling a shell and picks one survivor at random; its rejected frames are not reported.
- Ours: a nearest-first objective over symmetry-complete, counted pairs, instead of a cut-off and a trade-off or a sampled shell.
- Ours: one validity gate, validity_gate, on both endpoints, run after relaxation, with every rejection logged and its reason kept; a failing state is never paired.
- Ours: two numbers nobody reports, the recombination rate of nearest pairs and the lateral interaction E(FS near) − E(FS ∞), and the three final-state policies compared on the same dissociations.
- Not ours and not claimed: site finding, placement and ML relaxation. Every adsorption agent does steps 2, 3.5 and 4. These are wrapped tools.

## Measured

Two numbers are measured and two comparisons, on an OC20NEB subset starting with \*OH → \*O + \*H on Pt(111).

| Number | Definition | Compared |
|---|---|---|
| Recombination rate | How often the nearest pair bonds back after relaxation | Per system and per distance shell |
| Lateral interaction | E_lat in the equation below, with E(FS ∞) from separate cells | Per system; sign and size |
| Three policies | Nearest-first, ours; energy–distance Pareto, NEBscape; shell sampling, CatTSunami; on the same dissociations: distance, energy, validity, recombination | Per reaction; NEBscape converged 94 % of 304 |
| Final state versus OC20NEB | Our nearest validated final state against the product frame of the released band: A–B distance, energy, validity | Per reaction in the subset |

$$
E_{\mathrm{lat}} = E(\mathrm{FS\,near}) - E(\mathrm{FS}\,\infty),\qquad E(\mathrm{FS}\,\infty) = E(\mathrm{A}^*) + E(\mathrm{B}^*) - E(\mathrm{slab})
$$

Pass criterion, open: team decision: a validated minimum with no A–B bond, at least as near as the OC20NEB product frame, within an energy tolerance still to be set. The subset size and whether any DFT single point runs are also open: team decision.

## Who does what

Tools do every deterministic step; the LLM reads cards, chooses with a stated reason and drafts; the human locks, picks and interprets; skills are the written procedures the LLM follows.

![One card per board step; inside it the human, the LLM agent, the skill and the tool that act; the thick edge does the work](figures/who-does-what.png)

*Figure: who does what · 16 cards, 3 phases, 5 checkpoints, schematic*

Reading the figure: three phases left to right, cards top to bottom in the board's order; inside each card a chip per actor with its concrete name, H human, L LLM agent, S skill, T tool; the chip with the thick edge does the work, the thin ones feed it, dashed chips are extensions, and the pause sign marks a checkpoint where the agent waits. The planner runs every card: it calls each tool by name, reads cards, never writes coordinates, and the hooks enforce that.

<!-- board:who -->
| Step | Human | LLM agent | Skill | Tool | Checkpoint |
|---|---|---|---|---|---|
| Input prompt | supplies the surface, the adsorbates and a description; answers the five interview questions | dft-settings-interviewer: asks the fixed questions, writes PROJECT.md | dft-settings-protocol |  |  |
| (1) Structure retriever | approves the settings lock | final-state-planner: picks the protocol and states why | dft-settings-protocol | dft_settings_lock: the three relaxed inputs, A and B as structures, the cell; settings locked in PROJECT.md | approve settings |
| (1\*) MLIP selection, AL prospect | approves the plan | final-state-planner: records the choice and the reason | ml-mlip-benchmark, reused | mlip_choice: two or three candidates benchmarked on the system class; the chosen one relaxes, all form the committee of step 7 | approve the plan |
| (2) Adsorption sites with pymatgen |  |  |  | site_enumeration: symmetry-inequivalent sites, fcc and hcp apart, counted; pymatgen as the baseline |  |
| (3.1) Least distance before pull-back |  |  | dissociation-final-state | validity_gate, check 10: the A–B bond re-formed after relaxation; runs inside step 5 |  |
| (3.2) Window [1.5 d, 5] Å |  |  | dissociation-final-state | dissociation_final_state: every symmetry-distinct A–B pair in [1.5 d, 5] Å, nearest first by site-graph distance, counted |  |
| (3.3) Pull force with the MLIP |  |  | dissociation-final-state | dissociation_final_state: one MLIP force call per pair; a pull towards the other fragment queues the pair last |  |
| (3.4) Agentic critique of the cleavage |  | geometry-critic: proposes a site type per fragment, orders the list; never overrides a check | dissociation-final-state | geometry-critic reads descriptor_card text, proposes a site type and orientation per fragment, reorders; never edits coordinates |  |
| (3.5) Site and orientation, pymatgen |  |  | dissociation-final-state | adsorbate_placement: A at every symmetry-distinct site near its old site, counted; A fixed is the cheap baseline |  |
| (3.6) Or minima hopping with the MLIP |  |  | dissociation-final-state | dissociation_final_state: NEBscape's endpoint generator with the chosen MLIP, the alternative and the baseline policy |  |
| (4) Initial configurations |  |  | dissociation-final-state | dissociation_final_state: relax every pair with the chosen MLIP and the locked settings, random displacement first; Burnside-counted |  |
| (5) Physics-based and anomaly filtering |  | extension: geometry-critic: comments on cards, never overrides | dissociation-final-state | validity_gate: nine checks per fragment plus two final-state checks, before and after relaxation; verdict into the card; rejections logged |  |
| (6) SOAP clustering |  |  | dissociation-final-state | dissociation_final_state: SOAP clusters of the survivors; the nearest and the lowest per cluster; E(FS near), E(FS ∞) |  |
| (7) Uncertainty estimation | reviews the flagged cases | final-state-planner: stops on doubt and asks; extension: agentic uncertainty: N planner runs; DFT single points if D2 allows | mlip-doubt-calibration | mlip_doubt: committee disagreement across the 1\* candidates, calibrated on DFT or OC20NEB labels; doubt escalates | review flagged cases |
| (8) Rank; user chooses up to 5 | picks up to five on the cards; choice and reason to the case bank | final-state-planner: shows the cards with rank, doubt and verdicts |  | descriptor_card: one card per final state with rank, doubt and verdicts; the human picks; choice and reason to lessons.md | pick up to five final states |
| Solution | interprets the report | final-state-planner: drafts the report | final-state-report; general-peer-review, reused | final_state_report: E(FS near), E(FS ∞), rejections with reasons, recombination rate, decision trace | interpret results |

The actor that does the work in each step, in order: Input prompt human, (1) Structure retriever tool, (1*) MLIP selection, AL prospect tool, (2) Adsorption sites with pymatgen tool, (3.1) Least distance before pull-back tool, (3.2) Window [1.5 d, 5] Å tool, (3.3) Pull force with the MLIP tool, (3.4) Agentic critique of the cleavage llm, (3.5) Site and orientation, pymatgen tool, (3.6) Or minima hopping with the MLIP tool, (4) Initial configurations tool, (5) Physics-based and anomaly filtering tool, (6) SOAP clustering tool, (7) Uncertainty estimation tool, (8) Rank; user chooses up to 5 human, Solution llm.
<!-- /board:who -->

## The architecture in one picture

![The human at both ends, three LLM agents in one box, five skills under them, nine tools in a chain below](figures/architecture.png)

*Figure: architecture · 2 human boxes, 3 agents, 10 skills, 9 tools, schematic*

Reading the figure: the human supplies the inputs and answers the interview on the left and takes the five checkpoints and the interpretation on the right; the three agents in the middle only plan, propose and draft; the skills under them are the procedures they follow; the tools at the bottom, in the order the planner calls them, do every calculation and return descriptor cards. Nothing the agents say is a number they computed.

## Build order

The shortest route to one validated nearest final state runs through eight numbered tasks; the answers in column 0 unblock everything to their right.

1. D1 System and product: AB\*, surface, A\* + B\*; first case \*OH → \*O + \*H on Pt(111). Human decision.
2. T1 Settings lock. Needs D1, D3. Reuses AiiDA common workflows and SSSP.
3. T2 Site and pair enumeration. Needs T1. Reuses spglib and ACAT, pymatgen as the baseline.
4. T4 Validity gate. Needs T3. Reuses fairchem anomaly detection.
5. T6 MLIP choice. Needs D2. Reuses AtomisticSkills ml-mlip-benchmark.
6. P1 Nearest non-recombining final state. Needs T2, T4, T6, D5. Reuses the NEBscape endpoint generator and fairchem AutoFrameDissociation.
7. M2 The \*OH → \*O + \*H final state against the OC20NEB product frame. Needs P1, P5, D3.
8. R1 Release: SKILL.md, MCP tools on AtomisticSkills, benchmark data and traces on Zenodo. Needs M1, M2.

Off-path tasks the path needs, built when it needs them: T3 Placement script, needs T2, reuses ASE; P5 the final-state report, needs P1 and T7, reuses AtomisticSkills logging and general-peer-review; M1 H on Pt(111) end to end, needs T1 to T8. T9, DFT single points on the chosen final states, is an extension that needs T8 and D2.

Decisions D2 compute and codes, D3 benchmark and pass criterion, D4 headline claim and D5 final-state rules are open: team decision. The LLM and human layer, the skills, the Formulate interview run by dft-settings-interviewer, the lessons log and final-state-planner, is written last because it only calls the tools.

## Running the first case

Nothing runs yet; the first run waits on the settings lock and the site enumeration. Only `README.md`, `agent.md`, `CLAUDE.md`, `archive/` and `figures/` exist today. The first case is \*OH → \*O + \*H on Pt(111), decision D1, open: team decision. Before the first command, the Formulate interview run by dft-settings-interviewer writes `PROJECT.md` and the human locks it at the approve-settings checkpoint, and D2 and D3 are decided. The first run then calls dft_settings_lock, T1, and site_enumeration, T2; this section gains the command line when those two tools exist.

## Repository layout

A Claude Code plugin beside AtomisticSkills, with three rules: one kind per file and one folder per kind; calls go one way, agents to skills to tools to the library, never up or sideways; one reading order for a human and one for an agent. The drawing of it is archive/docs/figures/24-repository-layout.png.

```
open-science-hackathon/
├── README.md                     this file: the problem, the simplified and the full pipeline, what is ours, the build order, how to run the first case
├── agent.md                      what a coding agent needs: the exact pipeline, tools, repositories, rules
├── CLAUDE.md                     agent instructions: read agent.md first
├── archive/                      theory, design history, reviews, figure scripts; not needed to code
├── figures/                      the five figures of this page and their SVG sources: the team's plan, the pipeline, its evolution, who does what, the architecture
├── PROJECT.md                    the locked settings and decisions of the current campaign
├── pyproject.toml                one package: the library, the server and the tests
├── .claude-plugin/plugin.json    declares the skills, agents, hooks and the MCP server
├── skills/                       few, human-written, one folder each, under 200 lines each
│   ├── dft-settings-protocol/    pseudopotentials, cutoff, k-mesh, smearing, layers; the lock
│   ├── mlip-doubt-calibration/   committee disagreement against DFT labels; when to escalate
│   ├── dissociation-final-state/ board step 3, points 3.1 to 3.6, and steps 4 to 6
│   ├── final-state-report/       the report: E(FS near), E(FS ∞), rejections, trace
│   └── hpc-dft-jobs/             only with HPC: submission, what custodian handles, what to escalate
├── agents/                       one markdown file per role, one page each
│   ├── final-state-planner.md    decides the next tool call and when to stop
│   ├── dft-settings-interviewer.md runs the Formulate interview; writes PROJECT.md
│   ├── geometry-critic.md        extension: whether a card and its verdicts disagree; never overrides
│   └── dft-job-steward.md        only with HPC: resubmit, adjust or escalate a failed DFT job
├── hooks/hooks.json              blocks coordinate edits; pauses at human checkpoints
├── mcp/                          one server, typed tools, one file per tool
│   ├── server.py                 registers the tools
│   └── tools/                    dft_settings_lock, site_enumeration, adsorbate_placement,
│                                 validity_gate, descriptor_card, mlip_choice, mlip_doubt,
│                                 dissociation_final_state, final_state_report;
│                                 extension: dft_single_points, only if D2 allows DFT
├── finalstate/                   pure Python, no LLM, no MCP: one module per tool, same name
├── tests/                        one test file per tool; Burnside on C4v; the gate on known failures
├── benchmark/                    OC20NEB subset, baselines, scoring scripts, results
├── runs/<campaign>/              PROJECT.md copy, trace.jsonl, cards/, structures/, report.md
└── lessons.md                    the lessons log; recurring entries become skill lines
```

Only `README.md`, `agent.md`, `CLAUDE.md`, `archive/` and `figures/` exist today; the rest is the planned layout.

## Where everything else is

`agent.md` holds what a coding agent needs: the exact pipeline with inputs, outputs, checks and thresholds per tool, the repositories to wrap with their licences, the rules the LLM must obey and the decisions still open. `archive/README.md` indexes the theory and the design history in a table, one row per file: the design document with its figures, the agent context, the long build context, the repository survey, the review of chemistry agents and the writing style.

## Sources

- [NEBscape, npj Computational Materials 2026](https://www.nature.com/articles/s41524-026-02298-1) and its [code, MIT](https://gitlab.mpcdf.mpg.de/hjung/nebscape)
- [CatTSunami and OC20NEB](https://arxiv.org/abs/2405.02078) and the [fairchem code](https://github.com/facebookresearch/fairchem)
- [AdsorbML and OC20-Dense](https://arxiv.org/pdf/2211.16486)
- [OC20 dataset paper, with the DFT settings](https://arxiv.org/pdf/2010.09990)
- [AtomisticSkills](https://arxiv.org/abs/2605.24002) and its [code](https://github.com/learningmatter-mit/AtomisticSkills)
- [Pynta, JCIM 2023, preprint](https://chemrxiv.org/engage/chemrxiv/article-details/647114454f8b1884b755bc5a)
- [TSAgent](https://arxiv.org/abs/2605.14154) and [TSBench](https://arxiv.org/abs/2609.08503)
- [Kempen, Cheula and Andersen: 80 MLIPs benchmarked](https://phys.au.dk/intercat/news-and-events/show/artikel/new-intercat-paper-luuk-kempen-raffaele-cheula-and-mie-andersen)
- [CatKit](https://github.com/SUNCAT-Center/CatKit), [ACAT](https://gitlab.com/asm-dtu/acat), [spglib](https://github.com/spglib/spglib), [pymatgen-core](https://github.com/materialsproject/pymatgen-core), where AdsorbateSiteFinder now lives; the old path in [pymatgen](https://github.com/materialsproject/pymatgen) is a stub
- [AiiDA common workflows, npj Computational Materials 2021](https://www.nature.com/articles/s41524-021-00594-6) and the [SSSP library](https://www.materialscloud.org/discover/sssp)
- [AtomWorld](https://arxiv.org/html/2510.04704): LLM coordinate edits fail, so placement stays a script
- [Robocrystallographer](https://www.cambridge.org/core/journals/mrs-communications/article/robocrystallographer-automated-crystal-structure-text-descriptions-and-analysis/3C201F132450877464B2D0B1B8C4ED01), for the descriptor card
