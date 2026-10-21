# agent.md: what to build, how, and in which order

Audience: a coding agent about to write code in this repository. Read this file first and in full; `CLAUDE.md` points here. It is the operational form of the design history in `archive/docs/`. Where this file and the archive differ, the team's board of 21 October 2026 and the fixed scope of section 1 are the authority, then `archive/docs/adsorption-agent-workflow.md`; fix whichever disagrees with the board. Conventions: "open: team decision" marks a value the team has not fixed; expose it as a named parameter without a default and ask, never fill it from memory. Numbering is the board's: 1, 1\*, 2, 3 with its points 3.1 to 3.6, 4 to 8, Solution. The archive uses its own row numbers, 4.1 and 6 for the board's step 5, 3.1 to 3.6 for the board's step 3, 14 for the Solution; the table in section 2 gives the correspondence. Where two actors appear in a row, the Owner column does the work. Write code comments and docs as `archive/docs/agent-writing-style.md` says.

## 1. Scope and problem

Given a surface with adsorbate AB\* and the desired product A\* + B\*, both fragments adsorbed, determine the final state in which B\* is as close to A\* as possible while the two stay fully dissociated, that is, do not bond back. Scope fixed by the team on 21 October 2026. Not catalysis, not kinetics, not yet the barrier: those are a later phase.

A keeps the binding atom, the team's adsorbate #1; B is the dissociated part, adsorbate #2. The rule: over every symmetry-distinct site pair, minimise the site-graph distance between A\* and B\*, in-plane distance as tiebreaker, subject to the final-state gate of section 3.4. Keep the first few survivors in order. Adjacent fragments can repel, so the nearest is not always the lowest in energy: report both energies.

| Item         | Content                                                                                                     |
|--------------|-------------------------------------------------------------------------------------------------------------|
| Known, supplied | Relaxed surface with its energy; relaxed adsorbate in vacuum with its energy; relaxed initial state AB\* with its energy; the settings all three were relaxed with; E_ads from the literature, human-verified |
| Input prompt | Surface, adsorbates, system description; critic and knowledge prompts as a fixed list; reasoning questions as a written skill |
| Output, now  | Several nearest non-recombining final states in order, up to five picked by the human; E(FS near) and E(FS ∞); rejected pairs with reasons; recombination rate of nearest pairs; ML uncertainty; decision trace |
| Extensions, the board's question marks | Agentic uncertainty, the planner run N times; DFT, single points on the chosen five and labels for calibration; a vision model for placement, only after the geometry benchmark shows an image helps; active learning from 1\*; more than three configurations per cluster, set by the recombination rate; a settings sweep and AB\* enumeration when no relaxed inputs exist |
| Out of scope | The path from AB\* to the final state and its barrier; kinetics; catalysis. Archived: `archive/docs/` |
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

