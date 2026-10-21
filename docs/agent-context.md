# Agent context: what the humans on this project know

Audience: an agent working on this project. This file is `adsorption-agent-workflow.md` as text, each figure restated as a table, list or rule. The design document is the source of truth; where they differ, this file is wrong, see `CLAUDE.md`. Writing rules: `agent-writing-style.md`.

## 1. What we are building and why

Scope, fixed 21 October 2026: given a surface with adsorbate AB* and the desired product A* + B*, both fragments adsorbed, determine the final state in which B* is as close to A* as possible while the two stay fully dissociated. Not catalysis, not kinetics, not yet the barrier. The barrier, the path, planner steps 10 to 14, kinetics and catalysis are a later phase, the extension layer; no core task, demo or measurable depends on them. CatTSunami is prior work for the final-state step only.

- Goal: an agent that computes adsorption energies on surfaces reliably and knows when not to trust itself; pathways later; target an Open Science hackathon.
- Adsorption agents exist: Adsorb-Agent, AdsMind, DREAMS, CatMaster, Catalyst-Agent, AutoDFT. Our contribution is trust: symmetry-complete site enumeration, explicit validity checks, detection of ML-potential failure, notably on magnetic Ni and Co, designed human checkpoints, a failure rate measured against a baseline, an open release.
- Claim "an agent that knows when not to trust itself"; not "an agent that computes adsorption energies", which exists, nor "new catalyst discovery", which cannot be validated in time.
- Build on AtomisticSkills as skills and MCP tools, not a standalone agent.
- Every step has one owner: Tool, LLM, Human, or Literature, which includes benchmarks.

## 2. Definitions and equations

- `E_ads = E(slab+A) - E(slab) - E(A)`, E(A) a stated gas reference, for H ½ E(H2). Negative is favourable. A reference change shifts all values equally; site ranking stays.
- `ΔG = ΔE + ΔE_ZPE - T ΔS`; ZPE usually raises ΔE slightly; lost translational and rotational entropy makes ΔS < 0, so ΔG is less negative than ΔE, more so at higher T.
- Burnside: `N = (1/|G|) Σ_{g in G} |X^g|`, G the supercell symmetry group, |X^g| arrangements fixed by g. Check: two adsorbates on a square's corners, C4v, 8 operations: 6 arrangements, fixed-point sum 16, N = 2, adjacent and diagonal.
- `ΔE = E(FS) - E(IS)`, `E_a = E(TS) - E(IS)`; a TS has one imaginary mode and an IRC from it reaches IS and FS.
- `k = (k_B T / h) exp(-ΔG‡ / k_B T)`. An error δ scales k by `exp(δ / k_B T)`; at 500 K, k_B T ≈ 0.043 eV: 0.05 eV ≈ 3×, 0.1 eV ≈ 10×, 0.2 eV ≈ 100×.
- BEP: `E_a ≈ α ΔE + β`, fitted per reaction family.
- `E(FS ∞) = E(A*) + E(B*) - E(slab)` from separate cells; lateral interaction `E(FS near) - E(FS ∞)`.
- "Adsorption curve" is one of: 1, E(z) over a site, minimum at z0 gives E_ads; 2, lateral energy surface, hollow–bridge difference ≈ diffusion barrier; 3, E_ads(θ), rising towards zero with lateral repulsion; 4, Langmuir θ = KP/(1+KP), saturating at one monolayer, from DFT free energies via K. 1 to 3 come from DFT directly.

## 3. Symmetry facts the enumeration tool must encode

Inequivalent sites = inequivalent high-symmetry Wyckoff positions of the slab's two-dimensional layer group.

| Facet    | Site            | Site group | Coordination | Note                                                   |
|----------|-----------------|------------|--------------|--------------------------------------------------------|
| fcc(111) | top             | C3v        | 1            |                                                        |
| fcc(111) | bridge          | C2v        | 2            |                                                        |
| fcc(111) | fcc hollow      | C3v        | 3            | no second-layer atom beneath                           |
| fcc(111) | hcp hollow      | C3v        | 3            | second-layer atom beneath; same top view as fcc hollow |
| fcc(100) | top             | C4v        | 1            |                                                        |
| fcc(100) | bridge          | C2v        | 2            |                                                        |
| fcc(100) | four-fold hollow| C4v        | 4            |                                                        |

- Orientations: only those inequivalent under the site's stabiliser group. Flat diatomic on a C3v top site: 120° rotations are one calculation; a 30° rotation, towards a gap, is a second.
- Coverage and co-adsorption: Burnside counting in code, never by eye.
- Surface selection rule: on a metal only A1 modes are IR-active, a perpendicular dipole adding to its image, a parallel one cancelling; compare with experimental site assignments.
- Symmetry trap: an adsorbate exactly on a high-symmetry site can stay on a saddle, since forces keep symmetry. Displace slightly at random before relaxing; confirm minima by frequencies.

## 4. Workflow, in order, with owners

