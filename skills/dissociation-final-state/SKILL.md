---
name: dissociation-final-state
description: The six points of the board's step 3 and steps 4 to 6 as a procedure: keep the binding fragment at its site, enumerate the dissociated fragment's sites inside the window, place it, screen by pull force, order, gate, relax, gate again, cluster, keep the nearest and the lowest. Use whenever a dissociated final state is built.
---

# The nearest non-recombining final state

Order in code: 3.2 with B placed, 3.3, 3.4, then 4 with the gate before relaxation, 5, 6; 3.6 is the alternative generator; 3.1 runs inside step 5. Step 3.5 is deferred: A stays at its initial-state site until the team decides how to implement the enumeration.

1. `site_enumeration` on the selected cell; read the count and the site kinds, never the coordinates.
2. 3.5, deferred: A, the fragment on the side of the first atom of the named bond, stays at its initial-state site.
3. 3.2: d is a published bond length the human checked, which the literature-reader looks for, else the bond measured as `pair_enumeration.d_definition` says. `pair_enumeration` inside [1.5 d, upper] Å, nearest first by site-graph distance, counted; then `adsorbate_placement` puts B on every pair, because 3.3 screens placed structures.
4. 3.3: `pull_force_screen`, one force call per pair; a pull towards the other fragment queues the pair last, never drops it.
5. 3.4: the surface-chemist reads the cards and returns an ordering with a site type per fragment as advice; never its coordinates. It never adds or removes a pair.
6. 3.6, alternative and baseline: `minima_hopping` with the chosen potential, only when the human asks.
7. 4: `anomaly_filter` with stage before_relaxation and the checks the team listed; a candidate that fails is not relaxed. Then `relaxation` with the locked settings and the ordering, random displacement first.
8. 5: `anomaly_filter` on every relaxed pair, per fragment; check 10 is point 3.1; a failing pair is never kept; every rejection is logged with its reason.
9. 6: `soap_clustering`; keep the nearest and the lowest per cluster; nearest first overall.

The final states, `reference_energies` and the report follow the pick; see `final-state-report`.

Tools: `site_enumeration`, `adsorbate_placement`, `pair_enumeration`, `pull_force_screen`, `minima_hopping`, `relaxation`, `anomaly_filter`, `soap_clustering`, `descriptor_card`.