| Step | Owner | What it does | Tool, section 3 | Logs | Archive row |
|------|-------|--------------|-----------------|------|-------------|
| 1 Structure retriever | Tool | Takes the three supplied relaxed structures with their energies and A and B as structures; selects the surface cell so periodic images stay 10 Å apart; locks the settings the inputs were relaxed with, plus the human's physics choices, in PROJECT.md; `dft-settings-protocol` holds the protocol | dft_settings_lock | Settings as supplied; the cell and why; protocol and reason | 1 |
| 1\* MLIP selection | Tool | Benchmarks two or three candidate potentials on the system class before any placement; the chosen one relaxes every candidate; all candidates form the committee of step 7; spin for Ni and Co; active learning is an extension | mlip_choice | Benchmark results; the choice and the reason the LLM states | 5 |
| 2 Adsorption sites | Tool | Symmetry-inequivalent sites of the selected cell, fcc and hcp hollows apart, counted; pymatgen's finder as the baseline | site_enumeration | Symmetry group; every site; the count N and its check | 2 |
| 3.5 Site and orientation for the binding fragment | Tool | The fragment keeping the binding atom, A, placed at every symmetry-distinct site near its old site, counted; A fixed at its old site is the cheap baseline | adsorbate_placement, dissociation_final_state | Placements of A\* and their count | 3.5 |
| 3.2 Window for the dissociated atom | Tool | B sites around each A within [1.5 d, 5] Å, d the length of the bond to break; every symmetry-distinct pair, ordered by site-graph distance with in-plane tiebreak, counted | dissociation_final_state, site_enumeration | Ordered pairs and their count | 3.2 |
| 3.4 Agentic critique | LLM | `geometry-critic` reads the descriptor cards, proposes a site type and orientation per fragment, may reorder or add candidates; never edits coordinates, never removes a pair, never overrides a check | descriptor_card | Every proposal and what it changed | 3.5, 3.2 |
| 3.6 Minima hopping, alternative | Tool | NEBscape's endpoint generator with the chosen MLIP as the alternative generator and the baseline policy | dissociation_final_state | Generator used; its candidates | 3.5 |
| 3.3 Pull force | Tool | One MLIP force call per pair; the force component on each fragment along the A–B axis; a pull towards the other fragment above the threshold queues the pair last, never drops it | dissociation_final_state, mlip_choice | Flagged pairs; force calls | 3.3 |
| 4 Initial configurations | Tool | Every pair relaxed with the chosen potential and the locked settings; orientations under the site's stabiliser, Burnside-counted; random displacement first | site_enumeration, adsorbate_placement, dissociation_final_state | Every orientation and count; relaxed pairs | 4, 3.3 |
| 5 Physics-based and anomaly filtering | Tool | The gate of section 3.4 on every structure before and after relaxation: nine checks per fragment plus the two final-state checks, 3.1 among them as the bond-re-formed check; verdict into the card; a failing pair is never kept; the ML variant not taken; an LLM critic comments only, extension | validity_gate, descriptor_card | Every verdict with its value; every rejection with its reason | 4.1, 6, 5 |
| 6 SOAP clustering | Tool | Cluster the survivors by SOAP as NEBscape does; keep the lowest per cluster as the board says and the nearest, our objective; nearest first overall; E(A\*), E(B\*), E(FS ∞) with the chosen MLIP | dissociation_final_state | Final states; E(FS near); E(FS ∞); recombination rate | 6 |
| 7 Uncertainty estimation | Tool | Disagreement across the committee of 1\*, calibrated on a few DFT labels if available, else OC20NEB labels; doubt escalates instead of guessing; `mlip-doubt-calibration` says when | mlip_doubt | Labels used; disagreement against label error; every flag and escalation | 7 |
| 8 Rank; user chooses up to 5 | Human | Cards with rank, doubt and verdicts; the human picks; the choice and its reason go to the case bank | descriptor_card, 3.10 | The cards shown and their order; the choice; the reason | 8 |
| Solution | LLM | Drafts the report: both energies, lateral interaction, rejections with reasons, recombination rate, doubt, decision trace; `final-state-report` holds the format; the human interprets | final_state_report | The full decision trace | 14 |

Human checkpoints, where the agent stops and waits: approve settings; approve the plan; review flagged cases; pick up to five final states; interpret results. Autonomy level and which checkpoints a Balanced mode skips: open: team decision.

## 3. The tools

Nine core tools and one extension tool, one file each under `mcp/tools/`, each wrapping one module of the same name under `finalstate/`. The human checkpoint, T8, is a procedure, not a tool, section 3.10. Every tool returns each structure through the descriptor card of 3.5 and logs every parameter beside its outputs, as AtomisticSkills does. Write the tool docstrings for the model, per MatTools. Named calls the LLM may issue: `enumerate_sites(slab)`, `place(site, orientation, height)`, `displace(amplitude)`, `check(structure)`, `render(structure)`; the pair call name is open: team decision. Module and class names below were read from source on 21 October 2026, `archive/docs/repo-survey.md`.

### 3.1 dft_settings_lock, step 1

Record the settings the three supplied structures were relaxed with, lock them in PROJECT.md with the human's physics choices, and select the surface cell. One file serves IS, FS and the later band. The convergence sweep on E_ads is an extension that runs only when no relaxed inputs exist and DFT is available.

| Field  | Content                                                                                                              |
|--------|----------------------------------------------------------------------------------------------------------------------|
| Inputs | The three relaxed structures with their energies and the settings they were relaxed with; A and B as structures; physics choices from the human: functional, dispersion, spin, U; metal, facet; protocol chosen by the LLM with its reason; DFT code, if any |
| Outputs | Settings block in PROJECT.md; the surface cell; every later tool reads it; sweep data only when the sweep ran       |
| Procedure | Check that the three inputs share one settings set, check 8 of 3.4; select the cell so periodic images are 10 Å apart; lock. Extension, no relaxed inputs: one test adsorbate on the target surface; sweep cutoff, k-mesh, smearing and layers; report the cheapest setting with E_ads inside the target of the converged value |
| Wraps  | The precision-protocol pattern of `aiida_common_workflows.workflows.relax.CommonRelaxWorkChain`; SSSP; pymatgen input sets, `MPRelaxSet` as atomate2 uses it; ASE; VASP or Quantum ESPRESSO for the sweep |
| Logs   | Settings as supplied; the cell and its reason; protocol and the LLM's reason; every sweep point when the sweep ran; chosen values; pseudopotential family and version. Rejected: the LLM writing cutoff or k-points from memory |

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

