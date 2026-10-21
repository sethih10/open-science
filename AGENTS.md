# AGENTS.md: what to build, how, and in which order

Audience: a coding agent about to write code in this repository. Read this file first and in full; `CLAUDE.md` points here. It is the operational form of the design history in `docs/design/`. Where this file and the archive differ, the team's board of 21 October 2026 and the fixed scope of section 1 are the authority, then `docs/design/adsorption-agent-workflow.md`; fix whichever disagrees with the board. Conventions: "open: team decision" marks a value the team has not fixed; expose it as a named parameter without a default and ask, never fill it from memory. Numbering is the board's: 1, 1\*, 2, 3 with its points 3.1 to 3.6, 4 to 8, Solution. The archive uses its own row numbers, 4.1 and 6 for the board's step 5, 3.1 to 3.6 for the board's step 3, 14 for the Solution; the table in section 2 gives the correspondence. Where two actors appear in a row, the Owner column does the work. Write code comments and docs as `docs/design/agent-writing-style.md` says.

## 1. Scope and problem

Given a surface with adsorbate AB\* and the desired product A\* + B\*, both fragments adsorbed, determine the final state in which B\* is as close to A\* as possible while the two stay fully dissociated, that is, do not bond back. Scope fixed by the team on 21 October 2026. Not catalysis, not kinetics, not yet the barrier: those are a later phase.

A keeps the binding atom, the team's adsorbate #1; B is the dissociated part, adsorbate #2. The rule: over every symmetry-distinct site pair, minimise the site-graph distance between A\* and B\*, in-plane distance as tiebreaker, subject to the final-state gate of section 3.4. Keep the first few survivors in order. Adjacent fragments can repel, so the nearest is not always the lowest in energy: report both energies.

| Item         | Content                                                                                                     |
|--------------|-------------------------------------------------------------------------------------------------------------|
| Known, supplied | Relaxed surface with its energy; relaxed adsorbate in vacuum with its energy; relaxed initial state AB\* with its energy; the settings all three were relaxed with; E_ads from the literature, human-verified |
| Input prompt | Surface, adsorbates, system description; critic and knowledge prompts as a fixed list; reasoning questions as a written skill |
| Output, now  | Several nearest non-recombining final states in order, up to five picked by the human; E(FS near) and E(FS ∞); rejected pairs with reasons; recombination rate of nearest pairs; ML uncertainty; decision trace |
| Extensions, the board's question marks | Agentic uncertainty, the planner run N times; DFT, single points on the chosen five and labels for calibration; a vision model for placement, only after the geometry benchmark shows an image helps; active learning from 1\*; more than three configurations per cluster, set by the recombination rate; a settings sweep and AB\* enumeration when no relaxed inputs exist |
| Out of scope | The path from AB\* to the final state and its barrier; kinetics; catalysis. Archived: `docs/design/` |
| First case   | \*OH → \*O + \*H on Pt(111), our final state against the product frame of the OC20NEB band; confirm: open: team decision |

The team's five-panel visualisation maps onto the full pipeline as follows.

| Panel | Team's words                                                        | Board steps          |
|-------|---------------------------------------------------------------------|----------------------|
| 1     | Inputs: relaxed initial state, relaxed surface, relaxed adsorbate   | Board 1, 1\*         |
| 3     | Select unit cell and find unique adsorption sites                   | Board 2, 3.5; the cell is chosen in step 1 |
| 4     | Minimal distance before the molecule pulls the atoms back, "how far?" | Board 3.1, 3.2, 3.3, 4, 5 |
| 5     | Most favourable configuration for adsorbent #1 and adsorbent #2     | Board 3.4, 3.6, 6, 7, 8 |
| 2     | Output: dissociated final state                                     | Solution             |

Quantities the code computes:

- Separated product: `E(FS ∞) = E(A*) + E(B*) − E(slab)`, each term with the chosen MLIP in its own cell with the locked settings.
- Lateral interaction: `E(FS near) − E(FS ∞)`.
- Adsorption energy: `E_ads = E(slab+A) − E(slab) − E(A)`, E(A) the locked gas-phase reference.

## 2. The exact pipeline

The board's order and numbering, one row per step; tools do every deterministic step, the LLM chooses with a stated reason and drafts, humans approve, pick and interpret, skills hold the procedures. The plan follows NEBscape's shape; NEBscape is the closest prior work and CatTSunami is secondary. The six points of step 3 run in the board's order 3.1 → 3.2 → 3.3 → 3.4 → 3.5 or 3.6 as a design; in code 3.5 places first, 3.2 lists the pairs, 3.3 screens them, 3.4 orders the list, 3.6 is the alternative generator, and 3.1 is applied as a check inside step 5.

<!-- board:pipeline -->
| Step | Owner | What it does | Tools | Checkpoint |
|---|---|---|---|---|
| Input prompt | Human | The human supplies the surface, the adsorbates and a description and answers the five interview questions; the computational-chemist writes PROJECT.md; the literature-reader fetches E_ads and d with sources | `literature_lookup` |  |
| (1) Structure retriever | Tool | Takes the three supplied relaxed structures with their energies and A and B as structures; selects the surface cell so periodic images stay 10 Å apart; locks the settings the inputs were relaxed with, plus the human's physics choices, in PROJECT.md; `dft-settings-protocol` holds the protocol | `structure_retrieval`, `calculation_protocol` | approve settings |
| (1\*) MLIP selection, AL prospect | Tool | Benchmarks two or three candidate potentials on the system class before any placement; the chosen one relaxes every candidate; all candidates form the committee of step 7; spin for Ni and Co; active learning is an extension | `mlip_selection` ; extension: `active_learning` | approve the plan |
| (2) Adsorption sites with pymatgen | Tool | Symmetry-inequivalent sites of the selected cell, fcc and hcp hollows apart, counted; pymatgen's finder as the baseline | `site_enumeration` |  |
| (3.1) Least distance before pull-back | Tool | The bond-re-formed check as code, applied inside step 5 after relaxation; a pair that fails is never kept; the A–B threshold open: team decision | `anomaly_filter` |  |
| (3.2) Window [1.5 d, 5] Å | Tool | B sites around each A within [1.5 d, 5] Å, d the length of the bond to break; every symmetry-distinct pair, ordered by site-graph distance with in-plane tiebreak, counted | `pair_enumeration`, `literature_lookup` |  |
| (3.3) Pull force with the MLIP | Tool | One MLIP force call per pair; the force component on each fragment along the A–B axis; a pull towards the other fragment above the threshold queues the pair last, never drops it | `pull_force_screen` |  |
| (3.4) Agentic critique of the cleavage | LLM | `surface-chemist` reads the descriptor cards, proposes a site type and orientation per fragment, may reorder or add candidates; never edits coordinates, never removes a pair, never overrides a check | `descriptor_card` |  |
| (3.5) Site and orientation, pymatgen | Tool | The fragment keeping the binding atom, A, placed at every symmetry-distinct site near its old site, counted; A fixed at its old site is the cheap baseline | `adsorbate_placement` |  |
| (3.6) Or minima hopping with the MLIP | Tool | NEBscape's endpoint generator with the chosen MLIP as the alternative generator and the baseline policy | `minima_hopping` |  |
| (4) Initial configurations | Tool | Every pair relaxed with the chosen potential and the locked settings; orientations under the site's stabiliser, Burnside-counted; random displacement first | `relaxation`, `adsorbate_placement` |  |
| (5) Physics-based and anomaly filtering | Tool | The gate of section 3.4 on every structure before and after relaxation: nine checks per fragment plus the two final-state checks, 3.1 among them as the bond-re-formed check; verdict into the card; a failing pair is never kept; the ML variant not taken; an LLM critic comments only, extension | `anomaly_filter`, `descriptor_card` |  |
| (6) SOAP clustering | Tool | Cluster the survivors by SOAP as NEBscape does; keep the lowest per cluster as the board says and the nearest, our objective; nearest first overall; E(A\*), E(B\*), E(FS ∞) with the chosen MLIP | `soap_clustering` |  |
| (7) Uncertainty estimation | Tool | Disagreement across the committee of 1\*, calibrated on a few DFT labels if available, else OC20NEB labels; doubt escalates instead of guessing; `mlip-doubt-calibration` says when | `uncertainty_estimation` ; extension: `dft_single_points` | review flagged cases |
| (8) Rank; user chooses up to 5 | Human | Cards with rank, doubt and verdicts; the human picks; the choice and its reason go to the case bank | `ranking`, `descriptor_card` | pick up to five final states |
| Solution | LLM | Drafts the report: both energies, lateral interaction, rejections with reasons, recombination rate, doubt, decision trace; `final-state-report` holds the format; the human interprets | `reference_energies`, `report` ; extension: `dft_single_points` | interpret results |
<!-- /board:pipeline -->

