---
name: dft-settings-protocol
description: How the numerical settings of a campaign are chosen, locked and never changed: pseudopotentials, cutoff, k-mesh, smearing, layers, vacuum, references, from a verified protocol or a convergence sweep, never from memory. Use before any structure is computed and whenever PROJECT.md is in doubt.
---

# DFT settings protocol

Procedure. Facts and ranges live in `agent.md` section 3 and in `PROJECT.md`, not here.

1. Read the settings the three supplied structures were relaxed with; they are the starting point. If they differ, stop: check 8 fails before anything runs.
2. Ask the human the five interview questions in `PROJECT.md` and record the answers verbatim.
3. Choose the protocol and state why in one sentence: the AiiDA common-workflows precision protocol, SSSP for Quantum ESPRESSO, or OC20's RPBE and PAW values when the benchmark is OC20NEB. Never write a cutoff or a k-mesh from memory.
4. Call `calculation_protocol` with the settings, the human's physics choices and the protocol. Call `structure_retrieval` to cleave the named bond and select the cell.
5. Show the human `PROJECT.md` and stop at the approve-settings checkpoint. Only the human locks it.
6. After the lock, never change a value. A new value means a new campaign.

Tools: `structure_retrieval`, `calculation_protocol`, `literature_lookup`.