### 3.2 site_enumeration, steps 2, 3.2, 3.5 and 4

List every symmetry-inequivalent site, orientation and A–B pair, with the count.

| Field  | Content                                                                                                              |
|--------|----------------------------------------------------------------------------------------------------------------------|
| Inputs | The supplied slab in the selected cell; AB, A and B as structures; for pairs, the window [1.5 d, 5] Å              |
| Outputs | Sites with label, site group, coordination and atom beneath; orientations inequivalent under the site's stabiliser group; pairs with site-graph distance and in-plane distance; the count N |
| Checks | Sites are the inequivalent high-symmetry Wyckoff positions of the slab's layer group; fcc and hcp hollows told apart by the atom beneath; N = (1/\|G\|) Σ \|X^g\| checked against the explicit list |
| Unit tests | Two identical adsorbates on the corners of a square cell under C4v give N = 2; the fcc(111) and fcc(100) site table of `archive/docs/agent-context.md` section 3 |
| Wraps  | `spglib.get_symmetry_dataset` and `get_symmetry` for the operations Burnside needs; `spglib.get_layergroup` is a developer API, test it against the site table before relying on it; `acat.adsorption_sites.SlabAdsorptionSites` with `get_unique_sites`, `get_graph`, `get_neighbor_site_list`; `acat.build.adlayer.SystematicPatternGenerator` for unique pairs, `min_adsorbate_distance` 1.5 Å by default; CatKit `AdsorptionSites` as a pattern only, GPL; `pymatgen.core.adsorption.AdsorbateSiteFinder.find_adsorption_sites` as the baseline, no fcc or hcp label |
| Logs   | Symmetry group; every site, orientation and pair; N and its check                                                     |

### 3.3 adsorbate_placement, steps 3.5 and 4

Put a fragment at an enumerated site, orientation and height, by script. The LLM never places atoms.

| Field  | Content                                                                                                              |
|--------|----------------------------------------------------------------------------------------------------------------------|
| Inputs | Site and orientation from 3.2; conformer relaxed in vacuum first; height                                             |
| Outputs | Structure and its descriptor card                                                                                   |
| Checks | Start 2 to 3 Å above the site, never 10 Å; small random displacement before every relaxation, against the symmetry trap; few conformers |
| Wraps  | `ase.build`; `fairchem.data.oc.core.AdsorbateSlabConfig` with modes `random`, `heuristic`, `random_site_heuristic_placement` and `MultipleAdsorbateSlabConfig` as the fallback when symmetry is unknown and as the benchmark baseline; CatKit `Builder.add_adsorbate` as a pattern only |
| Logs   | Site, orientation, height, displacement amplitude and the random draw, conformer source                               |
| Open   | Displacement amplitude, shown in the docs only as an example call of 0.05 Å; number of conformers                    |

### 3.4 validity_gate, steps 3.1 and 5

One code path, `check(structure)`, that gives a verdict on every structure, initial and final, before ranking or pairing. A failing state is never paired.

| Field  | Content                                                                                                              |
|--------|----------------------------------------------------------------------------------------------------------------------|
| Inputs | Relaxed structure; its start structure and enumerated site; clean slab; settings record; E_ads prior; vibrational frequencies |
| Outputs | Pass or fail per check with the measured value and the reason, written into the descriptor card                    |
| Wraps  | `fairchem.data.oc.utils.DetectTrajAnomaly`: `is_adsorbate_dissociated`, `is_adsorbate_desorbed`, `has_surface_changed`, `is_adsorbate_intercalated`; `ase.vibrations.Vibrations`; `acat.adsorbate_coverage.SlabAdsorbateCoverage` for the moved-site check; CatBench's anomaly classes Normal, Migration, Energy Anom., Unphys. Relax and Reprod. Fail name each rejection |
| Per-fragment rule | `DetectTrajAnomaly` treats A\* + B\* as one adsorbate and passes B leaving while A stays, so check 1 runs per fragment; `is_adsorbate_dissociated` flags any connectivity change, so it also catches check 10 |
| Logs   | Every verdict with its measured value; every rejection with its reason                                               |

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

### 3.5 descriptor_card

Turn every structure into the text the LLM reads; it is the only view of geometry the LLM gets. `render(structure)` makes the image. Layout, a machine-readable twin and pair fields: open: team decision.