Human checkpoints, where the agent stops and waits: approve settings; approve the plan; review flagged cases; pick up to five final states; interpret results. Autonomy level and which checkpoints a Balanced mode skips: open: team decision.

## 3. The tools

Every tool is defined once, in `src/fragplace/registry/tools.py`, as a ToolSpec: purpose, board steps, inputs, outputs, checks, thresholds, the modules it wraps, what it logs, status. One module per category under `src/fragplace/tools/`, a function per tool with the spec's parameter names; `src/fragplace/mcp/server.py` builds the MCP tool list from the registry and `fragplace-server --list` prints it; the tests hold the three in step. Thresholds marked "open: team decision" are parameters without defaults and must be asked for. Every tool runs under `fragplace.runtime.journal.traced`, so each call lands in `runs/<campaign>/trace.jsonl`; every structure a tool writes goes through `descriptor_card` before an agent sees it. The block below is generated by `docs/figures/src/board_tables.py`; edit the registry, not this text.

<!-- registry:tools -->
### 3.1 `literature_lookup`, board steps prompt, 3.2, core

Published E_ads values with functional and site, and the length d of the bond to break, for a human to verify; one or two values, never from the model's memory.

| Field | Content |
|---|---|
| Inputs | system: str, metal, facet, adsorbate; quantity: E_ads \| bond_length_d \| site; sources: list of source names |
| Outputs | values: list[LiteratureValue], verified_by_human False until the checkpoint |
| Checks | every value carries a DOI or URL; at most two values per quantity |
| Wraps | paper-qa2 for papers; Materials Project API through the LLaMP pattern; Catalysis-Hub |
| Logs | query; every value with its source |
| Module | `src/fragplace/tools/literature.py`, function `literature_lookup(system, quantity, sources)` |

### 3.2 `structure_retrieval`, board step 1, core

Take the three supplied relaxed structures with their energies, cleave the named bond to make A and B, and select the surface cell so periodic images stay apart.

| Field | Content |
|---|---|
| Inputs | slab: StructureRef; adsorbate_vacuum: StructureRef; initial_state: StructureRef; bond_to_break: tuple[int, int], atom indices in AB |
| Outputs | fragment_A: StructureRef; fragment_B: StructureRef; cell_repeat: tuple[int, int]; structures: list[StructureRef] |
| Checks | the three inputs share one settings set, check 8; images at least min_image_distance_A apart |
| Thresholds | min_image_distance_A: 10 |
| Wraps | ase.io; pymatgen.core |
| Logs | input hashes; the cell and why |
| Module | `src/fragplace/tools/structure.py`, function `structure_retrieval(slab, adsorbate_vacuum, initial_state, bond_to_break)` |

### 3.3 `calculation_protocol`, board step 1, core

Lock the numerical and physical settings in PROJECT.md from the inputs' settings, the human's physics choices and a verified protocol; never from the model's memory.

| Field | Content |
|---|---|
| Inputs | settings_from_inputs: Settings, as read from the relaxed inputs; physics_choices: dict from the human: functional, dispersion, spin, U; protocol: aiida_common_workflows \| sssp \| oc20; protocol_reason: str, stated by the computational chemist |
| Outputs | settings: Settings with locked False until the human approves |
| Checks | cutoff, k-mesh, smearing, layers from the protocol table of agent.md section 3; if OC20NEB is the benchmark, RPBE and PAW as OC20 |
| Thresholds | convergence_target_meV: open: team decision; gas_references: open: team decision |
| Wraps | aiida_common_workflows.workflows.relax.CommonRelaxWorkChain protocols; SSSP; pymatgen.io.vasp.sets.MPRelaxSet |
| Logs | protocol and reason; every setting and its origin |
| Module | `src/fragplace/tools/structure.py`, function `calculation_protocol(settings_from_inputs, physics_choices, protocol, protocol_reason)` |

### 3.4 `mlip_selection`, board step 1*, core

Benchmark two or three candidate potentials on the system class and choose one; every candidate becomes the committee of uncertainty_estimation.

| Field | Content |
|---|---|
| Inputs | candidates: list[str], calculator names; system_class: str, metal \| oxide \| organometallic; labels: list[StructureRef] with DFT energies, or OC20NEB |
| Outputs | chosen: str; committee: list[str]; benchmark: dict name -> error_eV and anomaly classes |
| Checks | spin initialised on Co and Ni; cross-family comparison on E_ads only, never total energies |
| Thresholds | candidates: open: team decision; label_count: open: team decision |
| Wraps | catbench.adsorption.AdsorptionCalculation; catbench.adsorption.AdsorptionAnalysis; AtomisticSkills ml-mlip-benchmark; fairchem.core.FAIRChemCalculator; mace.calculators.MACECalculator; chgnet |
| Logs | benchmark results; the choice and the specialist's reason |
| Module | `src/fragplace/tools/uncertainty.py`, function `mlip_selection(candidates, system_class, labels)` |

### 3.5 `site_enumeration`, board step 2, core

Every symmetry-inequivalent site of the slab, fcc and hcp hollows apart, with the site graph and a Burnside-checked count; pymatgen's finder as the baseline.

| Field | Content |
|---|---|
| Inputs | slab: StructureRef; cell_repeat: tuple[int, int] |
| Outputs | sites: SiteEnumeration |
| Checks | Burnside count equals the explicit list; C4v square cell with two identical adsorbates gives 2 |
| Wraps | spglib.get_symmetry_dataset; acat.adsorption_sites.SlabAdsorptionSites; acat.adsorption_sites.SlabAdsorptionSites.get_graph; pymatgen.core.adsorption.AdsorbateSiteFinder as baseline |
| Logs | symmetry group; every site; count and check |
| Module | `src/fragplace/tools/sites.py`, function `site_enumeration(slab, cell_repeat)` |

### 3.6 `adsorbate_placement`, board steps 3.5, 4, core

Place fragment A at every symmetry-distinct site near its old site and B at a given site, by script; orientations under the site's stabiliser; a random displacement before relaxation.

| Field | Content |
|---|---|
| Inputs | sites: SiteEnumeration; fragment: StructureRef; site_index: int; orientation: int; height_A: float; displacement_amplitude_A: float |
| Outputs | candidate: Candidate |
| Checks | start 2 to 3 Å above the site; the LLM never places atoms |
| Thresholds | displacement_amplitude_A: open: team decision; fragment_A_fixed_at_old_site: open: team decision |
| Wraps | ase.build.add_adsorbate; fairchem.data.oc.core.AdsorbateSlabConfig as the baseline |
| Logs | site, orientation, height, displacement and random draw |
| Module | `src/fragplace/tools/placement.py`, function `adsorbate_placement(sites, fragment, site_index, orientation, height_A, displacement_amplitude_A)` |

### 3.7 `pair_enumeration`, board step 3.2, core

Every symmetry-distinct (A site, B site) pair inside the window [1.5 d, 5] Å, ordered by site-graph distance with in-plane distance as tiebreaker, nearest first, counted.

| Field | Content |
|---|---|
| Inputs | sites: SiteEnumeration; d_bond_A: float, from literature_lookup or the adsorbate structure; window: tuple[float, float] in units of d and Å |
| Outputs | pairs: list[Pair], nearest first; count: int |
| Checks | no pair outside the window; symmetry duplicates removed and counted |
| Thresholds | d_definition: open: team decision: vacuum or adsorbed bond length; upper_bound_A: open: team decision: 5 or NEBscape's 4.5 |
| Wraps | acat.adsorption_sites.SlabAdsorptionSites.get_neighbor_site_list; acat.build.adlayer.SystematicPatternGenerator |
| Logs | every pair with both distances; the count |
| Module | `src/fragplace/tools/sites.py`, function `pair_enumeration(sites, d_bond_A, window)` |

### 3.8 `pull_force_screen`, board step 3.3, core

One MLIP force call per pair; the force on B along the A–B axis; a pull towards A above the threshold queues the pair last, never drops it.

| Field | Content |
|---|---|
| Inputs | candidates: list[Candidate]; calculator: str |
| Outputs | screens: list[ForceScreen], queue order |
| Checks | one force call, no relaxation |
| Thresholds | threshold_eV_per_A: open: team decision |
| Wraps | fragplace.calculators |
| Logs | force per pair; queue order |
| Module | `src/fragplace/tools/screening.py`, function `pull_force_screen(candidates, calculator)` |

### 3.9 `minima_hopping`, board step 3.6, core

NEBscape's endpoint generator with the chosen potential as the alternative generator and the baseline policy our nearest-first choice is scored against.

| Field | Content |
|---|---|
| Inputs | slab: StructureRef; fragments: tuple[StructureRef, StructureRef]; calculator: str; n_hops: int |
| Outputs | candidates: list[Candidate] with generator minima_hopping |
| Checks | Hookean constraints keep A and B intact during hopping, as NEBscape |
| Wraps | nebscape endpoint generator, MIT; ase.optimize.minimahopping.MinimaHopping |
| Logs | hops; minima found |
| Module | `src/fragplace/tools/placement.py`, function `minima_hopping(slab, fragments, calculator, n_hops)` |

