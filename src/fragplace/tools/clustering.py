"""SOAP clustering and the ranking the human picks from. Tools: soap_clustering, ranking. Defined in fragplace.registry."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from ..runtime import artifacts, geometry, project
from ..runtime.journal import log, traced
from ..schemas.records import Candidate, Cluster, DescriptorCard, DoubtFlag, Pair, RankedCandidate, RelaxationResult

SOAP = {"r_cut": 5.0, "n_max": 8, "l_max": 6}   # dscribe's SOAP on the two binding atoms, 5 Å around each
SAME_SOAP = 0.02      # distance between normalised descriptors below which two survivors are one configuration


@traced(step="6", tool="soap_clustering")
def soap_clustering(survivors: List[Candidate], energies: List[RelaxationResult], pairs: List[Pair]) -> Dict[str, Any]:
    """Cluster the survivors by SOAP; keep the nearest and the lowest per cluster; nearest first overall.

    Board steps: 6. Status: core. Lane: laptop. Allowed roles: solution-planner.

    Inputs:
        survivors: list[Candidate]
        energies: list[RelaxationResult]
        pairs: list[Pair]
    Outputs:
        clusters: list[Cluster]
        kept: list[str]
    Checks:
        - nearest-first ordering preserved across clusters
    Thresholds:
        per_cluster: open: team decision: the board says 3, could be more
    Wraps:
        - dscribe.descriptors.SOAP
        - sklearn.cluster
    Logs: clusters and representatives.

    One descriptor per survivor: SOAP centred on A's binding atom then B's, in that order, normalised, so two
    survivors related by a symmetry of the slab coincide. Average-linkage clustering joins those closer than
    SAME_SOAP. Each cluster keeps its nearest member, its lowest, then the next lowest until per_cluster are kept.
    Nearest is the pair's site-graph distance with the in-plane distance as tiebreak; a survivor without a pair,
    from minima hopping, is placed by its A–B distance after every enumerated one.
    """
    per = int(project.decision("soap_clustering", "per_cluster"))
    energy = {r.candidate_id: r.energy_eV for r in energies}
    missing = [c.id for c in survivors if c.id not in energy]
    if missing:
        raise ValueError(f"no energy for {', '.join(missing)}")
    by_pair = {(p.site_A, p.site_B): p for p in pairs}           # every orientation of a pair is nearest as the pair
    if not survivors:
        log("soap_clustering", "no survivors to cluster")
        return {"clusters": [], "kept": []}
    structures = [artifacts.read(c.structure) for c in survivors]

    def nearest(k: int) -> Tuple[float, float, float]:
        c, atoms = survivors[k], structures[k]
        p = by_pair.get((c.site_A, c.site_B))
        if p:
            return (0.0, p.site_graph_distance, p.in_plane_distance_A)
        return (1.0, 0.0, geometry.min_distance(atoms, artifacts.fragment_indices(atoms, "A"), artifacts.fragment_indices(atoms, "B")))

    labels = _labels(_descriptors(structures))
    clusters, kept = [], []
    for label in sorted(set(labels), key=lambda lb: min(nearest(k) for k in range(len(survivors)) if labels[k] == lb)):
        members = sorted((k for k in range(len(survivors)) if labels[k] == label), key=nearest)
        by_energy = sorted(members, key=lambda k: energy[survivors[k].id])
        keep = list(dict.fromkeys([members[0], by_energy[0]]))
        for k in by_energy:
            if len(keep) >= per:
                break
            if k not in keep:
                keep.append(k)
        clusters.append(Cluster(id=len(clusters), members=[survivors[k].id for k in members], nearest=survivors[members[0]].id,
                                lowest=survivors[by_energy[0]].id))
        kept += keep
    kept_ids = [survivors[k].id for k in sorted(set(kept), key=lambda k: (nearest(k), energy[survivors[k].id]))]
    for c in clusters:
        log("soap_clustering", f"cluster {c.id}: {len(c.members)} member(s), nearest {c.nearest}, lowest {c.lowest} "
                               f"({energy[c.lowest]:.4f} eV); members {', '.join(c.members)}")
    log("soap_clustering", f"{len(survivors)} survivors, {len(clusters)} clusters, {len(kept_ids)} kept, up to {per} per cluster: "
                           + ", ".join(kept_ids))
    return {"clusters": clusters, "kept": kept_ids}


def _descriptors(structures) -> np.ndarray:
    from dscribe.descriptors import SOAP as DSOAP
    species = sorted({s for a in structures for s in a.get_chemical_symbols()})
    soap = DSOAP(species=species, periodic=True, sparse=False, **SOAP)
    rows = []
    for atoms in structures:
        work = atoms.copy()
        work.pbc = True
        centres = [artifacts.binding_index(atoms, f) for f in ("A", "B")]      # the atoms the human's bond names, not the lowest
        x = soap.create(work, centers=centres).ravel()
        rows.append(x / (np.linalg.norm(x) or 1.0))
    return np.array(rows)


def _labels(x: np.ndarray) -> List[int]:
    if len(x) == 1:
        return [0]
    from sklearn.cluster import AgglomerativeClustering
    return [int(k) for k in AgglomerativeClustering(n_clusters=None, distance_threshold=SAME_SOAP, linkage="average").fit(x).labels_]


@traced(step="8", tool="ranking")
def ranking(kept: List[str], cards: List[DescriptorCard], flags: List[DoubtFlag], pairs: List[Pair]) -> List[RankedCandidate]:
    """Rank the kept final states nearest first, then by energy, with doubt and verdicts on each card, for the human to pick up to five; record the choice and reason in the case bank.

    Board steps: 8. Status: core. Lane: laptop. Allowed roles: solution-planner.

    Inputs:
        kept: list[str]
        cards: list[DescriptorCard]
        flags: list[DoubtFlag]
        pairs: list[Pair]
    Outputs:
        ranked: list[RankedCandidate]
    Checks:
        - the human picks; the tool never drops a candidate
    Thresholds:
        shortlist_size: open: team decision: up to five, or fewer
    Wraps:
        - none
    Logs: the order shown; the human's choice and reason, to lessons.md.

    Nearest is read from each card, measured on the relaxed structure: site-graph distance, then A–B distance,
    then energy. The doubt shown is the escalating flag when one fires, the committee's otherwise; a committee
    that measured no spread on a candidate says not measured, never 0. The choice and its reason reach the case
    bank at the pick checkpoint, recorded by fragplace.runtime.checkpoints.
    """
    shortlist = int(project.decision("ranking", "shortlist_size"))
    by_card = {c.candidate_id: c for c in cards}
    missing = [k for k in kept if k not in by_card]
    if missing:
        raise ValueError(f"no card for {', '.join(missing)}")
    by_pair = {p.candidate_id: p for p in pairs}
    unmeasured = {f.candidate_id for f in flags if f.trigger == "unmeasured"}

    def doubt(cid: str) -> Optional[DoubtFlag]:
        mine = [f for f in flags if f.candidate_id == cid]
        return next((f for f in mine if f.escalate), None) or next((f for f in mine if f.trigger == "disagreement"), None)

    def key(cid: str):
        c = by_card[cid]
        return (c.site_graph_distance if c.site_graph_distance is not None else 10 ** 6, c.AB_distance_A or 0.0,
                c.energy_eV if c.energy_eV is not None else float("inf"))

    ranked = []
    for rank, cid in enumerate(sorted(kept, key=key), 1):
        c, f, p = by_card[cid], doubt(cid), by_pair.get(re.sub(r"o\d+$", "", cid))   # A002-B015o1 is an orientation of pair A002-B015
        reason = (f"site-graph {c.site_graph_distance}, A–B {c.AB_distance_A:.2f} Å, E {c.energy_eV:.4f} eV, {c.site_label}"
                  + (f"; enumerated {p.in_plane_distance_A:.2f} Å apart" if p else "")
                  + (f"; doubt {f.trigger}, spread " + ("not measured" if cid in unmeasured else f"{f.committee_spread_eV:.3f} eV")
                     + (", escalated" if f.escalate else "") if f else ""))
        ranked.append(RankedCandidate(candidate_id=cid, rank=rank, site_graph_distance=c.site_graph_distance if c.site_graph_distance is not None else -1,
                                      energy_eV=c.energy_eV if c.energy_eV is not None else float("nan"), doubt=f, reason=reason))
    log("ranking", f"order shown, the human picks up to {shortlist}: " + ", ".join(r.candidate_id for r in ranked))
    return ranked