| #  | Step                             | Owner      | What it does                                                        | Tools                                 |
|----|----------------------------------|------------|---------------------------------------------------------------------|---------------------------------------|
| 1  | Choose system and settings       | Human      | Metal, facet, adsorbate, functional, references                     | Literature, PROJECT.md                |
| 2  | Converge numerical settings      | Tool       | Pseudopotential set, cutoff, k-mesh, smearing, layers, on E_ads      | Convergence tool (ours), ASE          |
| 3  | Bulk relaxation                  | Tool       | Lattice constant                                                    | ASE, VASP or Quantum ESPRESSO         |
| 4  | Slab construction                | Tool       | Facet, layers, vacuum, fixed bottom layers                          | ASE, pymatgen                         |
| 5  | Site and orientation enumeration | Tool       | All symmetry-inequivalent sites, orientations, pairs                | spglib, pymatgen, CatKit, ACAT        |
| 6  | ML pre-screening                 | Tool       | Relax all candidates with a universal MLIP, keep the top few        | FairChem/UMA, MACE, AdsorbML          |
| 7  | Flag ML doubt                    | Tool + LLM | Detect MLIP disagreement or known-failure chemistry; escalate       | ml-mlip-benchmark, ml-mace-finetune   |
| 8  | DFT relaxation                   | Tool       | Accurate energies for the best candidates                           | VASP or QE via AiiDA or atomate2      |
| 9  | Diagnose failed jobs             | LLM        | Read errors, adjust, resubmit                                       | Agent                                 |
| 10 | Validity checks                  | Tool       | The nine checks of section 6                                        | Validity-check MCP server (ours)      |
| 11 | Review flagged cases             | Human      | Only cases that failed checks                                       |                                       |
| 12 | Energies and curves              | Tool       | E_ads, ΔG, E(z), E(θ)                                               | Custom scripts                        |
| 13 | Benchmark comparison             | Tool       | Error against known values                                          | OC20-Dense, CE27                      |
| 14 | Interpret results                | Human      | Mechanism, next targets                                             |                                       |

- Automate 2 to 10 and 12 to 13; humans own 1, 11 and 14, where a wrong choice silently corrupts later numbers. Gains: enumeration, dozens of configurations instead of three or four guesses; ML pre-screening, roughly an order of magnitude less DFT; job handling; checks.
- Build order: enumeration and checks, no supercomputer; DFT job management, reproducing a literature value for H on Pt(111); ML pre-screening, checked against DFT.
- Phases: 1 literature check, reaction network, one locked set of references and settings; 2 the agent above plus pair enumeration and the top few configurations; 3 the same for transition states; 4 microkinetics, benchmark, release. Rate-controlling steps loop back to DFT; review corrections go to the lessons log. Phase 3 and the kinetics of 4 are later.
- "Approve settings and network": the step whose silent failure corrupts everything downstream.

## 5. DFT settings protocol

Physics choices need judgement; a wrong one is plausible and untestable. Numerical choices are convergence tests; a wrong one is noise a sweep removes.

Physics, owner Human, locked in PROJECT.md at the Approve-settings checkpoint, one set for every intermediate and TS:
- Functional: PBE, RPBE or BEEF-vdW, by CE27 and literature; PBE over-binds CO, RPBE corrects part.
- Dispersion: D3 or vdW-DF for large or flat-lying adsorbates.
- Spin: Fe, Co, Ni spin-polarised with initial moments, or the SCF fails or finds a wrong state.
- Hubbard U for oxides: literature value per element, same for every intermediate.
- References: ½ E(H2) for H; O2, CO2, N2 need corrections for known GGA errors.
- Slab: facet, ≥ 4 layers close-packed, fixed bottom layers, cell for the coverage.

Numerical, owner Tool, converged on E_ads, written to PROJECT.md:
- Pseudopotentials: VASP recommended PAW, `_pv`/`_sv` where semicore states matter, e.g. early transition metals; QE: SSSP efficiency for screening, precision for final numbers, with per-element cutoffs, chosen against all-electron equations of state, phonons, cohesive energy, pressure and band structure. Δ-test verified, Lejaeghere et al. 2016, Bosoni et al. 2024. Never mix families or versions; one dataset per element in bulk, slab and gas; record the version: PBE 54 is the Materials Project and atomate2 default; OC20 used PAW with RPBE.
- Cutoff: largest ENMAX in the cell, × about 1.3 if the volume relaxes, against Pulay stress; converge E_ads, not the total. OC20 350 eV; Materials Project 520 eV, for cross-compound totals.
- `δE_ads = δE(slab+A) - δE(slab) - δE(A)` is far below any term: E_ads reaches ±10 meV while totals are hundreds of meV off, only with identical settings on both sides.
- k-points: denser for metals; Γ-centred on hexagonal cells; one along vacuum; in-plane ≈ 0.2–0.3 Å⁻¹, OC20: 40 / in-plane cell length; one mesh for slab and slab+A; cell-consistent across supercells; with smearing, converged near 7 × 7 × 1 on a 2 × 2 cell.
- Smearing: Methfessel–Paxton or Marzari–Vanderbilt, σ = 0.1–0.2 eV; extrapolate to σ → 0.
- Layers until E_ads stops changing, 4 to 5 close-packed; vacuum ≥ 12–15 Å; dipole correction with one face covered.
- Force 0.02–0.03 eV/Å; SCF 1e-5 to 1e-6 eV; owner Skill.

Convergence tool: one test adsorbate; sweep cutoff, k-mesh, smearing, layers; take the cheapest setting within ±10 meV of converged E_ads; write it and the sweep to PROJECT.md. Prefer AiiDA common workflows, fast, moderate, precise, eleven codes; SSSP; pymatgen input sets. The LLM may pick the protocol and must say why; numbers come from the protocol or sweep. Rejected: the LLM writing cutoff and k-points from memory, AutoDFT style; right for Pt, perhaps wrong for an oxide, unseen in the run.

## 6. Validity checks (code; run on every relaxed structure)

One code path, initial or final, before ranking or pairing. Reject or flag when:
1. Desorbed: adsorbate centre more than 3 Å above the surface plane; per fragment for a pair.
2. Migrated: on a site other than the one enumerated.
3. Dissociated: an intramolecular bond beyond its breaking threshold.
4. Reconstructed: surface atoms moved from their clean-slab positions.
5. Intercalated: an adsorbate atom below the top layer.
6. Not a minimum: any imaginary mode.
7. Magnetism collapsed: a magnetic slab's moment vanishes on adsorption.
8. Outside expected range: E_ads far from the prior, section 8.
9. Settings mismatch: slab and slab+A differ in cutoff, mesh, smearing or pseudopotentials.