### 3.10 `relaxation`, board step 4, core

Relax every candidate with the chosen potential and the locked settings, random displacement first; cached by content hash.

| Field | Content |
|---|---|
| Inputs | candidates: list[Candidate]; calculator: str; fmax_eV_per_A: float; max_steps: int |
| Outputs | results: list[RelaxationResult] |
| Checks | same settings as the initial state, check 8 |
| Wraps | ase.optimize; fragplace.calculators; fragplace.cache |
| Logs | steps, fmax, convergence, cache hit per candidate |
| Module | `src/fragplace/tools/relaxation.py`, function `relaxation(candidates, calculator, fmax_eV_per_A, max_steps)` |

### 3.11 `anomaly_filter`, board steps 5, 3.1, core

The nine checks of the gate per fragment, before and after relaxation, plus the two final-state checks: the A–B bond re-formed, and the periodic image; verdict into the card; a failing candidate is never kept.

| Field | Content |
|---|---|
| Inputs | candidate: Candidate; start: Candidate; slab: StructureRef; settings: Settings; prior_E_ads_eV: float \| None; frequencies_cm: list[float] \| None |
| Outputs | gate: GateResult |
| Checks | 1 desorbed per fragment; 2 migrated; 3 dissociated within a fragment; 4 reconstructed; 5 not a minimum; 6 magnetism collapsed; 7 outside expected range; 8 settings mismatch; 9 intercalated; 10 A–B bond re-formed; 11 periodic image |
| Thresholds | desorbed_A: 3; AB_bond_reformed_A: open: team decision; migrated: open: team decision; dissociated: open: team decision; reconstructed: open: team decision; imaginary_noise_cm: open: team decision; expected_range_width_eV: open: team decision; magnetism_collapsed: open: team decision; intercalated: open: team decision |
| Wraps | fairchem.data.oc.utils.DetectTrajAnomaly; ase.vibrations.Vibrations; acat.adsorbate_coverage.SlabAdsorbateCoverage; CatBench anomaly classes as names |
| Logs | every verdict with its measured value; every rejection with its reason |
| Module | `src/fragplace/tools/filtering.py`, function `anomaly_filter(candidate, start, slab, settings, prior_E_ads_eV, frequencies_cm)` |

### 3.12 `soap_clustering`, board step 6, core

Cluster the survivors by SOAP; keep the nearest and the lowest per cluster; nearest first overall.

| Field | Content |
|---|---|
| Inputs | survivors: list[Candidate]; energies: list[RelaxationResult]; pairs: list[Pair] |
| Outputs | clusters: list[Cluster]; kept: list[str] |
| Checks | nearest-first ordering preserved across clusters |
| Thresholds | per_cluster: open: team decision: the board says 3, could be more |
| Wraps | dscribe.descriptors.SOAP; sklearn.cluster |
| Logs | clusters and representatives |
| Module | `src/fragplace/tools/clustering.py`, function `soap_clustering(survivors, energies, pairs)` |

### 3.13 `uncertainty_estimation`, board step 7, core

Committee disagreement across the candidates benchmarked at 1*, calibrated on a few DFT or OC20NEB labels; a doubt flag that escalates to the human instead of guessing.

| Field | Content |
|---|---|
| Inputs | candidates: list[Candidate]; committee: list[str]; labels: list[StructureRef] \| None |
| Outputs | flags: list[DoubtFlag] |
| Checks | disagreement compared on E_ads, never on total energies across families; magnetic metals always flagged; unseen chemistry always flagged |
| Thresholds | escalation_threshold_eV: open: team decision; label_count: open: team decision |
| Wraps | mace.calculators.MACECalculator with model_paths; uncertainty_toolbox.metrics.get_all_metrics; AtomisticSkills ml-committee-uncertainty |
| Logs | labels used; spread against label error; every flag and escalation |
| Module | `src/fragplace/tools/uncertainty.py`, function `uncertainty_estimation(candidates, committee, labels)` |

### 3.14 `descriptor_card`, board steps 3.4, 5, 8, core

Render a structure as the text card the LLM reads, with site, distances, verdicts and the A–B distance; a PNG beside it as a second look.

| Field | Content |
|---|---|
| Inputs | candidate: Candidate; gate: GateResult \| None; sites: SiteEnumeration |
| Outputs | card: DescriptorCard |
| Checks | two configurations never share a card: distances and site labels always present |
| Wraps | pymatgen; robocrystallographer pattern; ase.io.write png |
| Logs | the card beside the structure |
| Module | `src/fragplace/tools/filtering.py`, function `descriptor_card(candidate, gate, sites)` |

### 3.15 `ranking`, board step 8, core

Rank the kept final states nearest first, then by energy, with doubt and verdicts on each card, for the human to pick up to five; record the choice and reason in the case bank.

| Field | Content |
|---|---|
| Inputs | kept: list[str]; cards: list[DescriptorCard]; flags: list[DoubtFlag]; pairs: list[Pair] |
| Outputs | ranked: list[RankedCandidate] |
| Checks | the human picks; the tool never drops a candidate |
| Thresholds | shortlist_size: open: team decision: up to five, or fewer |
| Logs | the order shown; the human's choice and reason, to lessons.md |
| Module | `src/fragplace/tools/clustering.py`, function `ranking(kept, cards, flags, pairs)` |

### 3.16 `reference_energies`, board step solution, core

E(A*), E(B*) and E(slab) each in its own cell with the chosen potential and the locked settings, for E(FS ∞) and the lateral interaction.

| Field | Content |
|---|---|
| Inputs | slab: StructureRef; fragments: tuple[StructureRef, StructureRef]; calculator: str |
| Outputs | E_slab_eV: float; E_A_eV: float; E_B_eV: float; E_inf_eV: float |
| Checks | same settings as every candidate, check 8 |
| Wraps | fragplace.calculators |
| Logs | the three energies |
| Module | `src/fragplace/tools/relaxation.py`, function `reference_energies(slab, fragments, calculator)` |

### 3.17 `report`, board step solution, core

One auditable record per campaign: final states with both energies, rejections with reasons, the recombination rate, doubt, the OC20NEB comparison, cost and the decision trace.

| Field | Content |
|---|---|
| Inputs | campaign: str; final_states: list[FinalState]; rejected: list[GateResult]; flags: list[DoubtFlag]; comparison: dict |
| Outputs | report: Report, written to runs/<campaign>/report.md and report.json |
| Checks | every number traces to a tool output; the scientific critic reads the draft with the general-peer-review skill |
| Wraps | AtomisticSkills hyperparameter logging pattern |
| Logs | the full trace path |
| Module | `src/fragplace/tools/report.py`, function `report(campaign, final_states, rejected, flags, comparison)` |

### 3.18 `dft_single_points`, board steps 7, solution, extension

DFT single points on the chosen final states and the separated fragments at the locked settings; only with a DFT code and compute.

| Field | Content |
|---|---|
| Inputs | structures: list[StructureRef]; settings: Settings; backend: local \| slurm |
| Outputs | energies: dict candidate_id -> eV; failures: list[str] |
| Checks | settings mismatch against PROJECT.md before submission; custodian handlers before any agent diagnosis; retries capped at three by the job tracker |
| Wraps | ase.calculators; atomate2 through the AtomisticSkills MCP server; custodian.vasp.handlers; fragplace.compute.tracker |
| Logs | force calls, failures, every resubmission |
| Module | `src/fragplace/tools/dft.py`, function `dft_single_points(structures, settings, backend)` |

### 3.19 `active_learning`, board step 1*, extension

High doubt to a few DFT labels to a fine-tuned potential to a re-run of steps 4 to 8.

| Field | Content |
|---|---|
| Inputs | flags: list[DoubtFlag]; labels: list[StructureRef]; base_model: str |
| Outputs | fine_tuned: str |
| Wraps | AtomisticSkills ml-mace-finetune |
| Logs | labels used; model path |
| Module | `src/fragplace/tools/uncertainty.py`, function `active_learning(flags, labels, base_model)` |
<!-- /registry:tools -->

### The settings `calculation_protocol` applies