| Field  | Content                                                                                                              |
|--------|----------------------------------------------------------------------------------------------------------------------|
| Inputs | Structure; start structure and enumerated site; clean slab; verdicts from 3.4                                        |
| Outputs | Text card with the fields of section 4.2 as a Pydantic model; PNG beside it                                         |
| Rules  | Every structure-producing tool returns its output through the card. The PNG is a second look, never the basis of a decision until the benchmark shows it helps. Cards carry the distances and site labels that CatBERTa's text lacked, so two configurations never share a card |
| Wraps  | pymatgen; the Robocrystallographer pattern; ASE rendering                                                            |
| Logs   | The card beside the structure                                                                                        |

### 3.6 mlip_choice, steps 1\* and 3.3

Choose one potential for IS and FS, with a recorded reason, before any placement; every candidate benchmarked here is the committee of 3.7.

| Field  | Content                                                                                                              |
|--------|----------------------------------------------------------------------------------------------------------------------|
| Inputs | System class; two or three candidate potentials; a few DFT labels if available, else OC20NEB labels                  |
| Outputs | Chosen potential and reason; the calculator every relaxation and force call uses; the list of candidates benchmarked, as the committee of 3.7 |
| Checks | Benchmark on the system class; spin initialised on Co and Ni; the same potential and settings for every IS and FS; cross-family checks on E_ads only, never on total energies |
| Wraps  | `catbench.adsorption.AdsorptionCalculation` and `AdsorptionAnalysis` with `threshold_sensitivity_analysis`; the AtomisticSkills skill `ml-mlip-benchmark`; `fairchem.core.FAIRChemCalculator` with `pretrained_mlip.get_predict_unit`, models `uma-s-1p2p1` and `uma-m-1p1`, task `oc20`; `mace.calculators.MACECalculator`; CHGNet as a cross-family second opinion on E_ads and a magnetic-moment check on Ni and Co; EquiformerV2 only to reproduce CatTSunami numbers, under `fairchem-core==1.10` |
| Logs   | Benchmark results; choice and reason                                                                                 |
| Context | No potential is best everywhere; best adsorption MAE on CatBench is about 0.2 eV; universal MLIPs fail badly on magnetic Co and Ni. Which candidates and how many labels: open: team decision |

### 3.7 mlip_doubt, step 7

Turn committee disagreement into a calibrated doubt that escalates instead of guessing.

| Field  | Content                                                                                                              |
|--------|----------------------------------------------------------------------------------------------------------------------|
| Inputs | The relaxed structures; every candidate potential benchmarked at 1\*, as the committee; a few DFT labels if available, else OC20NEB labels |
| Outputs | A doubt flag per structure with its evidence; escalation to a checkpoint                                            |
| Loop   | Sample a few configurations; label them; measure the error; fine-tune if needed; continue. If repair fails, stop at a checkpoint with the evidence |
| Wraps  | `mace.calculators.MACECalculator` with several files in `model_paths`, returning `energy_var` and `forces_var`, for the MACE members; other families through their own calculators, compared on E_ads only; `uct.metrics.get_all_metrics` from uncertainty-toolbox for calibration error, miscalibration area and recalibration; AtomisticSkills skills `ml-committee-uncertainty`, `ml-mlip-benchmark`, `ml-mace-finetune` |
| Triggers | The committee disagrees, threshold calibrated on the labels, value open: team decision; Co, Ni or another magnetic metal, always, initialise spin; unseen chemistry, oxide, high coverage, electrochemical interface or organometallics outside OC20, always; result outside the expected range, prior width open: team decision |
| Logs   | Labels used; disagreement against the label error; every flag and escalation                                         |

### 3.8 dissociation_final_state, step 3 with points 3.1 to 3.6, and steps 4 to 6

NEBscape's endpoint generator shape with fairchem's helpers and four changes: complete, counted enumeration as the primary generator, with minima hopping kept as the alternative; a nearest-first objective instead of NEBscape's fixed cut-off and the energy–distance Pareto front; the full gate as a test after relaxation instead of Hookean constraints during sampling; a report of every rejection.

