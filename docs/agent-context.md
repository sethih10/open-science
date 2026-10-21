# Agent context: what the humans on this project know

Audience: an agent (Claude Code, Codex, Gemini CLI or similar) that will work on this project. This file is the project's knowledge in text only: no figures, no narration. Every figure of the human document is restated here as a table, a list or a rule. The human version with figures is `adsorption-agent-workflow.md`; the two must say the same things (see `CLAUDE.md`). When they differ, the human document is the source of truth and this file is wrong. How to write for this project is in `agent-writing-style.md`.

## 1. What we are building and why

- Goal: an agent that computes adsorption energies on catalyst surfaces reliably and knows when not to trust itself. Later: reaction pathways and kinetics. Near-term target: an Open Science hackathon.
- Generic adsorption agents already exist (Adsorb-Agent, AdsMind, DREAMS, CatMaster, Catalyst-Agent, AutoDFT). Our contribution is trustworthiness, not the workflow: symmetry-complete site enumeration, explicit validity checks, detection of machine-learning-potential failure (notably magnetic Ni and Co), designed human checkpoints, a measured failure rate against a baseline, an open release.
- Claim to make: "an agent that knows when not to trust itself". Claim to avoid: "an agent that computes adsorption energies" (exists) and "new catalyst discovery" (cannot be validated in time).
- Substrate: build on AtomisticSkills (MIT, 2026) as skills and MCP tools, not as a standalone agent.
- Ownership rule: every step has exactly one owner: Tool (deterministic code), LLM, Human, or Literature.

## 2. Definitions and equations

- Adsorption energy: `E_ads = E(slab+A) - E(slab) - E(A)`. E(A) is a stated gas-phase reference (for H: ½ E(H2)). Negative means favourable. Changing the reference shifts all values equally and does not change the ranking of sites.
- Free energy: `ΔG = ΔE + ΔE_ZPE - T ΔS`. ZPE from vibrational frequencies. Adsorption loses translational and rotational entropy, so ΔS < 0, −TΔS > 0, and ΔG is less negative than ΔE; the gap grows with T.
- Burnside count of inequivalent arrangements: `N = (1/|G|) Σ_{g in G} |X^g|`, G the symmetry group of the supercell, |X^g| the number of arrangements fixed by g. Worked check: two identical adsorbates on the four corners of a square cell, C4v (8 operations): 6 raw arrangements, fixed-point sum 16, N = 16/8 = 2 (adjacent, diagonal).
- Reaction energy and barrier: `ΔE = E(FS) - E(IS)`, `E_a = E(TS) - E(IS)`. TS is a saddle point: exactly one imaginary mode; an IRC from it must reach IS and FS.
- Rate constant (harmonic TST): `k = (k_B T / h) exp(-ΔG‡ / k_B T)`. At 500 K, k_B T ≈ 0.043 eV, so a 0.1 eV error changes k by about 10×.
- BEP pre-screen: `E_a ≈ α ΔE + β`, fitted per reaction family.
- Four objects called "adsorption curve": (1) binding curve E(z) over one site, minimum gives z0 and E_ads; (2) lateral potential energy surface, hollow–bridge difference ≈ diffusion barrier; (3) coverage curve E_ads(θ), rises towards zero with lateral repulsion; (4) Langmuir isotherm θ = KP/(1+KP), built from DFT free energies via K. (1)–(3) come from DFT directly.

## 3. Symmetry facts the enumeration tool must encode

Inequivalent adsorption sites = inequivalent high-symmetry Wyckoff positions of the slab's two-dimensional layer group.

| Facet    | Site            | Site group | Coordination | Note                                                   |
|----------|-----------------|------------|--------------|--------------------------------------------------------|
| fcc(111) | top             | C3v        | 1            |                                                        |
| fcc(111) | bridge          | C2v        | 2            |                                                        |
| fcc(111) | fcc hollow      | C3v        | 3            | no second-layer atom beneath                           |
| fcc(111) | hcp hollow      | C3v        | 3            | second-layer atom beneath; same top view as fcc hollow |
| fcc(100) | top             | C4v        | 1            |                                                        |
| fcc(100) | bridge          | C2v        | 2            |                                                        |
| fcc(100) | four-fold hollow| C4v        | 4            |                                                        |

