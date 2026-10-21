# Agentic Workflow for Adsorption Energies and Reaction Pathways


## Purpose and direction

We are building an AI agent that computes adsorption energies on surfaces reliably and knows when not to trust itself, for an Open Science hackathon; pathways and kinetics come later. This document is the project's shared memory: a colleague or another Claude instance must be able to continue from it alone.

**Scope, fixed on 21 October 2026.** Given a surface with adsorbate AB\* and the desired product A\* + B\*, both fragments adsorbed, determine the final state in which B\* is as close to A\* as possible while the two stay fully dissociated. Not catalysis, not kinetics, not yet the barrier: those are a later phase, kept here as the extension layer, and no core task, demo or measurable depends on them. CatTSunami is prior work for the final-state step only.

**Position.** Adsorption agents exist: Adsorb-Agent, AdsMind, DREAMS, CatMaster, Catalyst-Agent, AutoDFT. We contribute trustworthiness: symmetry-complete site enumeration, explicit validity checks, detection of machine-learning failures, notably on magnetic Ni and Co, designed human checkpoints, a failure rate measured against a baseline, and an open release.

**Sections.** 2 science; 3 workflow; 4 DFT setup; 5 literature; 6 prior agents; 7 benchmarks; 8 human insight; 9 geometry; 10 prior work on intuition; 11 AtomisticSkills; 12 and 13 pathways; 14 whiteboard planner; 15 augmented pipeline; 16 final-state problem; 17 strategy; 18 decisions and next steps. Every step has one owner: Tool, LLM, Human, or Literature, which includes benchmarks.

## Scientific background

Everything builds on the adsorption energy, computed with density functional theory, DFT, on a periodic slab:

$$
E_{\mathrm{ads}} = E(\mathrm{slab}+A) - E(\mathrm{slab}) - E(A)
$$

E(slab + A) and E(slab) are the relaxed slab with and without adsorbate A; E(A) is a stated gas-phase reference, for H usually ½ E(H₂). Negative is favourable. The reference shifts every value but not the ranking of sites.

![adsorption energy as an energy-level drop · reference choice](../figures/01-adsorption-energy-levels.png)

*Figure: adsorption energy as an energy-level drop · reference choice*

Reading the figure: E_ads is the drop from A in the gas to A bound, left; another reference moves the top, bridge and hollow levels equally, right.

The free energy adds the zero-point energy, ZPE, from vibrational frequencies and the entropy S at temperature T:

$$
\Delta G = \Delta E + \Delta E_{\mathrm{ZPE}} - T\Delta S
$$

![from DFT energy to free energy · schematic, not to scale](../figures/02-free-energy-corrections.png)

*Figure: from DFT energy to free energy · schematic, not to scale*

Reading the figure: ZPE usually raises ΔE slightly; adsorption loses translational and rotational entropy, so ΔS < 0 and −TΔS raises it further. ΔG is less negative than ΔE, more so at higher temperature.

**Four objects called "adsorption curve".**

- Binding curve: energy against height z over one site; its minimum gives z₀ and E_ads.
- Potential energy surface: energy over lateral positions; the hollow-to-bridge difference approximates the diffusion barrier.
- Coverage curve: E_ads against coverage θ, rising towards zero as neighbours repel.
- Isotherm: coverage against pressure, e.g. Langmuir θ = KP / (1 + KP), saturating at one monolayer.

![four kinds of adsorption curve · schematic](../figures/03-four-adsorption-curves.png)

*Figure: four kinds of adsorption curve · schematic*

Reading the figure: panels 1 to 4 follow the list; curves 1 to 3 come directly from DFT, curve 4 from DFT free energies through the equilibrium constant K.

**Where symmetry enters.**

- Sites are the inequivalent high-symmetry Wyckoff positions of the slab's two-dimensional layer group: on fcc(111), top C3v, bridge C2v, fcc hollow C3v, hcp hollow C3v; on fcc(100), top, bridge, four-fold hollow.
- Orientations: only those inequivalent under the site's stabiliser group.
- Configurations at higher coverage: Burnside's lemma, with N the number of distinct arrangements, G the symmetry group of the supercell and \|X^g\| the arrangements fixed by operation g.
- Spectroscopy: by the surface selection rule only modes of the totally symmetric representation of the site group are IR-active on a metal, which helps identify the site.

![inequivalent adsorption sites · fcc(111) and fcc(100)](../figures/04-adsorption-sites-fcc111-fcc100.png)

*Figure: inequivalent adsorption sites · fcc(111) and fcc(100)*

Reading the figure: grey discs are surface atoms seen from above; coloured dots are the only sites to test, labelled with site group and coordination number. The fcc and hcp hollows differ only by the second-layer atom beneath hcp.

![orientation enumeration on a C3v top site](../figures/05-orientation-enumeration.png)

*Figure: orientation enumeration on a C3v top site*

Reading the figure: orientations of a flat-lying diatomic on a C3v top site related by 120° rotations are one calculation; a 30° rotation, pointing at a gap instead of a neighbour, is a second.

$$
N = \frac{1}{|G|} \sum_{g \in G} |X^{g}|
$$

![Burnside counting · two adsorbates on a square](../figures/06-burnside-counting.png)

*Figure: Burnside counting · two adsorbates on a square*

Reading the figure: two identical adsorbates on the corners of a square have six arrangements; the eight operations of C4v leave 16 unchanged in total, and 16 / 8 = 2: adjacent and diagonal.

![surface selection rule · image dipoles](../figures/07-surface-selection-rule.png)

*Figure: surface selection rule · image dipoles*

Reading the figure: a dipole perpendicular to a metal adds to its image inside the metal and absorbs infrared light; a parallel one cancels. Only A₁ modes carry a perpendicular dipole.

**Symmetry trap.** Forces preserve the starting symmetry, so an adsorbate placed exactly on a high-symmetry site can stay there when a tilted geometry is lower. Displace it slightly at random before relaxing, and confirm every minimum by a frequency calculation with no imaginary modes.

![binding curve and the symmetry trap · schematic, not to scale](../figures/08-binding-curve-symmetry-trap.png)

*Figure: binding curve and the symmetry trap · schematic, not to scale*

Reading the figure: left, the well of depth E_ads at height z₀. Right, the symmetric position θ = 0 is a zero-force maximum where an unperturbed relaxation stays and a frequency calculation shows an imaginary mode; a small displacement reaches the tilted minimum.

## The adsorption workflow and where to automate

Automate the deterministic middle; keep humans where a wrong choice silently corrupts every later number.

| Step | Owner | What it does | Tools |
|---|---|---|---|
| Choose system and settings | Human | Metal, facet, adsorbate, functional, references | Literature, PROJECT.md |
| Converge numerical settings | Tool | Pseudopotential set, cutoff, k-mesh, smearing, layers, on E_ads | Convergence tool, ours; ASE |
| Bulk relaxation | Tool | Lattice constant | ASE, VASP or Quantum ESPRESSO |
| Slab construction | Tool | Facet, layers, vacuum, fixed bottom layers | ASE, pymatgen |
| Site and orientation enumeration | Tool | All symmetry-inequivalent sites and orientations | spglib, pymatgen, CatKit, ACAT |
| ML pre-screening | Tool | Relax all candidates cheaply, keep the top few | Universal ML potentials, AdsorbML |
| DFT relaxation | Tool | Accurate energies for the best candidates | VASP or QE via AiiDA or atomate2 |
| Diagnose failed jobs | LLM | Read errors, adjust, resubmit | Agent |
| Validity checks | Tool | The nine checks below, on every relaxed structure | Custom scripts |
| Review flagged cases | Human | Only cases that failed checks | — |
| Energies and curves | Tool | E_ads, ΔG, E(z), E(θ) | Custom scripts |
| Benchmark comparison | Tool | Error against known values | OC20-Dense, CE27 |
| Interpret results | Human | Mechanism, next targets | — |

**Validity gate:** one code path on every relaxed structure, initial or final, before anything is ranked or paired.

| # | Check | Fails when | Threshold |
|---|---|---|---|
| 1 | Desorbed | Adsorbate centre too far above the surface plane | 3 Å |
| 2 | Migrated | Adsorbate ends on a site other than the one enumerated | Site label differs |
| 3 | Dissociated | An intramolecular bond stretched beyond its breaking threshold | Open |
| 4 | Reconstructed | Surface atoms displaced from their clean-slab positions | Open |
| 5 | Intercalated | An adsorbate atom below the top surface layer | Layer index |
| 6 | Not a minimum | One or more imaginary vibrational modes | Zero allowed |
| 7 | Magnetism collapsed | Total moment of a magnetic slab vanishes on adsorption | Open |
| 8 | Outside expected range | E_ads far from the prior for this adsorbate and metal | Prior width open |
| 9 | Settings mismatch | Slab and slab+A differ in cutoff, mesh, smearing or pseudopotentials | Exact equality |

Checks 1, 3, 4 and 5 are AdsorbML's four anomaly checks; the rest are ours. For a co-adsorbed pair check 1 runs per fragment, and the final-state gate adds A–B bond re-formed and periodic-image interaction: section 16.

Automation gains most in site enumeration, dozens of configurations instead of three or four guesses; ML pre-screening, roughly an order of magnitude less DFT; job handling; and validity checks. Build order: enumeration and checks, needing no supercomputer; DFT job management, reproducing a literature value for H on Pt(111); ML pre-screening, checked against DFT.

## Choosing the DFT numerical setup

Physics choices, functional, dispersion, spin, Hubbard U, gas-phase references and slab model, need judgement and literature; numerical choices are convergence tests a tool runs on the reported quantity. They fail differently: a wrong functional gives a plausible, biased number no test reveals; an unconverged cutoff gives noise a sweep removes.

![Physics choices need judgement; numerical choices are convergence tests the agent can run](../figures/13-dft-setup-two-kinds-of-choice.png)