| Setting            | Rule                                                                                   | Value in the docs                                              |
|--------------------|----------------------------------------------------------------------------------------|----------------------------------------------------------------|
| Pseudopotentials   | Library recommendation; never mix families or versions; same dataset per element everywhere | VASP recommended PAW, `_pv` or `_sv` where semicore states matter; QE: SSSP efficiency for screening, precision for final numbers |
| Cutoff             | Start at the largest ENMAX in the cell, × 1.3 if the cell volume relaxes; converge E_ads | OC20: 350 eV; Materials Project: 520 eV                       |
| k-mesh             | Γ-centred on hexagonal cells; one k-point along vacuum; same mesh for slab and slab+A   | 0.2 to 0.3 Å⁻¹ in-plane; OC20: 40 / in-plane cell length      |
| Smearing           | Methfessel–Paxton or Marzari–Vanderbilt; report E extrapolated to σ → 0                 | σ = 0.1 to 0.2 eV                                              |
| Layers             | Add until E_ads stops changing; fix the bottom layers                                   | ≥ 4 for close-packed metals; fixed count open: team decision   |
| Vacuum; dipole     | Converge the vacuum; dipole correction on when only one face is covered                | ≥ 12 to 15 Å                                                   |
| Cell width         | The pair never sees its periodic image                                                 | Images ≥ 10 Å apart; which atoms are measured: open: team decision |
| Target; force, SCF | Cheapest setting inside the target; force and SCF convention from `skills/dft-settings-protocol/SKILL.md` | ±10 meV in the protocol, 10 or 25 meV open: team decision; 0.02 to 0.03 eV/Å; 1e-5 to 1e-6 eV |
| Benchmark match    | If OC20NEB is the ground truth, the lock matches OC20                                  | RPBE and PAW; open: team decision                              |

H on Pt(111) is the first sweep when a sweep runs; the test adsorbate for the \*OH case is open: team decision.

H on Pt(111) is the first sweep when a sweep runs; the test adsorbate for the \*OH case is open: team decision.

### The eleven checks `anomaly_filter` applies

| #  | Check                   | Fails when                                                              | Threshold in the docs                           |
|----|-------------------------|-------------------------------------------------------------------------|-------------------------------------------------|
| 1  | Desorbed                | Adsorbate centre too far above the surface plane; per fragment for a pair | > 3 Å; surface-plane definition open          |
| 2  | Migrated                | Adsorbate ends on another site than the one enumerated                  | Site label differs; distance open               |
| 3  | Dissociated             | An intramolecular bond stretched beyond its breaking threshold; within A and within B for a pair | Open: team decision     |
| 4  | Reconstructed           | Surface atoms displaced from their clean-slab positions                 | Open: team decision                             |
| 5  | Not a minimum           | One or more imaginary vibrational modes                                 | Zero allowed; noise cutoff in cm⁻¹ open         |
| 6  | Magnetism collapsed     | Total moment of a magnetic slab vanishes on adsorption                  | Open: team decision                             |
| 7  | Outside expected range  | E_ads far from the prior for this adsorbate and metal                   | H on Pt(111) near −0.5 eV; width open           |
| 8  | Settings mismatch       | Slab and slab+A differ in cutoff, mesh, smearing or pseudopotentials    | Exact equality                                  |
| 9  | Intercalated            | An adsorbate atom below the top surface layer                           | Open: team decision                             |
| 10 | Bond re-formed, FS only | A and B bonded again after relaxation                                   | A–B distance threshold open: team decision      |
| 11 | Periodic image, FS only | The pair interacts with its periodic images                             | Images ≥ 10 Å apart                             |

Checks 1 to 9 run on every structure; the final-state gate adds 10 and 11. Which checks run before relaxation, and whether frequencies come from the MLIP or from DFT: open: team decision.

Checks 1 to 9 run on every structure; the final-state gate adds 10 and 11. `DetectTrajAnomaly` treats A\* + B\* as one adsorbate and passes B leaving while A stays, so check 1 runs per fragment; `is_adsorbate_dissociated` flags any connectivity change, so it also catches check 10 Which checks run before relaxation, and whether frequencies come from the MLIP or from DFT: open: team decision.

### Human checkpoints and the case bank

Stop where a wrong choice silently corrupts every later number; show the evidence; record the choice and its reason. It is a procedure the planner follows and `fragplace.runtime.policy` enforces, not a tool; the record is `fragplace.runtime.checkpoints`, the case bank `fragplace.memory.casebank`.

| Field  | Content                                                                                                              |
|--------|----------------------------------------------------------------------------------------------------------------------|
| Inputs | Descriptor cards, rank, uncertainty, verdicts, doubt evidence                                                        |
| Outputs | The human's choice and reason; a lessons-log entry in `lessons.md`, section 4.3                                     |
| Wraps  | The AtomisticSkills rule that a plan is reviewed before execution; the rest is ours                                   |
| Logs   | Every checkpoint: what was shown, the choice, the reason                                                             |
| Autonomy | Supervised or Balanced, as in Get Physics Done; which checkpoints Balanced skips: open: team decision              |

| Checkpoint                | Shown                                     | Recorded                                |
|---------------------------|-------------------------------------------|-----------------------------------------|
| Approve settings          | PROJECT.md with the settings as supplied  | Approval; the lock                      |
| Approve the plan          | The plan                                  | Approval                                |
| Review flagged cases      | Cards that failed a check; doubt evidence | Decision and reason, to the lessons log |
| Pick up to five final states | Cards, rank, uncertainty               | Choice and reason, to the lessons log   |
| Interpret results         | The report                                | Interpretation                          |

## 4. Data records

The records are the Pydantic classes of `src/fragplace/schemas/records.py`; a tool takes and returns them and nothing else, so every number in the trace has a field name and a unit. The table is generated from the code.

<!-- records:models -->
| Record | Fields |
|---|---|
| `Candidate` | id: str, structure: fragplace.schemas.records.StructureRef, site_A: Optional[int], site_B: Optional[int], orientation: Optional[int], displacement_amplitude_A: float, generator: str, parent: Optional[str] |
| `Case` | system: str, card: str, correction: str, reason: str, source_checkpoint: str, promoted_to: Optional[str], when: datetime.datetime |
| `CheckVerdict` | check_id: int, name: str, passed: bool, measured: Optional[float], threshold: Optional[str], reason: str, fragment: Optional[str] |
| `Cluster` | id: int, members: List[str], nearest: str, lowest: str |
| `DescriptorCard` | candidate_id: str, composition: str, cell: str, facet: str, layers: int, vacuum_A: float, fixed_layers: int, site_label: str, point_group: str, coordination: int, height_A: float, nn_distances_A: List[float], tilt_deg: Optional[float], displacement_from_start: str, magnetic_moment: Optional[float], verdicts: List[fragplace.schemas.records.CheckVerdict], AB_distance_A: Optional[float], site_graph_distance: Optional[int], image_path: Optional[str] |
| `DoubtFlag` | candidate_id: str, committee_spread_eV: float, calibrated_error_eV: Optional[float], trigger: str, escalate: bool |
| `FinalState` | candidate_id: str, E_near_eV: float, E_inf_eV: float, lateral_interaction_eV: float, AB_distance_A: float, site_graph_distance: int, recombined: bool |
| `ForceScreen` | candidate_id: str, force_on_B_along_AB_eV_per_A: float, flagged: bool, threshold_eV_per_A: Optional[float], queue_position: int |
| `GasReference` | species: str, energy_eV: float, correction_eV: float, note: str |
| `GateResult` | candidate_id: str, verdicts: List[fragplace.schemas.records.CheckVerdict], passed: bool, stage: str |
| `HumanChoice` | checkpoint: str, chosen: List[str], reason: str, who: str, when: datetime.datetime |
| `LiteratureValue` | quantity: str, value: float, unit: str, system: str, functional: Optional[str], site: Optional[str], source: str, verified_by_human: bool |
| `Pair` | candidate_id: str, site_A: int, site_B: int, site_graph_distance: int, in_plane_distance_A: float, within_window: bool, window_A: Tuple[float, float], d_bond_A: float |
| `RankedCandidate` | candidate_id: str, rank: int, site_graph_distance: int, energy_eV: float, doubt: Optional[fragplace.schemas.records.DoubtFlag], reason: str |
| `RelaxationResult` | candidate_id: str, energy_eV: float, fmax_eV_per_A: float, steps: int, converged: bool, trajectory_path: Optional[str], calculator: str, cache_hit: bool |
| `Report` | campaign: str, final_states: List[fragplace.schemas.records.FinalState], rejected: List[fragplace.schemas.records.GateResult], recombination_rate: float, recombination_rate_by_shell: Dict[int, float], doubt: List[fragplace.schemas.records.DoubtFlag], comparison_oc20neb: Dict[str, float], cost: Dict[str, float], trace_path: str, settings_hash: str |
| `Settings` | metal: str, facet: str, adsorbate: str, product: Tuple[str, str], functional: str, dispersion: Optional[str], spin_polarised: bool, initial_moments: Dict[str, float], hubbard_u: Dict[str, float], pseudopotential_family: Optional[str], pseudopotential_version: Optional[str], cutoff_eV: Optional[float], kmesh: Optional[Tuple[int, int, int]], smearing: Optional[str], sigma_eV: Optional[float], layers: Optional[int], fixed_layers: Optional[int], vacuum_A: Optional[float], dipole_correction: bool, cell_repeat: Optional[Tuple[int, int]], min_image_distance_A: float, force_threshold_eV_per_A: float, scf_threshold_eV: float, convergence_target_meV: Optional[float], gas_references: List[fragplace.schemas.records.GasReference], protocol: Optional[str], protocol_reason: Optional[str], mlip: Optional[str], mlip_committee: List[str], locked: bool, approved_by: Optional[str], approved_at: Optional[datetime.datetime] |
| `Site` | index: int, label: str, point_group: str, coordination: int, atom_beneath: Optional[str], position: Tuple[float, float, float] |
| `SiteEnumeration` | sites: List[fragplace.schemas.records.Site], count: int, burnside_count: int, symmetry_group: str, edges: List[Tuple[int, int]], baseline_count: Optional[int] |
| `StructureRef` | path: str, format: str, role: <enum Role, energy_eV: Optional[float], settings_hash: Optional[str], calculator: Optional[str] |
| `TraceEvent` | when: datetime.datetime, step: str, tool: str, actor: str, inputs_hash: str, outputs_ref: str, message: str |
<!-- /records:models -->