Rules:
- Orientations: test only orientations inequivalent under the site's stabiliser group. Example: a flat-lying diatomic on a C3v top site: orientations related by 120° rotation are one calculation; a 30° rotation (pointing at a gap instead of a neighbour) is a second, separate calculation.
- Higher coverage and co-adsorption: count configurations with Burnside's lemma in code, never by eye.
- Surface selection rule: on a metal only modes of the totally symmetric representation (A1) of the site group are IR-active, because a perpendicular dipole adds to its image dipole and a parallel one cancels. Use to compare with experimental site assignments.
- Symmetry trap: forces preserve the symmetry of the starting structure. An adsorbate placed exactly on a high-symmetry site can stay on a saddle. Always apply a small random displacement before relaxing, and confirm every minimum with a frequency calculation (no imaginary modes).

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
| 10 | Validity checks                  | Tool       | Desorbed, migrated, dissociated, reconstructed, imaginary modes     | Validity-check MCP server (ours)      |
| 11 | Review flagged cases             | Human      | Only cases that failed checks                                       |                                       |
| 12 | Energies and curves              | Tool       | E_ads, ΔG, E(z), E(θ)                                               | Custom scripts                        |
| 13 | Benchmark comparison             | Tool       | Error against known values                                          | OC20-Dense, CE27                      |
| 14 | Interpret results                | Human      | Mechanism, next targets                                             |                                       |

- Automate the deterministic middle (steps 2–10, 12–13). Keep humans where a wrong choice silently corrupts every later number (steps 1, 11, 14).
- Build order: enumeration and validity checks first (no supercomputer needed); then DFT job management on H on Pt(111), reproducing a literature value; then ML pre-screening, checked against DFT before it is relied on.
- The four-phase version used for pathways: Phase 1 fixes everything before any calculation (literature check, reaction network, one locked set of references and settings). Phase 2 is the adsorption agent above, plus pair (co-adsorption) enumeration and passing on the top few configurations per intermediate. Phase 3 repeats the Phase 2 pattern for transition states (ML search, DFT refinement, failure diagnosis, validation, review). Phase 4 adds the microkinetic model, benchmark comparison and the open release. A dashed loop sends rate-controlling steps from the microkinetic model back to DFT refinement. Corrections from either review step go to the lessons log.
- The single step whose silent failure corrupts everything downstream: "Approve settings and network" (a wrong reference or a missing elementary step cannot be repaired later).

## 5. DFT settings protocol

Two kinds of setting. Physics choices need judgement and literature; a wrong one is plausible and no test reveals it. Numerical choices are convergence tests; a wrong one is noise that a sweep removes. Keep them apart.

Physics choices (owner: Human; locked in PROJECT.md at the Approve-settings checkpoint; same set for every intermediate and transition state):
- Functional: PBE, RPBE or BEEF-vdW; pick with CE27 and the literature of the system. PBE over-binds CO; RPBE corrects part of it.
- Dispersion: D3 or vdW-DF for large or flat-lying adsorbates.
- Spin: Fe, Co, Ni spin-polarised with initial magnetic moments set, or the SCF fails or converges to a wrong state.
- Hubbard U for oxides: literature value per element, same U for every intermediate.
- Gas-phase references and corrections: ½ E(H2) for H; O2, CO2 and N2 carry known GGA errors and need corrections.
- Slab model: facet, ≥ 4 layers for close-packed metals, fixed bottom layers, surface cell chosen for the coverage.

Numerical choices (owner: Tool; converged on E_ads; written to PROJECT.md by the convergence tool):
- Pseudopotential family: VASP: the recommended PAW dataset per element from the VASP wiki; `_pv`/`_sv` variants when semicore states matter (early transition metals). Quantum ESPRESSO: SSSP efficiency (screening) or precision (final numbers), which gives a per-element cutoff. Never mix families or versions in one project. Same dataset for an element in bulk, slab and gas phase. Record the version (PBE 54 is the Materials Project and atomate2 default; OC20 used PAW with RPBE). All of these are Δ-test verified against all-electron codes.
- Plane-wave cutoff: start at ≥ the largest ENMAX in the cell, × 1.3 if the cell volume relaxes; then converge E_ads, not the total energy. Reference points: OC20 350 eV; Materials Project 520 eV (cross-compound comparisons).
- Error cancellation: `δE_ads = δE(slab+A) - δE(slab) - δE(A)` is much smaller than any single term because the basis-set error of a metal atom is nearly the same with and without the adsorbate. E_ads reaches ±10 meV at a cutoff where total energies are still hundreds of meV off. This requires identical settings on both sides of the difference.
- k-points: Γ-centred on hexagonal cells; one k-point along vacuum; in-plane spacing ≈ 0.2–0.3 Å⁻¹ (OC20: mesh from 40 / in-plane cell length); same mesh for slab and slab+A; cell-consistent density across supercells of different size; converge E_ads.
- Smearing on metals: Methfessel–Paxton or Marzari–Vanderbilt, σ = 0.1–0.2 eV; report energies extrapolated to σ → 0. Broader smearing damps the k-point oscillation.
- Vacuum ≥ 12–15 Å; dipole correction when only one face is covered; layers added until E_ads stops changing.
- Force threshold 0.02–0.03 eV/Å; SCF 1e-5 to 1e-6 eV (convention, in the skill).

