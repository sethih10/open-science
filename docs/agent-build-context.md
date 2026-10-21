# Build context: the nearest non-recombining final state and the barrier to it

Audience: a coding agent or a developer who builds the software the design documents describe. This file gathers what the code needs: steps and owners, tools with inputs, outputs and thresholds, data formats, rules for the LLM, the benchmark and the build order. It adds no knowledge of its own. It is drawn from `agent-context.md`, `adsorption-agent-workflow.md` and the scripts for figures 22 and 23. When it differs from `adsorption-agent-workflow.md`, the design document is right and this file is wrong. Write code comments and docs as `agent-writing-style.md` says.

Conventions:

- "open: team decision" marks a value or a choice the docs do not fix. Do not fill it in from memory. Expose it as a named parameter without a default, and ask.
- Step numbers are the planner's: 1 to 14, with 4.1 and 9a to 9e, as in `agent-context.md` sections 21 to 23.
- Task IDs are the build plan's: D, T, P, M and R, as in `docs/figures/src/22-build-plan.py`.

## 1. Purpose and problem

The software finds the closest final state in which the two fragments of a dissociated adsorbate do not bond back. It then computes the barrier from the initial state to that final state. A validated nearest final state gives a short band with one saddle. The DFT nudged-elastic-band calculation then needs fewer force calls and fails less often.

The problem in the team's words:

> Given an input system (surface + adsorbate) and desired product/final state (surface + cleaved adsorbate #1 + dissociated part of the adsorbate #1, which needs to be adsorbed as well, so it is effectively adsorbate #2), determine the product/final state such that adsorbate #2 is as close to adsorbate #1 as possible while remaining fully dissociated, i.e. the two do not bond back.

In the docs' notation the adsorbate is AB\*. Adsorbate #1 is A, the fragment that keeps the binding atom; adsorbate #2 is B. The rule: over every symmetry-distinct pair of sites, one for A and one for B, minimise the site-graph distance between A\* and B\*, with the in-plane distance as tiebreaker, subject to the final-state gate of section 3.8. Keep the first few survivors in that order. Then pair each with the chosen initial states, run an ML band with a climbing image, validate the saddle, refine with DFT and report. The nearest product is not always the lowest in energy, because adjacent fragments can repel, so report both.

| Item          | Content                                                                                                         |
|---------------|-----------------------------------------------------------------------------------------------------------------|
| Input         | Slab with AB\*; product named as A\* + B\*; both fragments stay adsorbed                                        |
| Output, first | Several nearest non-recombining final states in order; rejected pairs with reasons; recombination rate of nearest pairs |
| Output, then  | Barrier from AB\* to each kept final state; validated path; ML and agentic uncertainty; decision trace; DFT band cost |
| First case    | \*OH → \*O + \*H on Pt(111), against the OC20NEB DFT band                                                       |

Quantities the code computes:

- Barrier and reaction energy: `E_a = E(TS) − E(IS)`, `ΔE = E(FS) − E(IS)`.
- Separated product: `E(FS ∞) = E(A*) + E(B*) − E(slab)`, from separate cells with the locked settings.
- Lateral interaction: `E(FS near) − E(FS ∞)`.
- Rate factor of an energy error δ: `exp(δ / k_B T)`; at 500 K, `k_B T ≈ 0.043 eV`.
- Adsorption energy: `E_ads = E(slab+A) − E(slab) − E(A)`, with E(A) the locked gas-phase reference.

## 2. Owners

Tools do every deterministic step. The LLM chooses with a stated reason, diagnoses failures and drafts. Humans approve, pick and interpret. Skills hold the procedures the LLM follows. Where the docs name more than one owner, all are listed; the first does the work.

| Owner      | Means                                                                                          |
|------------|------------------------------------------------------------------------------------------------|
| Tool       | Deterministic code, exposed as an MCP tool                                                     |
| LLM        | The planner model: plans, chooses and explains, diagnoses, drafts; acts only through tool calls |
| Human      | A checkpoint: the agent stops and waits                                                        |
| Skill      | A procedure in SKILL.md that the LLM follows                                                   |
| Literature | Enters before the run and after it only; a human verifies every value                          |

| Step         | What                                                                                     | Owner      | Also named in the docs                                       |
|--------------|------------------------------------------------------------------------------------------|------------|--------------------------------------------------------------|
| Before 1     | Formulate interview: five questions, scope, assumptions, notation, verification targets, autonomy level | Human | Skill holds the questions                               |
| Before 1     | Literature check: settings, references, known failures for this system                   | Literature | Human verifies                                               |
| 1            | Choose system, product and physics settings                                              | Human      | Literature                                                   |
| 1            | Retrieve and lock: slab, AB, A and B as structures; gas references; settings in PROJECT.md | Tool     | Human approves; Skill for the settings protocol              |
| 1            | Pseudopotential lookup; converge cutoff, k-mesh, smearing, layers, vacuum, dipole correction | Tool   | LLM picks the protocol and explains                          |
| 1            | Force and SCF thresholds                                                                 | Skill      |                                                              |
| 1            | Approve settings; approve the plan before execution                                      | Human      |                                                              |
| 1            | Bulk relaxation; slab construction                                                       | Tool       |                                                              |
| 2 to 4       | Initial state AB\*: sites, orientations, placement, counted                              | Tool       |                                                              |
| 4.1, 6       | Validity gate on every structure                                                         | Tool       | LLM critic comments, extension only                          |
| 5            | ML relaxation                                                                            | Tool       |                                                              |
| 5, 7         | MLIP choice and calibrated doubt                                                         | Tool       | LLM chooses and explains; Skill for when to doubt            |
| Any          | Diagnose failed jobs: read errors, adjust, resubmit                                      | LLM        |                                                              |
| Any          | Review flagged cases                                                                     | Human      |                                                              |
| 8            | Rank initial states                                                                      | Tool       |                                                              |
| 8            | Pick up to five initial states                                                           | Human      | On cards the LLM prepares                                    |
| 9a to 9d     | Place A; enumerate B sites around A, nearest first; relax each A\* + B\* pair; gate each pair | Tool  |                                                              |
| 9e           | Choose the final states                                                                  | Tool       | LLM writes the choice up                                     |
| 10           | Atom mapping and IS–FS pairing                                                           | Tool       |                                                              |
| 11           | ML band and climbing image                                                               | Tool       |                                                              |
| 12           | Saddle and band validation                                                               | Tool       | LLM diagnoses a failure; Skill for the diagnosis procedure   |
| 13           | DFT refinement                                                                           | Tool       | LLM diagnoses failed jobs                                    |
| After 13     | Energies and curves; benchmark comparison                                                | Tool       |                                                              |
| 14           | Report                                                                                   | LLM drafts | Human interprets; Skill for the report format                |
| After 14     | Interpret results                                                                        | Human      |                                                              |
| After review | Lessons-log entry: the correction and its reason                                         | Human      |                                                              |
| On recurrence | Promote a lesson to the skill, a check or a prior                                       | Human, since skills are human-written | Trigger: open: team decision      |

## 3. Tools to implement

Every tool returns each structure it produces through the descriptor card of section 3.5. Every tool logs every parameter beside its outputs, as AtomisticSkills does. The docs name five calls: `enumerate_sites(slab)`, `place(site, orientation, height)`, `displace(amplitude)`, `check(structure)` and `render(structure)`. The docs do not name the other calls; the headings below are working labels, open: team decision. Write each tool's documentation for the model, following the MatTools finding.

### 3.1 Settings lock and convergence: T1, step 1

| Field     | Content                                                                                                    |
|-----------|------------------------------------------------------------------------------------------------------------|
| Purpose   | Fix every numerical setting by a verified protocol or a sweep on E_ads. Lock them with the human's physics choices in PROJECT.md before any structure is computed. One file serves IS, FS and band |
| Inputs    | Physics choices from the human; metal, facet, test adsorbate; protocol chosen by the LLM with its reason; DFT code |
| Outputs   | Settings block and sweep data in PROJECT.md; every later tool reads it                                     |
| Procedure | One test adsorbate on the target surface; sweep cutoff, k-mesh, smearing and layers; report the cheapest setting with E_ads inside the target of the converged value |
| Wraps     | AiiDA common workflows with fast, moderate and precise protocols; SSSP; pymatgen input sets; ASE; VASP or Quantum ESPRESSO |
| Logs      | Protocol and the LLM's reason; every sweep point; chosen values; pseudopotential family and version        |
| Rejected  | The LLM writing cutoff or k-points from memory                                                             |

| Setting            | Rule                                                                                       | Value in the docs                                                    |
|--------------------|--------------------------------------------------------------------------------------------|----------------------------------------------------------------------|
| Pseudopotentials   | Library recommendation; never mix families or versions; same dataset per element in bulk, slab and gas | VASP: recommended PAW, `_pv` or `_sv` where semicore states matter; QE: SSSP efficiency for screening, precision for final numbers; PBE 54 is the Materials Project and atomate2 default |
| Cutoff             | Start at the largest ENMAX in the cell, × 1.3 if the cell volume relaxes; converge E_ads, not the total energy | OC20: 350 eV; Materials Project: 520 eV       |
| k-mesh             | Γ-centred on hexagonal cells; one k-point along vacuum; same mesh for slab and slab+A; cell-consistent density | 0.2–0.3 Å⁻¹ in-plane; OC20: 40 / in-plane cell length |
| Smearing           | Methfessel–Paxton or Marzari–Vanderbilt; report E extrapolated to σ → 0                    | σ = 0.1–0.2 eV                                                       |
| Layers             | Add until E_ads stops changing; fix the bottom layers                                       | ≥ 4 for close-packed metals; fixed count open: team decision         |
| Vacuum             | Converge                                                                                   | ≥ 12–15 Å                                                            |
| Dipole correction  | On when only one face is covered                                                           |                                                                      |
| Cell width         | The pair never sees its periodic image                                                     | Periodic images ≥ 10 Å apart; which atoms are measured: open: team decision |
| Convergence target | Cheapest setting inside the target                                                         | ±10 meV in the protocol; 10 or 25 meV: open: team decision           |
| Force, SCF         | Convention from SKILL.md                                                                   | 0.02–0.03 eV/Å; 1e-5 to 1e-6 eV                                      |
| Benchmark match    | If OC20NEB is the ground truth, the lock matches OC20                                      | RPBE and PAW; open: team decision                                    |

The next steps name H on Pt(111) as the first sweep. The test adsorbate for the \*OH case is open: team decision.

### 3.2 Site and pair enumeration: T2, steps 2, 4, 9a, 9b

| Field      | Content                                                                                                  |
|------------|----------------------------------------------------------------------------------------------------------|
| Purpose    | List every symmetry-inequivalent site, orientation and A–B pair, with the count                          |
| Calls      | `enumerate_sites(slab)`; the pair call name is open: team decision                                       |
| Inputs     | Slab built with the locked settings; AB, A and B as structures                                            |
| Outputs    | Sites with label, site group, coordination and atom beneath; orientations inequivalent under the site's stabiliser group; pairs with site-graph distance and in-plane distance; the count N |
| Checks     | Sites are the inequivalent high-symmetry Wyckoff positions of the slab's layer group; fcc and hcp hollows told apart by the atom beneath; N = (1/\|G\|) Σ \|X^g\| checked against the explicit list |
| Unit tests | Two identical adsorbates on the corners of a square cell under C4v give N = 2; the site table of `agent-context.md` section 3 |
| Wraps      | spglib; ACAT SlabAdsorptionSites for labelled sites, get_graph and get_neighbor_site_list for the site-graph distance, SystematicPatternGenerator for unique pairs; CatKit as a pattern only (GPL); pymatgen as the baseline |
| Logs       | Symmetry group; every site, orientation and pair; N and its check                                         |
| Baseline   | AtomisticSkills mat-surface-adsorption: MatCalc AdsorptionCalc on pymatgen's AdsorbateSiteFinder, now in pymatgen.core.adsorption; the mat-htvs skills of the paper are not public |
| Open       | Definition of the site graph; site-graph or in-plane distance alone: D5                                  |

### 3.3 Placement: T3, steps 3, 9a, 9b

| Field   | Content                                                                                                 |
|---------|---------------------------------------------------------------------------------------------------------|
| Purpose | Put an adsorbate or fragment at an enumerated site, orientation and height, by script                   |
| Calls   | `place(site, orientation, height)`, `displace(amplitude)`                                               |
| Inputs  | Site and orientation from 3.2; conformer relaxed in vacuum first; height                                |
| Outputs | Structure and its descriptor card                                                                       |
| Checks  | Start 2–3 Å above the site, not 10 Å; small random displacement before every relaxation, against the symmetry trap; few conformers |
| Wraps   | ASE, CatKit; AdsorbML heuristic plus random placement as fallback when symmetry is unknown              |
| Logs    | Site, orientation, height, displacement amplitude and the random draw, conformer source                 |
| Open    | Displacement amplitude, shown in the docs only as an example call of 0.05 Å; number of conformers       |

### 3.4 Validity gate: T4, steps 4.1, 6, 9d

| Field   | Content                                                                                                     |
|---------|-------------------------------------------------------------------------------------------------------------|
| Purpose | One code path that gives a verdict on every structure, initial and final, before ranking or pairing. A failing state is never paired |
| Call    | `check(structure)`                                                                                          |
| Inputs  | Relaxed structure; its start structure and enumerated site; clean slab; settings record; E_ads prior; vibrational frequencies |
| Outputs | Pass or fail per check, with the measured value and the reason, written into the descriptor card            |
| Wraps   | fairchem DetectTrajAnomaly for AdsorbML's four checks; ASE vibrations; ACAT SlabAdsorbateCoverage for the moved-site check. DetectTrajAnomaly treats A* + B* as one adsorbate, so check 1 runs per fragment |
| Logs    | Every verdict with its measured value; every rejection with its reason                                      |

| #  | Check                  | Fails when                                                        | Threshold in the docs                          |
|----|------------------------|-------------------------------------------------------------------|------------------------------------------------|
| 1  | Desorbed               | Adsorbate centre too far above the surface plane; per fragment for a pair | > 3 Å; surface-plane definition open    |
| 2  | Migrated               | Adsorbate ends on another site than the one enumerated            | Site label differs; distance open              |
| 3  | Dissociated            | An intramolecular bond stretched beyond its breaking threshold    | Open: team decision                            |
| 4  | Reconstructed          | Surface atoms displaced from their clean-slab positions           | Open: team decision                            |
| 5  | Not a minimum          | One or more imaginary vibrational modes                           | Zero allowed; noise cutoff in cm⁻¹ open        |
| 6  | Magnetism collapsed    | Total moment of a magnetic slab vanishes on adsorption            | Open: team decision                            |
| 7  | Outside expected range | E_ads far from the prior for this adsorbate and metal             | H on Pt(111) near −0.5 eV; width open          |
| 8  | Settings mismatch      | Slab and slab+A differ in cutoff, mesh, smearing or pseudopotentials | Exact equality                              |
| 9  | Intercalated           | An adsorbate atom below the top surface layer                     | Open: team decision                            |
| 10 | Bond re-formed, FS only | A and B bonded again after relaxation                            | A–B distance threshold open: team decision     |
| 11 | Periodic image, FS only | The pair interacts with its periodic images                      | Images ≥ 10 Å apart                            |

The gate has nine checks on every structure, checks 1 to 9, as in section 6 of `agent-context.md`; the final-state gate adds checks 10 and 11. Figure 23 runs the gate before and after relaxation; which checks run before is open: team decision. Whether frequencies come from the MLIP or from DFT is open: team decision.

### 3.5 Descriptor card: T5

| Field   | Content                                                                                     |
|---------|---------------------------------------------------------------------------------------------|
| Purpose | Turn every structure into the text the LLM reads; the only view of geometry the LLM gets    |
| Call    | `render(structure)` for the image                                                           |
| Inputs  | Structure; start structure and enumerated site; clean slab; verdicts from 3.4               |
| Outputs | Text card with the fields of section 4.2; PNG beside it                                     |
| Rules   | Every structure-producing tool returns its output through the card. The PNG is a second look, never the basis of a decision until the benchmark shows it helps |
| Wraps   | pymatgen; the Robocrystallographer pattern; ASE render                                      |
| Logs    | The card beside the structure                                                               |
| Open    | Card layout; a machine-readable twin; fields for A\* + B\* pairs                            |

### 3.6 MLIP choice and calibrated doubt: T6, T7, steps 5, 7

| Field   | Content                                                                                                     |
|---------|-------------------------------------------------------------------------------------------------------------|
| Purpose | Choose one potential for IS, FS and band with a recorded reason. Turn ensemble disagreement into a calibrated doubt that escalates instead of guessing |
| Inputs  | System class; two or three candidate potentials; a few DFT labels                                           |
| Outputs | Chosen potential and reason; a doubt flag per structure with its evidence; escalation to a checkpoint      |
| Loop    | Sample a few configurations; label them with DFT; measure the error with ml-mlip-benchmark; fine-tune with ml-mace-finetune if needed; continue. If repair fails, stop at a checkpoint with the evidence |
| Wraps   | AtomisticSkills ml-committee-uncertainty, ml-mlip-benchmark, ml-mace-finetune; FairChem UMA, MACE and MatGL servers; MACE committees for variance; uncertainty-toolbox for calibration; CatBench for the choice; CHGNet as a cross-family check on E_ads |
| Logs    | Benchmark results; choice and reason; labels used; disagreement against DFT error; every flag and escalation |
| Context | No potential is best everywhere; best adsorption MAE on CatBench is about 0.2 eV; universal MLIPs fail badly on magnetic Co and Ni |

| Trigger          | Fires when                                                                     | Threshold                                     |
|------------------|--------------------------------------------------------------------------------|-----------------------------------------------|
| Disagreement     | Two universal MLIPs disagree                                                   | Calibrated on DFT labels; value open: team decision |
| Magnetic metal   | Co, Ni or another magnetic metal                                               | Always; initialise spin                       |
| Unseen chemistry | Oxide, high coverage, electrochemical interface, organometallics outside OC20 | Always                                        |
| Out of range     | Result outside the expected range                                              | Prior width open: team decision               |

### 3.7 Human checkpoint and lessons log: T8, step 8 and every checkpoint

| Field    | Content                                                                                           |
|----------|---------------------------------------------------------------------------------------------------|
| Purpose  | Stop where a wrong choice silently corrupts every later number; show the evidence; record the choice and its reason |
| Inputs   | Descriptor cards, rank, uncertainty, verdicts, doubt evidence                                     |
| Outputs  | The human's choice and reason; a lessons-log entry                                                |
| Wraps    | AtomisticSkills rule that a plan is reviewed before execution; the rest is ours                   |
| Logs     | Every checkpoint: what was shown, the choice, the reason                                          |
| Autonomy | Supervised or Balanced, as in Get Physics Done; which checkpoints Balanced skips: open: team decision |
| Seed     | Lessons log starts with CO on Pt-group metals, Ni and Co magnetism, the symmetry trap             |

| Checkpoint                                    | Shown                                     | Recorded                                |
|-----------------------------------------------|-------------------------------------------|-----------------------------------------|
| Approve settings, and the network for pathways | PROJECT.md with the sweep                | Approval; the lock                      |
| Approve the plan                              | The plan                                  | Approval                                |
| Review flagged cases                          | Cards that failed a check; doubt evidence | Decision and reason, to the lessons log |
| Pick up to five initial states                | Cards, rank, uncertainty                  | Choice and reason, to the lessons log   |
| Interpret results                             | The report                                | Interpretation                          |

### 3.8 Nearest non-recombining final state: P1, sub-steps 9a to 9e

The tool is CatTSunami's AutoFrameDissociation with four changes: complete enumeration, an explicit nearest-first objective, the full gate, and a report of what was rejected.

| Sub-step | Does                                                    | CatTSunami does                                  | We do                                                                 | Output                                   |
|----------|---------------------------------------------------------|--------------------------------------------------|-----------------------------------------------------------------------|------------------------------------------|
| 9a       | Place A, the fragment that keeps the binding atom, near the IS site | 5 lowest-energy placements within 2 Å of the old binding site | All symmetry-distinct placements, counted, or A fixed at its IS site: D5 | Placements of A\*, counted        |
| 9b       | Enumerate B sites around each A                         | 5 placements in a 1–3 Å shell, 25 pairs          | All symmetry-distinct pairs ordered by site-graph distance, in-plane tiebreak, counted | Ordered pairs and their count |
| 9c       | Relax every pair                                        | MLIP relaxation                                  | Same potential and settings as the IS; random displacement first      | Relaxed pairs                            |
| 9d       | Gate every pair                                         | Discard frames where the products react or another anomaly occurs | Checks 1 to 11 of 3.4; every rejection logged with its reason | Survivors; rejections with reasons |
| 9e       | Choose                                                  | One survivor at random                           | Nearest survivor first, then energy; keep several                     | Final states; E(FS near); E(FS ∞); recombination rate |

| Field   | Content                                                                                                    |
|---------|------------------------------------------------------------------------------------------------------------|
| Also computes | E(A\*) and E(B\*), each in its own cell with the locked settings, for E(FS ∞)                         |
| Gate note | Check 3 applies within A and within B; the A–B bond is check 10. The docs' 9d list names checks 1, 2, 4, 5, 9 and 10; "the same gate as the IS" adds the rest |
| Recombination rate | How often the nearest pair bonds back: pairs failing check 10 over pairs relaxed; per distance or nearest shell only is open: team decision |
| Wraps   | fairchem AutoFrameDissociation; tools 3.2, 3.3, 3.4 and 3.6                                                 |
| Logs    | Counts of placements and pairs; every rejection with its reason; E(FS near), E(FS ∞) and their difference; recombination rate |
| Open    | The three D5 questions; the A–B threshold; how many survivors to keep                                      |
| Extensions | Coverage scan over cell sizes at 9b; lowest energy within one site hop at 9e                            |

### 3.9 Atom mapping, pairing and the intended-reaction check: P2, step 10

| Field   | Content                                                                                                     |
|---------|-------------------------------------------------------------------------------------------------------------|
| Purpose | Pair each chosen IS with each kept FS so the same atoms sit at both ends, unwrapped across the cell, and confirm the pair is the intended reaction |
| Inputs  | Up to five IS; several FS; the reaction AB\* → A\* + B\*                                                    |
| Outputs | Mapped IS–FS pairs ready for interpolation; pairs tried and rejected, with reasons                          |
| Checks  | The atom map keeps every atom and element; unwrap by depth-first search from the binding atom, the unbroken part moved as one moiety; symmetry alignment of the endpoints; mirror-equivalent pairs computed once |
| Intended reaction | The bond graphs of IS and FS differ only by the A–B bond. This reading is derived from CatTSunami's band check; confirm it: open: team decision |
| Wraps   | CatTSunami unwrap_atoms and traverse_adsorbate_dissociation; NEBscape atommapper, minimize_rmsd and resolve_pbc (MIT)   |
| Logs    | Every pair tried, kept or rejected, with the reason                                                          |
| Open    | Bond cutoffs for the connectivity graph; how many pairs per reaction                                        |

### 3.10 ML band and climbing image: P3, step 11

| Field   | Content                                                                                                  |
|---------|----------------------------------------------------------------------------------------------------------|
| Purpose | Find the saddle on the MLIP. A wrapped tool; no claim rests on it                                        |
| Inputs  | Mapped pair; the chosen potential; locked settings                                                      |
| Outputs | Converged band; climbing-image saddle; energy per image; force calls                                    |
| Checks  | fmax < 0.05 eV/Å within the step limit; break the symmetry of the starting band; several pairs per reaction, lowest valid barrier kept; climbing image or dimer refinement |
| Wraps   | ASE DyNEB with the fairchem FAIRChemCalculator and UMA, as the current CatTSunami tutorial does; the old OCPNEB class is gone in fairchem v2 |
| Logs    | Images, iterations, force calls, convergence                                                             |
| Context | CatTSunami: within 0.1 eV of DFT 91 % of the time, 28× faster; ML bands converged 81–82 % for dissociations |
| Open    | Number of images; step limit; interpolation; symmetry-breaking amplitude; a TSAgent-style replan loop or not |

### 3.11 Saddle and band validation: P4, step 12

| Check            | Passes when                                               | Source in the docs                 |
|------------------|-----------------------------------------------------------|------------------------------------|
| Imaginary modes  | Exactly one at the saddle                                 | TS definition                      |
| Endpoints        | An IRC from the saddle reaches this IS and this FS        | TS definition; Pynta               |
| Breaking bond    | Elongated to 1.25–1.63 × its initial length in some frame | CatTSunami                         |
| Connectivity     | Constant along the band except the breaking bond          | CatTSunami                         |
| Frames           | Enough frames to sample the saddle                        | CatTSunami failure mode            |
| Band convergence | fmax < 0.05 eV/Å                                          | CatTSunami                         |

On failure the LLM diagnoses with the Skill procedure and revises once; TSBench reports success rising from 50 % to 67 % with such revision. A case that still fails is a flagged case for human review. Wraps: ASE vibrations, Sella, CatTSunami band checks. Logs: every verdict, the diagnosis, the revision, and the endpoint-to-barrier shift. Open: the tolerance for "reaches"; which elongation factor in the range applies to which bond; the minimum frame count.

### 3.12 DFT refinement: P5, step 13

| Field   | Content                                                                                                  |
|---------|----------------------------------------------------------------------------------------------------------|
| Purpose | Score the ML endpoints and saddle with DFT at the locked settings                                        |
| Inputs  | Validated IS, TS and FS; PROJECT.md                                                                     |
| Outputs | DFT single points on IS, TS and FS; then relaxed endpoints and saddle; force calls; failures            |
| Checks  | Settings-mismatch check against the endpoints; fmax < 0.05 eV/Å for a band; 0.02–0.03 eV/Å for relaxations; failed jobs go to the LLM to diagnose, adjust and resubmit |
| Wraps   | ASE calculators; AiiDA; the AtomisticSkills atomate2 MCP server; custodian handlers before any LLM diagnosis; VASP or Quantum ESPRESSO |
| Logs    | DFT force calls and failure rate, gated versus naive endpoints; every diagnosis and resubmission        |
| Context | CatTSunami: 3 DFT single points per reaction; in its case study 102 bands converged, 8 failed, 14 % of converged bands were wrong |
| Open    | DFT code and compute; whether any DFT band runs or ML with OC20NEB labels stands in: D2                 |

### 3.13 Report: P5, step 14

| Field   | Content                                                                                       |
|---------|-----------------------------------------------------------------------------------------------|
| Purpose | One auditable record per reaction                                                             |
| Inputs  | Outputs of 3.6 to 3.12; the decision trace                                                    |
| Outputs | The report of section 4.5                                                                     |
| Checks  | BEP sanity check, `E_a ≈ α ΔE + β` fitted per reaction family; energetic span if multi-step, an extension |
| Wraps   | AtomisticSkills hyperparameter logging; Zenodo export                                         |
| Logs    | The full decision trace                                                                       |
| Open    | Decision-trace format; source of the BEP fit                                                  |

## 4. Data formats

The docs list fields; they fix no file format or schema for any of the five records below. The format of each is open: team decision.

### 4.1 PROJECT.md

| Field                                                         | Set by                        | Note                                                  |
|---------------------------------------------------------------|-------------------------------|-------------------------------------------------------|
| Metal, facet, adsorbate AB                                    | Human                         |                                                       |
| Product A\* + B\*, with A and B as structures                 | Human                         | Listed as missing in the docs                         |
| Reaction network, for pathways                                | Human                         |                                                       |
| Functional                                                    | Human                         | PBE, RPBE or BEEF-vdW, chosen with CE27 and literature |
| Dispersion                                                    | Human                         | D3 or vdW-DF for large or flat-lying adsorbates       |
| Spin and initial magnetic moments                             | Human                         | Fe, Co and Ni spin-polarised                          |
| Hubbard U per element                                         | Human                         | Oxides; same U for every intermediate                 |
| Gas-phase references for AB, A and B, with corrections        | Human                         | One set for IS, FS and band                           |
| Slab model: facet, layers, fixed layers, surface cell         | Human; layers converged by Tool |                                                     |
| Pseudopotential family and version                            | Tool                          |                                                       |
| Cutoff; k-mesh; smearing method and σ                         | Tool                          |                                                       |
| Vacuum; dipole correction                                     | Tool                          |                                                       |
| Cell width for pairs                                          | Tool                          | Periodic images ≥ 10 Å apart                          |
| Force and SCF thresholds                                      | Skill                         |                                                       |
| Convergence target and sweep data                             | Tool                          |                                                       |
| Protocol chosen and the reason                                | LLM                           |                                                       |
| Interview answers to the five questions                       | Human                         | Each becomes a check, a prior or a skill line         |
| Scope, assumptions, notation, verification targets, autonomy level | Human                    | Get Physics Done pattern                              |
| One or two published E_ads with functional and preferred site | Literature                    | A human verifies                                      |
| Lock and approval                                             | Human                         | At the Approve-settings checkpoint                    |
| MLIP chosen and the reason                                    | LLM                           | Whether it lives here: open: team decision            |

### 4.2 Descriptor card

| Field                                                                 | Example line in the docs                         |
|-----------------------------------------------------------------------|--------------------------------------------------|
| Composition and cell; facet, layers, vacuum, fixed layers             |                                                  |
| Site label and point group; coordination number                       | "fcc hollow, C3v, coordination 3"; "hcp hollow, C3v, atom beneath" |
| Height above the surface plane; nearest-neighbour distances; tilt angle |                                                |
| Displacement from the start                                           | "migrated: fcc hollow to bridge, 1.4 Å"          |
| Total magnetic moment                                                 |                                                  |
| Validity verdicts                                                     | "one imaginary mode, 120i cm⁻¹"                  |

Fields for an A\* + B\* pair, such as the A–B distance and the site-graph distance, are not in the docs' list: open: team decision.

### 4.3 Lessons-log entry

| Field      | Basis in the docs                                                         |
|------------|---------------------------------------------------------------------------|
| System     | "Ni(111)"                                                                 |
| Correction | "set initial magnetic moments"                                            |
| Reason     | "or SCF fails"; the log holds corrections with reasons                    |
| Source     | The checkpoint where it was made: flagged-case review or the pick of initial states |
| Becomes    | A skill line, a check or a prior, once it recurs                          |

How many recurrences trigger promotion is open: team decision.

### 4.4 Decision trace

The docs list the decision-trace format as missing. They say what it must hold:

| Entry                                              | Written by |
|----------------------------------------------------|------------|
| Protocol choice and reason                         | 3.1        |
| Counts of sites, orientations and pairs            | 3.2        |
| Every verdict and rejection, with its reason       | 3.4, 3.8   |
| MLIP choice and reason; doubt flags; escalations   | 3.6        |
| Human choices and reasons                          | 3.7        |
| IS–FS pairs tried and rejected                     | 3.9        |
| Saddle verdicts, diagnoses and revisions           | 3.11       |
| Failed-job diagnoses and resubmissions             | 3.12       |

### 4.5 Report

| Field                                       | Note                                           |
|---------------------------------------------|------------------------------------------------|
| Barrier E_a and reaction energy ΔE          | Per kept final state; lowest valid kept        |
| Validated path                              | With the verdicts of 3.11                      |
| ML uncertainty                              | Calibrated doubt from 3.6                      |
| Agentic uncertainty                         | Extension: the planner run N times; N open     |
| Final state                                 | E(FS near), E(FS ∞), lateral interaction; recombination rate of nearest pairs; rejected pairs with reasons |
| Cost: DFT force calls and failures          | Gated versus naive endpoints                   |
| Endpoint-to-barrier shift                   | In eV and as a rate factor                     |
| Checks                                      | BEP; comparison with the OC20NEB band          |
| Decision trace                              | Section 4.4                                    |
| Energetic span                              | Multi-step only; extension                     |

## 5. Rules the LLM must obey

The LLM plans, chooses with a reason, diagnoses and drafts; code decides every geometric and numerical question. These rules come from the geometry rules and the locked decisions.

1. Never write, edit or reason from raw coordinates.
2. Act only through named tool calls. Bypassing a tool is a failure; the geometry benchmark exists to catch it.
3. Read descriptor cards and validity verdicts. A rendered image is a second look, never the basis of a decision.
4. Never choose a configuration from your own chemical reasoning. Every configuration comes from enumeration.
5. Never write numerical settings from memory. Pick the protocol and state why; the numbers come from the protocol or the sweep.
6. Read PROJECT.md at every step. Never change a locked setting.
7. Stop at every checkpoint and wait: approve settings, approve the plan, review flagged cases, pick initial states, interpret results.
8. Never override a code check. An LLM critic may comment on a card, as an extension only.
9. On ML doubt: stop, measure, repair, and ask only if repair fails.
10. Diagnose failed jobs: read the errors, adjust, resubmit. Diagnose a failed saddle validation and revise once; then flag it.
11. Never pair a failing state. Report rejected pairs; never hide them.
12. Gather at most one or two published E_ads values, with functional and site, for a human to verify. Never cite from memory.
13. Do not write skills. Skills are few, human-written and procedural; facts and ranges live in code and PROJECT.md.

## 6. Benchmark and measurables

The claim is measured by three numbers, gated against naive endpoints, on an OC20NEB subset that starts with \*OH → \*O + \*H on Pt(111).

| Number             | Definition                                                                          | Compared                                    |
|--------------------|-------------------------------------------------------------------------------------|---------------------------------------------|
| Barrier shift      | Barrier from naive endpoints minus barrier from gated endpoints, in eV and as `exp(δ / k_B T)` | Single placement versus enumeration plus checks |
| Recombination rate | How often the nearest pair bonds back after relaxation                              | Per reaction                                |
| DFT band cost      | DFT force calls and failure rate of the bands                                       | Gated versus naive endpoints                |

| Item                      | What the docs say                                                                  | Open                                  |
|---------------------------|------------------------------------------------------------------------------------|---------------------------------------|
| OC20NEB                   | 932 DFT NEB calculations, released with CatTSunami                                 | Subset size and selection             |
| Settings                  | OC20 used RPBE and PAW; our lock must match if OC20NEB is ground truth             | Accept it as ground truth: D3         |
| First case                | \*OH → \*O + \*H on Pt(111): simplest in OC20NEB's list, with DFT bands to compare | Confirm: D1                           |
| Single-placement baseline | Endpoints from single placement, as in the propagation experiment; adsorption baselines are a plain AdsorbML-style run and AtomisticSkills addadsorbate | Exact definition for the path benchmark |
| Pass criterion            | Our endpoints and band against the released DFT band; barrier within tolerance     | The tolerance                         |
| Reference points          | TSAgent 83 % on a 100-example OC20NEB subset; CatTSunami within 0.1 eV 91 %; 0.1 eV ≈ 10× in rate at 500 K; activity trends need about 50 meV | None is stated as the criterion |
| DFT check                 | One DFT check of the propagation experiment                                        | Compute: D2                           |

| Other measurement     | Task | Content                                                                                 |
|-----------------------|------|-----------------------------------------------------------------------------------------|
| H on Pt(111)          | M1   | Steps 1 to 8 end to end; E_ads against CE27 and OC20                                    |
| Ni(111) doubt demo    | M4   | The agent flags ML disagreement and stops for review                                    |
| Geometry tasks        | none | Twenty editing tasks: place, rotate, supercell, cut facet; target near 100 % with tools |
| Adsorption metrics    | none | Success in finding the DFT minimum; error against DFT; fraction of own failures flagged; compute cost; each against the baseline |

## 7. Build order

Build the ten numbered tasks first; they are the shortest route to one measured barrier. Each lists what it needs and what it reuses, as in the figure 22 script.

Critical path:

- [ ] 1 · D1 System and product: AB\*, surface, A\* + B\*; first case \*OH → \*O + \*H on Pt(111)? Human decision.
- [ ] 2 · T1 Settings lock, section 3.1. Needs D1, D3. Reuses AiiDA common workflows, SSSP.
- [ ] 3 · T2 Site and pair enumeration, section 3.2. Needs T1. Reuses spglib, CatKit, pymatgen.
- [ ] 4 · T4 Validity gate, section 3.4. Needs T3. Reuses fairchem anomaly detection.
- [ ] 5 · T6 MLIP choice, section 3.6. Needs D2. Reuses AtomisticSkills ml-mlip-benchmark.
- [ ] 6 · P1 Nearest non-recombining final state, section 3.8. Needs T2, T4, T6, D5. Reuses fairchem AutoFrameDissociation.
- [ ] 7 · P3 ML NEB and climbing image, section 3.10. Needs P2. Reuses fairchem CatTSunami, ASE NEB.
- [ ] 8 · P4 Saddle validation, section 3.11. Needs P3. Reuses ASE vibrations, Sella, CatTSunami band checks.
- [ ] 9 · M2 \*OH → \*O + \*H against OC20NEB. Needs P1 to P5, D3.
- [ ] 10 · R1 Release: SKILL.md, MCP tools on AtomisticSkills, benchmark data and traces on Zenodo. Needs M1, M2.

The path pulls in tasks off it: T1 needs D3, T4 needs T3, T6 needs D2, P1 needs D5, P3 needs P2, M2 needs P2 and P5, R1 needs M1. Build each when the path reaches it.

- Column 0, decide first
  - [ ] D2 Compute and codes: DFT code and budget; GPU for MLIPs; any DFT NEB at all, or ML only?
  - [ ] D3 Benchmark and pass criterion: OC20NEB subset as ground truth, so settings match OC20's RPBE and PAW?
  - [ ] D4 Headline claim: barrier-ready endpoints, or "knows when not to trust itself".
  - [ ] D5 Final-state rules: distance metric; binding fragment fixed or free; nearest survivor or lowest energy within one hop.
- Column 1, foundations
  - [ ] T3 Placement script, section 3.3. Needs T2. Reuses ASE, CatKit.
  - [ ] T5 Descriptor card, section 3.5. Needs T4. Reuses pymatgen, Robocrystallographer.
- Column 2, ML relaxation and trust
  - [ ] T7 Calibrated doubt, section 3.6. Needs T6, T4. Reuses UMA, MACE, EquiformerV2.
  - [ ] T8 Rank and human checkpoint, section 3.7. Needs T5, T7. Reuses nothing: ours.
- Column 3, path steps
  - [ ] P2 Pairing and connectivity, section 3.9. Needs P1. Reuses CatTSunami interpolation, the NEBscape idea.
  - [ ] P5 DFT refinement and report, sections 3.12 and 3.13. Needs P4, T7, D2. Reuses ASE calculators, AiiDA.
- Column 4, measure
  - [ ] M1 H on Pt(111) end to end. Needs T1 to T8.
  - [ ] M3 Three numbers nobody reports. Needs P1, P3, D2.
  - [ ] M4 Ni(111) doubt demo. Needs T7, T8.
- Extension layer, later
  - [ ] T9 DFT single points on the chosen five before any path search. Needs T8, D2.
  - [ ] T10 Active-learning loop: high doubt, a few DFT labels, fine-tune, re-run steps 6 to 8. Needs T7, D2. Reuses ml-mace-finetune.
  - [ ] M5 Agentic uncertainty: run the planner N times on one input; report how often its choices differ. Needs T8, P5.
  - [ ] LLM critic on descriptor cards that never overrides a code check, at steps 4.1 and 6.
  - [ ] Coverage scan over cell sizes for the lateral interaction, at 9b.
  - [ ] Lowest energy within one site hop as an alternative target, at 9e.
  - [ ] Multi-step mechanism scored by energetic span, at 14.
- LLM and human layer, written last because it only calls the tools
  - [ ] SKILL.md with the procedures: few, human-written.
  - [ ] Formulate interview and PROJECT.md template.
  - [ ] Lessons log that feeds the skill, seeded with the known pitfalls.
  - [ ] Planner that calls the tools by name, reads descriptor cards, never writes coordinates, and stops at the checkpoints.
- Also in the docs' next steps, outside the plan's boxes
  - [ ] Write model-facing documentation for the geometry tools.
  - [ ] Add twenty geometry editing tasks to the benchmark.
  - [x] Check the AtomisticSkills repository: done in `repo-survey.md`; no catalysis skill is public.
  - [ ] Run AtomisticSkills mat-surface-adsorption placement as the baseline.

## 8. Open decisions that block coding

Each question below blocks the step or task named beside it. Do not code around one with a guessed value.

| Question                                                                                                  | Blocks                         |
|-----------------------------------------------------------------------------------------------------------|--------------------------------|
| Is \*OH → \*O + \*H on Pt(111) the first system and product?                                             | D1; everything after it        |
| Which DFT code, compute and GPU; does any DFT band run, or ML with OC20NEB labels?                        | D2; T1 backend, T6, P5, M3     |
| Is an OC20NEB subset the ground truth, so the lock must match OC20's RPBE and PAW?                         | D3; T1, M2                     |
| What barrier tolerance against OC20NEB passes; which subset, how large; what exactly is the single-placement baseline for the path? | M2, M3 |
| Convergence target for E_ads: 10 or 25 meV?                                                               | T1                             |
| Which gas-phase references for AB, A and B in the first case?                                             | T1, PROJECT.md                 |
| What file format and schema for PROJECT.md, the card, the lessons log, the trace and the report?          | T1, T5, T8, P5                 |
| Thresholds for migrated, dissociated, reconstructed, intercalated, magnetism collapsed, expected-range width, imaginary-frequency noise; the surface plane; frequencies from the MLIP or from DFT? | T4 |
| A–B distance threshold for bond re-formed                                                                 | 9d; T4, P1                     |
| Distance metric: site-graph with in-plane tiebreak, or in-plane alone; how is the site graph built?       | 9b; T2, P1                     |
| Does A stay at its IS site or is it enumerated?                                                           | 9a; P1                         |
| Target: nearest survivor, or lowest energy within one site hop?                                           | 9e; P1                         |
| How many final states and IS–FS pairs to keep?                                                            | 9e, 10; P1, P2, P3             |
| Which MLIPs; doubt by ensemble, geometric sanity or both; what threshold; how many DFT labels?            | T6, T7                         |
| Random displacement amplitude; number of conformers                                                      | T3                             |
| Bond cutoffs for the connectivity graph; is "graphs differ only by A–B" the intended-reaction check?       | P2                             |
| Band images, step limit, interpolation, symmetry-breaking amplitude                                       | P3                             |
| Tolerance for an IRC reaching IS and FS; elongation factor per bond; minimum frame count                  | P4                             |
| Autonomy level; which checkpoints Balanced skips; recurrences before a lesson is promoted                 | T8, planner                    |
| Source of the BEP fit                                                                                     | Report                         |
| Adsorbate class and size beyond the first case                                                            | T3, T6                         |
| Headline claim                                                                                            | D4; report and demo, not code  |

## 9. Sources

Same list as in `adsorption-agent-workflow.md`, section *Sources*. Cite from there; do not add a source here that is not there.
