---
name: final-state-report
description: The format of the campaign report and what must trace to a tool output: both energies, rejections with reasons, the recombination rate, doubt, the OC20NEB comparison, cost and the decision trace. Use at the Solution step.
---

# Final-state report

1. Call `ranking` and show the cards; stop at the pick-up-to-five checkpoint; record the choice and reason in the case bank.
2. Call `reference_energies`, then `report`. Every number in the report is a field of a record in the trace; cite its `outputs_ref`.
3. Sections, in order: final states with E(FS near), E(FS ∞) and the lateral interaction; rejected pairs with reasons; recombination rate per shell; doubt flags; the OC20NEB product-frame comparison; cost; what was not checked.
4. Hand the draft to the scientific-critic, which applies the reused `general-peer-review` skill in its own context; apply what it finds; stop at the interpret-results checkpoint.
5. Never state a value the trace does not hold; never round a number the tool reported.

Tools: `ranking`, `reference_energies`, `report`.