Procedure for the convergence tool: take one test adsorbate on the target surface; sweep cutoff, k-mesh, smearing and layers; report the cheapest setting with E_ads inside ±10 meV of the converged value; write the result and the sweep data to PROJECT.md.

Prefer existing protocol libraries over inventing settings: AiiDA common workflows (fast / moderate / precise protocols, eleven codes), SSSP, pymatgen input sets. The LLM may choose which protocol applies and must explain the choice; the numbers come from the protocol or the sweep.

Rejected: the LLM writing cutoff and k-points from memory in one call (AutoDFT style). It can be right for Pt and wrong for an oxide with nothing in the run revealing which.

## 6. Validity checks (code; run on every relaxed structure)

Reject or flag when any of these holds:
- Desorbed: adsorbate centre more than 3 Å above the surface plane.
- Migrated: adsorbate moved to a different site than the one enumerated.
- Dissociated: an intramolecular bond stretched beyond its breaking threshold.
- Reconstructed: surface atoms displaced beyond a threshold from their clean-slab positions.
- Not a minimum: one or more imaginary vibrational modes.
- Magnetism collapsed: total magnetic moment of a magnetic slab vanished on adsorption.
- Outside expected range: E_ads far from the prior for this adsorbate–metal pair (see section 8).
- Settings mismatch: slab and slab+A computed with different cutoff, mesh, smearing or pseudopotentials.

## 7. ML-doubt detection and escalation

Trigger doubt when any holds: two universal MLIPs disagree beyond a threshold; the metal is Co or Ni (or otherwise magnetic); the chemistry is unseen (oxide, high coverage, electrochemical interface); the result is outside the expected range.

Loop ("stop, measure, repair, then ask only if repair fails"): sample a few configurations; label them with DFT; run ml-mlip-benchmark to measure the error; if needed fine-tune MACE with ml-mace-finetune; continue. If repair fails, pause at a checkpoint with the evidence instead of guessing.

Open design question: ensemble disagreement, geometric sanity, or both.

## 8. Priors and known pitfalls

- H on Pt(111): E_ads near −0.5 eV with ½ E(H2) reference (order of magnitude check; verify exact value per functional).
- CO on Pt(111): GGA predicts the hollow site, experiment shows the top site ("CO/Pt(111) puzzle"). Flag CO on Pt-group metals.
- PBE over-binds CO; RPBE corrects part of it.
- O2, CO2, N2 gas-phase energies carry known GGA errors; use the standard corrections.
- Open-shell molecules, magnetic surfaces and oxides needing a Hubbard U are known DFT trouble.
- Universal MLIPs fail badly on magnetic Co and Ni (80-model survey by Kempen, Cheula and Andersen); no single model is best everywhere; best adsorption MAE on CatBench ≈ 0.2 eV.
- Ni(111): set initial magnetic moments, or the SCF fails.
- Prior agents reach errors of order 1.5 eV (AdsMind MAE 1.55 eV on six systems); activity trends need about 50 meV.
- AdsMind's closed loop was found converging above the minimum found by exhaustive enumeration; Adsorb-Agent produced sign errors found later.
- Accuracy matters more for barriers than for site ranking: 0.1 eV ≈ 10× in rate at 500 K.
- A symmetric starting band in NEB can hide a lower, symmetry-broken path; mirror-equivalent paths need computing once.
- The global-minimum configuration of an intermediate may not lie on the lowest-barrier path: pass the top few configurations on, not one.

## 9. Human checkpoints and what to ask

Checkpoints: approve settings (and the reaction network for pathways); review flagged cases; approve the plan before execution; interpret results.

Formulate interview before a run (answers are frozen into PROJECT.md; each answer becomes a check, a prior or a skill line):
1. What do you check first when a number looks wrong?
2. On which systems do you not trust the default settings, and what do you change?
3. What do you do before you trust a machine-learned potential on a new metal?
4. Which published values would you compare a first result against?
5. What has silently gone wrong for you before?
Plus the GPD-style scope questions: scope, assumptions, notation, verification targets, autonomy level (Supervised or Balanced).