| Field  | Content                                                                                                              |
|--------|----------------------------------------------------------------------------------------------------------------------|
| Inputs | The supplied initial state; A and B as structures; d, the length of the bond to break; the calculator and the committee from 3.6; PROJECT.md |
| Outputs | Final states in order with cards; E(FS near); E(FS ∞); rejected pairs with reasons; recombination rate              |
| Checks, 3.5 | All symmetry-distinct placements of A near its IS site, counted; A fixed at its IS site is the cheap baseline; the `geometry-critic` proposes a site type and orientation per fragment and may reorder or add candidates |
| Checks, 3.2 | Pairs ordered by site-graph distance, in-plane tiebreak, within the board's window [1.5 d, 5] Å; whether d is the vacuum or the adsorbed bond length: open: team decision |
| Checks, 3.3 and 4 | One force call per pair; the force component on each fragment along the A–B axis; a pull towards the other fragment above the threshold queues the pair last, never drops it; threshold open: team decision; then relax with random displacement first |
| Checks, 3.1 and 5 | Checks 1 to 11 of 3.4 on every relaxed pair                                                                       |
| Checks, 6 | SOAP clustering of survivors as NEBscape does; keep the lowest-energy configurations per cluster as the board says and the nearest, our objective; configurations per cluster open: team decision |
| Also computes | E(A\*) and E(B\*), each in its own cell with the chosen MLIP and the locked settings, for E(FS ∞); DFT single points are the extension 3.11 |
| Generators | Primary: counted enumeration through 3.2 and 3.3. Alternative and baseline policy: minima hopping with the chosen MLIP, NEBscape's endpoint generator wrapped; its endpoint module is not named in `archive/docs/repo-survey.md`, read it from source before wrapping |
| Recombination rate | Pairs failing check 10 over pairs relaxed; per distance shell or nearest shell only: open: team decision     |
| Wraps  | NEBscape's endpoint generator, MIT, and its SOAP and farthest-point `selection`; secondary, `fairchem.applications.cattsunami.core.autoframe.AutoFrameDissociation` helpers `unwrap_atoms`, `traverse_adsorbate_dissociation`, `is_edge_list_respected`; its `get_best_sites_for_product1` and `get_best_unique_sites_for_product2`, 5 sites each and shells of 2× and 3× the largest slab covalent radius, are the shell-sampling policy we score against; tools 3.2, 3.3, 3.4 and 3.6 |
| Critic | Core at 3.5 and 3.2: the `geometry-critic` reads the cards, proposes a site type and orientation per fragment, AdsMind style, may reorder or add candidates, never removes a pair and never overrides a check |
| Extensions | Coverage scan over cell sizes at 3.2; lowest energy within one site hop at 6                                     |
| Logs   | Counts of placements and pairs; generator used; every critic proposal; every rejection with its reason; E(FS near), E(FS ∞) and their difference; recombination rate |

The later phase, the path from AB\* to the final state and its barrier, is out of scope; its tools and sources are in `archive/docs/agent-build-context.md`, sections 3.9 to 3.11.

### 3.9 final_state_report, the Solution

One auditable record per reaction, with every number traced to a tool output.

| Field  | Content                                                                                                              |
|--------|----------------------------------------------------------------------------------------------------------------------|
| Inputs | Outputs of 3.4 to 3.8 and 3.10; the decision trace; DFT single points when the extension 3.11 ran                    |
| Outputs | The report of section 4.5                                                                                           |
| Checks | Every number traces to a tool output; the AtomisticSkills `general-peer-review` skill reads the draft                |
| Wraps  | AtomisticSkills hyperparameter logging; Zenodo export. Logs the full decision trace                                   |

### 3.10 Human checkpoint and lessons log, T8, step 8 and every checkpoint

Stop where a wrong choice silently corrupts every later number; show the evidence; record the choice and its reason. T8 is a procedure the `final-state-planner` follows and the hook enforces, not a tool.

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

### 3.11 Extension: dft_single_points, T9

Score the chosen final states and the separated fragments with DFT at the locked settings. It runs only with HPC and a DFT code; the core scores with the chosen MLIP.

| Field  | Content                                                                                                              |
|--------|----------------------------------------------------------------------------------------------------------------------|
| Inputs | Kept final states; A\* and B\* in their own cells; PROJECT.md                                                        |
| Outputs | DFT single points, then relaxed endpoints; force calls; failures                                                    |
| Checks | Settings-mismatch check against PROJECT.md before submission; 0.02 to 0.03 eV/Å for relaxations; custodian handlers run before any LLM diagnosis; a failed job goes to the `dft-job-steward` to diagnose, adjust and resubmit |
| Wraps  | ASE calculators; atomate2 through the AtomisticSkills atomate2 MCP server; `custodian.vasp.handlers.VaspErrorHandler`, `UnconvergedErrorHandler`, `PotimErrorHandler`; VASP or Quantum ESPRESSO |
| Logs   | DFT force calls and failure rate; every diagnosis and resubmission                                                   |

## 4. Data records

The docs list fields but fix no file format or schema for the five records: open: team decision. Model each as a Pydantic class in `finalstate/`.

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

