# Agentic Workflow for Adsorption Energies and Reaction Pathways


## Purpose and direction

We are building an AI agent that computes adsorption energies on catalyst surfaces reliably, and that knows when not to trust itself. The longer-term aim is to extend the same agent to reaction pathways and kinetics. The near-term target is an Open Science hackathon.

This document records the reasoning behind that direction, so that a colleague or another Claude instance can pick up the work without the original conversation.

**The position in one paragraph.** A generic "agent that computes adsorption energies" already exists several times over (Adsorb-Agent, AdsMind, DREAMS, CatMaster, Catalyst-Agent, AutoDFT). Our contribution is therefore not the workflow itself but its trustworthiness: symmetry-complete site enumeration, explicit validity checks, detection of machine-learning failures (notably on magnetic Ni and Co), designed human checkpoints, a measured failure rate against a baseline, and an open, reusable release.

**How to read it.** Sections 2 to 4 give the science and the basic workflow. Sections 5 and 6 cover prior work and benchmarks. Section 7 explains how human insight enters the agent. Sections 8 and 9 extend the workflow to reaction pathways. Sections 10 and 11 give strategy, decisions and open questions.

**Who owns each step.** Each step has one owner: a deterministic tool (code), an LLM, a human, or a literature or benchmark input; knowledge files sit beside the flow. The diagram in section 9 carries its own key.

## Scientific background

The adsorption energy is the quantity everything else is built on. It is computed with density functional theory (DFT) on a periodic slab model of the surface:

$$
E_{\mathrm{ads}} = E(\mathrm{slab}+A) - E(\mathrm{slab}) - E(A)
$$

Here E(slab + A) is the energy of the relaxed slab with adsorbate A, E(slab) that of the clean relaxed slab, and E(A) that of a stated gas-phase reference (for an H atom, usually half of E(H₂)). A negative value means binding is favourable. Changing the reference shifts every value but not the ranking of sites.

![adsorption energy as an energy-level drop · reference choice](figures/01-adsorption-energy-levels.png)

adsorption energy as an energy-level drop · reference choice

Reading the figure: on the left, the upper level is the clean slab with A far away in the gas; the lower level is A bound to the slab. The drop between them is E_ads, negative when binding releases energy. On the right, the same three sites (top, bridge, hollow) are plotted with two different gas references: every level moves by the same amount, so the gaps between sites and their ranking do not change.

For thermodynamics we correct to a free energy:

$$
\Delta G = \Delta E + \Delta E_{\mathrm{ZPE}} - T\Delta S
$$

where ZPE is the zero-point energy from vibrational frequencies, T the temperature and S the entropy.

![from DFT energy to free energy · schematic, not to scale](figures/02-free-energy-corrections.png)

from DFT energy to free energy · schematic, not to scale

Reading the figure: start from the DFT adsorption energy ΔE (a drop below the gas reference). The zero-point correction usually raises it slightly. Because a gas molecule loses most of its translational and rotational entropy when it adsorbs, ΔS is negative and −TΔS raises the energy further. The result, ΔG, is less negative than ΔE, and the gap grows with temperature. Bar heights are schematic.

**What "adsorption curves" can mean.** Four different objects share the name:

- Binding curve: energy against height z over one site; its minimum gives the equilibrium height and E_ads.

- Potential energy surface: energy over lateral positions; the hollow-to-bridge difference approximates the diffusion barrier.

- Coverage curve: E_ads against coverage θ, showing lateral repulsion.

- Isotherm: coverage against pressure, e.g. Langmuir θ = KP / (1 + KP), built on top of the DFT energies.

![four kinds of adsorption curve · schematic](figures/03-four-adsorption-curves.png)

four kinds of adsorption curve · schematic

Reading the figure: (1) energy against height over one site, whose minimum gives z₀ and E_ads; (2) energy along a lateral path hollow–bridge–hollow, whose bump is the diffusion barrier; (3) E_ads against coverage, rising towards zero as neighbouring adsorbates repel; (4) the Langmuir isotherm, coverage against pressure, saturating at one monolayer. Curves 1 to 3 come directly from DFT; curve 4 is built from DFT free energies through the equilibrium constant K.

**Where symmetry and group theory enter.**