*Figure: two kinds of DFT setting · schematic*

Reading the figure: left, the physics choices and their sources, made by a human and locked in PROJECT.md at the Approve-settings checkpoint; right, the numerical choices and their rules. The highlighted convergence tool, ours, writes its numbers into PROJECT.md along the grey arrow.

**Pseudopotentials come from a library.** VASP marks one recommended PAW dataset per element in its wiki; `_pv` and `_sv` variants add semicore p or s states, for early transition metals and wherever semicore states matter. The [SSSP library](https://www.materialscloud.org/discover/sssp) for Quantum ESPRESSO picked per element the best public file against all-electron equations of state, phonons, cohesive energy, pressure and band structure: an *efficiency* set for screening, a *precision* set for final numbers, each with a cutoff per element. In the [Δ-test](https://archive.materialscloud.org/record/1874) of Lejaeghere et al., Science 2016, and [Bosoni et al., Nature Reviews Physics 2024](https://archive.materialscloud.org/record/2023.81), both families matched all-electron codes as closely as independent experiments agree. Rules: take the recommended set; never mix families or versions; one dataset per element in bulk, slab and gas phase; record the version.

**Converge E_ads, not the total energy.** A metal atom's basis-set error is nearly the same with and without the adsorbate, so it cancels:

$$
\delta E_{\mathrm{ads}} = \delta E(\mathrm{slab}+A) - \delta E(\mathrm{slab}) - \delta E(A) \ll \delta E(\mathrm{slab}+A)
$$

E_ads thus reaches ±10 meV while the total energy is hundreds of meV off, provided both sides share settings: the convergence tool uses one mesh and one cutoff for slab and slab+A.

![Converge the difference, not the total: errors cancel in E_ads](../figures/14-convergence-error-cancellation.png)

*Figure: convergence of E_ads against cutoff and k-points · schematic, not to scale*

Reading the figure: left, E_ads, blue, enters the ±10 meV band near 1.3 × ENMAX, long before the total energy, grey. Right, against the in-plane k-mesh, a sharp Fermi edge, grey, oscillates longer than Methfessel–Paxton smearing, blue, which converges at about 7 × 7 × 1 on a 2 × 2 cell.

| Setting | Rule | Value | Owner; channel |
|---|---|---|---|
| Pseudopotentials | Library recommendation, Δ-test verified | PBE 54 is the current Materials Project and atomate2 default; OC20 used PAW with RPBE | Tool; lookup, in PROJECT.md |
| Functional, dispersion, spin, Hubbard U | Literature and CE27, per system | | Human; checkpoint, locked in PROJECT.md |
| Gas-phase references and corrections | Literature | | Human; locked in PROJECT.md |
| Cutoff | Largest ENMAX in the cell or the SSSP value, × about 1.3 if the volume relaxes, against Pulay stress; sweep E_ads of a test adsorbate | ±10 meV; OC20 350 eV; Materials Project 520 eV, comparing total energies across compounds | Tool; convergence tool, result in PROJECT.md |
| k-mesh | Dense for metals, whose occupation drops sharply at the Fermi level; Γ-centred on hexagonal cells; one k-point along vacuum; cell-consistent across supercells | 0.2 to 0.3 Å⁻¹ in-plane; OC20: 40 divided by the in-plane cell lengths | Tool; convergence tool |
| Smearing | Methfessel–Paxton or Marzari–Vanderbilt, damping the k-point oscillation; extrapolate to σ → 0 | σ = 0.1 to 0.2 eV | Tool; convergence tool |
| Layers, vacuum, dipole correction | Layers until E_ads stops changing; dipole correction when one face is covered | 4 to 5 layers, close-packed; vacuum at least 12 to 15 Å | Tool; convergence tool |
| Force and SCF thresholds | Convention | 0.02 to 0.03 eV Å⁻¹; 10⁻⁵ to 10⁻⁶ eV | Skill; SKILL.md |

Protocol libraries hold this without a language model: [AiiDA common workflows](https://aiida-common-workflows.readthedocs.io/), *fast*, *moderate* and *precise* for eleven codes; SSSP; pymatgen input sets with the Materials Project settings. The agent calls these and the convergence tool.

**Rejected:** the LLM writing cutoff and k-points from memory, as [AutoDFT](https://arxiv.org/html/2605.26179v2) does; right for Pt, perhaps wrong for an oxide, and nothing in the run shows which. The LLM may choose the protocol and say why; the numbers come from the protocol or the sweep.

## Where the literature is needed

Every term in E_ads is our own DFT energy; literature fixes settings before the run and checks results on known systems after it.

- **Essential:** the first calculation on a system, for the functional, since PBE tends to overbind CO, RPBE corrects some of this and dispersion matters for large or flat-lying molecules, and for gas-phase corrections, since O₂, CO₂ and N₂ carry known GGA errors. Known DFT problems: CO on transition metals, the "CO/Pt(111) puzzle" where GGA predicts the hollow and experiment the top site; open-shell molecules; magnetic surfaces; oxides needing a Hubbard U. Any comparison with other work: settings must match.
- **Optional:** screening similar systems with a validated setup; relative trends, less sensitive to the functional.
- **Adds nothing:** new systems without prior data; validate on a similar known system instead.

A lookup of minutes suffices: one or two published E_ads values with functional, the preferred site, computed and if possible measured, and any reported DFT failure. The agent may gather them; a human verifies, since language models misquote values and invent citations. The project itself needs a review of 20 to 40 papers: section 6.

## Prior work and its gaps

The chain from structure to E_ads is automated, in two generations; reliability and scope are open.

| Work | Type | What it does | Documented limitation |
|---|---|---|---|
| [CatKit](https://www.aiche.org/conferences/aiche-annual-meeting/2018/proceeding/paper/699a-catkit-symmetry-methods-automated-generation-catalytic-structures) | Toolkit | Symmetry-based surface and site generation | — |
| [ACAT](https://pypi.org/project/acat/1.7.0/) | Toolkit | Site and coverage identification for slabs and nanoparticles | Metals and alloys only |
| [AdsorbML](https://arxiv.org/pdf/2211.16486) | ML + DFT | Graph neural network screening with DFT check | Bounded by ML accuracy |
| [Adsorb-Agent](https://arxiv.org/html/2410.16658v3) | LLM agent | LLM proposes configurations, then relaxes them | Open loop; sign errors found later |
| [AdsMind](https://arxiv.org/html/2606.19152) | LLM agent | Closed-loop, physics-grounded configuration search | DFT validation on six systems; MAE 1.55 eV |
| [DREAMS](https://alphaxiv.org/abs/2507.14267) | LLM agent | Hierarchical multi-agent DFT on Quantum ESPRESSO and AutoCat | — |
| [CatMaster](https://arxiv.org/pdf/2601.13508) | LLM agent | Surrogate exploration with targeted DFT validation | — |
| [Catalyst-Agent](https://arxiv.org/pdf/2603.01311) | LLM agent | MCP agent around FAIRchem AdsorbML | v3, July 2026: 1.40 to 3.41 trials per hit; randomised baseline 13.3, 16.7 and 0 %; success is an MLIP energy inside a descriptor window |
| [AutoDFT](https://arxiv.org/html/2605.26179v2) | LLM agent | Closed-loop DFT with monitoring and failure recovery | Task completion, not chemistry accuracy |

AtomisticSkills is infrastructure, not a competitor: section 11. **Gaps we target:**

- Thin DFT validation: errors of order 1.5 eV, where activity trends need about 50 meV.
- Agents against enumeration: an [independent review](https://pith.science/paper/2606.19152) found AdsMind's loop converging above the exhaustive minimum; whether agents beat symmetry-based brute force is unsettled.
- Dependence on ML potentials, which fail badly on magnetic Co and Ni.
- Narrow chemistry: oxides, magnetism, high coverage and electrochemical interfaces are largely untouched.
- Run-to-run variability of hosted LLM workflows.

## Benchmarks and the gap

Each benchmark tests one part; none tests an agent end to end against symmetry-exhaustive search with full DFT verification on hard chemistry.

| Benchmark | Tests | Size or scope | Note |
|---|---|---|---|
| [OC20-Dense](https://arxiv.org/pdf/2211.16486) | Global-minimum search | About 1,000 combinations per split; 74 adsorbates; 80,000+ configurations | Sampled heuristically and randomly, not by full symmetry |
| [OCD-GMAE, Alloy-GMAE, FG-GMAE](https://zenodo.org/records/12104162) | Global-minimum energy prediction | From OC20-Dense, Catalysis-Hub and a functional-groups set | Cleaned subsets |
| AA20, OCD-GMAE62 | Agent configuration search | Small sets of Adsorb-Agent and AdsMind | — |
| OC20 | ML energies | One configuration per combination | Unsuitable for global minima |
| OC22 | ML energies on oxides | Oxide surfaces | — |
| CatBench | ML potentials on adsorption | 13 MLIPs, 47,000+ reactions; best about 0.2 eV | — |
| [Kempen, Cheula and Andersen](https://phys.au.dk/intercat/news-and-events/show/artikel/new-intercat-paper-luuk-kempen-raffaele-cheula-and-mie-andersen) | Foundational MLIPs | 80 models; adsorption, barriers, vibrations; metals and oxides | Many fail on magnetic Co and Ni; no single best model |
| CE27, Wellendorff et al., 2015 | DFT against experiment | Experimental chemisorption energies on transition metals | For choosing the functional |
| [OC20NEB](https://arxiv.org/abs/2405.02078) | ML transition states | 932 DFT NEB calculations | For the pathway extension |
| VASPBench | Agent task completion | 34 DFT tasks | Runs succeed; chemistry not judged |

**Our plan:** 1, an OC20-Dense subset, for comparability with published agents; 2, our symmetry-complete enumeration on 30 to 50 of those systems, to test whether OC20-Dense missed lower minima; 3, a hard set where tools fail: Ni, Co, one oxide such as TiO₂(110) or CeO₂(111); 4, easy controls: H and O on Pt(111) and Cu(111). Metrics: success in finding the DFT minimum, error against DFT, fraction of own failures flagged, compute cost, each against a plain AdsorbML-style run and AtomisticSkills' mat-surface-adsorption placement, section 11.

## How human insight enters the agent

A skill is one of five channels; each insight goes where it is enforced most reliably.

| Channel | Holds | Acts | Example |
|---|---|---|---|
| Skill, SKILL.md | General know-how, written once | Loaded whenever the task matches | Always break symmetry before relaxing; flag CO on Pt-group metals |
| Project memory, PROJECT.md | Choices for this system | Read at every step | RPBE-D3, four-layer slab, ½E(H₂) reference |
| Checkpoints | Live judgement | Agent pauses for approval | Approve settings; review flagged cases |
| Tools, code | Insight turned into rules | Every run, without fail | Reject an adsorbate relaxed more than 3 Å above the surface |
| Lessons log | Corrections from review | Fed back into the skill | Ni(111): set initial magnetic moments, or SCF fails |

**Rule of thumb:** a test becomes a tool, a procedure a skill line, a choice for one system project memory, a judgement needed each time a checkpoint. Code is most reliable: an LLM can misread a prompt but cannot skip a check it does not control.

**From [Get Physics Done](https://github.com/psi-oss/get-physics-done), GPD**, physics-research commands for Claude Code, Codex and Gemini CLI, we copy the Formulate interview on scope, assumptions, notation and verification targets, frozen into PROJECT.md, REQUIREMENTS.md, ROADMAP.md and STATE.md; locked conventions; a discuss step before each plan and execute phase; and autonomy, Supervised or Balanced, each turn treated like a graduate student's work. GPD also has a Verify stage on dimensions, limiting cases, symmetry and conservation laws, and commands to defer a tangent or branch into an alternative hypothesis. It lacks an adsorption and transition-state skill with DFT pitfalls, and validity checks as an MCP server: ours.

**Four kinds of intuition**; only the fourth is hard to obtain. The agent need not hold intuition in its weights: the first three are written where they are enforced, the fourth reaches a human cheaply, and logged corrections slowly turn the fourth into the first three.

| Kind | Example | Written in | Goes into |
|---|---|---|---|
| Procedures | Break symmetry before relaxing; converge E_ads, not the total energy; same settings on both sides of a difference | Textbooks: Sholl and Steckel, *DFT: A Practical Introduction*, 2009; Nørskov, Studt, Abild-Pedersen and Bligaard, *Fundamental Concepts in Heterogeneous Catalysis*, 2014. Protocol libraries: SSSP, AiiDA common workflows, pymatgen input sets. Forum fixes such as "set initial moments on Ni" from the VASP wiki and forum, Quantum ESPRESSO users list, lab wikis | The skill, with the citation; libraries called as tools; each forum fix verified on a test case first |
| Priors, expected ranges | H on Pt(111) near −0.5 eV; CO prefers top on Pt although GGA says hollow; universal ML potentials fail on magnetic Ni and Co | Benchmarks: CE27, Δ-test, CatBench, the 80-MLIP survey. Inputs and datasets: OC20 settings, NOMAD, Materials Cloud, Catalysis-Hub | Thresholds in the checks and the ML-doubt detector |
| Sanity constraints | 3 Å above the surface is desorbed; a minimum has no imaginary modes; a magnetic moment does not vanish on adsorption | Physics, written once | Code |
| Judgement of when to stop | Two ML potentials disagree; unseen chemistry; a value out of range | Experienced researchers: which defaults they distrust; our own runs: corrections with reasons | Interview before a run, flagged-case review after; the lessons log, promoted to the skill on recurrence |

![Scientific intuition is written down in more places than it seems; the rest we elicit and log](../figures/15-where-intuition-comes-from.png)

*Figure: sources of intuition, kinds of intuition, enforcing channels · schematic*

Reading the figure: sources on the left, from textbooks to our own runs, with the experienced researcher highlighted as the only source of judgement; the four kinds in the middle; enforcing channels on the right, linked by grey arrows. The dashed learning loop turns a checkpoint correction into a lessons-log line and a recurring lesson into a skill line or test.

**Formulate interview**, adapted from cognitive task analysis; each answer becomes a check, a prior or a skill line.

1. What do you check first when a number looks wrong?
2. On which systems do you not trust the default settings, and what do you change?
3. What do you do before you trust a machine-learned potential on a new metal?
4. Which published values would you compare a first result against?
5. What has silently gone wrong for you before?

**Skills evidence**, hence few skills, human-written, procedural and verified on a test case, with facts and ranges in code and project memory:

| Study | Finding |
|---|---|
| [SkillsBench](https://www.emergentmind.com/papers/2602.12670), 2026 | Curated human-written skills raised success by 16.2 percentage points across 84 tasks; self-written skills gave no gain or a loss |
| [Demystifying Agent Skills](https://arxiv.org/pdf/2608.14036), 2026 | Skills act as procedural anchors in 65.7% of cases, as fact injection in 4.5%; selection precision falls from 29.6% to 3.3% as the pool grows from 5 to 100 skills |

## Geometry stays in code: what the LLM may touch

Language models cannot be trusted with three-dimensional geometry. Which hollow, orientation and height; whether the adsorbate migrated, desorbed or dissociated; termination and fixed layers; a symmetry-trap saddle: each has a deterministic answer that code computes and shows the LLM as text. The ability is improving, uneven and unverifiable case by case, so it never decides:

| Study | Finding |
|---|---|
| [AtomWorld](https://arxiv.org/html/2510.04704), 2025 | Frontier models given ten kinds of CIF edit: add, remove, change or swap an atom 60 to 95% success; move an atom 20 to 80%; rotate a group below 12%; pymatgen as a tool helped little on hard edits; the authors advise a copilot role, not unsupervised modelling |
| Adsorb-Agent, in the [AdsMind](https://arxiv.org/pdf/2606.19152) paper | LLM-proposed configurations: MAE 1.84 eV against DFT, maximum above 3.5 eV; worst are sign errors on molecular adsorbates with complex binding |
| [LLMConfBench](https://arxiv.org/html/2609.20666), 2026 | The newest models rank small-molecule conformers from raw XYZ with Kendall τ about 0.6, UFF 0.2; good on hydrogen bonding, poor on ring strain; tracks general reasoning, not geometric training |
| [MiSI-Bench](https://arxiv.org/html/2512.10867v1), 2025 | A fine-tuned 7-billion-parameter vision model beats human experts on molecular spatial transformations from images |

![Geometry stays in code: the LLM reads descriptor cards and verdicts, never coordinates](../figures/17-geometry-stays-in-code.png)

*Figure: geometry flow through the agent · evidence and design, schematic*

Reading the figure: the top row is the evidence above. Below, tools turn a structure into the highlighted descriptor card and an image; the LLM reads the card and acts only through named calls such as "place adsorbate at fcc hollow, orientation 2" or "displace by 0.05 Å", and the check verdict returns into the card, dashed. The red dotted path, the LLM editing coordinates, is forbidden.

| Geometric question | Who answers | What the LLM sees |
|---|---|---|
| Which sites exist and their symmetry | spglib, CatKit or ACAT; Tool | "fcc hollow, C3v, coordination 3; hcp hollow, C3v, atom beneath" |
| Which orientations are inequivalent | Stabiliser-group enumeration; Tool | A numbered list of orientations |
| Where to put the adsorbate | Tool call `place(site, orientation, height)` | The descriptor card of the result |
| Did it stay where it was put | Validity check; Tool | "migrated: fcc hollow to bridge, 1.4 Å" |
| Is it a minimum | Frequency calculation; Tool | "one imaginary mode, 120i cm⁻¹" |
| Is the slab built correctly | Checks on layers, vacuum, termination; Tool | Numbers with pass or fail |
| What does it look like | ASE render to PNG; Tool | An image for a second look, never the basis of a decision |

**Descriptor card**, one text block per structure: composition and cell; facet, layers, vacuum, fixed layers; site label and point group; coordination number; height above the surface plane; nearest-neighbour distances; tilt; displacement from the start; total magnetic moment; validity verdicts. It follows [Robocrystallographer](https://www.cambridge.org/core/journals/mrs-communications/article/robocrystallographer-automated-crystal-structure-text-descriptions-and-analysis/3C201F132450877464B2D0B1B8C4ED01); models given such text out-predicted graph neural networks given the structure, in [LLM-Prop](https://www.nature.com/articles/s41524-025-01536-2) and [LLM4Mat-Bench](https://arxiv.org/pdf/2411.00177).

**Informing the agent**, by value:

1. A geometry section in the skill: the site table of section 2, the orientation rule, the symmetry trap, the card format, no coordinates from the LLM.
2. Tool documentation written for the model: in [MatTools](https://arxiv.org/html/2505.10852v2), 2025, GPT-4o solved 18% of real pymatgen tasks alone, 40% with retrieved LLM-written docs, 55% adding self-reflection; model-written docs retrieved better than official ones.
3. An image beside the card, as AtomWorld recommends and MiSI-Bench supports: a check, not a decision input, until our benchmark shows otherwise.
4. Twenty AtomWorld-style editing tasks in our benchmark, place, rotate, build a supercell, cut a facet; near 100% expected with tools, so failures expose bypassed tools.

**Rejected:** the LLM writing or editing coordinates, or choosing configurations by its own chemical reasoning without enumeration, as Adsorb-Agent does.

## Prior work on giving agents scientific intuition

Nobody has solved the transfer of tacit knowledge into agents; approaches differ in where knowledge ends up, weights, context or code, and who checks it. We found no Anthropic research on this problem; its contributions are the skill format and science skill sets. Also in this landscape, and covered elsewhere: AtomisticSkills, context and tools, section 11; Get Physics Done and the skills studies, context, section 8; protocol libraries, code, section 4.

| Work | Approach | Lives in | Lesson |
|---|---|---|---|
| [Agent Skills](https://www.anthropic.com/news/skills), Anthropic, 2025 | Folders of instructions, scripts and resources loaded when a task matches | Context | Our skill format |
| [Claude for Life Sciences](https://www.anthropic.com/news/claude-for-life-sciences), [Claude Science](https://www.anthropic.com/news/claude-science-ai-workbench), Anthropic, 2025–26 | 60+ curated science skills; coordinating agent; reviewer agent checking citations and calculations; auditable artifacts | Context, tools | Reviewer and audit-trail patterns; no surface-chemistry or DFT-settings skill |
| [Scientific Agent Skills](https://github.com/k-dense-ai/scientific-agent-skills), K-Dense, 2025–26 | 146+ open skills over databases and packages | Context | Breadth; nothing on DFT trust |
| [ether0](https://www.futurehouse.org/news/ether0-a-scientific-reasoning-model-for-chemistry), FutureHouse, 2025 | 24B model, reinforcement learning on 640,730 verifiable chemistry tasks | Weights | Trainable where a verifier exists; DFT is one, beyond hackathon scope |
| [ChemCrow](https://arxiv.org/abs/2304.05376), 2023, 18 expert tools; [Coscientist](https://www.cmu.edu/news/stories/archives/2023/december/cmu-designed-artificially-intelligent-coscientist-automates-scientific-discovery), Nature 2023; [El Agente](https://arxiv.org/abs/2505.02484), 2025 | LLM plans, expert tools execute; El Agente over 87% on course exercises | Tools | Expertise in tools works; chemistry accuracy unscored |
| [Virtual Lab](https://biohub.org/news/with-no-need-for-sleep-or-food-ai-built-scientists-get-the-job-done-quickly/), Nature 2025; Google's [AI co-scientist](https://research.google/blog/accelerating-scientific-breakthroughs-with-an-ai-co-scientist/), 2025, generate, reflect, rank and evolve agents | Personas with a critic; the human wrote about 1% of the Virtual Lab's words | Context, the model's own | A critic helps; the knowledge stays the model's |
| [Kosmos](https://arxiv.org/html/2511.02824v2), 2025 | World model shared across 200 rollouts; 79.4% of claims judged accurate | Context, memory | Our PROJECT.md plus lessons log |
| [LLMs for tacit knowledge discovery](https://arxiv.org/pdf/2507.03811), 2025; [KUPAS MASTER](https://arxiv.org/abs/2609.37673), [Tacit Fragments](https://www.alphaxiv.org/abs/2609.operationalising-tacit-knowledge-agentic-ai), 2026 | Interview agents and governed memory of cues and judgements | Context | Formal versions of our interview and log; none in physics yet |
| [FrontierScience](https://openai.com/index/frontierscience), OpenAI, 2025; [K-Bench](https://arxiv.org/pdf/2608.21601), 2026; ChemBench; CURIE | Measure only: GPT-5.2 77% on olympiad problems, 25% on research tasks; in K-Bench no model reached what a domain scientist accepts, over-claiming the commonest failure | — | Weights are not enough; checks and humans stay |

![Expert knowledge can live in model weights, in context, or in code; only code and benchmarks enforce it](../figures/16-intuition-landscape.png)

*Figure: landscape of prior work on scientific intuition in agents · schematic*

Reading the figure: left to right, knowledge sits in weights, context or code; bottom to top, it is model-generated, expert-curated or benchmark-verified. The highlighted box is this project, checks as code, one procedural skill and a measured failure rate, reusing the skill-library layer along the dashed arrow.

**For us:** write the know-how down, since frontier models over-claim on open research tasks; put each kind in its enforcing channel, section 8; obtain judgement by structured interview and logged corrections, which interview agents may take over later.

## Building on AtomisticSkills

[AtomisticSkills](https://arxiv.org/abs/2605.24002), MIT, May 2026, [code](https://github.com/learningmatter-mit/AtomisticSkills), is our substrate: we ship skills and tools inside it, so our contribution narrows to a trust layer for surface chemistry. It is an open-source outer harness for coding agents such as Claude Code, Gemini CLI and Cursor, in four layers: workflows the agent plans and a human approves; over 100 human-curated skills validated against literature values where available; more than 50 type-checked MCP tools on more than 10 servers, including FairChem with UMA, MACE, MatGL and Atomate2 for remote DFT; rules such as a mandatory literature review and an MLIP registry check. Hyperparameters are logged beside outputs; the authors call the mode co-pilot, with human supervision essential for multi-day campaigns.

Its Fe-oxide OER case study chains surface cleavage, O\*, OH\* and OOH\* placement, MLIP relaxation, DFT, and a free-energy and volcano analysis, close to our phases 2 and 4. It lacks, as far as the paper says, symmetry-complete enumeration, validity checks, ML-doubt escalation and a measured failure rate; its authors call evaluating autonomous atomistic research open, which our benchmark addresses.

![Our trust layer plugs into AtomisticSkills; most plumbing is reused](../figures/09-atomisticskills-layers.png)

*Figure: our skills on AtomisticSkills · 4 layers*

Reading the figure: under the coding agent, reused skills are outlined and our four trust-layer skills highlighted: symmetry-complete site enumeration, ML-doubt escalation, transition-state search, benchmark harness. The tool layer reuses the FairChem, MACE, MatGL and Atomate2 servers and adds a validity-check server; of the rules on the right, the lower three are ours.

| Our step | AtomisticSkills component | Plan |
|---|---|---|
| Literature check | Rule: mandatory literature review | Reuse; add our DFT-pitfall list |
| Approve settings and network | Plan reviewed before execution | Reuse; add the PROJECT.md lock |
| Converge numerical settings | Not described | New tool, section 4 |
| Build bulk and slab | mat-db-mp; ASE build | Reuse; mat-htvs-cutcleansurface is not public |
| Enumerate sites and pairs | mat-surface-adsorption: MatCalc AdsorptionCalc on pymatgen's AdsorbateSiteFinder, which labels no fcc or hcp hollow | New skill on ACAT and spglib; theirs is our baseline |
| ML pre-screen | FairChem, MACE and MatGL MCP servers | Reuse; mat-htvs-mlip-relax is not public |
| Flag ML doubt and escalate | ml-committee-uncertainty, ml-mlip-benchmark, ml-mace-finetune | New skill that triggers these; calibration on DFT labels is ours |
| DFT relaxation | Atomate2 MCP server | Reuse; mat-htvs-vasp is not public |
| Validity checks | — | New MCP tool server |
| Transition-state search and validation | chem-neb-barrier: ASE NEB, IDPP, climbing image, no frequency or connectivity check; chem-ts-optimization, chem-irc-verification: Sella, molecules only | New: periodic saddle validation with frequencies, IRC, band connectivity |
| Free-energy diagram | chem-thermochemistry; the catalysis-activity skill is not public | Build for thermal catalysis |
| Microkinetic model | Thermodynamics and kinetics skills, unspecified | Check coverage |
| Benchmark comparison | — | New; our main contribution |
| Open release | Hyperparameter logging | Reuse; add provenance and Zenodo export |

**ML doubt to fine-tuning.** On doubt, as on Ni or Co, sample a few configurations, label them with DFT, measure the error with ml-mlip-benchmark and, if needed, fine-tune MACE with ml-mace-finetune: stop, measure, repair, then ask only if repair fails.

**Verified on 21 October 2026** in the [repository survey](repo-survey.md): 133 public skills under MIT, none of the paper's mat-htvs catalysis skills; the table records what ships. The catalysis layer is ours to write.

## Extension to reaction pathways

This is the later phase of section 1: the adsorption agent becomes a subroutine of adsorption energies → reaction energies → transition states and barriers → a microkinetic model of rates and selectivity.

![Each level reuses everything below it](../figures/10-adsorption-to-kinetics.png)

*Figure: from adsorption to kinetics · 4 levels*

Reading the figure: the highlighted box is what the agent computes now; each box builds on those to its left, so early errors propagate.

ΔE = E(FS) − E(IS) and E_a = E(TS) − E(IS), with IS and FS the relaxed initial and final states and TS the transition state, a saddle point. Harmonic transition-state theory gives the rate, with k_B Boltzmann's constant, h Planck's constant and ΔG‡ the free-energy barrier; the Brønsted–Evans–Polanyi relation, E_a ≈ αΔE + β fitted per reaction family, is a cheap pre-screen.

$$
k = \frac{k_{\mathrm{B}} T}{h} \exp\left(-\frac{\Delta G^{\ddagger}}{k_{\mathrm{B}} T}\right)
$$

![A barrier is measured from the relaxed initial state up to the saddle point](../figures/11-reaction-energy-profile.png)

*Figure: reaction energy profile · schematic, not to scale*

Reading the figure: from the co-adsorbed initial state A\* + B\*, IS, over TS to AB\*, FS, E_a is the rise to TS and ΔE the drop to FS. A TS has exactly one imaginary mode, and an IRC from it must reach IS and FS.

**Accuracy.** An energy error δ scales the rate by exp(δ / k_B T); at 500 K, k_B T ≈ 0.043 eV, so 0.1 eV gives exp(2.3) ≈ 10, harmless for site ranking but tenfold in rate, hence rate-controlling steps return to DFT. An initial-state error enters E_a in full, and a wrong initial configuration, another site, an unrelaxed geometry or a symmetry-trap saddle, ties the TS to the wrong reactant: trust the adsorption stage before any barrier.

| Endpoint error δ | Rate factor at 500 K |
|---|---|
| 0.05 eV | about 3 |
| 0.1 eV | about 10 |
| 0.2 eV | about 100 |

![An endpoint error moves the barrier one-to-one and the rate exponentially](../figures/18-endpoint-error-propagation.png)

*Figure: endpoint error propagation · schematic, not to scale*

Reading the figure: left, an IS wrong by δ, red dashed, against the correct IS, blue, shifts the barrier by δ. Right, the rate factor exp(δ / k_B T) at two temperatures, the tolerable range as a blue band.

**Changes to the adsorption stage:** one set of gas-phase references, e.g. H₂, H₂O, CO or CO₂, and identical settings for every intermediate and TS; A\* + B\* endpoints in one cell, so pair enumeration with Burnside counting, and lateral interactions; the top few configurations per intermediate, since the global minimum may miss the lowest-barrier path; mirror-equivalent paths once; no symmetric NEB starting band, which can hide a lower, symmetry-broken path.

**Prior work on transition states.** This table records that a plain transition-state agent is not novel; open are endpoint quality and saddle validation. Pynta and El Agente Potente are in section 16.

| Work | Type | What it does | Limitation or gap |
|---|---|---|---|
| [CatTSunami](https://arxiv.org/abs/2405.02078), 2024 | ML, no LLM | ML NEB on surfaces; TS within 0.1 eV of DFT 91% of the time, 28× faster; 174-reaction network in 12 GPU days | Needs good endpoints |
| [Fine-tuned MLIP TS search](https://arxiv.org/pdf/2603.24482), 2026 | ML, no LLM | TS with fewer than 10 DFT single points on average | Surface elementary steps only, not reconstructions |
| [NEBscape](https://www.nature.com/articles/s41524-026-02298-1), npj Comput. Mater. 2026, [code, MIT](https://gitlab.mpcdf.mpg.de/hjung/nebscape) | Automated, no LLM | Endpoints by minima hopping from symmetry-inequivalent sites, separations above 4.5 Å excluded, energy–distance Pareto selection, atom mapping, graph checks along the band; 304 OC20NEB reactions, 94 % converged | Cut-off and trade-off instead of a nearest-first objective; no agent reasoning or checkpoints |
| [TSAgent](https://arxiv.org/abs/2605.14154), 2026, [code, no licence](https://github.com/transition-state-search/TSAgent) | LLM agent | Plan–execute–analyse–replan at DFT level; 83% on a 100-example OC20NEB subset; 70% held-out against 73 ± 12% for human experts; reproduces BEP for NH₃ dissociation | Saddle accepted on band convergence, one significant imaginary mode and a barrier fitting the endpoints; no IRC; endpoints given, not generated; VASP only |
| [CatDT](https://arxiv.org/html/2606.05050), arXiv June 2026 | LLM multi-agent | Eight agents, 27 tools; a validation agent checks proposed endpoints in code: overlaps below 0.8 Å, element counts, path collisions, a UMA energy screen, up to ten rounds; endpoint success 41 % to 84 % over 600 OC20 surfaces; memory ablation: none 49 %, distilled banks 52 to 54 %, raw case bank 68 %, full stack 84 % | No distance objective, no recombination check; code promised on publication, link returns 404 |
| [CopyCAT](https://iciq.org/es/?p=72665), ICIQ, 2026 | LLM multi-agent | Chemical reasoning turned into 3D adsorbate and TS structures on surfaces | Thesis-stage; no accuracy against DFT found |
| [TSBench](https://arxiv.org/abs/2609.08503), 2026 | Benchmark | Seven frontier LLMs build TS guesses with editing tools for 78 elementary reactions: 50% success, 67% with diagnosis-driven revision | Most failures are plausible saddles linking the wrong reactant–product pair |

CatDT's endpoint gate is the closest to our trust layer and confirms the need; its ablation shows a raw case bank beats distilled lessons. TSBench's main failure, a saddle linking the wrong pair, is an endpoint problem that enumeration, pair enumeration and connectivity checks prevent. The gap is *barrier-ready endpoints*, validated before any barrier run, and a measurement nobody reports: how far endpoint quality moves the barrier.

**Automate the middle**, endpoint mapping, TS search, validation, free-energy corrections and microkinetics, which is repetitive and error-prone; a human approves the network and interprets the mechanism, since a missing step cannot be recovered downstream.

## The complete workflow

Four phases; phase 2, the adsorption agent, is reused for every intermediate in phase 3. Phase 3 and the kinetics of phase 4 are the later phase of section 1.

![People set and judge; tools compute; the LLM plans and repairs](../figures/12-complete-workflow.png)

*Figure: complete agent workflow · 4 phases, 20 steps*

Reading the figure: the dashed loop sends rate-controlling steps from the microkinetic model back to DFT refinement; corrections from either review go to the lessons log, recurring ones into the skill.

1. Phase 1 fixes everything before any calculation: literature check, reaction network, one locked set of references and settings.
2. Phase 2 adds pair enumeration and passes on the top few configurations; "Flag ML doubt" is the Ni and Co self-distrust.
3. Phase 3 repeats phase 2 for transition states: ML search, DFT refinement, failure diagnosis, validation, review.
4. Phase 4 adds kinetics, benchmark comparison and the open release.

"Approve settings and network" is the box whose silent failure corrupts everything downstream: no later accuracy repairs a wrong reference or a missing step.

## The solution planner from the whiteboard

The second board of 21 October 2026 makes step 3, placing the dissociated fragment, the heart of the plan, and its six points are the final-state procedure 9a to 9e of section 16. The plan follows NEBscape's shape: potential chosen first, sites by symmetry, a distance window for the fragment, SOAP clustering of the survivors, minima hopping as the alternative generator. The start is known, surface and adsorbates with their energies, and E_ads for the adsorbate is in the literature.

![Step 3 of the board is the final-state problem; its six points land in 9a to 9e](../figures/19-solution-planner-pipeline.png)

*Figure: solution planner, second board · 10 steps, 6 points, extension layer, schematic*

Reading the figure: the board's steps in grey carry a red problem and fix each; step 3 is highlighted because it is the stated problem. The blue block takes the six points written under step 3 and names the sub-step each becomes. The dashed band holds the board's question marks.

| Whiteboard step | Workflow step, section 3 | Status |
|---|---|---|
| (1) Structure retriever | Choose system and settings | Keep; lock settings and references in PROJECT.md first |
| (1*) MLIP selection, before placement | ML pre-screening | Benchmark on the system class, record why; one potential for IS and FS; spin for Ni and Co |
| (2) Adsorption sites with pymatgen | Site and orientation enumeration | Fix: symmetry-complete with spglib and ACAT; fcc and hcp hollows apart |
| (3) Adsorbate placement, six points | The final-state procedure 9a to 9e | Point 1, least distance before B is pulled back: the bond-re-formed check, 9d. Point 2, window [1.5 d, 5] Å with d the length of the bond to break: the range of B sites around A, 9b; NEBscape cuts at 4.5 Å. Point 3, the MLIP's pull force on the binding fragment: a one-force-call pre-filter per pair before relaxing, new in 9c. Point 4, agentic critique of the cleavage: the geometry critic proposes a site type per fragment and never overrides a check. Point 5, pymatgen site and orientation so the fragment adsorbs: 9a, symmetry-complete and counted. Point 6, minima hopping with the MLIP: NEBscape's generator, wrapped as the baseline policy |
| (4) Initial configurations | Site and orientation enumeration | Fix: conformers in vacuum first, Burnside counting; start 2 to 3 Å up |
| (4.1) Physics-based filtering | Validity checks | Fix: write the tests of section 3 |
| (5) MLIP selection | ML pre-screening; flag ML doubt | Problem: organometallics; dispersion, spin, images 10 Å apart |
| (6) SOAP clustering, lowest per cluster | Choose, 9e | Cluster the gate's survivors by SOAP as NEBscape does; keep the nearest and the lowest per cluster; three or more per cluster is open |
| (7) Uncertainty estimation | Flag ML doubt | Fix: calibrate disagreement against a few DFT labels |
| (8) Rank; human picks up to five | Review flagged cases | Fix: choose on card, rank and uncertainty; choice and reason to the case bank |
| Input prompt: critic and knowledge prompts, reasoning questions | Skill and interview | Knowledge as a written skill, prompts as a fixed list; the LLM reads cards only |
| (9) to (14) path steps | Extension to reaction pathways, section 12 | Later phase |

**Extension layer**, the board's question marks: a vision model that predicts the whole placement, only after the geometry benchmark shows an image helps; more than three configurations per cluster, set by the recombination rate per cluster; agentic uncertainty, the variance of the planner's choices over several runs on one input; active learning from high uncertainty to DFT labels to a fine-tuned MLIP; an LLM critic of descriptor cards that never overrides a code check; DFT on the five chosen configurations before any path search; multi-step mechanisms by energetic span, then catalysis. Open questions: section 18.

## The augmented pipeline: what to borrow, what is missing, what is ours

Against the transition-state papers every step is borrowed or standard, so the claim rests on four things none reports: validated endpoints with measured endpoint-to-barrier propagation, calibrated ML doubt, agentic uncertainty, and an open release scored on a public benchmark.

![Every step borrows from a named paper or is standard; the claim lives in the blue column](../figures/20-augmented-pipeline.png)

*Figure: augmented pipeline · 15 steps, 5 columns, one colour per kind of idea, schematic*

Reading the figure: rows are steps, read left to right under the legend: white the step, path steps 9 to 14 marked "to build"; green the refinement and its paper; amber missing; red existing elsewhere, so no claim; blue ours; dashed purple the extension beside its step; grey italics nothing to add. The three bottom boxes give the verdict: taken, missing, ours.

**Refinements to borrow.**

1. Settings from a protocol or an E_ads sweep, never the LLM: [AiiDA common workflows](https://www.nature.com/articles/s41524-021-00594-6), [SSSP](https://arxiv.org/pdf/1806.05609), [Δ-test](https://archive.materialscloud.org/record/1874); AutoDFT rejected, section 4.
2. Heuristic plus random placement when symmetry is unknown; ML relaxation of many candidates, then DFT on the top few; four anomaly checks, to which we add the imaginary-mode check: [AdsorbML](https://arxiv.org/pdf/2211.16486).
3. Product states placed by the same enumeration as reactants, several initial–final pairs per reaction, the lowest valid barrier kept; its OC20NEB set of DFT nudged-elastic-band calculations as the path benchmark: [CatTSunami](https://arxiv.org/abs/2405.02078).
4. Atom mapping and symmetry alignment of the endpoints before interpolation: [NEBscape](https://www.nature.com/articles/s41524-026-02298-1).
5. Fine-tuning at the saddle with a few DFT single points, the active-learning extension at step 5 with ml-mace-finetune: [fine-tuned MLIP transition-state search](https://arxiv.org/pdf/2603.24482).
6. A propose-then-validate endpoint gate before any barrier run, [CatDT](https://arxiv.org/html/2606.05050); diagnosis-driven revision when validation fails, [TSBench](https://arxiv.org/abs/2609.08503).
7. BEP as a sanity check on each barrier, reproduced for NH₃ dissociation by [TSAgent](https://arxiv.org/abs/2605.14154); the energetic span of Kozuch and Shaik, from memory, not looked up here, for multi-step mechanisms.
8. Placement by script, since LLM coordinate edits fail: [AtomWorld](https://arxiv.org/html/2510.04704), the TSBench failure analysis, section 9.

| Step | Already exists in | What makes it ours |
|---|---|---|
| (2) Sites | pymatgen site finder in Adsorb-Agent, AdsMind, AtomisticSkills | Symmetry-complete and counted; the count checked |
| (3) Placement | Every agent scripts it; CopyCAT bets on LLM reasoning to 3D | The LLM never touches coordinates; descriptor card and named tools |
| (4.1), (6) Validity checks | AdsorbML's four checks | One gate in code on both endpoints before any path: barrier-ready |
| (8) Top-k then DFT | AdsorbML | The human picks on cards with uncertainty; choice and reason logged |
| (9) Final-state enumeration | CatTSunami, NEBscape | The same gate on the final state; a failing state is never paired |
| (11) Path search | CatTSunami, TSAgent, CatDT, NEBscape | Nothing; a wrapped tool |
| (12) Saddle validation | Partly: TSBench revision, CatDT gate | Imaginary mode and endpoint connectivity as code; propagation measured |
| (13) DFT refinement | Standard | Same locked settings as the endpoints |

**Still missing:** the product as a structure, with one set of gas-phase references; A\* + B\* pair enumeration when the product forms from two adsorbates; an intended-reaction check per initial–final pair, against TSBench's main failure; imaginary-mode and endpoint validation as code, since TSAgent runs no IRC and CatDT is unpublished; ML disagreement calibrated on a few DFT labels; an OC20NEB subset with a single-placement baseline.

**Verdict.** A plain transition-state agent is not novel, per the table of section 12, and AdsorbML has validity checks and top-k DFT. Ours, in hackathon time: barrier-ready endpoints, one gate on both, the endpoint-to-barrier propagation in eV and as a rate factor following in the later phase; calibrated ML doubt that escalates instead of guessing; agentic uncertainty over repeated planner runs; an open skill and MCP tools on AtomisticSkills, scored on an OC20NEB subset. Questions: section 18.

## The final-state problem: the nearest non-recombining product

The product of a dissociation step is the co-adsorbed pair as close as possible without bonding back. CatTSunami builds it heuristically; we enumerate it completely, gate it in code and report what was rejected.

**Names.** The problem is the scope of section 1; its answer is the *nearest non-recombining final state*. CatTSunami calls such placements *proximate*; classical DFT papers co-adsorb the fragments at nearest-neighbour or next-nearest-neighbour sites.

**Why nearest.** A band from AB\* to a far product holds the bond-breaking saddle and one or more diffusion saddles; the climbing image can lock onto the wrong maximum, and the barrier is not the elementary step's. The nearest valid product gives one saddle. It need not be the lowest in energy, since adjacent fragments often repel; report E(FS near) and, from separate cells,

$$
E(\mathrm{FS}\ \infty) = E(A^*) + E(B^*) - E(\mathrm{slab})
$$

Their difference is the lateral interaction; diffusion to the stable product is a separate step.

**Cost.** The DFT band is the expensive step and the one that fails; a far or invalid product lengthens it, so it needs more images and iterations and may not converge or may find the wrong maximum. CatTSunami, even with heuristic endpoints:

| CatTSunami quantity | Value |
|---|---|
| DFT single points per reaction in its ML + DFT approach: initial, transition, final state | 3 |
| Force convergence criterion for a band | fmax < 0.05 eV/Å within the step limit |
| ML bands converged, Equiformer V2: dissociations; transfers | 81 to 82 %; 68 to 72 % |
| DFT bands in the CO-hydrogenation case study converged at standard settings | 102; 8 failed and needed a rerun |
| Converged bands that were nevertheless wrong | 14 % |

Wrong bands had too few frames to sample the saddle, or an unintended bond broke or formed. Its two filters join our saddle validation, step 12: the breaking bond elongated to 1.25 to 1.63 times its initial length in some frame; connectivity constant except that bond. Of three measurable outputs, nearest-pair recombination is measured now; the barrier shift and the DFT force calls and failure rate, gated against naive endpoints, come later.

![The product fragments go as close as possible without bonding back; a far final state folds diffusion into the band](../figures/21-nearest-non-recombining-final-state.png)

*Figure: nearest non-recombining final state · 4 candidates, 1 profile, 4 recipe steps, schematic, not to scale*

Reading the figure: of three candidates, A blue and B orange, B at the adjacent hollow bonds back, rejected in red; B one lattice spacing away stays apart, chosen in blue; a far B is valid but its band includes diffusion. The profile shows the one saddle to the near product, blue, against a far product's extra diffusion saddles, dashed grey; the recipe adds our step to each of CatTSunami's four.

**Formal statement.** Over all symmetry-distinct site pairs, s_A for A and s_B for B, minimise the site-graph distance between A\* and B\*, in-plane distance breaking ties, subject to: after relaxation the connectivity graph is the product graph, no A–B bond; no fragment desorbed, moved site or went subsurface; surface unchanged; zero imaginary modes; no interaction with periodic images. Desorption is checked per fragment, since fairchem's DetectTrajAnomaly treats A\* + B\* as one adsorbate and passes a frame where B has left and A stays bound. Keep the first few survivors in order.

| Work | What it does for the product state | What it does not do |
|---|---|---|
| [CatTSunami](https://arxiv.org/abs/2405.02078), AutoFrameDissociation, 2024 | Product 1, the fragment with the reactant's binding atom: 5 lowest-energy placements within 2 Å; for each, 5 placements of product 2 in a 1 to 3 Å shell; 25 frames relaxed by ML; frames "where the products react or some other anomaly occurs" discarded; one survivor picked at random. Current fairchem code: shells at 2 and 3 times the largest slab covalent radius; band on ASE's DyNEB with the UMA calculator | No minimum-distance objective; sampled, not symmetry-complete; random pick; rejected frames not reported |
| [Pynta](https://chemrxiv.org/engage/chemrxiv/article-details/647114454f8b1884b755bc5a), JCIM 2023 | Reactants, products and atom maps in; symmetry-unique adsorbate configurations; harmonically forced saddle guesses; frequencies and IRC on every saddle; rate coefficients out | Not aimed at the closest product; DFT-level cost |
| [NEBscape](https://www.nature.com/articles/s41524-026-02298-1), 2026, [code, MIT](https://gitlab.mpcdf.mpg.de/hjung/nebscape) | Symmetry-inequivalent sites by spglib; two adsorbates placed combinatorially on unique sites without steric overlap; separations above 4.5 Å excluded; Hookean constraints keep fragments intact during minima hopping; candidates within 1.2 eV of the minimum on the first two energy–distance Pareto fronts, deduplicated by SOAP; atom mapping and periodic alignment; graph-isomorphism checks along the band; 304 OC20NEB reactions, 94 % converged, 9 % multi-step against 17 % | No nearest-first objective: a cut-off and a trade-off; stochastic sampling, uncounted; recombination prevented by constraint, not tested and logged |
| [Reproducible NEB orchestration](https://arxiv.org/abs/2603.14737), 2026 | Snakemake workflow: endpoint minimisation, structural alignment, initial path with PET-MAD and eOn | Gas-phase molecules; no surface product placement |
| [El Agente Potente](https://arxiv.org/abs/2609.14840), 2026 | LLM agent, typed execution graphs plus a coding mode on MLIPs; adsorption and catalytic reaction workflows; selects the band's initial and final images | The abstract gives no success rate and no final-image rule for a dissociation |
| Classical DFT studies | Fragments at nearest-neighbour or next-nearest-neighbour hollows, chosen by the author | Not automated; the choice rarely justified |

So NEBscape is the closest prior work, closer than CatTSunami: it bounds the separation at 4.5 Å and trades distance against energy on a Pareto front; CatTSunami samples a shell. Not done by either: a nearest-first objective over symmetry-complete, counted pairs; a gate after relaxation with a logged reason per rejection; the recombination rate of nearest pairs; and the comparison of the three final-state policies, nearest-first, Pareto, sampled, on the same OC20NEB dissociations. NEBscape's endpoint generator is what step 9 wraps, and its Pareto choice is the baseline our policy is scored against beside the OC20NEB product frame.

**In the pipeline.** This is step 9, with the pair enumeration of section 12 and the step 4.1 gate plus a connectivity criterion, and it ends the core for now. It feeds step 10, pairing, which reuses CatTSunami's unwrapping by depth-first search from the binding atom, the unbroken part moved as one moiety. Extensions: a coverage scan over cell sizes for the lateral interaction; the lowest energy within one site hop as alternative target. Measured now: nearest-pair recombination per system and shell; E(FS near) − E(FS ∞); our final state against the OC20NEB product frame in A–B distance, energy and validity.

Figure 23 redraws section 15 around this problem, with the final-state search as sub-steps 9a to 9e.

![Surface + AB* in; the nearest non-recombining A* + B* and the barrier to it out](../figures/23-problem-pipeline.png)

*Figure: pipeline for the stated problem · 15 rows, 5 columns, one colour per kind of idea, schematic*

Reading the figure: the output box lists the final state with E(FS near), E(FS ∞), the pairs tried and rejected, the recombination rate and the uncertainty, and marks the barrier as later. Rows use the colours of figure 20 with an owner line, and rows 10 to 14 are dashed grey, a later phase. The blue bracket marks 9a to 9e; 9a and 9c are CatTSunami's, so the claim sits in 9b, 9d and 9e. The verdict band counts two numbers now, the recombination rate and E(FS near) − E(FS ∞), and the barrier shift and band cost later.

| Sub-step | Owner | Does | Output |
|---|---|---|---|
| 9a | Tool | Place A, the fragment keeping the binding atom, at symmetry-distinct sites near the IS site, or fixed at it | Placements of A\*, counted |
| 9b | Tool | Enumerate B sites around each A by site-graph distance, within the board's window [1.5 d, 5] Å, d the length of the bond to break | Symmetry-distinct pairs, nearest first, counted |
| 9c | Tool | Pre-filter by one MLIP force call per pair, a force on B towards A flagging likely recombination and sending the pair to the back of the queue; then relax every pair with the potential and settings of the initial state | Flagged pairs; relaxed pairs |
| 9d | Tool | Gate: no A–B bond; nothing desorbed, moved or subsurface; surface intact; no imaginary mode | Survivors; every rejection with its reason |
| 9e | Tool, LLM writes it up | Cluster survivors by SOAP as NEBscape does; nearest first, then energy; keep the nearest and the lowest per cluster | Final states, E(FS near), E(FS ∞), recombination rate |

Open questions: section 18.

## Positioning and hackathon strategy

Sharpen, do not pivot: keep the adsorption domain and claim "an agent that knows when not to trust itself", not "an agent that computes adsorption energies".

At the [2025 LLM Hackathon for Materials Science and Chemistry](https://arxiv.org/pdf/2605.03205) over 40 of 88 projects used tool-calling agents, so a DFT-calling agent is the median entry; literature and RAG agents, "AI scientist" pipelines, DFT and MD wrappers, ML screens, data assistants and unmeasured demos are crowded. Winners stress critique and reliability, as the 2026 NAIS top prize for an agent that spots research flaws before work begins; human-in-the-loop design, judged at dkNET–Texera; validation, traceability and explainability, in the Cambridge multi-agent rubric.

| Option | Novelty | Feasible in hackathon time | Verdict |
|---|---|---|---|
| Generic adsorption agent | Low, exists | High | Avoid as the main claim |
| Open skill + MCP tool pack | Medium–high | High | Do |
| Reliability benchmark against a baseline | High | High | Do |
| Agent that detects ML failure and escalates | High | Medium | Do; the demo centrepiece |
| New catalyst discovery | Highest | Low | Avoid; cannot validate in time |

**Hackathon scope.** Phases 1 and 2 in full, with benchmark comparison and open release; as finale, the nearest non-recombining final state of one dissociation step, section 16, on ML with one pre-computed DFT check. The barrier of one elementary step, H₂ dissociation or CO oxidation on Pt(111), and the microkinetic loop are later. Pre-compute everything slow; keep a recorded fallback.

**Three-minute demo:** 1, agents report adsorption energies without warning when wrong, as in the sign errors AdsMind found; 2, live Pt(111): Formulate interview, symmetry enumeration, results with a decision trace; 3, live Ni(111): the agent flags ML disagreement and stops for review; 4, the benchmark table: success, error, cost against a baseline; 5, the open release: skill, MCP tools, Zenodo data, one install command.

**Judges' hardest questions.** Difference from AdsMind or Adsorb-Agent: a table of verified features only. Why trust the benchmark: full DFT, settings in PROJECT.md, data released. What the LLM adds over a script: diagnosed failures and escalations, with candour where a script suffices. An unseen system: uncertainty flags and a checkpoint, not a guess.

## Decisions, open questions and next steps

**Decided so far.**

- Wrap CatKit, ACAT, pymatgen, ASE and AiiDA; do not rewrite them.
- Every check that can be code is code; the LLM plans, diagnoses failures, prunes networks and drafts.
- Human checkpoints: settings approval, flagged-case review, network approval, interpretation.
- Literature only before the run, for settings, and after it, for benchmarks on known systems.
- References and DFT settings locked in PROJECT.md before any intermediate is computed.
- The top few configurations per intermediate passed on, not one minimum.
- Hackathon: adsorption core plus one pathway step, its final state only for now; no discovery claim.
- Build on AtomisticSkills; contribute the trust layer as its skills and tools.
- Numerical settings, pseudopotential set, cutoff, k-mesh, smearing and layers, from a verified protocol or a convergence sweep on E_ads, never the LLM's memory; the LLM picks the protocol and explains.
- Four kinds of intuition: procedures into the skill, priors into thresholds, constraints into code, judgement through interview and flagged-case review; corrections into the lessons log, promoted to the skill on recurrence.
- Skills few, human-written, procedural; facts and ranges in code and PROJECT.md.
- The LLM never writes or edits coordinates: code enumerates, places and checks geometry; the LLM reads descriptor cards and acts through named tool calls.

**Open questions.**

- Which hackathon: rubric, build period, pass criterion?
- Which DFT code, compute budget and ML potentials: VASP, Quantum ESPRESSO, or ML only? Which potential for pre-screening, none being best everywhere?
- ML doubt by ensemble disagreement, geometric sanity, or both?
- Does symmetry-complete enumeration find lower minima than OC20-Dense, and how often?
- E_ads convergence target: 10 meV or 25 meV, cheap enough for the hackathon, tight enough for the benchmark?
- How many lessons-log entries until Ni(111) is caught without a human; can the demo show that curve?
- Can an interview agent, as in the tacit-knowledge papers, run the Formulate interview without losing what a human interviewer catches?
- Does an image beside the descriptor card help catch geometry errors or add noise? The geometry test decides.
- Adsorbate class and size? The same molecule in a final geometry, or a new one from two adsorbates, which moves pair enumeration into the core? One elementary step or a short mechanism, and who supplies it?
- Final-state metric: site-graph distance with in-plane tiebreak, or in-plane distance between the two binding atoms alone?
- Does the fragment keeping the binding atom stay at the reactant's site, as CatTSunami assumes, or move?
- Target: the nearest surviving pair, or the lowest-energy pair within one site hop? They differ when adjacent fragments repel.
- First dissociation: \*OH → \*O + \*H on Pt(111), the simplest in OC20NEB's list, with DFT bands to compare?
- Is an OC20NEB subset acceptable ground truth for the path steps, given it fixes the settings to OC20's RPBE and PAW choices, which our lock must then match?
- Is there DFT nudged-elastic-band compute for the propagation experiment, or does it run on ML with OC20NEB labels as reference?
- Should the headline move from "knows when not to trust itself" to "barrier-ready endpoints", every adsorption energy validated as a transition-state endpoint with the endpoint-to-barrier propagation measured? TSAgent and CatDT crowd the plain transition-state claim; the endpoint claim is free. Which of the four claims of section 15 heads the three-minute demo?

**Build plan.** Column 0's answers unblock everything to their right.

![The shortest route to one validated nearest final state runs through eight numbered boxes; the path is a later phase](../figures/22-build-plan.png)

*Figure: build plan · 5 columns, 26 tasks, critical path of 8, schematic*

Reading the figure: columns run from the team's decisions, grey, through code foundation, ML trust and final state to measurements, amber, and release, blue; the board's two question marks and the later path steps are dashed, and each box names what it reuses, green, and needs, grey. The numbered blue path: system and product, settings lock, enumeration, validity gate, potential choice, nearest final state, the \*OH → \*O + \*H final state against the OC20NEB product frame, release. The LLM and human layer at the bottom comes last because it only calls tools.

**Repository layout:** a Claude Code plugin beside AtomisticSkills; docs/agent-build-context.md, section 9, gives the tree and rules.

![One folder per kind, one file per tool, and calls go one way: agents to skills to tools to the library](../figures/24-repository-layout.png)

*Figure: repository layout · tree, reading orders, the one-way rule, schematic*

Reading the figure: the tree is coloured by kind, skills green, agents purple, MCP tools blue, library white, data amber, tests pink, with the rules beneath it: skills under 200 lines naming tools without code, one-page agents, one tool per file wrapping the library module of its name. Top right are the human and agent reading orders; bottom right the one-way rule: agents decide, skills say how, tools are typed entry points, the library holds all logic and tests, runs hold every call and verdict.

**Compute, agents and skills:** the roster stays short because tools do the work; the build context, section 9, gives lanes and roster.

![HPC is needed for DFT and for nothing else; the roster is five roles and six skills at most](../figures/25-compute-and-roster.png)

*Figure: compute lanes and the roster · 3 lanes, 5 roles, 12 skills, schematic*

Reading the figure: left, steps sit in lanes: laptop, grey, for checks, enumeration, mapping and reports; GPU, blue, for ML relaxations, bands and frequencies; HPC, red, for DFT. The dashed red box replaces HPC without a cluster: OC20's settings for the sweep, OC20NEB's DFT bands as labels and ground truth, one DFT check run beforehand. Right, each agent with its decision and status, then our six skills, green, and six reused, grey, above the evidence for short lists.

**Next steps.**

- [ ] Draft SKILL.md for adsorption and transition-state calculations
- [ ] Draft the PROJECT.md template and the Formulate interview questions
- [ ] Implement site and pair enumeration and the validity-check tools
- [ ] Reproduce H on Pt(111) end to end as the first validation
- [ ] Assemble the benchmark subset: OC20-Dense, hard set, controls
- [ ] Build the Ni(111) failure-detection demo
- [ ] Package the tools as an MCP server; plan the Zenodo release
- [x] Check the AtomisticSkills repository: no catalysis skill public; MIT; baseline mat-surface-adsorption on pymatgen's site finder, which does not label fcc and hcp hollows; repository survey
- [ ] Run its mat-surface-adsorption placement as our benchmark baseline
- [ ] Prototype the ML-doubt loop with ml-mlip-benchmark and ml-mace-finetune on Ni(111)
- [ ] Build the convergence tool, sweeping cutoff, k-mesh, smearing and layers on E_ads of H on Pt(111), writing PROJECT.md
- [ ] Write the Formulate interview questions into SKILL.md; test them on one experienced researcher
- [ ] Start the lessons log with the known pitfalls: CO on Pt, Ni and Co magnetism, symmetry trap
- [ ] Redraw figure 12 with the "Converge numerical settings" step; its script is not in the repository, so recreate it under docs/figures/src/
- [ ] Build the descriptor-card tool, structure in, text card and PNG out, and route every other tool's output through it
- [ ] Write model-facing documentation for the geometry tools, place, enumerate, check, after the MatTools finding
- [ ] Add twenty geometry editing tasks to the benchmark; record success with and without tools
- [ ] Propagation experiment: the same ML NEB, CatTSunami style, for one step on Pt(111) from single-placement endpoints and from enumerated, checked endpoints; barrier difference in eV and as a rate factor; one case checked with DFT
- [ ] Read TSAgent and TSBench in full; fill the endpoint-choice and saddle-validation gaps in the table
- [ ] Define the product as a structure with one set of gas-phase references; add A* + B* pair enumeration if the product forms from two adsorbates
- [ ] Write the initial–final connectivity check, same reaction by atom mapping as in NEBscape, and the saddle validation tool, one imaginary mode, path ending at both endpoints
- [ ] Select an OC20NEB subset and the single-placement baseline for the path benchmark
- [ ] Build the nearest-non-recombining final-state tool, enumerating, relaxing, gating and ranking pairs by distance and reporting rejected pairs and E(FS near) − E(FS ∞); run it for *OH → *O + *H on Pt(111) against the OC20NEB band

## Sources

- [AdsorbML and OC20-Dense](https://arxiv.org/pdf/2211.16486)
- [Adsorb-Agent](https://arxiv.org/html/2410.16658v3)
- [AdsMind](https://arxiv.org/html/2606.19152) and an [independent review of it](https://pith.science/paper/2606.19152)
- [DREAMS](https://alphaxiv.org/abs/2507.14267)
- [CatMaster](https://arxiv.org/pdf/2601.13508)
- [Catalyst-Agent](https://arxiv.org/pdf/2603.01311)
- [AutoDFT](https://arxiv.org/html/2605.26179v2)
- [CatKit](https://www.aiche.org/conferences/aiche-annual-meeting/2018/proceeding/paper/699a-catkit-symmetry-methods-automated-generation-catalytic-structures)
- [ACAT](https://pypi.org/project/acat/1.7.0/)
- [AdsMT and GMAE benchmarks](https://zenodo.org/records/12104162)
- [Kempen, Cheula and Andersen: 80 MLIPs benchmarked](https://phys.au.dk/intercat/news-and-events/show/artikel/new-intercat-paper-luuk-kempen-raffaele-cheula-and-mie-andersen)
- [Review of MLIPs for energy materials](https://advanced.onlinelibrary.wiley.com/doi/10.1002/aenm.71046)
- [CatTSunami and OC20NEB](https://arxiv.org/abs/2405.02078)
- [Fine-tuning universal MLIPs for transition-state search](https://arxiv.org/pdf/2603.24482)
- [Get Physics Done](https://github.com/psi-oss/get-physics-done)
- [Outcomes of the 2025 LLM Hackathon for Materials Science and Chemistry](https://arxiv.org/pdf/2605.03205)
- [Cambridge hackathon on multi-agent systems for scientific research](https://science.ai.cam.ac.uk/events/hackathon-multi-agent-systems-for-scientific-research)
- [dkNET–Texera agent hackathon](https://texera.apache.org/blog/2026/05/20/dknet-ai-apache-texera-agent-hackathon/)
- [NAIS AI Hackathon 2026 report](https://biz.heraldcorp.com/article/10890887)
- [AtomisticSkills](https://arxiv.org/abs/2605.24002) and its [code](https://github.com/learningmatter-mit/AtomisticSkills)
- [SSSP paper, 2018](https://arxiv.org/pdf/1806.05609) and [library](https://www.materialscloud.org/discover/sssp)
- [Δ-test, Lejaeghere et al., Science 2016](https://archive.materialscloud.org/record/1874) and [Bosoni et al. 2024](https://archive.materialscloud.org/record/2023.81)
- [AiiDA common workflows, Huber et al., npj Computational Materials 2021](https://www.nature.com/articles/s41524-021-00594-6) and [documentation](https://aiida-common-workflows.readthedocs.io/)
- [VASP wiki: choosing pseudopotentials](https://vasp.at/wiki/Choosing_pseudopotentials) and [energy cutoff and FFT mesh](https://vasp.at/wiki/Energy_cut_off_and_FFT_mesh)
- [OC20 dataset paper, with the DFT settings](https://arxiv.org/pdf/2010.09990)
- [Convergence and ML prediction of k-points and cutoff in high-throughput DFT](https://arxiv.org/pdf/1809.01753)
- Anthropic: [Agent Skills](https://www.anthropic.com/news/skills), [Claude for Life Sciences](https://www.anthropic.com/news/claude-for-life-sciences), [Claude Science workbench](https://www.anthropic.com/news/claude-science-ai-workbench), [AI for Science program](https://support.claude.com/en/articles/11199177-anthropic-s-ai-for-science-program)
- [Scientific Agent Skills, K-Dense](https://github.com/k-dense-ai/scientific-agent-skills) and [K-Bench](https://arxiv.org/pdf/2608.21601)
- [SkillsBench](https://www.emergentmind.com/papers/2602.12670) and [Demystifying Agent Skills](https://arxiv.org/pdf/2608.14036)
- [ether0](https://www.futurehouse.org/news/ether0-a-scientific-reasoning-model-for-chemistry) and its [paper](https://arxiv.org/html/2506.17238v2)
- [ChemCrow](https://arxiv.org/abs/2304.05376), [Coscientist](https://www.cmu.edu/news/stories/archives/2023/december/cmu-designed-artificially-intelligent-coscientist-automates-scientific-discovery), [El Agente](https://arxiv.org/abs/2505.02484)
- [Virtual Lab, Nature 2025](https://biohub.org/news/with-no-need-for-sleep-or-food-ai-built-scientists-get-the-job-done-quickly/), [Google AI co-scientist](https://research.google/blog/accelerating-scientific-breakthroughs-with-an-ai-co-scientist/), [Kosmos](https://arxiv.org/html/2511.02824v2)
- Tacit knowledge and agents: [LLMs for tacit knowledge discovery](https://arxiv.org/pdf/2507.03811), [KUPAS MASTER](https://arxiv.org/abs/2609.37673), [Tacit Fragments](https://www.alphaxiv.org/abs/2609.operationalising-tacit-knowledge-agentic-ai)
- [OpenAI FrontierScience](https://openai.com/index/frontierscience)
- Repositories to wrap or copy, each opened on 21 October 2026: [repository survey](repo-survey.md); agents with chemistry or surface knowledge, by the channel it enters through: [chemistry-agents review](chemistry-agents-review.md)
- Final-state generation and automated kinetics: [Pynta, JCIM 2023, preprint](https://chemrxiv.org/engage/chemrxiv/article-details/647114454f8b1884b755bc5a) and [code](https://github.com/zadorlab/pynta), [El Agente Potente](https://arxiv.org/abs/2609.14840), [Reproducible orchestration of NEB best practices](https://arxiv.org/abs/2603.14737)
- Transition-state agents and benchmarks: [TSAgent](https://arxiv.org/abs/2605.14154), [TSBench](https://arxiv.org/abs/2609.08503), [NEBscape](https://www.nature.com/articles/s41524-026-02298-1), [CatDT](https://urop.hkust.edu.hk/node/40500), [CopyCAT, ICIQ thesis](https://iciq.org/es/?p=72665)
- Geometry: [AtomWorld](https://arxiv.org/html/2510.04704), [LLMConfBench](https://arxiv.org/html/2609.20666), [MiSI-Bench](https://arxiv.org/html/2512.10867v1), [Robocrystallographer](https://www.cambridge.org/core/journals/mrs-communications/article/robocrystallographer-automated-crystal-structure-text-descriptions-and-analysis/3C201F132450877464B2D0B1B8C4ED01), [LLM-Prop](https://www.nature.com/articles/s41524-025-01536-2), [LLM4Mat-Bench](https://arxiv.org/pdf/2411.00177), [MatTools](https://arxiv.org/html/2505.10852v2), [LLaMP](https://arxiv.org/pdf/2401.17244)

From memory, not looked up here: Kozuch and Shaik, "How to conceptualize catalytic cycles? The energetic span model", Accounts of Chemical Research, 2011; Sholl and Steckel, *Density Functional Theory: A Practical Introduction*, Wiley, 2009; Nørskov, Studt, Abild-Pedersen and Bligaard, *Fundamental Concepts in Heterogeneous Catalysis*, Wiley, 2014; Wellendorff et al., "A benchmark database for adsorption bond energies to transition metal surfaces", CE27, Surface Science, 2015.