Literature enters at two points only: before the run (settings, references, known failures for this system) and after it (comparison on known systems). The agent may gather one or two published E_ads values with their functional and preferred site, but a human verifies them: language models misquote values and invent citations.

## 10. Where insight lives: the five channels

| Channel                     | Holds                          | Acts                       | Example                                                            |
|-----------------------------|--------------------------------|----------------------------|--------------------------------------------------------------------|
| Skill (SKILL.md)            | General know-how, written once | Loaded when the task matches | Always break symmetry before relaxing; flag CO on Pt-group metals |
| Project memory (PROJECT.md) | Choices for this system        | Read at every step         | RPBE-D3, four-layer slab, ½ E(H2) reference                        |
| Checkpoints                 | Live judgement                 | Agent pauses for approval  | Approve settings; review flagged cases                              |
| Tools (code)                | Insight turned into rules      | Every run, without fail    | Reject an adsorbate relaxed more than 3 Å above the surface         |
| Lessons log                 | Corrections from review        | Fed back into the skill    | Ni(111): set initial magnetic moments, or SCF fails                 |

Rule of thumb: if an insight can be written as a test, make it a tool; if it is a procedure, put it in the skill; if it is a choice for one system, put it in project memory; if it needs judgement each time, make it a checkpoint. Code is most reliable: an LLM can misread a prompt but cannot skip a check it does not control.

Four kinds of intuition and where each goes: procedures → skill; priors and expected ranges → thresholds in checks and the doubt detector; sanity constraints → code; judgement of when to stop → interview and flagged-case review, logged, promoted to the skill when it recurs.

Sources of the first three kinds: textbooks (Sholl and Steckel 2009; Nørskov, Studt, Abild-Pedersen and Bligaard 2014); protocol libraries (SSSP, AiiDA common workflows, pymatgen input sets); published inputs and datasets (OC20 settings, NOMAD, Materials Cloud, Catalysis-Hub); benchmarks (CE27, Δ-test, CatBench, the 80-MLIP survey); forums (VASP wiki and forum, QE users list), verified on a test case before adoption; our own lessons log.

Evidence on skills: curated human-written skills raise success by about 16 points, self-written skills give nothing (SkillsBench 2026); skills act as procedural anchors (65.7% of cases), not fact injection (4.5%), and selection precision falls from 29.6% to 3.3% as a pool grows from 5 to 100 skills (Demystifying Agent Skills 2026). Therefore: few skills, procedural, human-written, verified; facts in code and PROJECT.md.

## 11. Prior work, compact

Adsorption agents and toolkits:
- CatKit: symmetry-based surface and site generation (toolkit).
- ACAT: site and coverage identification; metals and alloys only.
- AdsorbML: GNN screening with DFT check; bounded by ML accuracy.
- Adsorb-Agent: LLM proposes configurations then relaxes; open loop; sign errors found later.
- AdsMind: closed-loop configuration search; DFT validation on six systems; MAE 1.55 eV.
- DREAMS: hierarchical multi-agent DFT on Quantum ESPRESSO and AutoCat.
- CatMaster: surrogate exploration with targeted DFT validation.
- Catalyst-Agent: MCP agent around FAIRchem AdsorbML; success 23–34%.
- AutoDFT: closed-loop DFT with monitoring and recovery; measures task completion, not chemistry accuracy.
- AtomisticSkills (MIT, 2026): outer harness for coding agents; four layers (workflows, 100+ skills, 50+ MCP tools on 10+ servers incl. FairChem/UMA, MACE, MatGL, Atomate2, rules); hyperparameters logged; co-pilot mode. Its Fe-oxide OER case study chains cleavage, O*/OH*/OOH* placement, MLIP relaxation, DFT, free-energy and volcano analysis. Not offered: symmetry-complete enumeration, validity checks, ML-doubt escalation, failure rate. Check which catalysis skills are public (they run on an in-house htvs pipeline).
- Transition states: CatTSunami finds TS within 0.1 eV of DFT 91% of the time at 28× speed-up; a 2026 fine-tuned-MLIP method needs fewer than 10 DFT single points per TS but does not suit reconstructions.