Other thresholds are open. Checks 1, 3, 4, 5 are AdsorbML's; the rest are ours. The final-state gate adds A–B bond re-formed and periodic-image interaction, section 23.

## 7. ML-doubt detection and escalation

Doubt when two universal MLIPs disagree beyond a threshold; the metal is Co, Ni or otherwise magnetic; the chemistry is unseen: oxide, high coverage, electrochemical interface; or the result is out of range. Then stop, measure, repair, ask only if repair fails: label a few configurations with DFT, measure the error with ml-mlip-benchmark, fine-tune MACE with ml-mace-finetune if needed; if that fails, stop at a checkpoint with the evidence. Open: ensemble disagreement, geometric sanity, or both.

## 8. Priors and known pitfalls

- H on Pt(111): E_ads near −0.5 eV with ½ E(H2); verify per functional.
- CO/Pt(111) puzzle: GGA says hollow, experiment top; flag CO on Pt-group metals.
- Known DFT trouble: open-shell molecules, magnetic surfaces, oxides needing U.
- Universal MLIPs fail badly on magnetic Co and Ni, per the 80-model survey of Kempen, Cheula and Andersen; none is best everywhere; best adsorption MAE on CatBench ≈ 0.2 eV.
- Ni(111): set initial magnetic moments, or the SCF fails.
- Prior agents err by order 1.5 eV, AdsMind MAE 1.55 eV on six systems; activity trends need about 50 meV. AdsMind's loop converged above the exhaustive minimum; Adsorb-Agent made sign errors.
- An initial-state error enters E_a in full; a wrong initial configuration ties the TS to the wrong reactant.
- A symmetric NEB starting band can hide a lower path; compute mirror-equivalent paths once. The global minimum may miss the lowest-barrier path: pass on the top few.

## 9. Human checkpoints and what to ask

Checkpoints: approve settings, and the network for pathways; approve the plan; review flagged cases; interpret results.

Formulate interview, from cognitive task analysis; answers frozen into PROJECT.md, each becoming a check, a prior or a skill line:
1. What do you check first when a number looks wrong?
2. On which systems do you not trust the default settings, and what do you change?
3. What do you do before you trust a machine-learned potential on a new metal?
4. Which published values would you compare a first result against?
5. What has silently gone wrong for you before?
Plus scope, assumptions, notation, verification targets, autonomy: Supervised or Balanced.

Literature only before the run, for settings, references and known failures, and after it, on known systems. The agent may gather one or two published E_ads values with functional and site; a human verifies, since LLMs misquote values and invent citations. The project needs a review of 20 to 40 papers.

## 10. Where insight lives: the five channels

| Channel                     | Holds                          | Acts                       | Example                                                            |
|-----------------------------|--------------------------------|----------------------------|--------------------------------------------------------------------|
| Skill (SKILL.md)            | General know-how, written once | Loaded when the task matches | Always break symmetry before relaxing; flag CO on Pt-group metals |
| Project memory (PROJECT.md) | Choices for this system        | Read at every step         | RPBE-D3, four-layer slab, ½ E(H2) reference                        |
| Checkpoints                 | Live judgement                 | Agent pauses for approval  | Approve settings; review flagged cases                              |
| Tools (code)                | Insight turned into rules      | Every run, without fail    | Reject an adsorbate relaxed more than 3 Å above the surface         |
| Lessons log                 | Corrections from review        | Fed back into the skill    | Ni(111): set initial magnetic moments, or SCF fails                 |

A test becomes a tool, a procedure a skill line, a one-system choice project memory, a recurring judgement a checkpoint; code is most reliable, since an LLM cannot skip a check it does not control.

Four kinds of intuition: procedures, from Sholl and Steckel 2009, Nørskov, Studt, Abild-Pedersen and Bligaard 2014, protocol libraries and forum fixes verified on a test case, into the skill; priors, from CE27, Δ-test, CatBench, the 80-MLIP survey, OC20 settings, NOMAD, Materials Cloud, Catalysis-Hub, into thresholds; sanity constraints, physics, into code; judgement, from researchers and our runs, by interview and flagged-case review, logged and promoted on recurrence.

From Get Physics Done: the Formulate interview into PROJECT.md, REQUIREMENTS.md, ROADMAP.md, STATE.md; locked conventions; discuss before each plan and execute phase; autonomy setting. It also has a Verify stage on dimensions, limiting cases, symmetry and conservation laws, and tangent and branch commands. We add an adsorption and TS skill with DFT pitfalls and validity checks as an MCP server.

Skills evidence: curated human-written skills +16.2 percentage points over 84 tasks, self-written none or negative, SkillsBench 2026; procedural anchors 65.7% of cases, fact injection 4.5%, selection precision 29.6% at 5 skills, 3.3% at 100, Demystifying Agent Skills 2026. So few, procedural, human-written, verified skills; facts in code and PROJECT.md.

## 11. Prior work, compact

Adsorption: CatKit, symmetry-based sites; ACAT, slabs and nanoparticles, metals and alloys only; AdsorbML, GNN screening plus DFT, bounded by ML accuracy; Adsorb-Agent, LLM-proposed configurations, open loop, sign errors; AdsMind, closed loop, six DFT-validated systems, MAE 1.55 eV; DREAMS, multi-agent DFT on Quantum ESPRESSO and AutoCat; CatMaster, surrogate exploration with targeted DFT; Catalyst-Agent, MCP around FAIRchem AdsorbML, success 23–34%, DFT slow; AutoDFT, scores task completion, not chemistry.