The five human-facing files below hold these records; their on-disk formats are fixed by `fragplace.runtime.project` (PROJECT.md, a Markdown page with one ```yaml block), `fragplace.runtime.journal` (trace.jsonl), `fragplace.memory.casebank` (lessons.md, one ```json block per case) and `report` (report.md with report.json).

### 4.1 PROJECT.md

| Field                                                              | Set by     | Note                                               |
|--------------------------------------------------------------------|------------|----------------------------------------------------|
| Metal, facet, adsorbate AB                                         | Human      |                                                    |
| Product A\* + B\*, with A and B as structures                      | Human      | Missing in the docs; must be added                  |
| Functional; dispersion; spin and initial moments; Hubbard U        | Human      | PBE, RPBE or BEEF-vdW; D3 or vdW-DF; Fe, Co, Ni spin-polarised; same U for every intermediate |
| Gas-phase references for AB, A and B, with corrections             | Human      | One set for IS, FS and band                        |
| Slab model: facet, layers, fixed layers                            | Human      | As supplied; layers converged by Tool only when the sweep extension runs |
| Surface cell for pairs                                             | Tool       | Images ≥ 10 Å apart                                |
| Pseudopotential family and version; cutoff; k-mesh; smearing and σ; vacuum; dipole correction | Tool | As supplied with the inputs; from the sweep only when it runs |
| Force and SCF thresholds                                           | `dft-settings-protocol` |                                       |
| Convergence target and sweep data; protocol chosen and the reason  | Tool; LLM  | Sweep data only when the sweep ran                 |
| Interview answers to the five questions; scope, assumptions, notation, verification targets, autonomy level | Human | Get Physics Done pattern; each answer becomes a check, a prior or a skill line |
| One or two published E_ads with functional and preferred site      | Literature | A human verifies                                   |
| Lock and approval; MLIP chosen and the reason; the committee       | Human; LLM | At the approve-settings checkpoint; whether the MLIP lives here: open: team decision |

### 4.2 Descriptor card

| Field                                                                   | Example line in the docs                                           |
|-------------------------------------------------------------------------|--------------------------------------------------------------------|
| Composition and cell; facet, layers, vacuum, fixed layers               |                                                                    |
| Site label and point group; coordination number                         | "fcc hollow, C3v, coordination 3"; "hcp hollow, C3v, atom beneath" |
| Height above the surface plane; nearest-neighbour distances; tilt angle |                                                                    |
| Displacement from the start                                             | "migrated: fcc hollow to bridge, 1.4 Å"                            |
| Total magnetic moment                                                   |                                                                    |
| Validity verdicts                                                       | "one imaginary mode, 120i cm⁻¹"                                    |
| Pair fields: A–B distance, site-graph distance                          | Open: team decision                                                |

### 4.3 Lessons-log entry

The lessons log, `lessons.md`, is the case bank: one file, two names in the archive. It stores raw cases, not distilled lessons, because a raw case bank scores highest. The `solution-planner` retrieves cases by system and failure; only a human promotes a case into a skill line, a check or a prior. Seed: CO on Pt-group metals, Ni and Co magnetism, the symmetry trap.