- Site enumeration: the slab has a two-dimensional layer group, and inequivalent sites are its inequivalent high-symmetry Wyckoff positions. On fcc(111) these are top (C3v), bridge (C2v), fcc hollow (C3v) and hcp hollow (C3v); on fcc(100), top, bridge and four-fold hollow.

- Orientation enumeration: only orientations inequivalent under the site's stabiliser (site-symmetry) group need testing.

- Configuration counting at higher coverage uses Burnside's lemma, below, where N is the number of distinct arrangements, G the symmetry group of the supercell and \|X^g\| the number of arrangements left unchanged by operation g.

- Spectroscopy: by the surface selection rule, only modes of the totally symmetric representation of the site group are IR-active on a metal, which helps identify the site experimentally.

![inequivalent adsorption sites · fcc(111) and fcc(100)](figures/04-adsorption-sites-fcc111-fcc100.png)

inequivalent adsorption sites · fcc(111) and fcc(100)

Reading the figure: grey discs are surface metal atoms seen from above; coloured dots mark the only sites the agent needs to test, each labelled with its site-symmetry group and coordination number. The fcc and hcp hollows look alike from above and differ only in whether a second-layer atom lies beneath (hcp) or not (fcc). Every other point on the surface is equivalent by symmetry to one of these.

![orientation enumeration on a C3v top site](figures/05-orientation-enumeration.png)

orientation enumeration on a C3v top site

Reading the figure: a flat-lying diatomic sits on a top site, whose surroundings have threefold (C3v) symmetry. The three orientations on the left are carried into one another by a 120° rotation, so they have identical energies and the agent computes only one. Rotating by 30° points the molecule at a gap between neighbours instead of at a neighbour; no symmetry operation maps this onto the first case, so it is a separate calculation.

$$
N = \frac{1}{|G|} \sum_{g \in G} |X^{g}|
$$

![Burnside counting · two adsorbates on a square](figures/06-burnside-counting.png)

Burnside counting · two adsorbates on a square

Reading the figure: two identical adsorbates on the four corners of a square cell can be placed in six ways. The square's symmetry group C4v has eight operations; counting how many of the six arrangements each operation leaves unchanged gives 16, and 16 / 8 = 2. Indeed the six collapse into two classes, adjacent and diagonal, so the agent computes two configurations, not six. The same count, done by code, scales to large supercells where enumerating by eye is impossible.

![surface selection rule · image dipoles](figures/07-surface-selection-rule.png)

surface selection rule · image dipoles

Reading the figure: the conduction electrons of a metal respond to a nearby dipole as if a mirror-image dipole sat inside the metal. A dipole perpendicular to the surface has an image pointing the same way, so the two add and the vibration absorbs infrared light. A dipole parallel to the surface has an image pointing the opposite way, so they cancel. Only vibrations of the totally symmetric representation (A₁) of the site group carry a perpendicular dipole, which is why IR spectra help identify the adsorption site.

**A trap that matters for automation.** Forces preserve the symmetry of the starting structure. An adsorbate placed exactly on a high-symmetry site can stay there even when a tilted, lower-symmetry geometry is lower in energy. The agent must apply a small random displacement before relaxing and confirm minima with a frequency calculation (no imaginary modes).

![binding curve and the symmetry trap · schematic, not to scale](figures/08-binding-curve-symmetry-trap.png)

binding curve and the symmetry trap · schematic, not to scale

Reading the figure: on the left, energy falls as the adsorbate approaches the site, reaches a minimum at height z₀, and rises steeply when it is pushed closer; the depth of the well below the gas-phase limit is E_ads. On the right, energy is plotted against a tilt or lateral offset. The symmetric position (θ = 0) is a local maximum where symmetry makes the force exactly zero, so an unperturbed relaxation stays there; a frequency calculation reveals it through an imaginary mode. A small displacement lets the structure roll into the lower, tilted minimum. Both curves are schematic.

## The adsorption workflow and where to automate

Automate the deterministic middle; keep humans where a wrong choice silently corrupts every later number. The table lists the steps in order, with who owns each.