The lessons log, `lessons.md`, is the case bank: one file, two names in the archive. It stores raw cases, not distilled lessons, because a raw case bank scores highest. The `final-state-planner` retrieves cases by system and failure; only a human promotes a case into a skill line, a check or a prior. Seed: CO on Pt-group metals, Ni and Co magnetism, the symmetry trap.

| Memory form                                   | Score                      | Source                                                   |
|-----------------------------------------------|----------------------------|----------------------------------------------------------|
| None                                          | 49 %                       | [CatDT](https://arxiv.org/html/2606.05050) ablation       |
| Distilled knowledge or skill banks            | 52 to 54 %                 | CatDT ablation                                           |
| Raw case bank                                 | 68 %                       | CatDT ablation                                           |
| Full stack                                    | 84 %                       | CatDT ablation                                           |
| Self-written skills                           | lose 8 to 12 points        | [SkillsBench](https://arxiv.org/html/2602.12670)          |

| Field      | Content                                                                   |
|------------|---------------------------------------------------------------------------|
| Structure  | The descriptor card as the `final-state-planner` saw it                   |
| System     | "Ni(111)"                                                                 |
| Correction | "set initial magnetic moments"                                            |
| Reason     | "or SCF fails"                                                            |
| Source     | The checkpoint where it was made: flagged-case review or the pick of final states |
| Becomes    | A skill line, a check or a prior, once it recurs and a human promotes it; recurrences before promotion open: team decision |

### 4.4 Decision trace

`runs/<campaign>/trace.jsonl`; format open: team decision. Entries and who writes them:

| Entry                                              | Written by |
|----------------------------------------------------|------------|
| Settings as supplied; protocol choice and reason   | 3.1        |
| Counts of sites, orientations and pairs            | 3.2, 3.8   |
| Every verdict and rejection, with its reason       | 3.4, 3.8   |
| MLIP choice and reason; doubt flags; escalations   | 3.6, 3.7   |
| Critic proposals and what they changed             | 3.8        |
| Human choices and reasons                          | 3.10       |
| Failed-job diagnoses and resubmissions             | 3.11, extension |

### 4.5 Report

| Field                               | Note                                                                         |
|-------------------------------------|------------------------------------------------------------------------------|
| Final states                        | In order; the up to five the human picked; E(FS near), E(FS ∞), lateral interaction per kept state |
| Rejected pairs                      | With reasons; recombination rate of nearest pairs                            |
| ML uncertainty                      | Calibrated doubt from 3.7                                                    |
| Comparison with OC20NEB             | Our final state against the product frame: A–B distance, energy, validity    |
| Cost                                | ML force calls; DFT force calls and failures when the extension 3.11 ran     |
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
8. Never override a code check. The `geometry-critic` proposes and reorders candidates at 3.5 and 3.2 and comments on cards elsewhere; it never removes a pair.
9. On ML doubt: stop, measure, repair, and ask only if repair fails.
10. Diagnose failed jobs: read the errors, adjust, resubmit.
11. Never pair a failing state. Report rejected pairs; never hide them.
12. Gather at most one or two published E_ads values, with functional and site, for a human to verify. Never cite from memory.
13. Do not write skills. Skills are few, human-written and procedural; facts and ranges live in code and PROJECT.md.

## 6. The roster

Four agents and five skills of ours: four core, hpc-dft-jobs only with HPC. The roster is short because selection precision falls with skill count and self-written skills gain nothing, as the table shows. Add a role only when a human can say in one sentence what it decides, and a skill only when a human has written and checked it.

| Finding                                         | Number                                          | Source                                                                 |
|-------------------------------------------------|-------------------------------------------------|------------------------------------------------------------------------|
| Selection precision falls as the pool grows     | 29.6 % with 5 skills; 3.3 % with 100            | [Demystifying Agent Skills](https://arxiv.org/abs/2608.14036)          |
| Curated human-written skills raise success      | about 16 points over 84 tasks                   | [SkillsBench](https://arxiv.org/html/2602.12670)                        |
| Self-written skills gain nothing                | No gain or a loss                               | SkillsBench                                                            |
| Many agents, nothing to copy per agent          | CatDT runs eight agents and has released no code | [CatDT](https://arxiv.org/html/2606.05050)                            |
| The human sets the agenda                       | About 1 % of the Virtual Lab's words            | [Virtual Lab](https://biohub.org/news/with-no-need-for-sleep-or-food-ai-built-scientists-get-the-job-done-quickly/) |

| Agent                    | Decides                                                              | Status                         | Pattern copied from                               |
|--------------------------|----------------------------------------------------------------------|--------------------------------|---------------------------------------------------|
| final-state-planner      | The next tool call and when to stop; holds the checkpoint list       | Core                           | AdsMind's pick-from-labels interface; CatDT's propose and validate rounds with fatal violations in code; TSAgent's replan log; El Agente Potente's typed graph for 3.1 to 3.6 |
| dft-settings-interviewer | What the Formulate interview locks into PROJECT.md                   | Core, runs once before the run | Get Physics Done's Formulate step; AutoDFT's settings rules; DREAMS's comparability judge |
| geometry-critic          | The site type and orientation to try per fragment at 3.5 and 3.2; whether a card and its verdicts disagree; never overrides | Core at 3.5 and 3.2; comments on gate cards as an extension | Adsorb-Agent's site-versus-binding-atom check; AdsMind's site-type proposal; AtomWorld and LLMConfBench on cards not coordinates |
| dft-job-steward          | Resubmit, adjust or escalate a failed DFT job                        | Only with HPC, extension 3.11  | AutoDFT's capped recovery; TSAgent's failure taxonomy; VASPilot's handlers |

The critic is separate so it cannot see the planner's reasoning and be anchored; the interviewer, so the planner cannot rewrite its fixed questions. `general-peer-review` from AtomisticSkills reviews the report; it is a reused skill, not a new role.

| Skill, ours              | Procedure                                                       | Status        |
|--------------------------|-----------------------------------------------------------------|---------------|
| dft-settings-protocol    | Pseudopotentials, cutoff, k-mesh, smearing, layers; the lock    | Core          |
| mlip-doubt-calibration   | Committee disagreement against DFT labels; when to escalate     | Core          |
| dissociation-final-state | 3.1 to 3.6; what to report                                        | Core          |
| final-state-report       | Report format: both energies, rejections, trace                 | Core          |
| hpc-dft-jobs             | Submission; what custodian handles; what to escalate            | Only with HPC |

Reused from AtomisticSkills: `ml-committee-uncertainty`, `ml-mlip-benchmark`, `ml-mace-finetune`, `chem-thermochemistry`, `general-peer-review`. Ten in all keeps selection precision high. Each skill stays under 200 lines and names its tools.

## 7. Repository layout

A Claude Code plugin beside AtomisticSkills. Three rules: each file has one kind and lives in that kind's folder; calls go one way, agents to skills to tools to the library, never up or sideways; one reading order for a human and one for an agent.

```
open-science-hackathon/
├── README.md                     the human entry point: problem, simplified and full pipeline, how to run the first case
├── CLAUDE.md                     points here
├── agent.md                      this file
├── PROJECT.md                    the locked settings and decisions of the current campaign
├── pyproject.toml                one package: the library, the server and the tests
├── archive/docs/                 design document, agent context, build context, survey, review, figures
├── figures/                      the README figures: problem, simplified and full pipeline, build plan, layout
├── .claude-plugin/plugin.json    declares the skills, agents, hooks and the MCP server
├── skills/<name>/SKILL.md        the five skills of section 6, one folder each
├── agents/<role>.md              the four agents of section 6, one page each
├── hooks/hooks.json              blocks coordinate edits; pauses at human checkpoints
├── mcp/server.py                 registers the tools on the MCP Python SDK
├── mcp/tools/                    dft_settings_lock, site_enumeration, adsorbate_placement, validity_gate,
│                                 descriptor_card, mlip_choice, mlip_doubt, dissociation_final_state,
│                                 final_state_report; extension: dft_single_points
├── finalstate/                   pure Python, no LLM, no MCP: one module per tool, same name
├── tests/                        one test file per tool; Burnside on C4v; the gate on known failures
├── benchmark/                    OC20NEB subset, baselines, scoring scripts, results
├── runs/<campaign>/              PROJECT.md copy, trace.jsonl, cards/, structures/, report.md
└── lessons.md                    the lessons log; a human promotes entries
```

| Reader   | Reads, in order                                                                     |
|----------|-------------------------------------------------------------------------------------|
| A human  | `README.md`, `PROJECT.md`, the run's `report.md`, `lessons.md`                      |
| An agent | `CLAUDE.md`, `agent.md`, the skill it was given, the tool docstrings                |

| Kind    | Folder                              | One item is                                       | May call           | Holds logic |
|---------|-------------------------------------|---------------------------------------------------|--------------------|-------------|
| Agent   | `agents/`                           | A one-page role: what to do next and when to stop | Skills, tools      | No          |
| Skill   | `skills/<name>/`                    | A procedure, step by step, naming tools           | Tools              | No          |
| Tool    | `mcp/tools/`                        | One typed entry point, one file                   | One library module | No          |
| Library | `finalstate/`                       | One module per tool, same name                    | Other modules      | Yes, tested |
| Test    | `tests/`                            | One file per tool                                 | The library        | No          |
| Data    | `runs/`, `benchmark/`, `lessons.md` | Outputs, never code                               |                    | No          |
| Docs    | `archive/docs/`, `figures/`         | What and why; never how to call                   |                    | No          |

Naming: `mcp/tools/validity_gate.py` wraps `finalstate/validity_gate.py`, tested by `tests/test_validity_gate.py`. Names say what is computed in the field's words: `dissociation_final_state`, not `final_state`; `geometry-critic`, not `critic`. Licences: ASE, ACAT and Sella are LGPL and may be imported; CatKit, Pynta, arkimede and CatMAP are GPL, copy their ideas only; TSAgent and Adsorb-Agent state no licence; UMA weights need a Hugging Face account and the FAIR Chemistry License.

## 8. Compute lanes

HPC is needed for DFT and nothing else, and DFT is an extension: the laptop and GPU lanes complete the pipeline.

| Lane   | Steps                                                            | Without HPC in the hackathon                                                                 |
|--------|------------------------------------------------------------------|----------------------------------------------------------------------------------------------|
| Laptop | 1 lock from the supplied settings; 2 to 4; 5; 6; 8; 3.5; 3.2; 5; 14 | Unchanged                                                                                  |
| GPU    | 1\* benchmark; 7 committee; 3.3 force calls and relaxations; 6 MLIP energies; ML frequencies | Unchanged; one workstation or cloud GPU                          |
| HPC, extensions only | Settings sweep when no relaxed inputs exist; DFT calibration labels for 7; DFT single points of 3.11; DFT frequencies | Not needed: OC20's RPBE and PAW values as the settings record; OC20NEB's released DFT bands as labels and ground truth; one DFT check run beforehand and recorded, if available |

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

Build the eight numbered tasks first; they are the shortest route to one validated nearest final state. Task IDs D, T, P, M and R are the build plan's.

Critical path:

- [ ] 1 · D1 System and product: AB\*, surface, A\* + B\*; first case \*OH → \*O + \*H on Pt(111). Human decision.
- [ ] 2 · T1 `dft_settings_lock`, 3.1. Needs D1, D3.
- [ ] 3 · T2 `site_enumeration`, 3.2. Needs T1.
- [ ] 4 · T4 `validity_gate`, 3.4. Needs T3.
- [ ] 5 · T6 `mlip_choice`, 3.6. Needs D2.
- [ ] 6 · P1 `dissociation_final_state`, 3.8. Needs T2, T4, T6, D5.
- [ ] 7 · M2 \*OH → \*O + \*H final state against the OC20NEB product frame. Needs P1, P5, D3.
- [ ] 8 · R1 Release: SKILL.md files, MCP tools beside AtomisticSkills, benchmark data and traces on Zenodo. Needs M1, M2.

Off-path tasks, built when the path needs them:

| Group               | Task                                                                                       | Needs          |
|---------------------|--------------------------------------------------------------------------------------------|----------------|
| Decide first        | D2 compute and codes; D3 benchmark and pass criterion; D4 headline claim; D5 final-state rules | Humans      |
| Foundations         | T3 `adsorbate_placement`, 3.3; T5 `descriptor_card`, 3.5                                    | T2; T4         |
| ML trust            | T7 `mlip_doubt`, 3.7; T8 rank and human checkpoint with the lessons log, 3.10               | T6, T4; T5, T7 |
| Final state         | P5 `final_state_report`, 3.9                                                               | P1, T7         |
| Measure             | M1 H on Pt(111) end to end; M4 Ni(111) doubt demo; M3 the three later numbers              | T1 to T8; T7, T8; P1, P3, D2 |
| LLM and human layer, last | SKILL.md files; interview and PROJECT.md template; `lessons.md` seeded; `final-state-planner` that calls tools by name and stops at checkpoints; `geometry-critic` at 3.5 and 3.2; hooks | The tools |
| Extensions, later   | T9 `dft_single_points`, 3.11, DFT on the chosen five; T10 active-learning loop; M5 agentic uncertainty, N planner runs; `geometry-critic` on gate cards at 5; coverage scan at 3.2; one-hop target at 6; settings sweep and AB\* enumeration when no relaxed inputs exist | T8, D2; T7, D2; T8, P5 |

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
| Autonomy level; which checkpoints Balanced skips; recurrences before a case is promoted                     | T8, `final-state-planner`   |
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
- Review of what none of them do: `archive/docs/chemistry-agents-review.md`.

Tools wrapped, each opened on 21 October 2026, details in `archive/docs/repo-survey.md`:

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