| Memory form                                   | Score                      | Source                                                   |
|-----------------------------------------------|----------------------------|----------------------------------------------------------|
| None                                          | 49 %                       | [CatDT](https://arxiv.org/html/2606.05050) ablation       |
| Distilled knowledge or skill banks            | 52 to 54 %                 | CatDT ablation                                           |
| Raw case bank                                 | 68 %                       | CatDT ablation                                           |
| Full stack                                    | 84 %                       | CatDT ablation                                           |
| Self-written skills                           | lose 8 to 12 points        | [SkillsBench](https://arxiv.org/html/2602.12670)          |

| Field      | Content                                                                   |
|------------|---------------------------------------------------------------------------|
| Structure  | The descriptor card as the `solution-planner` saw it                      |
| System     | "Ni(111)"                                                                 |
| Correction | "set initial magnetic moments"                                            |
| Reason     | "or SCF fails"                                                            |
| Source     | The checkpoint where it was made: flagged-case review or the pick of final states |
| Becomes    | A skill line, a check or a prior, once it recurs and a human promotes it; recurrences before promotion open: team decision |

### 4.4 Decision trace

`runs/<campaign>/trace.jsonl`; format open: team decision. Entries and who writes them:

| Entry                                              | Written by |
|----------------------------------------------------|------------|
| Settings as supplied; protocol choice and reason   | calculation_protocol |
| Counts of sites, orientations and pairs            | site_enumeration, pair_enumeration |
| Every verdict and rejection, with its reason       | anomaly_filter |
| MLIP choice and reason; doubt flags; escalations   | mlip_selection, uncertainty_estimation |
| Critic proposals and what they changed             | descriptor_card, step 3.4 |
| Human choices and reasons                          | fragplace.runtime.checkpoints |
| Failed-job diagnoses and resubmissions             | dft_single_points, extension |

### 4.5 Report

| Field                               | Note                                                                         |
|-------------------------------------|------------------------------------------------------------------------------|
| Final states                        | In order; the up to five the human picked; E(FS near), E(FS ∞), lateral interaction per kept state |
| Rejected pairs                      | With reasons; recombination rate of nearest pairs                            |
| ML uncertainty                      | Calibrated doubt from uncertainty_estimation                                 |
| Comparison with OC20NEB             | Our final state against the product frame: A–B distance, energy, validity    |
| Cost                                | ML force calls; DFT force calls and failures when dft_single_points ran        |
| Decision trace                      | Section 4.4                                                                  |

## 5. Rules the LLM must obey

Code decides every geometric and numerical question; the LLM plans, chooses with a reason, diagnoses and drafts. Hooks in `hooks/hooks.json` enforce rules 1 and 7, so they do not depend on the model reading them.

1. Never write, edit or reason from raw coordinates.
2. Act only through named tool calls. Bypassing a tool is a failure; the geometry benchmark exists to catch it.
3. Read descriptor cards and validity verdicts. A rendered image is a second look, never the basis of a decision.
4. Never choose a configuration from your own chemical reasoning. Every configuration comes from enumeration.
5. Never write numerical settings from memory. Pick the protocol and state why; the numbers come from the supplied inputs, the protocol or the sweep.
6. Read PROJECT.md at every step. Never change a locked setting.
7. Stop at every checkpoint and wait: approve settings, approve the plan, review flagged cases, pick up to five final states, interpret results.
8. Never override a code check. The `surface-chemist` proposes and reorders candidates at 3.4 and comments on cards elsewhere; it never removes a pair.
9. On ML doubt: stop, measure, repair, and ask only if repair fails.
10. Diagnose failed jobs: read the errors, adjust, resubmit.
11. Never pair a failing state. Report rejected pairs; never hide them.
12. Gather at most one or two published E_ads values, with functional and site, for a human to verify. Never cite from memory.
13. Do not write skills. Skills are few, human-written and procedural; facts and ranges live in code and PROJECT.md.

## 6. The roster

Seven agents, each named as the literature names the role and each deciding one thing; six act in the core and one only with HPC. The evidence for keeping the roster short stands: selection precision falls with the number of skills, self-written skills gain nothing, CatDT runs eight agents and has released no code. A role is added only when a human can say in one sentence what it decides. The survey behind the names is `docs/design/scientific-agent-architectures.md`.

| Agent                    | Decides                                                                                 | Status          | Name from                                                        | May call |
|--------------------------|-----------------------------------------------------------------------------------------|-----------------|------------------------------------------------------------------|----------|
| solution-planner         | The next tool call and when to stop; holds the checkpoint list                          | Core            | The board's title; Adsorb-Agent's Solution Planner               | every core tool but the three below |
| literature-reader        | Which published values and sources to put before the human: E_ads with functional and site, and d | Core | ChemAgents' Literature Reader; FutureHouse's Crow             | `literature_lookup` |
| computational-chemist    | Which protocol and settings to propose for the lock, and why                            | Core, before the run | El Agente Q's computational chemist agent                   | `structure_retrieval`, `calculation_protocol` |
| surface-chemist          | Which site types and orderings to try per fragment, from the chemistry of the cleavage; never a coordinate, never an override | Core, step 3.4 | A discipline agent in the Virtual Lab's style; Adsorb-Agent's Critic in function | `descriptor_card`, read only |
| mlip-specialist          | Which potential to use, and whether to trust, repair or escalate on the calibrated doubt | Core, steps 1\* and 7 | The Virtual Lab's Machine Learning Specialist; AdsMind's Analyzer in function | `mlip_selection`, `uncertainty_estimation`, `active_learning` |
| scientific-critic        | Whether the plan and the report hold up, judged in its own context                      | Core, the approve-the-plan and interpret-results checkpoints | The Virtual Lab's Scientific Critic; Agent Laboratory's reviewers | `descriptor_card`, `report`, read only |
| dft-recovery-agent       | How to retry a failed DFT step, one change at a time, capped at three                   | Only with HPC   | AutoDFT's Recovery Agent; DREAMS' Convergence Agent               | `dft_single_points` |

The planner is not called principal investigator, although the Virtual Lab uses that name for its lead agent, because here the human approves, picks and interprets and is the investigator; the Virtual Lab's human only sets the agenda. The surface-chemist and the scientific-critic work in their own contexts so the planner's reasoning cannot anchor them. Each agent is one page under `agents/`, with the tools it may call in its frontmatter, and `tests/test_registry.py` holds that list equal to the registry's `allowed_roles`.

| Skill, ours              | Procedure                                                       | Followed by                  | Status        |
|--------------------------|-----------------------------------------------------------------|------------------------------|---------------|
| dft-settings-protocol    | Pseudopotentials, cutoff, k-mesh, smearing, layers; the lock    | computational-chemist        | Core          |
| mlip-doubt-calibration   | Committee disagreement against DFT labels; when to escalate     | mlip-specialist              | Core          |
| dissociation-final-state | The six points of step 3 and steps 4 to 6; what to report       | solution-planner             | Core          |
| final-state-report       | Report format: both energies, rejections, trace                 | solution-planner, scientific-critic | Core   |
| hpc-dft-jobs             | Submission; what custodian handles; the retry cap               | dft-recovery-agent           | Only with HPC |

Reused from AtomisticSkills: `ml-committee-uncertainty`, `ml-mlip-benchmark`, `ml-mace-finetune`, `chem-thermochemistry`, `general-peer-review`. Ten in all keeps selection precision high. Each skill stays under 200 lines and names its tools.

## 7. Repository layout

One Python package, `fragplace` under `src/`, that a Claude Code plugin wraps. The plugin side is the layout Claude Code documents: `.claude-plugin/plugin.json`, `agents/`, `skills/<name>/SKILL.md`, `hooks/hooks.json`, `.mcp.json`. The package side is the layout ChemCrow, Biomni and ChemGraph practise: `registry/`, `tools/` by category, `schemas/`, `runtime/`, `memory/`, `execution/`, `agent/`, `mcp/`, `eval/`, `cli/`. Three rules: each file has one kind and lives in that kind's folder; calls go one way, agents to skills to tools to the runtime, never up or sideways; one reading order for a human and one for an agent. The tree is the repository as it is, not a plan; `tests/` and `fragplace check` keep it so. The name: the board calls the pieces of the broken bond the binding fragments, and the agent places them.

```
open-science-hackathon/                 the FragPlace plugin, laid out as Claude Code lays out a plugin
├── README.md, CLAUDE.md, AGENTS.md     the entry points; CLAUDE.md points a coding agent to AGENTS.md
├── PROJECT.md, lessons.md              the settings template; the case bank
├── pyproject.toml                      package `fragplace`, commands `fragplace` and `fragplace-server`, one extra per lane
├── .claude-plugin/plugin.json          declares skills/, agents/, hooks/hooks.json and .mcp.json
├── .mcp.json                           the MCP server: fragplace-server, one tool per registry entry, prefix mcp__fragplace__
├── hooks/hooks.json                    PreToolUse: block coordinate edits; require the checkpoint before a gated tool
├── agents/                             the seven agents of section 6, one page each, tools in the frontmatter
│   ├── solution-planner.md        the next tool call and when to stop
│   ├── literature-reader.md       which published values and sources to put before the human: E_ads with functional and site
│   ├── computational-chemist.md   which protocol and settings to propose for the lock
│   ├── surface-chemist.md         which site types and orderings to try per fragment
│   ├── mlip-specialist.md         which potential to use
│   ├── scientific-critic.md       whether the plan and the report hold up
│   ├── dft-recovery-agent.md      how to retry a failed DFT step; only with HPC
├── skills/                             the five skills of section 6; five more are reused from AtomisticSkills
│   ├── dft-settings-protocol/SKILL.md
│   ├── mlip-doubt-calibration/SKILL.md
│   ├── dissociation-final-state/SKILL.md
│   ├── final-state-report/SKILL.md   
│   ├── hpc-dft-jobs/SKILL.md         
├── src/fragplace/                      the package, in the layout of ChemCrow, Biomni and ChemGraph
│   ├── registry/tools.py               ToolSpec and REGISTRY: the 19 tools of section 3, defined once; CATEGORY maps each to its module
│   ├── registry/agents.py              the roster, the checkpoints, the skill names; the figures import it
│   ├── tools/                          one module per category, as ChemCrow groups its tools; a function per tool, parameters as in the registry
│   │   ├── literature.py    literature_lookup
│   │   ├── structure.py     structure_retrieval, calculation_protocol
│   │   ├── uncertainty.py   mlip_selection, uncertainty_estimation, active_learning
│   │   ├── sites.py         site_enumeration, pair_enumeration
│   │   ├── placement.py     adsorbate_placement, minima_hopping
│   │   ├── screening.py     pull_force_screen
│   │   ├── relaxation.py    relaxation, reference_energies
│   │   ├── filtering.py     anomaly_filter, descriptor_card
│   │   ├── clustering.py    soap_clustering, ranking
│   │   ├── report.py        report
│   │   ├── dft.py           dft_single_points
│   ├── schemas/records.py              the records of section 4
│   ├── runtime/project.py              PROJECT.md: read, write, lock, require_locked, settings_hash
│   ├── runtime/journal.py              Run, trace.jsonl, the @traced decorator
│   ├── runtime/cache.py                content-addressed results of relaxations and force calls
│   ├── runtime/checkpoints.py          the five checkpoints: require, record
│   ├── runtime/state.py                the resumable run state
│   ├── runtime/policy.py               the two hook commands
│   ├── memory/casebank.py              lessons.md as records; retrieve by system and failure
│   ├── calculators/                    one interface; uma, mace with committees, chgnet
│   ├── execution/                      Job and Backend; local, slurm with custodian in the job script; the tracker with its retry cap
│   ├── agent/                          roles.py, the roster as code; prompts.py loads agents/<name>.md
│   ├── mcp/server.py                   builds the MCP tool list from the registry
│   ├── eval/harness.py                 the campaign with and without each skill and agent, on the OC20NEB subset
│   ├── cli/main.py                     fragplace registry | check | init
│   └── errors.py                       SettingsNotLocked, Rejected, Escalate, CheckpointPending, OpenDecision
├── tests/                              registry, tool modules, agent files and the figures' data module agree; records; operations; hooks; state and jobs
├── ci/github-workflow.yml              ruff, pytest, the figures rendered, the generated blocks checked; move to .github/workflows/ with a token that has the workflow scope
├── runs/<campaign>/                    PROJECT.md copy, trace.jsonl, checkpoints.json, state.json, cards/, structures/, cache/, report.md
├── figures/                            the README figures, PNG and SVG
└── docs/                               README.md indexes it
    ├── design/                         the design history and the three reviews
    ├── figures/src/_board.py           the data module the figures 29 to 32 and the generated blocks come from
    └── benchmark/                      the OC20NEB subset, baselines, scoring: planned
```

| Reader   | Reads, in order                                                                                      |
|----------|------------------------------------------------------------------------------------------------------|
| A human  | `README.md`, `PROJECT.md`, the run's `report.md`, `lessons.md`                                       |
| An agent | `CLAUDE.md`, `AGENTS.md`, the skill it was given, `fragplace registry`, the tool docstrings          |

| Kind    | Folder                              | One item is                                            | May call           | Holds logic |
|---------|-------------------------------------|--------------------------------------------------------|--------------------|-------------|
| Agent   | `agents/`                           | A one-page role: what it decides and when it stops     | Skills, tools      | No          |
| Skill   | `skills/<name>/`                    | A procedure, step by step, naming tools                | Tools              | No          |
| Tool    | `src/fragplace/tools/`              | One function per registry entry, in its category module, exposed by `mcp/server.py` | The runtime | Yes, tested |
| Runtime | `src/fragplace/` other modules      | Schemas, project, journal, cache, checkpoints, state, case bank, calculators, execution | Each other | Yes, tested |
| Test    | `tests/`                            | Registry consistency, records, operations, hooks       | The runtime        | No          |
| Data    | `runs/`, `benchmark/`, `lessons.md` | Outputs, never code                                    |                    | No          |
| Docs    | `docs/`, `figures/`                 | What and why; never how to call                        |                    | No          |

| Operational need       | Where it lives                                                                                       |
|------------------------|------------------------------------------------------------------------------------------------------|
| Configuration          | `PROJECT.md` through `fragplace.runtime.project`; locked at the approve-settings checkpoint; a hash on every record |
| Provenance             | `fragplace.runtime.journal`: every tool call, choice and escalation in `trace.jsonl`; outputs stored by hash |
| Caching                | `fragplace.runtime.cache`: key of structure, calculator and settings hash, so a changed setting never returns a stale result |
| Errors and retries     | `fragplace.errors` typed; custodian handlers inside the DFT job script, before any agent diagnosis   |
| Compute backends       | `fragplace.execution`: local for the laptop and GPU lanes, slurm for DFT                              |
| Human checkpoints      | `fragplace.runtime.checkpoints` records; `fragplace.runtime.policy` blocks tools past an unpassed checkpoint        |
| Memory                 | `fragplace.memory.casebank`: raw cases in `lessons.md`; a human promotes                                   |
| Run state              | `fragplace.runtime.state`: the current step and the pending checkpoint in `state.json`, so a campaign resumes where it stopped |
| Evaluation             | `fragplace.eval.harness`: the same campaign with and without each skill and agent, scored on the OC20NEB subset once D3 fixes it |
| Potentials             | `fragplace.calculators`: one interface, adapters imported lazily                                    |
| Literature and databases | `fragplace.tools.literature`: paper-qa, Materials Project, Catalysis-Hub; every value carries a source  |
| Secrets                | environment variables only: `HF_TOKEN` for UMA weights, `MP_API_KEY`; never in PROJECT.md            |
| Tests and CI           | `pytest`; `ci/github-workflow.yml` also renders the figures and checks the generated blocks; it moves to `.github/workflows/` with a token that has the workflow scope |
| Packaging              | `pyproject.toml` with extras: structures, mlip, literature, dft, agents, figures, dev                 |
| Licence                | open: team decision; constraints in the Licences line below                                          |

Naming: `src/fragplace/tools/filtering.py` holds `anomaly_filter(...)` and `descriptor_card(...)`, the registry's CATEGORY names the module, and `tests/test_registry.py` imports the function through it. Names say what is computed in the field's words: `anomaly_filter`, the board's own term; `pair_enumeration`; `uncertainty_estimation`. Licences: ASE, ACAT and Sella are LGPL and may be imported; CatKit, Pynta, arkimede and CatMAP are GPL, copy their ideas only; TSAgent and Adsorb-Agent state no licence; UMA weights need a Hugging Face account and the FAIR Chemistry License.

## 8. Compute lanes

HPC is needed for DFT and nothing else, and DFT is an extension: the laptop and GPU lanes complete the pipeline.

| Lane   | Steps                                                            | Without HPC in the hackathon                                                                 |
|--------|------------------------------------------------------------------|----------------------------------------------------------------------------------------------|
| Laptop | 1 lock from the supplied settings; 2 to 4; 5; 6; 8; 3.5; 3.2; 5; 14 | Unchanged                                                                                  |
| GPU    | 1\* benchmark; 7 committee; 3.3 force calls and relaxations; 6 MLIP energies; ML frequencies | Unchanged; one workstation or cloud GPU                          |
| HPC, extensions only | Settings sweep when no relaxed inputs exist; DFT calibration labels for 7; DFT single points of dft_single_points; DFT frequencies | Not needed: OC20's RPBE and PAW values as the settings record; OC20NEB's released DFT bands as labels and ground truth; one DFT check run beforehand and recorded, if available |

## 9. Benchmark and measurables

Two numbers are measured on an OC20NEB subset, starting with \*OH → \*O + \*H on Pt(111). Score with and without our skill, as AtomisticSkillsBenchmark does. Side runs: H on Pt(111) end to end against CE27 and OC20; the Ni(111) doubt demo; the geometry editing tasks of the table.

| Number                     | Definition                                                                                   | Compared                                   |
|----------------------------|----------------------------------------------------------------------------------------------|--------------------------------------------|
| Recombination rate         | How often the nearest pair bonds back after relaxation                                       | Per system and per distance shell          |
| Lateral interaction        | E(FS near) − E(FS ∞), with E(FS ∞) from separate cells                                       | Per system; sign and size                  |
| Final state versus OC20NEB | Our nearest validated final state against the product frame of the released band: A–B distance, energy, validity | Per reaction in the subset |
| Three policies             | Nearest-first, ours; energy–distance Pareto, NEBscape; shell sampling, CatTSunami; on the same dissociations: distance, energy, validity, recombination | Per reaction; NEBscape converged 94 % of 304 |
| Geometry editing           | Place, rotate, supercell, cut facet, with tools against without                              | 20 tasks; target near 100 % with tools     |

| Item              | What the docs say                                                                                   | Open                                  |
|-------------------|-----------------------------------------------------------------------------------------------------|---------------------------------------|
| OC20NEB           | 932 DFT NEB calculations, CC-BY-4.0, released with CatTSunami in the fairchem repository            | Subset size and selection             |
| Settings; first case | OC20 used RPBE and PAW, so the lock must match if OC20NEB is ground truth; \*OH → \*O + \*H on Pt(111) is the simplest in OC20NEB's list with DFT bands to compare | Accept it as ground truth; confirm the case |
| Baselines         | A plain AdsorbML-style run with `AdsorbateSlabConfig`; AtomisticSkills `mat-surface-adsorption`, which calls MatCalc `AdsorptionCalc` on pymatgen's `AdsorbateSiteFinder`; NEBscape's Pareto choice and CatTSunami's shell sampling for the policy comparison | Exact definition |
| Pass criterion    | Our final state is a validated minimum with no A–B bond, at least as near as the OC20NEB product frame, within an energy tolerance of it | The tolerance and the distance rule |
| Reference points  | NEBscape's endpoint convergence, 94 % of 304 OC20NEB reactions; the OC20NEB product frame per reaction | None is stated as the criterion      |

## 10. Build order

Build the eight numbered tasks first; they are the shortest route to one validated nearest final state. Task IDs D, T, P, M and R are the build plan's. Every tool exists as a typed stub that raises NotImplementedError; a task is done when its stub is filled and its test passes.

Critical path:

- [ ] 1 · D1 System and product: AB\*, surface, A\* + B\*; first case \*OH → \*O + \*H on Pt(111). Human decision.
- [ ] 2 · T1 `structure_retrieval` and `calculation_protocol`. Needs D1, D3.
- [ ] 3 · T2 `site_enumeration`. Needs T1.
- [ ] 4 · T4 `anomaly_filter`. Needs T3.
- [ ] 5 · T6 `mlip_selection`. Needs D2.
- [ ] 6 · P1 `pair_enumeration`, `pull_force_screen`, `relaxation`, `soap_clustering`, with `minima_hopping` as the baseline. Needs T2, T4, T6, D5.
- [ ] 7 · M2 \*OH → \*O + \*H final state against the OC20NEB product frame. Needs P1, P5, D3.
- [ ] 8 · R1 Release: the skills, the MCP server beside AtomisticSkills, benchmark data and traces on Zenodo. Needs M1, M2.

Off-path tasks, built when the path needs them:

| Group               | Task                                                                                       | Needs          |
|---------------------|--------------------------------------------------------------------------------------------|----------------|
| Decide first        | D2 compute and codes; D3 benchmark and pass criterion; D4 headline claim; D5 final-state rules | Humans      |
| Foundations         | T0 `literature_lookup`; T3 `adsorbate_placement`; T5 `descriptor_card`                      | D1; T2; T4     |
| Tool layer, from the architecture review | typed input and output records per tool, so the server publishes an output schema and the registry test reads the signature instead of strings; a call-time check that every numeric argument comes from a traced record or an explicit human value; one golden example per tool run as a test | the stubs |
| ML trust            | T7 `uncertainty_estimation`; T8 `ranking` and the checkpoint record with the case bank       | T6, T4; T5, T7 |
| Final state         | P5 `reference_energies` and `report`                                                       | P1, T7         |
| Measure             | M1 H on Pt(111) end to end; M4 Ni(111) doubt demo; M3 the two numbers and the policy comparison | T1 to T8; T7, T8; P1, P5 |
| LLM and human layer, last | the skill files; the interview in PROJECT.md; `lessons.md` seeded; the agents of section 6; the hooks | The tools |
| Extensions, later   | T9 `dft_single_points`; T10 `active_learning`; M5 agentic uncertainty, N planner runs; the critic on gate cards at 5; coverage scan at 3.2; one-hop target at 6 | T8, D2; T7, D2; T8, P5 |

## 11. Open decisions that block coding

Each question blocks the step or task beside it; never code around one with a guessed value.

| Question                                                                                                   | Blocks                      |
|------------------------------------------------------------------------------------------------------------|-----------------------------|
| Is \*OH → \*O + \*H on Pt(111) the first system and product?                                              | D1; everything after it     |
| Which DFT code, compute and GPU; does any DFT run, or OC20NEB labels only?                                 | D2; T6, T7, T9              |
| Is an OC20NEB subset the ground truth, so the lock must match OC20's RPBE and PAW?                          | D3; T1, M2                  |
| Which subset, how large; what energy tolerance and distance rule pass; what exactly is the baseline?       | D3; M2                      |
| Convergence target for E_ads when the sweep runs: 10 or 25 meV? Which gas-phase references for AB, A and B? | T1, PROJECT.md             |
| File format and schema for PROJECT.md, the card, the lessons log, the trace and the report                 | T1, T5, T8, P5              |
| Thresholds for migrated, dissociated, reconstructed, intercalated, magnetism collapsed, expected-range width, imaginary-frequency noise; the surface plane; frequencies from MLIP or DFT; which checks run before relaxation | T4 |
| A–B distance threshold for bond re-formed                                                                  | 5; T4, P1                  |
| Distance metric: site-graph with in-plane tiebreak, or in-plane alone; how the site graph is built; the pair call name | 3.2; T2, P1          |
| Does the cheap baseline, A fixed at its IS site, run before the full enumeration of A?                     | 3.5; P1                      |
| Is d the vacuum or the adsorbed bond length; the pull-force threshold                                      | 3.2, 3.3; P1                  |
| Target: nearest survivor, or lowest energy within one site hop; configurations per SOAP cluster; how many final states to keep; recombination rate per shell or nearest shell only | 6; P1, report |
| Which candidate potentials at 1\*, so which committee at 7; doubt by ensemble, geometric sanity or both; threshold; how many labels; where the MLIP choice is recorded | T6, T7 |
| Random displacement amplitude; number of conformers; test adsorbate for the \*OH sweep; adsorbate class and size beyond the first case | T3, T1, T6     |
| Autonomy level; which checkpoints Balanced skips; recurrences before a case is promoted                     | T8, `solution-planner`   |
| Headline claim: the nearest non-recombining final state, validated, or "knows when not to trust itself"    | D4; report and demo, not code |

## 12. References

NEBscape is the closest prior work and every other source below is reused for one pattern or one tool; nothing is cited from memory except CE27, and the numbers live in section 9.

Prior work for the final state:

- [NEBscape, npj Computational Materials 2026](https://www.nature.com/articles/s41524-026-02298-1), [code, MIT](https://gitlab.mpcdf.mpg.de/hjung/nebscape): the closest prior work; combinatorial pairs on symmetry-inequivalent sites, a fixed separation cut-off, Hookean fragment integrity, minima hopping, energy–distance Pareto selection, SOAP deduplication; its endpoint convergence on OC20NEB is the reference point of section 9.
- [CatTSunami and OC20NEB, arXiv 2405.02078](https://arxiv.org/abs/2405.02078), [code in fairchem, MIT](https://github.com/facebookresearch/fairchem): `AutoFrameDissociation` by shell sampling; the released DFT bands are the ground truth of section 9.
- [AdsorbML and OC20-Dense](https://arxiv.org/pdf/2211.16486): the four anomaly checks and the top-k then DFT recipe.
- [Pynta, JCIM 2023](https://chemrxiv.org/engage/chemrxiv/article-details/647114454f8b1884b755bc5a), [code, GPL](https://github.com/zadorlab/pynta): ACAT plus Sella on slabs; pattern only.
- [El Agente Potente](https://arxiv.org/abs/2609.14840): typed execution graphs; reports a dissociated state unflagged.
- [Reproducible orchestration of NEB best practices](https://arxiv.org/abs/2603.14737): gas phase only.
- [CatDT](https://arxiv.org/html/2606.05050): endpoint gate in code and the memory ablation; [AdsMind](https://arxiv.org/html/2606.19152), [code](https://github.com/AI4QC/AdsMind): the pick-from-labels interface; [Adsorb-Agent](https://arxiv.org/html/2410.16658v3): the counter-example. Transition-state agents and benchmarks belong to the later phase and are listed in the archive.
- Review of what none of them do: `docs/design/chemistry-agents-review.md`; role names, tool declarations and operations of 28 scientific-agent systems: `docs/design/scientific-agent-architectures.md`.

Tools wrapped, each opened on 21 October 2026, details in `docs/design/repo-survey.md`:

- [fairchem](https://github.com/facebookresearch/fairchem): CatTSunami, AdsorbML, OC placement, UMA; [UMA weights](https://huggingface.co/facebook/UMA).
- [ASE](https://gitlab.com/ase/ase); [Sella](https://github.com/zadorlab/sella); [spglib](https://github.com/spglib/spglib), [developer API](https://spglib.readthedocs.io/en/v2.6.0/api/develop.html); [ACAT](https://gitlab.com/asm-dtu/acat); [pymatgen-core](https://github.com/materialsproject/pymatgen-core); [MatCalc](https://github.com/materialyzeai/matcalc); [CatKit](https://github.com/SUNCAT-Center/CatKit), pattern only.
- [AtomisticSkills](https://github.com/learningmatter-mit/AtomisticSkills) and its [paper](https://arxiv.org/abs/2605.24002); [AtomisticSkillsBenchmark](https://github.com/learningmatter-mit/AtomisticSkillsBenchmark); [AiiDA common workflows](https://github.com/aiidateam/aiida-common-workflows) and [paper](https://www.nature.com/articles/s41524-021-00594-6); [SSSP](https://www.materialscloud.org/discover/sssp); [atomate2](https://github.com/materialsproject/atomate2); [custodian](https://github.com/materialsproject/custodian).
- [MACE](https://github.com/ACEsuit/mace); [CHGNet](https://github.com/CederGroupHub/chgnet); [uncertainty-toolbox](https://github.com/uncertainty-toolbox/uncertainty-toolbox); [CatBench](https://github.com/JinukMoon/CatBench); [EquiformerV2](https://github.com/atomicarchitects/equiformer_v2), reproduction only; [OC20 dataset paper, with the DFT settings](https://arxiv.org/pdf/2010.09990); [VASP wiki on pseudopotentials](https://vasp.at/wiki/Choosing_pseudopotentials).
- Patterns: [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk); [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python); [Anthropic Agent Skills](https://github.com/anthropics/skills); [Get Physics Done](https://github.com/psi-oss/get-physics-done); [Pydantic AI](https://github.com/pydantic/pydantic-ai); [CatMaster](https://github.com/q734738781/CatMaster).

Agent design evidence:

- Geometry stays in code, text cards over images: [AtomWorld](https://arxiv.org/html/2510.04704); [LLMConfBench](https://arxiv.org/html/2609.20666); [MiSI-Bench](https://arxiv.org/html/2512.10867v1); [MatTools](https://arxiv.org/html/2505.10852v2); [Robocrystallographer](https://www.cambridge.org/core/journals/mrs-communications/article/robocrystallographer-automated-crystal-structure-text-descriptions-and-analysis/3C201F132450877464B2D0B1B8C4ED01); [LLM-Prop](https://www.nature.com/articles/s41524-025-01536-2); [CatBERTa](https://ar5iv.labs.arxiv.org/html/2309.00563).
- Few skills, human-written: [SkillsBench](https://arxiv.org/html/2602.12670); [Demystifying Agent Skills](https://arxiv.org/abs/2608.14036); [K-Bench](https://arxiv.org/abs/2608.21601); [Virtual Lab](https://biohub.org/news/with-no-need-for-sleep-or-food-ai-built-scientists-get-the-job-done-quickly/).
- MLIP doubt, settings and checkpoints: [Kempen, Cheula and Andersen, 80 MLIPs](https://phys.au.dk/intercat/news-and-events/show/artikel/new-intercat-paper-luuk-kempen-raffaele-cheula-and-mie-andersen); [fine-tuning universal MLIPs for TS search](https://arxiv.org/pdf/2603.24482); [DREAMS](https://arxiv.org/html/2507.14267); [AutoDFT](https://arxiv.org/html/2605.26179v2); [VASPilot](https://arxiv.org/html/2508.07035v1); [QUASAR](https://arxiv.org/html/2602.00185v2); [ChemCrow](https://arxiv.org/abs/2304.05376).
- From memory, not looked up here: Wellendorff et al., CE27 adsorption benchmark, Surface Science 2015.