Transition states, the record that a plain TS agent is not novel; Pynta and El Agente Potente in section 23:
- CatTSunami, no LLM: TS within 0.1 eV of DFT 91% of the time, 28× faster; 174 reactions in 12 GPU days; needs good endpoints.
- Fine-tuned MLIP TS search, no LLM: fewer than 10 DFT single points per TS; surface steps only, not reconstructions.
- NEBscape, npj 2026, code MIT: endpoints by minima hopping from symmetry-inequivalent sites; two adsorbates placed combinatorially, separations above 4.5 Å excluded; Hookean constraints keep fragments intact; candidates within 1.2 eV on the first two energy–distance Pareto fronts, SOAP-deduplicated; atom mapping; graph checks along the band; 304 OC20NEB reactions, 94 % converged, 9 % multi-step vs 17 %. Closest prior work for the final state; cut-off and trade-off, not nearest-first; no checkpoints.
- TSAgent, 2026, code without licence: plan–execute–analyse–replan at DFT level; 83% on a 100-example OC20NEB subset; 70% held-out vs 73 ± 12% for experts; reproduces BEP for NH3 dissociation; accepts a saddle on band convergence, one significant imaginary mode and a fitting barrier; no IRC; endpoints given; VASP only.
- CatDT, arXiv 2606.05050, June 2026: eight agents, 27 tools; endpoint checks in code, overlaps below 0.8 Å, element counts, path collisions, UMA energy screen, up to ten rounds; endpoint success 41 → 84 % on 600 OC20 surfaces; memory ablation none 49 %, distilled 52–54 %, raw case bank 68 %, full 84 %; no distance objective, no recombination check; code not yet released. Closest to our trust layer; raw cases beat distilled lessons.
- Catalyst-Agent, v3 July 2026: 1.40 to 3.41 trials per hit; randomised baseline 13.3, 16.7, 0 %; success is an MLIP energy inside a descriptor window.
- CopyCAT, ICIQ thesis: 3D adsorbate and TS structures from chemical reasoning; no DFT accuracy reported.
- TSBench, 2026: seven LLMs, editing tools, 78 reactions; 50% success, 67% with diagnosis-driven revision; most failures connect the wrong pair, an endpoint problem.
- Gap: barrier-ready endpoints, validated before any barrier, and a measurement nobody reports of how far endpoint error moves the barrier.

Intuition in agents, by where knowledge lives; no Anthropic research on the problem was found. Weights: ether0, FutureHouse 2025, 24B, RL on 640,730 verifiable chemistry tasks; needs a verifier. Curated context: Agent Skills, our format; Claude for Life Sciences and Claude Science, 60+ skills, coordinating and reviewer agents, auditable artifacts, no DFT skill; Scientific Agent Skills, K-Dense, 146+ skills; AtomisticSkills; Get Physics Done. Model-generated: Virtual Lab, Nature 2025, the human wrote about 1% of words; Google AI co-scientist, generate, reflect, rank, evolve; Kosmos, world model over 200 rollouts, 79.4% of claims accurate. Elicited: tacit-knowledge discovery 2025, KUPAS MASTER and Tacit Fragments 2026, none in physics. Tools: ChemCrow, 18 expert tools; Coscientist, Nature 2023; El Agente, over 87% on course exercises; chemistry accuracy unscored. Code: SSSP, AiiDA common workflows, pymatgen input sets. Measure only: FrontierScience, GPT-5.2 77% olympiad, 25% research; K-Bench, no model at scientist level, over-claiming commonest; ChemBench; CURIE.

## 12. Benchmarks and metrics

Existing: OC20-Dense, global minima, ~1,000 combinations per split, 74 adsorbates, 80,000+ configurations, not symmetry-complete; OCD-GMAE, Alloy-GMAE, FG-GMAE, cleaned subsets; AA20, OCD-GMAE62, small agent sets; OC20, one configuration per combination; OC22, oxides; CatBench, 13 MLIPs, 47,000+ reactions, best ≈ 0.2 eV; Kempen–Cheula–Andersen, 80 MLIPs; CE27, experimental chemisorption energies; OC20NEB, 932 DFT NEBs; VASPBench, 34 agent tasks, chemistry not judged. None tests an agent end to end against symmetry-exhaustive search with full DFT on hard chemistry.

Plan: 1, an OC20-Dense subset; 2, our enumeration on 30–50 of its systems, for missed minima; 3, hard set: Ni, Co, one oxide, TiO2(110) or CeO2(111); 4, controls: H and O on Pt(111) and Cu(111). Metrics against a plain AdsorbML-style run and AtomisticSkills' mat-surface-adsorption placement: success in finding the DFT minimum; error against DFT; fraction of own failures flagged; compute cost.

## 13. Mapping onto AtomisticSkills

AtomisticSkills, MIT, 2026: an outer harness for coding agents such as Claude Code, Gemini CLI and Cursor; human-approved workflows; 100+ curated skills; 50+ typed MCP tools on 10+ servers; rules incl. a literature review and an MLIP registry check; hyperparameters logged; co-pilot mode. Its Fe-oxide OER case study chains cleavage, O*/OH*/OOH* placement, MLIP relaxation, DFT, free energy and volcano, near our phases 2 and 4, without our trust layer.