| Step                             | Owner | What it does                                                    | Tools                             |
|----------------------------------|-------|-----------------------------------------------------------------|-----------------------------------|
| Choose system and settings       | Human | Metal, facet, adsorbate, functional, references                 | Literature, PROJECT.md            |
| Bulk relaxation                  | Tool  | Lattice constant                                                | ASE, VASP or Quantum ESPRESSO     |
| Slab construction                | Tool  | Facet, layers, vacuum, fixed bottom layers                      | ASE, pymatgen                     |
| Site and orientation enumeration | Tool  | All symmetry-inequivalent sites and orientations                | spglib, pymatgen, CatKit, ACAT    |
| ML pre-screening                 | Tool  | Relax all candidates cheaply, keep the top few                  | Universal ML potentials, AdsorbML |
| DFT relaxation                   | Tool  | Accurate energies for the best candidates                       | VASP or QE via AiiDA or atomate2  |
| Diagnose failed jobs             | LLM   | Read errors, adjust, resubmit                                   | Agent                             |
| Validity checks                  | Tool  | Desorbed, migrated, dissociated, reconstructed, imaginary modes | Custom scripts                    |
| Review flagged cases             | Human | Only cases that failed checks                                   | —                                 |
| Energies and curves              | Tool  | E_ads, ΔG, E(z), E(θ)                                           | Custom scripts                    |
| Benchmark comparison             | Tool  | Error against known values                                      | OC20-Dense, CE27                  |
| Interpret results                | Human | Mechanism, next targets                                         | —                                 |

The largest gains from automation are site enumeration (dozens of inequivalent configurations instead of three or four guesses), ML pre-screening (roughly an order of magnitude less DFT), job handling, and validity checks.

A sensible build order is: enumeration plus validity checks first (no supercomputer time needed); then DFT job management on a known system such as H on Pt(111), reproducing a literature value; then ML pre-screening, checked against DFT before relying on it.

## Where the literature is needed

The calculation itself needs nothing from the literature: every term in E_ads is our own DFT energy. The literature supplies confidence that the setup behind those energies is sound, and it enters at two points only: before the run, to fix settings, and after it, to check results on known systems.

**Essential.**

- Before the first calculation on a system: choice of functional (PBE tends to overbind CO; RPBE corrects some of this; dispersion matters for large or flat-lying molecules), reference states and gas-phase corrections (O₂, CO₂ and N₂ carry known GGA errors).

- Systems with known DFT problems: CO on transition metals (the "CO/Pt(111) puzzle", where GGA predicts the hollow site but experiment shows the top site), open-shell molecules, magnetic surfaces, oxides needing a Hubbard U.

- Any comparison with, or publication against, other work: settings must match.

**Optional.** Screening many similar systems with a validated setup; relative trends, which are less sensitive to the functional than absolute values.

**Adds nothing.** Genuinely new systems with no prior data; validate the method on a similar known system instead.

**In practice** this is a targeted lookup of minutes, not a formal review: one or two published E_ads values with their functional, the preferred site (computed and, if possible, measured), and any reported DFT failure. The agent may gather these, but a human must verify them, because language models can misquote values or invent citations.

A separate, proper literature review (20 to 40 papers) is needed for the project itself, to show what the agent adds beyond existing work. That is section 5.

## Prior work and its gaps

The full chain from structure generation through DFT to E_ads has already been automated, in two generations. A re-implementation on simple metals would add little; the open problems are reliability and scope.

