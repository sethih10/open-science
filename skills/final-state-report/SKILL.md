---
name: final-state-report
description: The format of the study report and what must trace to a tool output: both energies, each fragment's adsorption energy, rejections with reasons, the recombination rate, doubt, open decisions, the OC20NEB comparison, cost and the decision trace. Use at the pick and the Solution step.
---

# Final-state report

1. Call `ranking`, open its sheet for the human, and ask the Pick boxes it returns; the hook records the pick, and in a study that is not an example the choice and reason go to the case bank. With no survivor, the box closes the pick with none.
2. Call `reference_energies`, then `report`. The report tool writes the report; every number in it is a field of a record in the trace, and agents add only notes.
3. Sections: the steps in brief from `summary.md`; final states with E(FS near), E(FS ∞), the lateral interaction and each fragment's adsorption energy; every survivor with its status; rejected pairs with reasons, before and after relaxation; recombination rate per shell beside the check-10 threshold; doubt flags; open decisions; the OC20NEB comparison, waiting for D3; cost; what was not checked; the human's choices and interpretation.
4. Hand `report.md` to the scientific-critic, which reviews it in its own context and leaves a note; call `report` again so the review is in it; ask the interpret-results box; then show the whole `summary.md`.
5. Never state a value the trace does not hold; never round a number the tool reported, least of all to zero.

Tools: `ranking`, `reference_energies`, `report`.