Giving agents scientific intuition (by where knowledge ends up):
- Weights: ether0 (FutureHouse 2025), 24B model trained by RL on 640,730 verifiable chemistry tasks. Lesson: intuition can be trained where a verifier exists; out of hackathon scope.
- Context, expert-curated: Anthropic Agent Skills (format), Claude for Life Sciences and Claude Science (60+ curated science skills, reviewer agent for citations and calculations, auditable artifacts), Scientific Agent Skills (K-Dense, 146+ skills), AtomisticSkills, Get Physics Done (Formulate interview, locked conventions, verify stage). Anthropic has not published research on extracting tacit scientific knowledge as such.
- Context, model-generated: Virtual Lab (Nature 2025; personas plus critic; human wrote about 1% of words), Google AI co-scientist (generate/reflect/rank/evolve agents), Kosmos (structured world model across 200 rollouts; 79.4% claims judged accurate).
- Context, elicited from people: LLMs for tacit knowledge discovery (2025), KUPAS MASTER and Tacit Fragments (2026): interview agents and governed memory of cues and judgements. None applied to physics yet.
- Tools: ChemCrow (18 expert tools), Coscientist (Nature 2023), El Agente (quantum chemistry, over 87% on course exercises).
- Code, verified: SSSP, AiiDA common workflows, pymatgen input sets (Δ-test verified, no LLM).
- Benchmarks that only measure: FrontierScience (GPT-5.2: 77% olympiad, 25% research), K-Bench (no model reaches scientist-acceptable; over-claiming the commonest failure), ChemBench, CURIE.
Conclusions: write the know-how down; put each kind in the channel that enforces it; obtain judgement by structured interview and logged corrections.

## 12. Benchmarks and metrics

Existing: OC20-Dense (global-minimum search; ~1,000 combinations per split, 74 adsorbates, 80,000+ configurations; sampled heuristically, not by full symmetry); OCD-GMAE, Alloy-GMAE, FG-GMAE (cleaned subsets); AA20, OCD-GMAE62 (small agent sets); OC20 (one configuration per combination; unsuitable for minima); OC22 (oxides); CatBench (13 MLIPs, 47,000+ reactions, best ≈ 0.2 eV); Kempen–Cheula–Andersen (80 MLIPs; many fail on magnetic Co and Ni); CE27 (experimental chemisorption energies, for choosing the functional); OC20NEB (932 DFT NEBs); VASPBench (34 agent tasks; chemistry not judged).

Our plan: (1) a subset of OC20-Dense for comparability; (2) our own symmetry-complete enumeration on 30–50 of those systems to test whether OC20-Dense missed lower minima; (3) a hard set: Ni, Co, one oxide (TiO2(110) or CeO2(111)); (4) easy controls: H and O on Pt(111) and Cu(111). Baseline: a plain AdsorbML-style run and AtomisticSkills' addadsorbate placement.

Metrics: success in finding the DFT minimum; error against DFT; fraction of own failures flagged; compute cost; each against the baseline.

## 13. Mapping onto AtomisticSkills

| Our step                               | AtomisticSkills component                       | Plan                                                      |
|----------------------------------------|-------------------------------------------------|-----------------------------------------------------------|
| Literature check                       | Rule: mandatory literature review               | Reuse; add our DFT-pitfall list                           |
| Approve settings and network           | Plan reviewed before execution                  | Reuse; add PROJECT.md lock                                |
| Build bulk and slab                    | mat-db-mp, mat-htvs-cutcleansurface             | Reuse if public                                           |
| Enumerate sites and pairs              | mat-htvs-addadsorbate                           | New skill: symmetry-complete; theirs becomes the baseline |
| ML pre-screen                          | mat-htvs-mlip-relax; FairChem, MACE servers     | Reuse                                                     |
| Flag ML doubt and escalate             | ml-mlip-benchmark, ml-mace-finetune             | New skill that triggers these                             |
| DFT relaxation                         | mat-htvs-vasp; Atomate2 MCP                     | Reuse                                                     |
| Converge numerical settings            | (not described)                                 | New tool                                                  |
| Validity checks                        | (none)                                          | New MCP tool server                                       |
| Transition-state search and validation | (not described)                                 | New skills                                                |
| Free-energy diagram                    | mat-htvs-catalysis-activity-analysis            | Reuse for electrochemistry; extend for thermal catalysis  |
| Microkinetic model                     | Thermodynamics and kinetics skills (unspecified)| Check coverage                                            |
| Benchmark comparison                   | (none)                                          | New; main contribution                                    |
| Open release                           | Hyperparameter logging                          | Reuse; add provenance and Zenodo export                   |

## 14. Pathway extension: rules that change the adsorption stage

