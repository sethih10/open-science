---
name: mlip-doubt-calibration
description: When to doubt a machine-learned potential and what to do about it: benchmark candidates on the system class, keep every candidate as the committee, calibrate disagreement against a few labels, escalate instead of guessing. Use at MLIP selection and at uncertainty estimation.
---

# MLIP doubt and calibration

The mlip-specialist follows this; the solution-planner only receives the decision.

1. Call `mlip_selection` with two or three candidates and the system class; record the choice and the reason. Every candidate becomes the committee.
2. Magnetic metals, Co and Ni, are always doubted: spin on, moments initialised, a cross-family check on E_ads.
3. Unseen chemistry is always doubted: oxides, high coverage, electrochemical interfaces, organometallics outside the training set.
4. Call `uncertainty_estimation`; compare committee spread with the error on the labels, DFT if available, else OC20NEB. Compare on E_ads only across families, never on total energies.
5. A flag above the threshold stops the run at the review-flagged-cases checkpoint. Measure, repair with `active_learning` if DFT labels exist, and ask only if repair fails.
6. Never silence a flag; every flag and its evidence go to the trace.

Tools: `mlip_selection`, `uncertainty_estimation`, `active_learning`.
