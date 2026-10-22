---
name: dissociation-final-state
description: The six points of the board's step 3 and steps 4 to 6 as a procedure: place the binding fragment, enumerate the dissociated atom's sites inside the window, screen by pull force, relax, gate, cluster, keep the nearest and the lowest. Use whenever a dissociated final state is built.
---

# The nearest non-recombining final state

Order in code: 3.2, 3.3, 3.4, then 4, 5, 6; 3.6 is the alternative generator; 3.1 runs inside step 5. Step 3.5 is deferred: A stays at its initial-state site until the team decides how to implement the enumeration.

1. `site_enumeration` on the selected cell; read the count, never the coordinates.
2. 3.5, deferred: A, the fragment that keeps the binding atom, stays at its initial-state site; the enumeration of its sites waits for the team's decision. `adsorbate_placement` is used at step 4 to place B.
3. 3.2: `literature_lookup` for d, the length of the bond to break; `pair_enumeration` inside [1.5 d, 5] Å, nearest first by site-graph distance, counted.
4. 3.3: `pull_force_screen`, one force call per pair; a pull towards the other fragment queues the pair last, never drops it.
5. 3.4: hand the descriptor cards to the surface-chemist; take its ordering; never its coordinates. It never removes a pair.
6. 3.6, alternative and baseline: `minima_hopping` with the chosen potential.
7. 4: `relaxation` with the locked settings, random displacement first.
8. 5: `anomaly_filter` on every relaxed pair, per fragment; check 10 is point 3.1; a failing pair is never kept; every rejection is logged with its reason.
9. 6: `soap_clustering`; keep the nearest and the lowest per cluster; nearest first overall.
10. `reference_energies` for E(FS ∞); report both energies and the recombination rate.

Tools: `site_enumeration`, `adsorbate_placement`, `pair_enumeration`, `pull_force_screen`, `minima_hopping`, `relaxation`, `anomaly_filter`, `soap_clustering`, `descriptor_card`, `reference_energies`.