| Our step                               | AtomisticSkills component                       | Plan                                                      |
|----------------------------------------|-------------------------------------------------|-----------------------------------------------------------|
| Literature check                       | Rule: mandatory literature review               | Reuse; add our DFT-pitfall list                           |
| Approve settings and network           | Plan reviewed before execution                  | Reuse; add PROJECT.md lock                                |
| Converge numerical settings            | (not described)                                 | New tool                                                  |
| Build bulk and slab                    | mat-db-mp; ASE build                            | Reuse; mat-htvs-cutcleansurface is not public             |
| Enumerate sites and pairs              | mat-surface-adsorption (MatCalc AdsorptionCalc on pymatgen AdsorbateSiteFinder; no fcc or hcp labels) | New skill: symmetry-complete on ACAT and spglib; theirs is the baseline |
| ML pre-screen                          | FairChem, MACE, MatGL MCP servers               | Reuse; mat-htvs-mlip-relax is not public                  |
| Flag ML doubt and escalate             | ml-committee-uncertainty, ml-mlip-benchmark, ml-mace-finetune | New skill that triggers these; calibration is ours |
| DFT relaxation                         | Atomate2 MCP server                             | Reuse; mat-htvs-vasp is not public                        |
| Validity checks                        | (none)                                          | New MCP tool server                                       |
| Transition-state search and validation | chem-neb-barrier (ASE NEB, IDPP, climbing image; no frequency or connectivity check); chem-ts-optimization, chem-irc-verification (Sella, molecules only) | New: periodic saddle validation with frequencies, IRC, band connectivity |
| Free-energy diagram                    | chem-thermochemistry; catalysis-activity skill not public | Build for thermal catalysis                      |
| Microkinetic model                     | Thermodynamics and kinetics skills (unspecified)| Check coverage                                            |
| Benchmark comparison                   | (none)                                          | New; main contribution                                    |
| Open release                           | Hyperparameter logging                          | Reuse; add provenance and Zenodo export                   |

Verified 21 October 2026, docs/repo-survey.md: 133 public skills, MIT; no mat-htvs catalysis skill; the catalysis layer is ours.

## 14. Pathway extension: rules that change the adsorption stage

Later phase. One set of gas references, H2, H2O, CO or CO2, and identical settings for every intermediate and TS. A* + B* in one cell: pair enumeration with Burnside counting; lateral interactions. Top few configurations per intermediate. Mirror-equivalent paths once; break the NEB starting band's symmetry. Every TS: one imaginary mode; IRC reaches IS and FS. Automate endpoint mapping, TS search, validation, free-energy corrections, microkinetics; a human approves the network and interprets the mechanism.

## 15. Hackathon scope and demo

- Scope: phases 1 and 2 in full, with benchmark comparison and open release; as finale the nearest non-recombining final state of one dissociation step, section 23, on ML with one pre-computed DFT check. The barrier of one elementary step, H2 dissociation or CO oxidation on Pt(111), and the microkinetic loop are later. Pre-compute everything slow; keep a recorded fallback.
- Field: over 40 of 88 projects at the 2025 LLM Hackathon for Materials Science and Chemistry used tool-calling agents; winners stress critique and reliability, NAIS 2026, human-in-the-loop design, dkNET–Texera, and traceability, the Cambridge rubric. ML-failure detection is the demo centrepiece.
- Demo, 3 minutes: 1, agents report E_ads without warning when wrong, as AdsMind found; 2, live Pt(111): interview, enumeration, decision trace; 3, live Ni(111): MLIP disagreement flagged, stop for review; 4, benchmark table against a baseline; 5, open skill, MCP tools, Zenodo data, one install command.
- Judges: versus AdsMind and Adsorb-Agent, a table of verified features only; trust, full DFT, settings in PROJECT.md, data released; LLM over a script, diagnosed failures and escalations, candour where a script suffices; unseen system, flags and a checkpoint.

## 16. Decisions (locked)

- Wrap CatKit, ACAT, pymatgen, ASE, AiiDA; do not rewrite.
- Every check that can be code is code; the LLM plans, diagnoses failures, prunes networks, drafts.
- Human checkpoints: settings approval, flagged-case review, network approval, interpretation.
- Literature only before the run, for settings, and after it, for benchmarks.
- References and DFT settings locked in PROJECT.md before any intermediate is computed.
- Top few configurations per intermediate, not one minimum.
- Hackathon: adsorption core plus one pathway step, its final state only for now; no discovery claim.
- Build on AtomisticSkills; contribute the trust layer as its skills and tools.
- Numerical settings from a verified protocol or a sweep on E_ads, never the LLM's memory; the LLM picks the protocol and explains.
- Four kinds of intuition into four channels; corrections into the lessons log as raw cases (structure, verdict, fix) the planner can retrieve, promoted to the skill by a human on recurrence; CatDT's ablation: raw case bank 68 % vs distilled banks 52–54 %.
- Skills few, human-written, procedural; facts and ranges in code and PROJECT.md.
- The LLM never writes or edits coordinates; code enumerates, places and checks geometry and shows a descriptor card, section 20.

## 17. Open questions

- Which hackathon: rubric, build period, pass criterion?
- Which DFT code, compute budget and MLIPs: VASP, Quantum ESPRESSO, or MLIPs only? Which MLIP for pre-screening, none being best everywhere?
- ML doubt: ensemble disagreement, geometric sanity, or both?
- Does symmetry-complete enumeration find lower minima than OC20-Dense, how often?
- E_ads convergence target: 10 meV or 25 meV?
- How many lessons-log entries before Ni(111) is caught without a human; can the demo show the curve?
- Can an interview agent run the Formulate interview without losing what a human catches?
- Does an image beside the descriptor card help catch geometry errors or add noise?
- Adsorbate class and size; same molecule in a final geometry or a new one from two adsorbates, which moves pair enumeration into the core; one step or a short mechanism, and who supplies it?
- Final-state metric: site-graph distance with in-plane tiebreak, or in-plane distance between the binding atoms alone?
- Does the binding fragment stay at the reactant's site, as CatTSunami assumes, or move?
- Target: nearest survivor, or lowest energy within one site hop? They differ when adjacent fragments repel.
- First case: *OH → *O + *H on Pt(111), simplest in OC20NEB's list, with DFT bands to compare?
- Is an OC20NEB subset acceptable ground truth, though it fixes the settings to OC20's RPBE and PAW, which our lock must match?
- Does any DFT nudged-elastic-band compute exist for the propagation experiment, or does it run on ML with OC20NEB labels?
- Headline: "barrier-ready endpoints" with measured propagation, since TSAgent and CatDT crowd the plain TS claim? Which of the four claims of section 22 heads the demo?

