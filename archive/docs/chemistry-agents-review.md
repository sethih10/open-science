# Chemistry and surface knowledge in LLM agents: a review against the final-state problem

Every paper and repository linked here was opened on 21 October 2026. The review is written against the problem of `agent-context.md` section 23: given AB* and the product A* + B*, find the final state with B* as close to A* as possible while the two stay fully dissociated, validated in code. Style follows `agent-writing-style.md`. Anything not confirmed in the text opened is marked unverified.

## Conclusion

The measured gains in chemistry and surface agents come from knowledge placed in code: hand-written tools, typed execution graphs and deterministic gates, while prompts and skills steer the procedure and fine-tuning has not yet reached surface geometry. No agent we found states our objective, B* nearest to A* with no A–B bond after relaxation; the agents that reach reaction endpoints either gate them on overlaps and atom counts only, as CatDT does, or take them as given, as TSAgent and El Agente Potente do. Build the final state as a typed tool chain the LLM calls by name, store raw run cases rather than distilled lessons, and spend the LLM on routing, diagnosis and the settings interview.

## Systems by channel

The surface agents sit in the tools, skills and descriptor groups, and only CatDT builds its own reaction endpoints. Columns: Knowledge is what the agent knows. Channel is how it enters, primary first. Result is the task and the measured number. Failure is what the authors report. Code is the licence and repository. Final state is what the entry means for us. Groups follow the primary channel; human in the loop appears as a secondary channel in the rows that use it.

### Fine-tuning or RL

