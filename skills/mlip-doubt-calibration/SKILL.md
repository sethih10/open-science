---
name: mlip-doubt-calibration
description: When to doubt a machine-learned potential and what to do about it: benchmark candidates on the system class, keep every candidate as the committee, calibrate disagreement against a few labels, escalate instead of guessing. Use at MLIP selection and at uncertainty estimation.
---

# MLIP doubt and calibration

The mlip-specialist follows this; the orchestrator only receives the decision.

1. Before the lock, propose two or three installed candidates whose training covers both the products and the substrate class, each with the source of that claim; the human chooses them as `mlip_selection.candidates`. Call `mlip_selection` with the study and your reason; record the choice. Every candidate becomes the committee. Without DFT energies the benchmark is geometric: the residual force each potential leaves on the supplied relaxed structures and how far it moves them. A score against labels the same potential computed is circular.
2. Magnetic metals, Co and Ni, are always doubted: spin on, moments initialised, a cross-family check on E_ads.
3. Unseen chemistry is always doubted: oxides and ionic surfaces outside the training set, high coverage, electrochemical interfaces, organometallics, open-shell fragments on a potential without spin.
4. Call `uncertainty_estimation`; compare committee spread with the error on the labels, DFT if available, else OC20NEB. Compare on E_ads only across families, never on total energies.
5. A flag above the threshold stops the run at the review-flagged-cases checkpoint. Measure, repair with `active_learning` if DFT labels exist, and ask only if repair fails.
6. Never silence a flag; every flag and its evidence go to the trace.

Tools: `mlip_selection`, `uncertainty_estimation`, `active_learning`.