## 18. Next steps

Critical path, figure 22: 1 system and product; 2 settings lock; 3 site and pair enumeration; 4 validity gate; 5 MLIP choice; 6 nearest non-recombining final state; 7 *OH → *O + *H final state against the OC20NEB product frame; 8 release. Column 0 decisions, system, compute, benchmark, headline, final-state rules, unblock the rest; the path and barrier measurements are later; the LLM and human layer, SKILL.md, interview, lessons log, planner, comes last because it only calls tools.

Layout, figure 24, with tree and rules in agent-build-context.md section 9: a Claude Code plugin beside AtomisticSkills; calls go one way, agents to skills to tools to library; skills under 200 lines. Agent reading order: CLAUDE.md, agent-context.md, agent-build-context.md, the given SKILL.md, tool docstrings.

Compute, figure 25: laptop for checks, enumeration, mapping, reports: 1 lock, 2 to 4, 4.1, 6, 9a, 9b, 9d, 10, 12 checks, 14. One GPU for ML relaxations, bands, frequencies: 5, 7, 9c, 11, 12. HPC for DFT: 1 sweep, 7 labels, 13, benchmark check. Without HPC: OC20's RPBE and PAW values for the sweep; OC20NEB's DFT bands as labels and ground truth; one DFT check run beforehand.

Roster, at most 5 roles and 12 skills, listed in agent-build-context.md section 9: final-state planner and DFT-settings interviewer core; geometry critic an extension that never overrides; DFT job steward only with HPC; peer review the reused general-peer-review skill. Add a role only when a human can state in one sentence what it decides.

- [ ] Draft SKILL.md for adsorption and transition-state calculations
- [ ] Draft the PROJECT.md template and the Formulate interview questions
- [ ] Implement site and pair enumeration and the validity-check tools
- [ ] Reproduce H on Pt(111) end to end as the first validation
- [ ] Assemble the benchmark subset: OC20-Dense, hard set, controls
- [ ] Build the Ni(111) failure-detection demo
- [ ] Package tools as an MCP server; plan the Zenodo release
- [x] Check the AtomisticSkills repository: no catalysis skill public; MIT; baseline mat-surface-adsorption on pymatgen's site finder, no fcc or hcp labels; docs/repo-survey.md
- [ ] Run its mat-surface-adsorption placement as the baseline
- [ ] Prototype the ML-doubt loop with ml-mlip-benchmark and ml-mace-finetune on Ni(111)
- [ ] Build the convergence tool, cutoff, k-mesh, smearing, layers on E_ads of H on Pt(111); have it write PROJECT.md
- [ ] Write the Formulate interview questions into SKILL.md; test on one experienced researcher
- [ ] Seed the lessons log with the known pitfalls: CO on Pt, Ni and Co magnetism, symmetry trap
- [ ] Redraw figure 12 of the design document with the "Converge numerical settings" step; recreate its script under docs/figures/src/
- [ ] Build the descriptor-card tool, structure in, card and PNG out; route every structure-producing tool through it
- [ ] Write model-facing documentation for the geometry tools: place, enumerate, check
- [ ] Add twenty geometry editing tasks to the benchmark; record success with and without tools
- [ ] Propagation experiment: the same ML NEB on Pt(111) from single-placement vs enumerated-and-checked endpoints; barrier difference in eV and rate factor; one DFT check
- [ ] Read TSAgent and TSBench in full; fill the endpoint-choice and saddle-validation gaps in the prior-work table
- [ ] Define the product as a structure with one set of gas-phase references; add A* + B* pair enumeration if the product forms from two adsorbates
- [ ] Write the initial–final connectivity check, atom mapping as in NEBscape, and the saddle validation tool: one imaginary mode, path ends at both endpoints
- [ ] Select an OC20NEB subset and the single-placement baseline for the path benchmark
- [ ] Build the nearest-non-recombining final-state tool: enumerate pairs, relax, gate, rank by distance, report rejected pairs and E(FS near) − E(FS ∞); run *OH → *O + *H on Pt(111) against the OC20NEB band

## 20. Geometry rules: the LLM never touches coordinates

Evidence that LLM geometry is uneven and unverifiable per case: AtomWorld 2025, ten kinds of CIF edit: add, remove, change, swap 60–95%, move an atom 20–80%, rotate a group below 12%; pymatgen as a tool helped little; copilot role advised. Adsorb-Agent configurations: MAE 1.84 eV vs DFT, maximum above 3.5 eV, sign errors on molecular adsorbates. LLMConfBench 2026: conformer ranking from XYZ, Kendall τ about 0.6 vs UFF 0.2, poor on ring strain, tied to general reasoning. MiSI-Bench 2025: a fine-tuned 7B vision model beats experts on molecular spatial transformations.

Rules:
- The LLM never writes, edits or reasons from raw coordinates. It reads descriptor cards and verdicts and acts through named calls: `enumerate_sites(slab)`, `place(site, orientation, height)`, `displace(amplitude)`, `check(structure)`, `render(structure)`; e.g. "place adsorbate at fcc hollow, orientation 2", "displace by 0.05 Å".
- Tools answer in text: sites from spglib, CatKit or ACAT, "fcc hollow, C3v, coordination 3; hcp hollow, C3v, atom beneath"; orientations as a numbered list; "migrated: fcc hollow to bridge, 1.4 Å"; "one imaginary mode, 120i cm⁻¹"; slab layers, vacuum, termination as numbers with pass or fail.
- Descriptor card from every structure-producing tool: composition and cell; facet, layers, vacuum, fixed layers; site label and point group; coordination; height above the surface plane; nearest-neighbour distances; tilt; displacement from start; total magnetic moment; verdicts. After Robocrystallographer; in LLM-Prop and LLM4Mat-Bench such text beat GNNs given the structure.
- An ASE-rendered PNG is a second look, as AtomWorld recommends and MiSI-Bench supports; never a decision input until the benchmark shows it helps.
- Tool docs are written for the model: MatTools 2025, GPT-4o 18% of pymatgen tasks alone, 40% with retrieved LLM-written docs, 55% with self-reflection; model-written docs retrieve better than official ones.
- Benchmark: twenty editing tasks, place, rotate, supercell, cut facet; near 100% with tools; catches bypassed tools.
- Rejected: configurations from the LLM's own chemical reasoning without enumeration, Adsorb-Agent style.