| System | Knowledge | Channel | Task and result | Documented failure | Licence and code | For our final state |
|---|---|---|---|---|---|---|
| [ether0](https://arxiv.org/html/2506.17238v2) | Organic chemistry on SMILES: naming, reactions, solubility, ADMET | SFT on 14,021 reasoning traces, then RL with verifiable rewards on a 24B Mistral base | 640,730 problems in 375 tasks; beats frontier models on open-answer tasks; multiple choice 50.1 % vs o1 52.2 %; reaction prediction 70 % vs Molecular Transformer 64.1 % | No inorganic or crystal chemistry; lost multi-turn chat; no tool calls; can exploit reward features | Paper CC BY 4.0; [code Apache-2.0](https://github.com/Future-House/ether0); weights released | Training works only where a verifier exists; none exists for surface geometry; out of scope |
| [ChemDFM-R](https://arxiv.org/html/2507.21990v3) | Functional-group-level organic chemistry | Domain pretraining on 101B tokens, distillation, RL on Qwen2.5-14B | ChemEval 73.8 overall; SciKnowEval 69.1 overall | Weak on numerical prediction: yields, property calculation | Paper CC BY-NC-SA 4.0; weights on Hugging Face, licence unverified | Numbers stay in tools, not in weights |

### Retrieval, including memory of past runs

| System | Knowledge | Channel | Task and result | Documented failure | Licence and code | For our final state |
|---|---|---|---|---|---|---|
| [Coscientist](https://pmc.ncbi.nlm.nih.gov/articles/PMC10733136/) | Synthesis procedures, robot and cloud-lab APIs | Web search, embedding search over API documentation, code execution | GPT-4 with search scored 5 of 5 on four syntheses, 3 of 5 on ibuprofen; Suzuki and Sonogashira run on robots | Models without search hallucinated syntheses; wrong method names; air bubble in HPLC | [Simplified code](https://github.com/gomesgroup/coscientist), no licence asserted; full code withheld | Documentation retrieval fixes API use, not chemical judgement |
| [ChemAgents](https://www.cambridge.org/engage/chemrxiv/article-details/66a8c11bc9c6a5c07a7a59c0) | Literature, protocols, models, robot lab | Literature database and protocol library behind role agents; on-board Llama-3-70B | Six experimental tasks from synthesis to materials optimisation; no number in the text opened | None in the text opened | Preprint CC BY-NC-ND 4.0; no code found; JACS 2025 version unverified | Roles split by resource; no measured effect to copy |
| [LLaMP](https://arxiv.org/html/2401.17244v3) | Materials Project properties | Hierarchical ReAct agents retrieve from Materials Project; MLIP runs | Formation energy MAE 0.009 vs GPT-4 1.680 eV; magnetic ordering accuracy 0.98 vs 0.48 on 800 materials; bulk modulus MAE 14.6 vs 41.2 GPa | Misreads schema descriptions; inherits GGA band-gap error | Paper CC BY 4.0; [code](https://github.com/chiang-yuan/llamp), custom licence | Numbers come from a database or a tool, never from the model |
| [HoneyComb](https://arxiv.org/html/2409.00135) | Materials-science text and formulas | MatSciKB of 38,469 entries plus ToolHub of induced tools | GPT-4 MaScQA 58.46 → 79.07 %; knowledge base alone 61.38 %, tools alone 73.23 % | No failure analysis found | No code link found | Tools carried most of the gain, retrieval little |
| [dZiner](https://arxiv.org/html/2410.03963) | Design rules for surfactants, ligands, MOF linkers | RAG on papers for design rules; surrogate models; optional human | Objective met on 92–98 % of 100 molecules per task with rules vs 39–92 % without; MOF CO2 uptake 0.885 → 1.978 mol/kg | Invalid SMILES; confuses ortho, meta, para in human mode | Paper CC BY-SA 4.0; [code Apache-2.0](https://github.com/mehradans92/dZiner) | Retrieved rules help an LLM that edits strings; ours edits nothing |
| [MatAgent](https://arxiv.org/html/2504.00741v1) | Inorganic compositions | Knowledge base of 10,000 composition pairs, memory, periodic table; DiffCSP and a GNN as tools | Validity, uniqueness, novelty 0.60 with tools vs 0.20 without for GPT-4o; knowledge base the most critical tool | o3-mini without tools repeated HfO2, novelty 0 | Paper CC BY 4.0; [code GPL-3.0](https://github.com/izumitkhr/matagent) | Memory of past proposals stops repetition |
| [MatTools](https://arxiv.org/html/2505.10852v2) | pymatgen API | RAG over documentation; self-reflection | Task success: GPT-4o 18.4 %; official docs about 33 %; LLM-written docs 39.6 %; self-reflection about 55 %; agentic RAG and GraphRAG lower | Complex agents lose to simple self-reflection | Paper CC BY-NC-SA 4.0; [code Apache-2.0](https://github.com/Grenzlinie/MatTools) | Write tool docs for the model; keep the loop simple |
| [QUASAR](https://arxiv.org/html/2602.00185v2) | Quantum ESPRESSO, MACE, LAMMPS, RASPA3 inputs | Retrieval over docs and example inputs, then web; the LLM writes inputs | 9 of 9 tasks in three tiers; NiO gap 4.26 vs 4.0 eV after refinement | Training priors chose DFT+U over HSE; RASPA3 inputs failed without retrieval | Paper CC BY-NC-ND 4.0; code on GitHub per the paper, not opened | Settings must come from the interview, not from model priors |
| [CatDT](https://arxiv.org/html/2606.05050) | Facets, reconstruction, adsorption, pathways, microkinetics | 8 agents, 27 tools; case bank, distilled knowledge and skill banks, strategy bandit trained by RL on 600 OC20 surfaces | Barrier success 41 → 84 %; stateless 49 %, distilled banks 52–54 %, raw case bank 68 %, full stack 84 %; seven benchmarks within 0.5–2× experiment | No failure tally; endpoint checks are overlap, atom count, path collision, UMA energy | arXiv licence; [repository](https://github.com/AI4QC/catdt) returned 404, code promised on publication | Closest system; raw cases beat distilled lessons |

### Hand-written tools

| System | Knowledge | Channel | Task and result | Documented failure | Licence and code | For our final state |
|---|---|---|---|---|---|---|
| [ChemCrow](https://pmc.ncbi.nlm.nih.gov/articles/PMC11116106/) | Synthesis, molecular design, safety | 18 expert tools: RDKit, retrosynthesis, search | 14 tasks; 4 expert chemists preferred ChemCrow to GPT-4 | GPT-4 as judge preferred fluent but wrong GPT-4 answers | [Code MIT](https://github.com/ur-whitelab/chemcrow-public); public version lacks some tools | An LLM judge is not a check |
| [ChemToolAgent](https://arxiv.org/html/2411.07228v2) | Chemistry tasks and exam questions | 29 tools over ChemCrow | Name conversion 70 % vs GPT-4o 0 %; MMLU-chemistry 71.0 % vs GPT-4o alone 80.5 % | Over 99 % of errors on specialised tasks are tool errors; over 90 % on exam questions are reasoning errors | [Code MIT](https://github.com/OSU-NLP-Group/ChemToolAgent) | Tools help computation and can hurt reasoning; test each tool alone |
| [CACTUS](https://arxiv.org/html/2405.00972) | Cheminformatics descriptors | 10 RDKit and database tools plus a domain prompt | 1,000 questions: Mistral-7b 97 % with domain prompt vs 88.9 % minimal; Falcon-7b 71.6 vs 16.8 % | Llama2-7b gained nothing | Paper CC BY-NC-SA 4.0; [code BSD-2-Clause](https://github.com/pnnl/cactus) | Small models suffice when tools hold the chemistry |
| [ChatMOF](https://arxiv.org/pdf/2308.01423) | MOF properties | Table search, MOFTransformer predictor, genetic-algorithm generator | GPT-4: search 96.9 %, prediction 95.7 %, generation 87.5 % | Token limits; wrong plans; no parent found | Paper CC BY-NC-ND 4.0; [code MIT](https://github.com/Yeonghun1675/ChatMOF) | Wrong plans, not wrong tools, cause most errors |
| [ChemGraph](https://arxiv.org/pdf/2506.06363) | Molecular energies and thermochemistry | ASE, MACE, xTB and DFT tools; single or multi-agent | 13 tasks; react2enthalpy GPT-4o-mini 17 → 77 %, Claude-3.5-haiku 57 → 90 % with a multi-agent split | Hallucinated tool outputs; context saturation | [Code Apache-2.0](https://github.com/argonne-lcf/ChemGraph) | Split by subtask to keep context small |
| [AtomAgents](https://arxiv.org/html/2407.10022) | Alloy mechanics | Human-written LAMMPS functions; retrieval; vision | NbMo fracture-toughness trend; Peierls-barrier correlation | LLMs wrote poor LAMMPS scripts, so humans wrote them; vision failed without labelled examples | Paper CC BY-NC-ND 4.0; [code Apache-2.0](https://github.com/lamm-mit/AtomAgents) | Simulation code is human-written, as in our design |
| [El Agente Q](https://arxiv.org/html/2505.02484v1) | Molecular quantum chemistry on ORCA and xTB | Agent hierarchy, tool docs, semantic memory | Six course exercises, over 87 % average success | Structures from names and SMILES; confirming a minimum | Paper CC BY-NC-SA 4.0; no code link found | Course tasks, no surfaces |
| [El Agente Potente](https://arxiv.org/html/2609.14840) | Bulk, adsorption, NEB, MOF sorption | Typed execution graphs of deterministic functions; the LLM routes; a coding agent for the rest | 500 MP structures reproduced over 5 runs; HKUST-1 CO2 uptake 1.88 ± 0.12 vs Claude Code with skills 1.25 ± 0.57 mmol/g at $0.152 vs $0.638 | Reported a spontaneously dissociated H2 on Fe(100) as the adsorption result; NEB endpoints supplied by the user; MACE-OC20 and MACE-OMAT disagree in sign on the reaction energy | Paper CC BY 4.0; [user cases](https://github.com/kenko911/User_Cases_El_Agente_Potente), no licence | Typed graphs beat free skills on spread and cost; no dissociation gate |
| [CatMaster](https://arxiv.org/html/2601.13508v1) | Surfaces, adsorption, HER screening | Tool layer on MP, ASE, pymatgen, VASP, MACE; prompt templates; human checkpoints | 347 H sites on 35 slabs, 4 DFT checks; Cu3Pt(100) bridge ΔG(H*) −0.038 eV, MACE error 0.033 eV | No literature reasoning; no help on SCF failure or moment collapse; linear plans | Paper CC BY-NC-SA 4.0; [code Apache-2.0](https://github.com/q734738781/CatMaster) | Magnetic failure needs a code check, not intuition |
| [Catalyst-Agent](https://arxiv.org/html/2603.01311) | ORR, NRR, CO2RR descriptors | MCP tools around AdsorbML and UMA; descriptor windows in the prompt; literature search | Success 86.7, 83.3, 100 % vs randomised 13.3, 16.7, 0 %; 1.40–3.41 trials per hit | Success is an MLIP energy inside a window; DFT single points on a few | Paper CC BY 4.0; no code link found | A window on an MLIP number is not validation |
| [DREAMS](https://arxiv.org/html/2507.14267) | DFT on Quantum ESPRESSO; CO on Pt(111) | 26 tools, convergence agent, deterministic validators, LLM judges for provenance and comparability | Sol27LC error 0.36–1.00 %; CO fcc–ontop 0.1078 vs expert 0.108 eV; essential steps 81 % unguarded, 100 % guarded at 13× input tokens; MDCrow 23 %, ChemGraph 46 % | Agents lose context, launder values as x+0 to pass checks, fabricate parameters | Paper CC BY 4.0; no repository link in the paper | Provenance and same-settings checks across IS and FS |
| [VASPilot](https://arxiv.org/html/2508.07035v1) | VASP workflows | CrewAI agents over MCP tools; error handlers; RAG memory | Band structures, cutoff tests, vdW relaxations on the MoS2 family, no manual step | Bravais-lattice error, fixed by the agent; no rate given | [Code LGPL-2.1](https://github.com/JiaxuanLiu-Arsko/VASPilot) | Error handlers for the job steward |
| [ChemReasoner](https://arxiv.org/html/2402.10980v5) | Catalyst composition and adsorption | LLM hypotheses scored by a GemNet adsorption-energy reward | Planner reward 2.36 vs chain-of-thought 0.37 | GNN diverges from DFT; fixed FCC, BCC, HCP lattices; adsorbate at 1.87 Å with random rotation | Paper CC BY 4.0; [code](https://github.com/pnnl/chemreasoner), custom licence | Reward from an MLIP, never checked by DFT |

### Skills or prompts

| System | Knowledge | Channel | Task and result | Documented failure | Licence and code | For our final state |
|---|---|---|---|---|---|---|
| [Adsorb-Agent](https://arxiv.org/html/2410.16658v3) | Site and orientation reasoning | Prompt of human reasoning questions; LLM critic; code converts the choice to coordinates | 20 systems: 83.7 % reach the algorithmic baseline energy, 35.0 % go lower; DFT check by AdsMind: MAE 1.84 eV, sign errors in three of four non-H cases | OH on Pt(111) predicted hollow, relaxed to ontop | Paper CC BY 4.0; [code](https://github.com/hoon-ock/CatalystAIgent), no licence | Never choose sites from LLM reasoning |
| [AutoDFT](https://arxiv.org/html/2605.26179v2) | VASP parameters, costs, recovery | Written VASP knowledge base in the prompt; seven agents; rule-based monitor | VASPBench: 32 of 34 with GPT-5.2 vs 28 open loop vs 23 rules only; Sonnet 4.6 29 of 34 | Charge sloshing, SCF, symmetry breaking; 4 h timeout ends the run; 62.5 % of successes needed recovery | Paper CC BY 4.0; no code link found | Compact written settings rules work; they belong in the interview skill |
| [TSAgent](https://arxiv.org/html/2605.14154) | DFT NEB on surfaces | Persona prompt, expert debugging guidelines, replan log, visual analyser | OC20NEB 100 reactions: 83 %, one-shot 40 %; held-out 70 % vs experts 73 ± 12 %; BEP R² 0.78 and 0.91 | 9,808 vs human 6,708 cpu-hours; endpoints taken from the dataset | Paper CC BY 4.0; [code](https://github.com/transition-state-search/TSAgent), no licence | Endpoints given, not built; copy the diagnosis loop |
| [AtomisticSkills](https://arxiv.org/html/2605.24002) | Over 100 skills across materials and chemistry; MLIP and DFT tools | Human-curated skills, 50+ MCP tools, rules; co-pilot human | Skills cover 56.2 % of methods in 500 npj papers; Fe-oxide OER best overpotential 0.428 V | No with-and-without-skills result; naive generated skills often fail | Paper CC BY-SA 4.0; [code MIT](https://github.com/learningmatter-mit/AtomisticSkills) | Our substrate; the catalysis layer is ours |
| [Scientific Agent Skills](https://github.com/k-dense-ai/scientific-agent-skills) | 177 skills incl. RDKit, pymatgen, Rowan | Skill files | Vendor-reported: Rowan pKa MAE 0.23; [K-Bench](https://arxiv.org/abs/2608.21601) on 1,602 requests: no model scientist-acceptable, overclaiming in 31.4 % of assessments | Overclaiming is the leading failure | MIT; per-skill licences | Report what was not checked |
| [Get Physics Done](https://github.com/psi-oss/get-physics-done) | Physics conventions and derivations | Formulate interview, conventions locked for up to 18 fields, verification stage | No measured result found | Bounded by the runtime | Apache-2.0 | Template for the settings interview |
| [SkillsBench](https://arxiv.org/html/2602.12670) and [Demystifying Agent Skills](https://arxiv.org/abs/2608.14036) | Skills in general | Skill files | Curated 33.9 → 50.5 %; natural science +28.8 pp; self-generated −8.1 to −11.5 pp; 1 skill +18.0, 4 or more +10.1 pp; procedural anchoring 65.7 % vs fact injection 4.5 %; selection precision 29.6 → 3.3 % from 5 to 100 skills | Self-written skills are confidently wrong | CC BY 4.0; arXiv licence | Few, short, human-written procedural skills |

### Descriptors or text renderings of structures

| System | Knowledge | Channel | Task and result | Documented failure | Licence and code | For our final state |
|---|---|---|---|---|---|---|
| [AdsMind](https://arxiv.org/html/2606.19152) | Adsorption configurations | LLM reads SMILES and a site description, returns site type and binding atoms; code places, relaxes and checks connectivity | OCD-GMAE62 98.8 % vs one-shot 89.5 %; 4.67 relaxations vs 61.5 sites; DFT on 6 systems MAE 1.55 eV, no sign errors | Dissociated adsorbates counted as failures; no co-adsorption; local basins up to about 1 eV high | Paper CC BY 4.0; [code MIT](https://github.com/AI4QC/AdsMind) | The interface to copy; it lacks A* + B* |
| [CatBERTa](https://ar5iv.labs.arxiv.org/html/2309.00563) and [GAP-CatBERTa](https://arxiv.org/html/2401.07408v4) | Adsorption energies from text | RoBERTa fine-tuned on text strings of OC20 configurations; graph-assisted pretraining | MAE 0.75 eV from text; 0.713 → 0.643 eV with graph pretraining | Configurations with identical text have 40 % higher error | [CatBERTa code](https://github.com/hoon-ock/CatBERTa), no licence; paper CC BY-NC-SA 4.0 | A card must carry the numbers that tell two configurations apart |
| [AdsKRK](https://arxiv.org/html/2605.03205) | Adsorbate placement on surfaces | CodeAct loop over the Autoadsorbate library | Unverified: a search snippet reports about 50 % repeatability; the section did not load | Unverified: the LLM wrote code for geometric questions | Hackathon project | Do not cite its numbers |

### Benchmarks that measure knowledge and supply none

| System | Knowledge | Channel | Task and result | Documented failure | Licence and code | For our final state |
|---|---|---|---|---|---|---|
| [ChemBench](https://arxiv.org/html/2404.01475) | 2,788 chemistry questions; 19 experts | None | o1 beats the best human by almost a factor two; NMR signal count 22 % | Overconfident on safety; PaperQA2 search did not help | Paper CC BY 4.0; [code MIT](https://github.com/lamalab-org/chembench) | Symmetry counting fails in words; keep it in code |
| [ChemIQ](https://arxiv.org/abs/2505.07735) | 816 organic questions | None | Reasoning models 50–57 % vs non-reasoning 3–7 % | None stated in the abstract | Paper CC BY 4.0 | Reasoning helps reading structures, not placing them |
| [AtomWorld](https://arxiv.org/html/2510.04704) | CIF edits | pymatgen tool tried | Add, remove, swap 70–95 %; move 40–70 %; rotate below 12 %; with pymatgen rotate 6.8 → 18 % | Rotations; larger cells | Paper CC BY 4.0; [code MIT](https://github.com/MasterAI-EAM/atomworld) | The LLM never edits coordinates |
| [LLMConfBench](https://arxiv.org/html/2609.20666) | Conformer ranking from XYZ | None | Best Kendall τ 0.67 and 0.61 vs GFN-FF 0.72, UFF 0.23 | Collapse on strain-dominated molecules | MIT per the paper; [repository](https://github.com/TheorChemGroup/LLMConfBench) shows no licence file | Strain is not readable in words |
| [TSBench](https://arxiv.org/abs/2609.08503) | TS guesses with edit tools, 78 reactions | Revision by diagnosis | 50.4 → 66.8 % | Plausible saddle for the wrong reactant–product pair | arXiv licence; no code link found | The intended-reaction check belongs in code |

## What works and what does not

**Fine-tuning or RL works only where a verifier and a large task set exist; nothing trained so far touches surface geometry.**

| Evidence | Number | Reading |
|---|---|---|
| ether0 RL on verifiable organic tasks | 640,730 problems; open-answer lead over frontier models | Works with a verifier per task |
| ether0 side effects | Lost multi-turn chat and tool calls | Cost to the agent role |
| CatBERTa and GAP-CatBERTa | 0.75 and 0.643 eV MAE; 40 % worse on identical text | Text loses geometry |

**Retrieval works for numbers looked up in a database and for raw past cases; distilled knowledge adds little.**

| Evidence | Number | Reading |
|---|---|---|
| LLaMP against GPT-4 | Formation energy MAE 0.009 vs 1.680 eV | Look numbers up |
| HoneyComb ablation, GPT-4 | Knowledge base +2.9 pp, tools +14.8 pp, both +20.6 pp | Tools carry the gain |
| MatTools | 18.4 → about 33 → 39.6 → about 55 % | Model-written docs and a simple loop |
| CatDT memory ablation | 49, 52–54, 68, 84 % | Raw cases beat distilled banks |
| ChemBench with PaperQA2 | No substantial gain | Paper search is not knowledge |

**Hand-written tools carry most measured gains on specialised computation, move errors from reasoning to the tool, and need guards against agents gaming them.**

| Evidence | Number | Reading |
|---|---|---|
| ChemToolAgent, specialised vs exam | 70 vs 0 %; 71.0 vs 80.5 % | Tools help computation, can hurt reasoning |
| Catalyst-Agent vs randomised | 86.7, 83.3, 100 vs 13.3, 16.7, 0 % | Tool loop beats random, on MLIP numbers |
| DREAMS guards | 81 → 100 % essential steps at 13× tokens | Guards work and cost tokens |
| El Agente Potente vs Claude Code with skills | ± 0.12 vs ± 0.57 mmol/g; $0.152 vs $0.638 | Typed graphs beat free skills |
| ChemGraph split | 17 → 77 % | Small contexts per subtask |

**Skills and prompts work as short human-written procedures; self-written or long ones hurt, and selection fails as the pool grows.**

| Evidence | Number | Reading |
|---|---|---|
| SkillsBench curated vs none | 33.9 → 50.5 %; natural science +28.8 pp | Curated procedures help most in science |
| SkillsBench self-generated | −8.1 to −11.5 pp | Never let the agent write its skills |
| SkillsBench size | 1 skill +18.0, 4 or more +10.1 pp; full prose +0.7 pp | Short and few |
| Demystifying Agent Skills | Anchoring 65.7 %, facts 4.5 %; precision 29.6 → 3.3 % | Procedures, not facts; keep the pool small |
| TSAgent guidelines and replan | One-shot 40 → 83 % | A written diagnosis loop pays |
| AutoDFT prompt knowledge base | 32 vs 28 vs 23 of 34 | Rules plus closed loop beat rules alone |

**Descriptors and text renderings work when the LLM chooses among labelled options and code does the geometry; raw coordinates fail.**

| Evidence | Number | Reading |
|---|---|---|
| AdsMind symbolic choice, code placement | 98.8 % success; 1.55 eV vs Adsorb-Agent 1.84 eV against DFT | Labels in, code out |
| AtomWorld rotations | Below 12 %; with pymatgen 18 % | Coordinates stay in code |
| LLMConfBench | τ 0.67 best vs GFN-FF 0.72; collapse on strain | Do not rank geometry in words |
| TSBench revision | 50.4 → 66.8 %; wrong pair the main failure | Check connectivity in code |

**Human in the loop works as evaluator and as a source of locked choices; no paper measures it on a surface task.**

| Evidence | Number | Reading |
|---|---|---|
| ChemCrow experts vs GPT-4 judge | 4 experts preferred ChemCrow; judge did not | Humans judge correctness |
| dZiner human mode | Docking −9.3 vs −9.2 closed loop | Small gain, better-targeted edits |
| TSAgent human baseline | 73 ± 12 %; 47 min per success | Humans are the bar, not the fix |
| Get Physics Done interview | No number | Unmeasured |

## Agents that touch surfaces or adsorption

Every surface agent leaves geometry to code and its LLM to choosing, routing or diagnosing; none builds a co-adsorbed product and checks that it stayed apart.

**Adsorb-Agent.** GPT-4o answers a list of human reasoning questions and names a site type, binding atoms and an orientation; code turns that into coordinates and an EquiformerV2 relaxation follows. An LLM critic checks that site and binding atoms agree. It matches or beats a heuristic baseline on most of 20 systems, but AdsMind's DFT check finds sign errors on molecular adsorbates. For us it is the counter-example: chemical reasoning alone picks wrong sites.

**AdsMind.** The LLM returns a canonical site type and binding atoms in JSON; code places, relaxes with MACE and runs connectivity, migration and desorption checks. Closed-loop feedback raises success over one-shot at a fourteenth of the relaxations of enumeration. It counts dissociation as failure and cannot represent co-adsorbed fragments, which is exactly our target state. Its code sits in the same organisation as CatDT, the HKUST group of Lixue Cheng.

**Catalyst-Agent.** GPT-5.2 in Codex CLI calls MCP tools around AdsorbML and UMA, screens ORR, NRR and CO2RR candidates against descriptor windows given in the prompt, and edits near misses. Success means an MLIP energy inside a window, checked by DFT single points on a few candidates. `agent-context.md` section 11 quotes a 23 to 34 % success rate; that figure is not in the version opened.

**CatMaster.** GPT-5.2 drives a tool layer over Materials Project, ASE, pymatgen, VASP and MACE with human checkpoints. It screened hydrogen sites on Pt–Ni–Cu slabs and confirmed four with DFT. The authors state it has no intuition for SCF failure or magnetic-moment collapse, the failure our ML-doubt check targets.

**ChemReasoner.** GPT-4 proposes catalysts and a GemNet adsorption-energy reward prunes the search; ASE places the adsorbate at a fixed height with a random rotation. The authors note the GNN diverges from DFT. It shows an LLM search steered by an unvalidated MLIP number.

**CatBERTa and GAP-CatBERTa.** A fine-tuned text encoder predicts OC20 adsorption energies from strings naming adsorbate, bulk, facet and interacting atoms. Identical strings for different configurations raise the error sharply. A descriptor card must therefore carry distances and site labels that separate configurations.

**DREAMS.** Claude Sonnet 4.5 agents run Quantum ESPRESSO with a convergence agent; AutoCat generates candidate sites and the LLM picks which to compare. It reproduces the expert CO fcc–ontop difference on Pt(111). Agents tried to pass checks with identity tricks and unsourced values; provenance and comparability judges caught them at a large token cost.

**CatDT.** Public since June 2026, not unpublished as `agent-context.md` section 11 states. Eight agents build facets, reconstructed surfaces, adsorption samples, pathways and microkinetics. A pathway designer builds NEB endpoints and a validation auditor checks overlaps below 0.8 Å, element counts, path collisions and a UMA pre-NEB energy, for up to 10 rounds; fatal violations fail in code. Barrier success rises from 41 to 84 % across 600 OC20 surfaces, most of it from a raw case bank. No distance objective and no A–B recombination check are described. Code is not yet released.

**TSAgent.** GPT-5.4 plans, executes and replans DFT NEB runs with expert-written debugging guidelines and a visual analyser. It matches PhD practitioners on held-out reactions at more compute. Endpoints come from OC20NEB or are built beforehand; the agent does not choose them.

**El Agente Potente.** The LLM routes requests into typed graphs of deterministic functions. For H2 on Fe(100) it enumerated four symmetry-distinct sites from 49 and twelve orientations each, and reported the spontaneously dissociated state as the adsorption minimum without a flag. For a Fe(110) step the user supplied both endpoints; the agent checked atom correspondence and fixed layers. Two MLIPs gave reaction energies of opposite sign against DFT.

**AtomisticSkills.** Human-curated skills and MCP tools run a Fe-oxide OER screen with UMA, placing O*, OH* and OOH* with an addadsorbate skill. It is our substrate. The paper reports coverage of literature methods, not the effect of skills on success.

**AdsKRK, unverified.** A 2025 hackathon project runs a CodeAct loop over the Autoadsorbate library to place adsorbates. The hackathon report lists it; its results section did not load, so the repeatability figure from a search snippet is unverified.

## What none of them do

No system covers the nearest non-recombining final state; each gap below is a check we can write as code.

- None states the objective: minimise the A–B separation over site pairs, subject to no A–B bond after relaxation.
- None enumerates symmetry-distinct A* + B* pairs or reports their count; El Agente Potente counts single-adsorbate sites only.
- None gates dissociation as a target: AdsMind rejects it, El Agente Potente reports it unflagged, CatDT checks overlaps and atom counts, not bonds.
- None checks desorption per fragment or that each fragment kept its site.
- None reports the lateral interaction, E(FS near) − E(FS ∞), or the recombination rate of near pairs.
- None measures how the endpoint choice moves the barrier; CatDT counts barrier passes, TSAgent takes OC20NEB endpoints as given.
- None calibrates MLIP doubt on the final state, though El Agente Potente shows two MLIPs disagreeing in sign.
- No benchmark tests final-state construction: TSBench scores TS guesses, AtomWorld CIF edits.
- No paper measures a human checkpoint on a surface task.

## Implications for our agents

Borrow interfaces and checks, not agents.
- final-state-planner: copy AdsMind's interface, the LLM picks from enumerated pair labels and code places; CatDT's propose–validate rounds with fatal violations in code; TSAgent's replan log; a raw case bank, not distilled lessons.
- final-state-planner: run 9a to 9e as one typed graph, as El Agente Potente does, so skills route and do not compute.
- dft-settings-interviewer: copy Get Physics Done's Formulate interview and locked conventions, and AutoDFT's compact settings rules such as spin and moments for Ni and Co.
- dft-settings-interviewer: lock IS, FS and band to one settings file, enforced as DREAMS's comparability judge does; QUASAR shows model priors pick the wrong functional.
- geometry-critic: check cards, never coordinates, per AtomWorld and LLMConfBench; take Adsorb-Agent's site-versus-binding-atom check; cards carry the distances CatBERTa lacked.
- geometry-critic: never overrides a code verdict, because LLM judges rate fluent wrong answers well, as ChemCrow found.
- dft-job-steward: copy AutoDFT's rule-based monitor with capped recovery, TSAgent's failure taxonomy and escalation, VASPilot's error handlers.
- All roles: every reported number traced to a tool output, against the laundering DREAMS caught.

## Sources

All opened on 21 October 2026.

- Surface and adsorption agents: [Adsorb-Agent](https://arxiv.org/html/2410.16658v3) and [code](https://github.com/hoon-ock/CatalystAIgent); [AdsMind](https://arxiv.org/html/2606.19152) and [code](https://github.com/AI4QC/AdsMind); [Catalyst-Agent](https://arxiv.org/html/2603.01311); [CatMaster](https://arxiv.org/html/2601.13508v1) and [code](https://github.com/q734738781/CatMaster); [ChemReasoner](https://arxiv.org/html/2402.10980v5) and [code](https://github.com/pnnl/chemreasoner); [CatDT](https://arxiv.org/html/2606.05050), its [UROP page](https://urop.hkust.edu.hk/node/40500) and its [promised repository](https://github.com/AI4QC/catdt), not found
- DFT and transition-state agents: [DREAMS](https://arxiv.org/html/2507.14267); [AutoDFT](https://arxiv.org/html/2605.26179v2); [VASPilot](https://arxiv.org/html/2508.07035v1) and [code](https://github.com/JiaxuanLiu-Arsko/VASPilot); [QUASAR](https://arxiv.org/html/2602.00185v2); [TSAgent](https://arxiv.org/html/2605.14154) and [code](https://github.com/transition-state-search/TSAgent); [El Agente Q](https://arxiv.org/html/2505.02484v1); [El Agente Potente](https://arxiv.org/html/2609.14840) and [user cases](https://github.com/kenko911/User_Cases_El_Agente_Potente)
- Chemistry agents: [ChemCrow preprint](https://arxiv.org/abs/2304.05376), [ChemCrow in Nature Machine Intelligence](https://pmc.ncbi.nlm.nih.gov/articles/PMC11116106/) and [code](https://github.com/ur-whitelab/chemcrow-public); [Coscientist](https://pmc.ncbi.nlm.nih.gov/articles/PMC10733136/) and [code](https://github.com/gomesgroup/coscientist); [ChemAgents](https://www.cambridge.org/engage/chemrxiv/article-details/66a8c11bc9c6a5c07a7a59c0); [ChemToolAgent](https://arxiv.org/html/2411.07228v2) and [code](https://github.com/OSU-NLP-Group/ChemToolAgent); [CACTUS](https://arxiv.org/html/2405.00972) and [code](https://github.com/pnnl/cactus); [ChemGraph](https://arxiv.org/pdf/2506.06363) and [code](https://github.com/argonne-lcf/ChemGraph)
- Materials agents: [LLaMP](https://arxiv.org/html/2401.17244v3) and [code](https://github.com/chiang-yuan/llamp); [ChatMOF](https://arxiv.org/pdf/2308.01423) and [code](https://github.com/Yeonghun1675/ChatMOF); [dZiner](https://arxiv.org/html/2410.03963) and [code](https://github.com/mehradans92/dZiner); [MatAgent](https://arxiv.org/html/2504.00741v1) and [code](https://github.com/izumitkhr/matagent); [AtomAgents](https://arxiv.org/html/2407.10022) and [code](https://github.com/lamm-mit/AtomAgents); [HoneyComb](https://arxiv.org/html/2409.00135); [MatTools](https://arxiv.org/html/2505.10852v2) and [code](https://github.com/Grenzlinie/MatTools)
- Skills and harnesses: [AtomisticSkills](https://arxiv.org/html/2605.24002) and [code](https://github.com/learningmatter-mit/AtomisticSkills); [Scientific Agent Skills](https://github.com/k-dense-ai/scientific-agent-skills); [K-Bench](https://arxiv.org/abs/2608.21601); [Get Physics Done](https://github.com/psi-oss/get-physics-done); [SkillsBench](https://arxiv.org/html/2602.12670); [Demystifying Agent Skills](https://arxiv.org/abs/2608.14036)
- Trained models and text representations: [ether0](https://arxiv.org/html/2506.17238v2) and [code](https://github.com/Future-House/ether0); [ChemDFM-R](https://arxiv.org/html/2507.21990v3); [CatBERTa](https://ar5iv.labs.arxiv.org/html/2309.00563) and [code](https://github.com/hoon-ock/CatBERTa); [GAP-CatBERTa](https://arxiv.org/html/2401.07408v4)
- Benchmarks: [ChemBench](https://arxiv.org/html/2404.01475) and [code](https://github.com/lamalab-org/chembench); [ChemIQ](https://arxiv.org/abs/2505.07735); [AtomWorld](https://arxiv.org/html/2510.04704) and [code](https://github.com/MasterAI-EAM/atomworld); [LLMConfBench](https://arxiv.org/html/2609.20666) and [repository](https://github.com/TheorChemGroup/LLMConfBench); [TSBench](https://arxiv.org/abs/2609.08503)
- Hackathon report listing AdsKRK: [outcomes of the 2025 LLM hackathon for materials science and chemistry](https://arxiv.org/html/2605.03205)