| Work                                                                                                                                                          | Type      | What it does                                                 | Documented limitation                      |
|---------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------|--------------------------------------------------------------|--------------------------------------------|
| [CatKit](https://www.aiche.org/conferences/aiche-annual-meeting/2018/proceeding/paper/699a-catkit-symmetry-methods-automated-generation-catalytic-structures) | Toolkit   | Symmetry-based surface and site generation                   | —                                          |
| [ACAT](https://pypi.org/project/acat/1.7.0/)                                                                                                                  | Toolkit   | Site and coverage identification for slabs and nanoparticles | Metals and alloys only; not for oxides     |
| [AdsorbML](https://arxiv.org/pdf/2211.16486)                                                                                                                  | ML + DFT  | Graph neural network screening with DFT check                | Bounded by ML accuracy                     |
| [Adsorb- Agent](https://arxiv.org/html/2410.16658v3)                                                                                                          | LLM agent | LLM proposes configurations, then relaxes them               | Open loop; sign errors found later         |
| [AdsMind](https://arxiv.org/html/2606.19152)                                                                                                                  | LLM agent | Closed-loop, physics-grounded configuration search           | DFT validation on six systems; MAE 1.55 eV |
| [DREAMS](https://alphaxiv.org/abs/2507.14267)                                                                                                                 | LLM agent | Hierarchical multi-agent DFT on Quantum ESPRESSO and AutoCat | —                                          |
| [CatMaster](https://arxiv.org/pdf/2601.13508)                                                                                                                 | LLM agent | Surrogate exploration with targeted DFT validation           | —                                          |
| [Catalyst-Agent](https://arxiv.org/pdf/2603.01311)                                                                                                            | LLM agent | MCP agent around FAIRchem AdsorbML                           | Success rate 23–34%; DFT slow              |
| [AutoDFT](https://arxiv.org/html/2605.26179v2)                                                                                                                | LLM agent | Closed-loop DFT with monitoring and failure recovery         | Task completion, not chemistry accuracy    |

AtomisticSkills (2026) is not in this table because it is infrastructure rather than a competitor: a general skill library we can build on (see "Building on AtomisticSkills").

**Gaps we target.**

- Thin DFT validation: errors of order 1.5 eV, against a need for about 50 meV to preserve activity trends.

- Agents versus plain enumeration: an independent review found a case where AdsMind's closed loop converged above the minimum found by exhaustive enumeration. Whether agents beat symmetry-based brute force is unsettled.

- Dependence on ML potentials, which fail badly on magnetic Co and Ni.

- Narrow chemistry: mostly metals and alloys; oxides, magnetism, high coverage and electrochemical interfaces are largely untouched.

- Run-to-run variability of hosted LLM workflows.

## Benchmarks and the gap

Several benchmarks exist, but each tests one part of the pipeline; none tests an agent end to end against symmetry-exhaustive search with full DFT verification on hard chemistry.

| Benchmark                                                                                                                                               | Tests                            | Size or scope                                                             | Note                                                                    |
|---------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------|---------------------------------------------------------------------------|-------------------------------------------------------------------------|
| [OC20-Dense](https://arxiv.org/pdf/2211.16486)                                                                                                          | Global-minimum search            | About 1,000 combinations per split; 74 adsorbates; 80,000+ configurations | Configurations sampled heuristically and randomly, not by full symmetry |
| [OCD-GMAE, Alloy-GMAE, FG-GMAE](https://zenodo.org/records/12104162)                                                                                    | Global-minimum energy prediction | Derived from OC20-Dense, Catalysis-Hub and a functional-groups set        | Cleaned subsets                                                         |
| AA20, OCD-GMAE62                                                                                                                                        | Agent configuration search       | Small sets used by Adsorb-Agent and AdsMind                               | —                                                                       |
| OC20                                                                                                                                                    | ML energies                      | One configuration per combination                                         | Not suitable for global minima                                          |
| OC22                                                                                                                                                    | ML energies on oxides            | Oxide surfaces                                                            | —                                                                       |
| CatBench                                                                                                                                                | ML potentials on adsorption      | 13 MLIPs, 47,000+ reactions; best about 0.2 eV                            | —                                                                       |
| [Kempen, Cheula and Andersen](https://phys.au.dk/intercat/news-and-events/show/artikel/new-intercat-paper-luuk-kempen-raffaele-cheula-and-mie-andersen) | Foundational MLIPs               | 80 models; adsorption, barriers, vibrations; metals and oxides            | Many fail on magnetic Co and Ni; no single best model                   |
| CE27 (Wellendorff et al., 2015)                                                                                                                         | DFT against experiment           | Experimental chemisorption energies on transition metals                  | For choosing the functional                                             |
| [OC20NEB](https://arxiv.org/abs/2405.02078)                                                                                                             | ML transition states             | 932 DFT NEB calculations                                                  | For the pathway extension                                               |
| VASPBench                                                                                                                                               | Agent task completion            | 34 DFT tasks                                                              | Runs succeed; chemistry not judged                                      |

**Our benchmark plan.**

1.  A subset of OC20-Dense, for comparability with published agents.

2.  Our own symmetry-complete enumeration on 30 to 50 of those systems, to test whether OC20-Dense missed lower minima.

3.  A small hard set (Ni, Co, one oxide such as TiO₂(110) or CeO₂(111)) where current tools are known to fail.

4.  Controls that should be easy: H and O on Pt(111) and Cu(111).

Reported metrics: success in finding the DFT minimum, error against DFT, fraction of own failures flagged, and compute cost, each against a baseline (a plain AdsorbML-style run).

## How human insight enters the agent

A skill is one of five channels, not the only one. Each kind of insight belongs in the channel that enforces it most reliably.

| Channel                     | Holds                          | Acts                             | Example                                                           |
|-----------------------------|--------------------------------|----------------------------------|-------------------------------------------------------------------|
| Skill (SKILL.md)            | General know-how, written once | Loaded whenever the task matches | Always break symmetry before relaxing; flag CO on Pt-group metals |
| Project memory (PROJECT.md) | Choices for this system        | Read at every step               | RPBE-D3, four-layer slab, ½E(H₂) reference                        |
| Checkpoints                 | Live judgement                 | Agent pauses for approval        | Approve settings; review flagged cases                            |
| Tools (code)                | Insight turned into rules      | Every run, without fail          | Reject an adsorbate relaxed more than 3 Å above the surface       |
| Lessons log                 | Corrections from review        | Fed back into the skill          | Ni(111): set initial magnetic moments, or SCF fails               |

**Rule of thumb.** If an insight can be written as a test, make it a tool; if it is a procedure, put it in the skill; if it is a choice for one system, put it in project memory; if it needs judgement each time, make it a checkpoint. Insight in code is the most reliable, because an LLM can misread a prompt but cannot skip a check it does not control.

**Lessons from [Get Physics Done](https://github.com/psi-oss/get-physics-done) (GPD).** GPD installs physics-research commands into agent runtimes such as Claude Code, Codex and Gemini CLI. Its ways of bringing in the human:

- A Formulate stage that asks targeted questions on scope, assumptions, notation and verification targets, and freezes the answers into files (PROJECT.md, REQUIREMENTS.md, ROADMAP.md, STATE.md).

- Locked conventions across a project, so notation and assumptions stay consistent.

- A discuss step before each plan and execute phase.

- Adjustable autonomy (Supervised, Balanced), treating each agent turn like a graduate student's work.

- A Verify stage checking dimensions, limiting cases, symmetry and conservation laws.

- Commands to defer a tangent or branch into an alternative hypothesis.

We copy the pattern (Formulate interview, locked settings, discuss-then-execute, autonomy setting) and add what GPD lacks for our domain: an adsorption and transition-state skill with DFT pitfalls, and deterministic validity-check tools exposed as an MCP server.

## Building on AtomisticSkills

[AtomisticSkills](https://arxiv.org/abs/2605.24002) (MIT, May 2026) should become our substrate: instead of a standalone agent, we ship our adsorption and pathway work as skills and tools inside it. This sharpens our contribution to a "trust layer" for surface chemistry, and shrinks what we must build ourselves.

**What it is.** An open-source "outer harness" for general-purpose coding agents such as Claude Code, Gemini CLI and Cursor. It decomposes research into four layers:

- Workflows: whole campaigns, planned by the agent and approved by a human before execution.

- Skills: over 100 human-curated, mid-level procedures, each a SKILL.md with scripts and examples, validated against literature values where available.

- Tools: more than 50 type-checked MCP tools on more than 10 servers, including FairChem (UMA), MACE, MatGL and Atomate2 for remote DFT.

- Rules: research standards the agent must follow, such as a mandatory preliminary literature review and an MLIP registry check.

Every hyperparameter a skill uses is logged to configuration files beside its outputs. The authors describe the current mode as co-pilot, with human supervision still essential for multi-day campaigns. Code: [github.com/learningmatter-mit/AtomisticSkills](https://github.com/learningmatter-mit/AtomisticSkills).

**Why it matters to us.** Its Fe-oxide OER case study already chains surface cleavage, adsorbate placement of O\*, OH\* and OOH\*, MLIP relaxation, DFT and a free-energy and volcano analysis. That is close to our phases 2 and 4. What it does not offer, as far as the paper describes, is our trust layer: symmetry-complete site and pair enumeration, explicit validity checks, ML-doubt detection with escalation, and a measured failure rate. The authors also name evaluation of autonomous atomistic research as an open challenge, which our benchmark addresses.

![Our trust layer plugs into AtomisticSkills; most plumbing is reused](figures/09-atomisticskills-layers.png)

*Figure: our skills on AtomisticSkills · 4 layers*

Reading the figure: the coding agent sits on top and runs our campaign (workflow layer). Below it, skills are split into those reused from AtomisticSkills (outlined) and the four we add as the trust layer (highlighted): symmetry-complete site enumeration, ML-doubt escalation, transition-state search, and a benchmark harness. The tool layer reuses the FairChem, MACE, MatGL and Atomate2 MCP servers and adds one new validity-check server. Rules on the right apply to every layer; the lower three are ours. Skill names are shortened; full names are in the table below.

**Step-by-step mapping.**

| Our step                               | AtomisticSkills component                        | Plan                                                                           |
|----------------------------------------|--------------------------------------------------|--------------------------------------------------------------------------------|
| Literature check                       | Rule: mandatory literature review                | Reuse; add our DFT-pitfall list                                                |
| Approve settings and network           | Plan reviewed before execution                   | Reuse; add PROJECT.md lock                                                     |
| Build bulk and slab                    | mat-db-mp, mat-htvs-cutcleansurface              | Reuse, if public (see below)                                                   |
| Enumerate sites and pairs              | mat-htvs-addadsorbate (placement)                | New skill: symmetry-complete enumeration; their placement becomes our baseline |
| ML pre-screen                          | mat-htvs-mlip-relax; FairChem, MACE MCP servers  | Reuse                                                                          |
| Flag ML doubt and escalate             | ml-mlip-benchmark, ml-mace-finetune              | New skill that triggers these on doubt                                         |
| DFT relaxation                         | mat-htvs-vasp; Atomate2 MCP                      | Reuse                                                                          |
| Validity checks                        | —                                                | New MCP tool server                                                            |
| Transition-state search and validation | — (not described)                                | New skills                                                                     |
| Free-energy diagram                    | mat-htvs-catalysis-activity-analysis             | Reuse for electrochemistry; extend for thermal catalysis                       |
| Microkinetic model                     | Thermodynamics and kinetics skills (unspecified) | Check coverage                                                                 |
| Benchmark comparison                   | —                                                | New; our main contribution                                                     |
| Open release                           | Hyperparameter logging                           | Reuse; add provenance and Zenodo export                                        |

**A new loop from ML doubt to fine-tuning.** When the agent doubts its ML potential (as on Ni or Co), it can sample a few configurations, label them with DFT, run the ml-mlip-benchmark skill to measure the error, and, if needed, fine-tune MACE with ml-mace-finetune before continuing. This turns "stop and ask" into "stop, measure, repair, then ask only if repair fails".

**To verify before relying on it.** The catalysis skills run on htvs, which the paper describes as an in-house pipeline; whether those skills work outside MIT is not stated. Check the repository for which skills are public, their licence, and how well the adsorbate-placement skill handles symmetry.

## Extension to reaction pathways

The adsorption agent becomes a subroutine inside a larger loop: adsorption energies → reaction energies → transition states and barriers → a microkinetic model of rates and selectivity.

![Each level reuses everything below it](figures/10-adsorption-to-kinetics.png)

*Figure: from adsorption to kinetics · 4 levels*

Reading the figure: the highlighted box is what the current agent already computes; each box to its right is built from the outputs of the boxes to its left, so errors made early propagate to every later level.

**Governing relations.** ΔE = E(FS) − E(IS) and E_a = E(TS) − E(IS), where IS and FS are the relaxed initial and final states and TS the transition state (a saddle point). The rate constant from harmonic transition-state theory is:

$$
k = \frac{k_{\mathrm{B}} T}{h} \exp\left(-\frac{\Delta G^{\ddagger}}{k_{\mathrm{B}} T}\right)
$$

where k_B is Boltzmann's constant, h Planck's constant and ΔG‡ the free-energy barrier. A cheap pre-screen is the Brønsted–Evans–Polanyi relation, E_a ≈ αΔE + β, fitted per reaction family.

![A barrier is measured from the relaxed initial state up to the saddle point](figures/11-reaction-energy-profile.png)

*Figure: reaction energy profile · schematic, not to scale*

Reading the figure: the curve traces energy along the reaction coordinate from the co-adsorbed initial state (IS, A\* + B\*) over the transition state (TS) to the final state (FS, AB\*). The barrier E_a is the rise from IS to TS; the reaction energy ΔE is the drop from IS to FS. The TS is a saddle point: a minimum in every direction but one, hence exactly one imaginary vibrational mode, and an IRC from it must lead back to IS and FS. The energies shown are schematic.

**Why accuracy matters more here.** At 500 K, k_B T ≈ 0.043 eV, so a 0.1 eV error changes k by exp(2.3) ≈ 10. An error harmless for ranking sites is a tenfold error in rate. Hence the loop that sends rate-controlling steps back to DFT.

**What changes for the adsorption stage.**

- One consistent set of gas-phase references (e.g. H₂, H₂O, CO or CO₂) for every intermediate.

- Identical DFT settings for every intermediate and transition state.

- Co-adsorbed endpoints: A\* + B\* in one cell, so pair enumeration (where Burnside counting earns its keep) and lateral interactions.

- Return the top few configurations per intermediate, since the global minimum may not lie on the lowest-barrier path.

- Mirror-equivalent paths need computing once; a symmetric starting band in NEB can hide a lower, symmetry-broken path.

**Prior work.** [CatTSunami](https://arxiv.org/abs/2405.02078) found transition states within 0.1 eV of DFT 91% of the time with a 28-fold speed-up, and reproduced a 61-intermediate, 174-reaction network in 12 GPU days instead of an estimated 52 GPU years. A [2026 study](https://arxiv.org/pdf/2603.24482) reports transition states with fewer than 10 DFT single points on average, but notes the method suits surface elementary reactions, not reconstructions or collective lattice distortions. As far as we found, no LLM agent yet runs the whole loop with network pruning, validation, human checkpoints and kinetics-driven refinement.

**Is automation worth it?** Yes for the middle (endpoint mapping, TS search, validation, free-energy corrections, microkinetics): repetitive, numerous and error-prone. No for the ends: a human approves the network and interprets the mechanism, because a missing step cannot be recovered downstream.

## The complete workflow

The whole agent runs in four phases; phase 2 is the original adsorption agent, reused for every intermediate in phase 3.

![People set and judge; tools compute; the LLM plans and repairs](figures/12-complete-workflow.png)

*Figure: complete agent workflow · 4 phases, 20 steps*

The dashed loop on the left sends rate-controlling steps from the microkinetic model back to DFT refinement. Corrections made in either review step go to the lessons log, and recurring lessons are folded into the skill.

- **Phase 1** fixes everything before any calculation: literature check, reaction network, and one locked set of references and settings.

- **Phase 2** adds two upgrades for pathways: pair (co-adsorption) enumeration, and passing on the top few configurations. "Flag ML doubt" is the Ni/Co self-distrust feature.

- **Phase 3** repeats the phase 2 pattern for transition states: ML search, DFT refinement, failure diagnosis, validation, review.

- **Phase 4** adds kinetics, benchmark comparison and the open release.

The single box whose silent failure corrupts everything downstream is "Approve settings and network": a wrong reference or a missing step cannot be repaired by later accuracy.

## Positioning and hackathon strategy

Do not pivot; sharpen. Keep the adsorption domain and change the claim from "an agent that computes adsorption energies" to "an agent that knows when not to trust itself".

**What other teams will likely build.** At the 2025 LLM Hackathon for Materials Science and Chemistry, over 40 of 88 projects used tool-calling agents. So a DFT-calling agent is the median entry. Crowded ground: literature and RAG agents, end-to-end "AI scientist" pipelines, DFT and MD wrappers, large ML screening runs, data-analysis assistants, and demos without measured results.

**What tends to win.** Critique and reliability (the 2026 NAIS top prize went to an agent that spots research flaws before work begins); human-in-the-loop design (a judged criterion at the dkNET–Texera hackathon); systematic validation, traceability and explainability (Cambridge multi-agent hackathon rubric).

| Option                                      | Novelty      | Feasible in hackathon time | Verdict                        |
|---------------------------------------------|--------------|----------------------------|--------------------------------|
| Generic adsorption agent                    | Low (exists) | High                       | Avoid as the main claim        |
| Open skill + MCP tool pack                  | Medium–high  | High                       | Do                             |
| Reliability benchmark against a baseline    | High         | High                       | Do                             |
| Agent that detects ML failure and escalates | High         | Medium                     | Do; the demo centrepiece       |
| New catalyst discovery                      | Highest      | Low                        | Avoid; cannot validate in time |

**Scope for the hackathon.** Build phases 1 and 2 fully, with benchmark comparison and open release. Add one elementary step (H₂ dissociation or CO oxidation on Pt(111)) as a finale, on ML with one pre-computed DFT check. Leave the microkinetic loop for later. Pre-compute everything slow; keep a recorded fallback.

**Three-minute demo.**

1.  The problem: agents report adsorption energies without warning when wrong (AdsMind's finding of sign errors in an earlier agent).

2.  Live run on Pt(111): Formulate interview, symmetry enumeration, results with a full decision trace.

3.  Live run on Ni(111): the agent flags ML disagreement and stops for review instead of guessing.

4.  The benchmark table: success rate, error, cost, against a baseline.

5.  What is open: skill, MCP tools, data on Zenodo; one install command.

**Judges' hardest questions.** How is this different from AdsMind or Adsorb-Agent (a comparison table of verified features only)? Why trust the benchmark (full DFT, settings in PROJECT.md, data released)? Does the LLM add anything over a script (show diagnosed failures and escalations; be candid where a script suffices)? What happens on an unseen system (uncertainty flags and a checkpoint, not a guess)?

## Decisions, open questions and next steps

**Decided so far.**

- Wrap existing toolkits (CatKit, ACAT, pymatgen, ASE, AiiDA) rather than rewrite them.

- Put every check that can be code into code; keep the LLM for planning, failure diagnosis, network pruning and drafting.

- Human checkpoints at settings approval, flagged-case review, network approval and interpretation.

- Literature enters only before the run (settings) and after it (benchmarks on known systems).

- Lock references and DFT settings in PROJECT.md before any intermediate is computed.

- Pass on the top few configurations per intermediate, not one minimum.

- For the hackathon: adsorption core plus one pathway step; no discovery claim.

<!-- -->

- Build on AtomisticSkills rather than a standalone agent; contribute the trust layer as its skills and tools.

**Open questions.**

- Which hackathon, with what rubric and build period?

- Which DFT code and compute are available (VASP, Quantum ESPRESSO, ML potentials only)?

- Which ML potential to use for pre-screening, given that none is best everywhere?

- How should the agent detect ML doubt: ensemble disagreement, geometric sanity, or both?

- Does symmetry-complete enumeration find lower minima than OC20-Dense, and how often?

**Next steps.**

- [ ] Draft SKILL.md for adsorption and transition-state calculations

- [ ] Draft the PROJECT.md template and the Formulate interview questions

- [ ] Implement symmetry enumeration (sites and pairs) and the validity-check tools

- [ ] Reproduce H on Pt(111) end to end as the first validation

- [ ] Assemble the benchmark subset (OC20-Dense, hard set, controls)

- [ ] Build the Ni(111) failure-detection demo

- [ ] Package tools as an MCP server and plan the Zenodo release

<!-- -->

- [ ] Check the AtomisticSkills repository: which catalysis skills are public, licence, how addadsorbate handles symmetry

- [ ] Run its addadsorbate placement as the baseline in our benchmark

- [ ] Prototype the ML-doubt loop with ml-mlip-benchmark and ml-mace-finetune on Ni(111)

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

<!-- -->

- [AtomisticSkills: harnessing agent skills for atomistic research](https://arxiv.org/abs/2605.24002) and its [code](https://github.com/learningmatter-mit/AtomisticSkills)

From memory, not looked up here: Wellendorff et al., "A benchmark database for adsorption bond energies to transition metal surfaces" (CE27), Surface Science, 2015.