## 21. Solution planner (whiteboard, 21 October 2026)

Double-ended search: start, surface and adsorbates relaxed in vacuum with energies; end, the known product; unknown path, whose transition energy sets the rate.

Core steps and fixes:
1. Structure retriever: surface, adsorbates, description from the prompt. Fix: lock settings and references in PROJECT.md first.
2. Sites with pymatgen. Fix: symmetry-complete, spglib and CatKit; fcc and hcp hollows apart.
3. Placement. Fix: script only; symmetry plus random displacement; conformers in vacuum first; start 2–3 Å up, not 10 Å.
4. Initial configurations, all DoF × all sites. Fix: Burnside counting; few conformers.
4.1. Physics filter. Fix: the checks of section 6.
5. MLIP selection. Problem: organometallics, where universal MLIPs fail; dispersion; spin; periodic images ≥ 10 Å apart.
6. Anomaly filter: the code of 4.1 on every relaxed structure; verdict into the card.
7. Uncertainty across the MLIPs of 5. Fix: calibrate on a few DFT labels first.
8. Rank; human picks up to five on card, rank and uncertainty; then DFT on the five.

Later path steps: 9 final-state enumeration: product geometry, sites, orientations, pair distances; 10 atom mapping and IS–FS pairing, minimal displacement after symmetry, several pairs; 11 ML NEB, then climbing image or dimer; 12 saddle validation, one imaginary mode, path reaches this IS and FS; 13 DFT single points, then relax with locked settings; 14 report: barrier, path, MLIP and agentic uncertainties, energetic span if multi-step. The board's question marks are the extension column of section 22. Open questions: section 17.

## 22. Augmented pipeline: borrow, gaps, ours (figure 20 as a table)

Every step is borrowed or standard; the claim rests on four things no paper reports: validated endpoints with measured propagation, calibrated ML doubt, agentic uncertainty, an open release scored on OC20NEB. Paper numbers: section 11.

| Step | Borrow, from | Gap | Ours | Extension (later) |
|---|---|---|---|---|
| 1 Structure retriever | AiiDA common workflows, SSSP, Δ-test; never the LLM | Missing: product as a structure; one set of gas references | Locked, converged settings file | none |
| 2 Sites | CatKit symmetry; AdsorbML heuristic + random | Exists: pymatgen site finder in Adsorb-Agent, AdsMind, AtomisticSkills | Symmetry-complete, counted | none |
| 3 Placement | TSBench, AtomWorld: LLM edits fail | Exists: scripted; CopyCAT bets the other way | No LLM coordinates; card, named tools | none |
| 4 Initial configurations | AdsorbML, CatTSunami: many candidates, ML relax | Missing: A* + B* pairs; conformers in vacuum first | Pair enumeration by symmetry, counted | none |
| 4.1 Physics filter | AdsorbML: desorbed, dissociated, intercalated, reconstructed | Exists; no imaginary-mode check | One code gate on both endpoints | LLM critic, never overrides (4.1, 6) |
| 5 MLIP selection | CatTSunami EquiformerV2; fine-tuned MLIP TS; CatDT UMA/CHGNet; ml-mlip-benchmark | Missing: rule by system class; organometallics outside OC20 | Benchmark, choose, record why; flag doubt | Active learning: uncertainty → DFT labels → fine-tune → re-run 6 to 8 (5) |
| 6 Anomaly filter | AdsorbML | Exists: code of 4.1 | Verdict into the card | none |
| 7 Uncertainty | 80-MLIP survey: no best potential, so ensemble | Missing: calibration on DFT labels | Calibrated doubt that escalates | Agentic uncertainty: planner run N times, decision variance (7, 8) |
| 8 Rank, human picks ≤ 5 | AdsorbML top-k then DFT | Exists | Human picks on cards; choice and reason logged | DFT on the five before any path (8) |
| 9 Final-state enumeration | CatTSunami product placement; NEBscape global optimisation | Exists | Same gate on the final state; failing state never paired | none |
| 10 Atom mapping, pairing | NEBscape mapping + alignment; CatTSunami several pairs, lowest valid kept | Missing: intended-reaction check, TSBench's main failure | Rejected pairs reported with reasons | none |
| 11 Path search | CatTSunami ML NEB; fine-tuned MLIP; TSAgent replan | Exists | None: a wrapped tool | none |
| 12 Saddle validation | TSBench revision loop; CatDT gate, unpublished | Missing: mode count and connectivity as code | Validation in code; propagation measured | none |
| 13 DFT refinement | CatTSunami single points on the ML saddle | Exists; cost open | Same locked settings | none |
| 14 Report | TSAgent BEP check; energetic span | Missing: OC20NEB subset, single-placement baseline, trace format | Barrier, path, both uncertainties, trace; open skill and tools | Multi-step by energetic span; catalysis later (14) |

Verdict: taken: ML NEB, CatTSunami; LLM barrier agents, TSAgent, CatDT, CopyCAT; automated endpoints, NEBscape; checks and top-k DFT, AdsorbML. Missing: the rows so marked. Ours: barrier-ready endpoints, propagation measured later; calibrated doubt; agentic uncertainty; open skill and tools on OC20NEB. An LLM critic of descriptor cards attaches at 4.1 and 6. Open questions: section 17.

