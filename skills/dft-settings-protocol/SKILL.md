---
name: dft-settings-protocol
description: How the settings of a study are chosen, locked and never changed: protocol mlip with no DFT setting when no DFT runs, which is every study until dft_single_points is built; else pseudopotentials, cutoff, k-mesh, smearing, layers, vacuum, references, from a verified protocol or a convergence sweep, never from memory. Use before any structure is computed and whenever PROJECT.md is in doubt.
---

# DFT settings protocol

The computational-chemist follows this as a subagent; the orchestrator asks the human, and the literature-reader supplies the published values.

Procedure. Facts and ranges live in `AGENTS.md` section 3 and in `PROJECT.md`, not here.

1. At the prompt step, draft two to four likely answers to each of the five interview questions in `PROJECT.md`, from the inputs and the system, for the orchestrator to offer in its question box. The human's answers reach the Interview table of `PROJECT.md` word for word.
2. Read the settings the supplied structures were relaxed with; they are the starting point. If they differ, stop: check 8 fails before anything runs.
3. Decide whether the study runs DFT. It does not, unless the study says it will: no study does until `dft_single_points` is built. Then the protocol is `mlip`, the potential chosen at 1\* computes every energy, and steps 4 and 5 ask the human nothing about DFT: no functional, cutoff, k-mesh, smearing, PAW or convergence target is proposed, asked or shown. This holds also when the human supplies only relaxed `.xyz` files without energies.
4. Choose the protocol and state why in one sentence: `mlip` for a study without DFT; for a study that runs DFT, the AiiDA common-workflows precision protocol, SSSP for Quantum ESPRESSO, or OC20's RPBE and PAW values when the benchmark is OC20NEB. Never write a cutoff or a k-mesh from memory: the tool applies the protocol's k-mesh rule to the selected cell, and a mesh the human gives wins.
5. Call `structure_retrieval` to cleave the named bond and select the cell, then `calculation_protocol` with the protocol, its reason and the human's physics choices from the Interview table; under `mlip` the only physics choice is spin.
6. Return the proposal, the origin of every setting and the reason to the orchestrator, which shows `PROJECT.md` and asks the human at the approve-settings checkpoint. Only the human locks it.
7. After the lock, never change a value. A new value means a new study.

A lock under `mlip` holds what the run uses: the selected cell, the force threshold, the gas references and the open decisions. It is never asked `calculation_protocol.convergence_target_meV`, and `anomaly_filter.frequencies_source` is `mlip`. The DFT settings come back only with `dft_single_points`.

Tools: `structure_retrieval`, `calculation_protocol`.