- One consistent set of gas-phase references (H2, H2O, CO or CO2) for every intermediate.
- Identical DFT settings for every intermediate and transition state.
- Co-adsorbed endpoints (A* + B* in one cell): pair enumeration with Burnside counting; lateral interactions.
- Return the top few configurations per intermediate.
- Compute mirror-equivalent paths once; break the symmetry of the NEB starting band.
- Validate every TS: exactly one imaginary mode; IRC reaches IS and FS.
- Automate the middle (endpoint mapping, TS search, validation, free-energy corrections, microkinetics). A human approves the network and interprets the mechanism.

## 15. Hackathon scope and demo

- Scope: Phases 1 and 2 in full, with benchmark comparison and open release; one elementary step (H2 dissociation or CO oxidation on Pt(111)) on ML with one pre-computed DFT check; microkinetic loop left for later. Pre-compute everything slow; keep a recorded fallback.
- Demo (3 minutes): (1) the problem: agents report E_ads without warning when wrong; (2) live Pt(111): Formulate interview, symmetry enumeration, results with decision trace; (3) live Ni(111): agent flags MLIP disagreement and stops for review; (4) benchmark table against baseline; (5) open release: skill, MCP tools, Zenodo data, one install command.
- Expected judge questions: difference from AdsMind and Adsorb-Agent (comparison table of verified features only); why trust the benchmark (full DFT, settings in PROJECT.md, data released); does the LLM add anything over a script (show diagnosed failures and escalations; be candid where a script suffices); what happens on an unseen system (uncertainty flags and a checkpoint, not a guess).

## 16. Decisions (locked)

- Wrap existing toolkits (CatKit, ACAT, pymatgen, ASE, AiiDA); do not rewrite.
- Every check that can be code is code; the LLM plans, diagnoses failures, prunes networks, drafts.
- Human checkpoints: settings approval, flagged-case review, network approval, interpretation.
- Literature only before the run (settings) and after it (benchmarks).
- References and DFT settings locked in PROJECT.md before any intermediate is computed.
- Top few configurations per intermediate, not one minimum.
- Hackathon: adsorption core plus one pathway step; no discovery claim.
- Build on AtomisticSkills; contribute the trust layer as its skills and tools.
- Numerical settings from a verified protocol or a convergence sweep on E_ads, never from the LLM's memory; the LLM picks the protocol and explains the choice.
- Four kinds of intuition into four channels; corrections into the lessons log, promoted to the skill when they recur.
- Skills few, human-written, procedural; facts and ranges in code and PROJECT.md.

## 17. Open questions

- Which hackathon, rubric, build period?
- Which DFT code and compute (VASP, Quantum ESPRESSO, MLIPs only)?
- Which MLIP for pre-screening, given none is best everywhere?
- ML-doubt detection: ensemble disagreement, geometric sanity, or both?
- Does symmetry-complete enumeration find lower minima than OC20-Dense, and how often?
- Convergence target for E_ads: 10 meV or 25 meV?
- How many lessons-log entries before Ni(111) is caught without a human; can that curve be shown?
- Can an interview agent run the Formulate interview without losing what a human interviewer catches?

## 18. Next steps

- [ ] Draft SKILL.md for adsorption and transition-state calculations
- [ ] Draft the PROJECT.md template and the Formulate interview questions
- [ ] Implement symmetry enumeration (sites and pairs) and the validity-check tools
- [ ] Reproduce H on Pt(111) end to end as the first validation
- [ ] Assemble the benchmark subset (OC20-Dense, hard set, controls)
- [ ] Build the Ni(111) failure-detection demo
- [ ] Package tools as an MCP server; plan the Zenodo release
- [ ] Check the AtomisticSkills repository: public catalysis skills, licence, how addadsorbate handles symmetry
- [ ] Run its addadsorbate placement as the baseline
- [ ] Prototype the ML-doubt loop with ml-mlip-benchmark and ml-mace-finetune on Ni(111)
- [ ] Build the convergence tool (cutoff, k-mesh, smearing, layers on E_ads of H on Pt(111)); have it write PROJECT.md
- [ ] Write the Formulate interview questions into SKILL.md; test on one experienced researcher
- [ ] Seed the lessons log with the known pitfalls (CO on Pt, Ni and Co magnetism, symmetry trap)
- [ ] Redraw figure 12 of the human document with the "Converge numerical settings" step

## 19. Sources

Same list as in `adsorption-agent-workflow.md`, section *Sources*. Cite from there; do not add a source here that is not there.