## 23. Nearest non-recombining final state (dissociation steps)

The answer to the problem of section 1. CatTSunami builds it by sampling and calls the placements proximate; classical DFT papers place fragments at nearest- or next-nearest-neighbour hollows by hand. Ours: complete enumeration, a code gate, rejections reported.

Rule: over all symmetry-distinct site pairs s_A, s_B, minimise the site-graph distance between A* and B*, in-plane distance as tiebreaker, subject to: product connectivity after relaxation, no A–B bond; no fragment desorbed, moved or subsurface; surface unchanged; zero imaginary modes; no periodic-image interaction. Check desorption per fragment: fairchem's DetectTrajAnomaly treats A* + B* as one adsorbate and passes B leaving while A stays. Keep the first few survivors in order.

Why nearest: a band to a far product adds diffusion saddles, and the climbing image can lock onto the wrong maximum; the nearest valid product gives one saddle. It need not be lowest in energy, as adjacent fragments can repel: report E(FS near) and E(FS ∞), section 2. Diffusion to the stable product is a separate step.

Cost: the DFT band is the expensive step and the one that fails; a far or invalid product needs more images and iterations and may not converge or may find the wrong maximum. CatTSunami, heuristic endpoints: 3 DFT single points per reaction, IS, TS, FS; band criterion fmax < 0.05 eV/Å within the step limit; ML bands converged 81–82 % for dissociations, 68–72 % for transfers, Equiformer V2; CO-hydrogenation case study: 102 DFT bands converged, 8 failed; 14 % of converged bands wrong, from too few frames or an unintended bond breaking or forming. Its two filters join saddle validation, step 12: breaking bond elongated 1.25× to 1.63× in some frame; connectivity constant except that bond.

Measured now: recombination rate of nearest pairs, per system and shell; E(FS near) − E(FS ∞); our final state against the OC20NEB product frame in A–B distance, energy, validity. Later: barrier shift; DFT force calls and failure rate, gated versus naive endpoints.

Prior work: CatTSunami AutoFrameDissociation, open source in fairchem, does 9a to 9e by sampling, see the table: no distance objective, not symmetry-complete, rejections unreported; the current code uses shells at 2 and 3 times the largest slab covalent radius and runs the band on ASE's DyNEB with UMA. Pynta, JCIM 2023: atom maps in, symmetry-unique configurations, harmonically forced saddle guesses, frequencies and IRC on every saddle, rate coefficients out; not aimed at the closest product; DFT cost. NEBscape, code MIT: the closest prior work: combinatorial pairs on symmetry-inequivalent sites, separations above 4.5 Å excluded, Hookean fragment integrity, energy–distance Pareto selection; 94 % of 304 OC20NEB reactions converged; cut-off and trade-off, not nearest-first; step 9 wraps its generator and scores our policy against its Pareto choice. Reproducible NEB orchestration, 2026: Snakemake, endpoint minimisation, alignment, PET-MAD and eOn paths; gas phase only. El Agente Potente, 2026: LLM agent, typed execution graphs plus a coding mode on MLIPs; picks band images; no success rate or final-image rule given.

Position: planner step 9, with the pair enumeration of section 14 and the step 4.1 gate plus a connectivity criterion; the end of the core for now. Step 10 reuses CatTSunami's unwrapping: depth-first search from the binding atom, the unbroken part moved as one moiety. Extensions: coverage scan over cell sizes, at 9b; lowest energy within one site hop, at 9e.

Figure 23 as text. Input: a slab with AB*, e.g. *OH on Pt(111), and the product named as A* + B*, *O + *H. Output: the final state with E(FS near), E(FS ∞), pairs tried and rejected, recombination rate, uncertainty; the barrier is later. Other rows follow section 22; the problem is 9a to 9e:

| Sub-step | Owner | CatTSunami | Ours | Output |
|---|---|---|---|---|
| 9a Place A, the fragment keeping the binding atom, near the IS site | Tool | 5 lowest-energy placements within 2 Å | All symmetry-distinct placements, counted, or A fixed at its IS site: team decision | Placements of A*, counted |
| 9b Enumerate B sites around A | Tool | 5 placements in a 1 to 3 Å shell, 25 pairs | All symmetry-distinct pairs by site-graph distance, nearest first, counted; the explicit objective is new | Ordered pairs |
| 9c Relax each pair | Tool | ML relaxation | Potential and settings of the IS; random displacement first | Relaxed pairs |
| 9d Gate each pair | Tool | Discard frames "where the products react or some other anomaly occurs" | The IS gate plus an A–B distance threshold; rejections logged; failing states never paired | Survivors; rejections with reasons |
| 9e Choose | Tool, LLM writes it up | One survivor at random | Nearest survivor first, then energy; keep several | Final states, E(FS near), E(FS ∞), recombination rate |

Verdict. Taken: the final state by cut-off and Pareto trade-off, NEBscape, and by sampling, CatTSunami; ML bands; LLM barrier agents incl. El Agente Potente; rates with IRC, Pynta; global-optimisation endpoints, NEBscape; steps 2 to 8, every adsorption agent, e.g. AtomisticSkills addadsorbate. Missing: A* + B* as structures and gas references; distance metric; bond-re-formed threshold; final-state pass criterion; an OC20NEB subset to compare product frames against; a single-placement baseline; whether any DFT single point runs. Ours: the explicit objective over symmetry-complete pairs, not lowest energy in a shell and a random pick; one logged code gate on both endpoints; two numbers now, recombination rate and E(FS near) − E(FS ∞), later barrier shift and band cost; calibrated doubt; open skill and tools scored against OC20NEB product frames; agentic uncertainty as extension. Open questions: section 17.

## 19. Sources

Same list as in `adsorption-agent-workflow.md`, section *Sources*. Cite from there; do not add a source here that is not there.
