"""The tools as the agents call them: by campaign name and candidate id, never by record; each answers with a
summary an LLM can read. mcp/server.py publishes these under the registry's names.

The records stay on disk in runs/<campaign>/, and these functions reach the same Campaign handlers as the
deterministic rollout of pipeline.py, so both paths compute the same thing. A call that cannot run says why
instead of raising: a checkpoint the human has not passed comes back with the command the human runs, an open
decision with its key and meaning for the planner to ask the human about, a missing earlier step with the tool
that makes it. A choice an agent makes, an order, a potential, a protocol, a review, travels as an argument and
lands in the trace under the agent's name. A step whose results the human already passed at a checkpoint is not
run again: a new value then means a new campaign.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..errors import FragPlaceError, OpenDecision
from ..registry.agents import AGENTS
from ..registry.tools import BY_NAME
from ..runtime import artifacts, checkpoints, project
from ..runtime.journal import default_root
from ..schemas.records import (Candidate, DescriptorCard, DoubtFlag, FinalState, ForceScreen, GateResult, LiteratureValue, Pair, RankedCandidate,
                               RelaxationResult, SiteEnumeration, StructureRef)
from ..tools import get as tool
from .campaign import DUE_WHEN, Campaign, briefing, due_checkpoint

# The artifacts in the order the steps make them, and the tool that makes each one.
MADE_BY: List[Tuple[str, str]] = [
    ("retrieval", "structure_retrieval"), ("protocol_proposed", "calculation_protocol"), ("mlip", "mlip_selection"),
    ("sites", "site_enumeration"), ("pairs", "pair_enumeration"), ("placed", "adsorbate_placement"), ("screens", "pull_force_screen"),
    ("relaxed", "relaxation"), ("gates", "anomaly_filter"), ("kept", "soap_clustering"), ("flags", "uncertainty_estimation"),
    ("ranked", "ranking"), ("final_states", "reference_energies"), ("report", "report"),
]
NOTE_CHARS, EVIDENCE_CHARS = 300, 6000   # a status stays far below what Claude Code accepts from one tool; the rest is in the files
DOWNSTREAM = {"pairs": ["A_base"], "screens": ["queue", "order", "cards_placed"], "relaxed": ["slab_relaxed"], "gates": ["cards"],
              "kept": ["clusters"], "ranked": ["cards_kept"]}


def root() -> Path:
    return default_root()


def approve_command(campaign: str, checkpoint: str) -> str:
    chosen = {"approve settings": " [--chosen lit:<index> ...]", "review flagged cases": " [--chosen <id> ... to keep only these]",
              "pick up to five final states": " --chosen <id> ..."}.get(checkpoint, "")
    return f'fragplace approve {campaign} "{checkpoint}" --reason "..." --who <name>{chosen}'


def _call(campaign: str, tool_name: str, needs: Tuple[str, ...], makes: Optional[str], body: Callable[[Campaign], Dict[str, Any]]) -> Dict[str, Any]:
    """Run one agent-facing call: the campaign exists, the tool's checkpoint gate has passed, the steps it needs have
    run, its results are not ones the human already passed on; then the body, with typed failures turned into answers."""
    c = Campaign(root(), campaign)
    if "inputs" not in c.data:
        return {"blocked": f"campaign {campaign} has no inputs", "human_runs": f"fragplace init {campaign} --example, or --slab, --adsorbate, "
                                                                              "--initial-state and --bond for supplied structures"}
    passed = {x.checkpoint for x in checkpoints.passed(c.run.dir)}
    gate = BY_NAME[tool_name].checkpoint_gate if tool_name in BY_NAME else None
    if gate and gate not in passed:
        due = due_checkpoint(c)
        return {"blocked": f"{tool_name} needs the '{gate}' checkpoint, which the human has not passed",
                "checkpoint_due": due, "human_runs": approve_command(campaign, due) if due else None}
    missing = [k for k in needs if k not in c.data]
    if missing:
        made = dict(MADE_BY)
        return {"blocked": "an earlier step has not run", "run_first": [made.get(k, k) for k in missing]}
    if makes:
        keys = [k for k, _ in MADE_BY]
        later = keys[keys.index(makes):]
        reviewed = [cp for cp, key in DUE_WHEN.items() if cp in passed and key in later and key in c.data]
        if reviewed:
            return {"blocked": f"the human passed '{reviewed[0]}' on results this step would replace; a new value means a new campaign"}
        for k in later:
            for key in [k] + DOWNSTREAM.get(k, []):
                c.data.pop(key, None)
    try:
        return body(c)
    except OpenDecision as e:
        return {"open_decision": str(e), "ask_human": "ask the human for each value, with the meaning shown; record each with: "
                f"fragplace decide {campaign} <key> '<value as JSON>' --who <name> --reason '...'",
                "meanings": {k: _meaning(k) for k in project.missing_decisions(c.settings(locked=False))}}
    except FragPlaceError as e:
        return {"error": type(e).__name__, "message": str(e)}
    finally:
        c.run.step = None


def _meaning(key: str) -> str:
    tool_name, name = key.split(".", 1)
    return BY_NAME[tool_name].thresholds[name]


def _due(c: Campaign) -> Dict[str, Any]:
    due = due_checkpoint(c)
    return {"checkpoint_due": due, "human_runs": approve_command(c.run.campaign, due)} if due else {}


# ---- the campaign as a whole
def campaign_status(campaign: str) -> Dict[str, Any]:
    """Where the campaign stands: what has run, the next tool, the checkpoint due with what the human looks at and
    the command the human runs, the open decisions still missing, the notes the agents left."""
    c = Campaign(root(), campaign)
    if "inputs" not in c.data:
        return {"campaign": campaign, "inputs": False, "human_runs": f"fragplace init {campaign} --example"}
    s = c.settings(locked=False)
    passed = [x.checkpoint for x in checkpoints.passed(c.run.dir)]
    done = [t for k, t in MADE_BY if k in c.data]
    nxt = next((t for k, t in MADE_BY if k not in c.data), None)
    gate = BY_NAME[nxt].checkpoint_gate if nxt else None
    due = due_checkpoint(c)
    out = {"campaign": campaign, "system": f"{s.adsorbate}* -> {s.product[0]}* + {s.product[1]}* on {s.metal}({s.facet})",
           "project_md": str(c.run.dir / "PROJECT.md"), "settings_locked": s.locked, "potential": c.data.get("mlip", {}).get("calculator"),
           "done": done, "passed_checkpoints": passed,
           "next": f"wait: the human passes '{gate}'" if gate and gate not in passed else nxt,
           "checkpoint_due": due, "notes_total": len(c.data.get("notes", [])),
           "notes": [{"author": n["author"], "text": n["text"][:NOTE_CHARS] + (" …" if len(n["text"]) > NOTE_CHARS else "")}
                     for n in c.data.get("notes", [])[-10:]],
           "full_notes_and_trace": str(c.run.dir / "trace.jsonl")}
    if due:
        evidence = briefing(root(), campaign, due)
        if len(evidence) > EVIDENCE_CHARS:
            evidence = evidence[:EVIDENCE_CHARS] + f"\n… cut here; the rest is in {c.run.dir}"
        out.update({"human_runs": approve_command(campaign, due), "evidence": evidence})
    if not s.locked:
        out["open_decisions_missing"] = {k: _meaning(k) for k in project.missing_decisions(s)}
    return out


def note(campaign: str, author: str, text: str) -> Dict[str, Any]:
    """An agent's decision or review with its reason, into the trace and the report under the agent's name."""
    if author not in AGENTS:
        return {"error": "ValueError", "message": f"author {author!r} is not an agent of the roster: {', '.join(AGENTS)}"}
    c = Campaign(root(), campaign)
    c.note(author, text)
    return {"noted": len(c.data["notes"]), "author": author}


# ---- prompt and 1: published values, the cleaved fragments and the cell, the proposed lock
def literature_lookup(campaign: str, quantity: str = "E_ads", sources: Optional[List[str]] = None) -> Dict[str, Any]:
    """Published values for the human to verify, each with its source; never a value from memory."""
    def body(c: Campaign):
        s = c.settings(locked=False)
        try:
            found = tool("literature_lookup")(f"{s.metal}({s.facet}) {s.adsorbate}", quantity, sources or ["catalysis_hub"])
        except LookupError as e:
            return {"found": [], "message": str(e)}
        values = c.many("literature", LiteratureValue)
        values += [v for v in found if (v.source, v.quantity, v.value) not in {(w.source, w.quantity, w.value) for w in values}]
        c.put("literature", values)
        return {"values": [{"index": k, **v.model_dump(include={"quantity", "value", "unit", "functional", "site", "source"})}
                           for k, v in enumerate(values)],
                "verify": "the human verifies a value at approve settings with --chosen lit:<index>; check 7 uses only a verified one"}
    return _call(campaign, "literature_lookup", (), None, body)


def structure_retrieval(campaign: str) -> Dict[str, Any]:
    """Cleave the named bond into A, which keeps the binding atom, and B; choose the surface cell."""
    def body(c: Campaign):
        c.run.step = "1"
        c.retrieval()
        r = c.data["retrieval"]
        frag = {k: artifacts.read(StructureRef.model_validate(r[k])).get_chemical_formula() for k in ("fragment_A", "fragment_B")}
        slab = artifacts.read(StructureRef.model_validate(r["structures"][0]))
        return {"fragment_A": frag["fragment_A"], "fragment_B": frag["fragment_B"], "cell_repeat": r["cell_repeat"],
                "cell_A": [round(float(x), 2) for x in slab.cell.lengths()[:2]], "atoms_in_cell": len(slab)}
    return _call(campaign, "structure_retrieval", (), "retrieval", body)


def calculation_protocol(campaign: str, protocol: str, protocol_reason: str, physics_choices: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Propose the lock: the inputs' settings, the human's physics choices and the protocol the computational
    chemist picked, with its reason. Every open decision must be set; the human locks at approve settings."""
    def body(c: Campaign):
        c.run.step = "1"
        s = c.settings(locked=False)
        if s.locked:
            return {"blocked": "PROJECT.md is locked; a new value means a new campaign"}
        out = c.propose(c.prepared(s), physics_choices or {}, protocol, protocol_reason)
        return {"proposed": out.model_dump(include={"functional", "pseudopotential_family", "cutoff_eV", "kmesh", "smearing", "sigma_eV", "layers",
                                                    "cell_repeat", "protocol", "protocol_reason", "convergence_target_meV"}),
                "project_md": str(c.run.dir / "PROJECT.md"), **_due(c)}
    return _call(campaign, "calculation_protocol", ("retrieval",), "protocol_proposed", body)


# ---- 1*: the potential
def mlip_selection(campaign: str, reason: str, choose: Optional[str] = None) -> Dict[str, Any]:
    """Benchmark the locked candidate potentials on the supplied inputs. The mlip-specialist may choose another
    member of the committee than the smallest error, and states why; PROJECT.md wins when the human locked one."""
    def body(c: Campaign):
        c.run.step = "1*"
        c.mlip()
        m = c.data["mlip"]
        if choose and choose != m["calculator"]:
            if c.settings().mlip:
                return {"error": "SettingsMismatch", "message": f"PROJECT.md locks the potential {c.settings().mlip}"}
            if choose not in m["committee"]:
                return {"error": "ValueError", "message": f"{choose} is not in the committee {m['committee']}"}
            m["calculator"], m["reason"] = choose, "chosen by the mlip-specialist"
            c.put("mlip", m)
        c.note("mlip-specialist", f"potential {m['calculator']}: {reason}")
        return {"benchmark": m["benchmark"], "smallest_error": m["chosen"], "using": m["calculator"], "committee": m["committee_used"], **_due(c)}
    return _call(campaign, "mlip_selection", ("retrieval",), "mlip", body)


# ---- 2, 3.2 and the placement of B
def site_enumeration(campaign: str) -> Dict[str, Any]:
    """Every symmetry-inequivalent site of the selected cell, fcc and hcp apart, counted and checked by Burnside."""
    def body(c: Campaign):
        c.run.step = "2"
        c.sites()
        e = c.one("sites", SiteEnumeration)
        reps = sorted({s.orbit for s in e.sites})
        return {"count": e.count, "burnside_count": e.burnside_count, "pymatgen_baseline": e.baseline_count, "symmetry": e.symmetry_group,
                "sites_in_cell": e.total_sites,
                "inequivalent": [{"site": r, "label": e.sites[r].label, "group": e.sites[r].point_group, "coordination": e.sites[r].coordination,
                                  "atom_beneath": e.sites[r].atom_beneath, "copies": sum(1 for s in e.sites if s.orbit == r)} for r in reps]}
    return _call(campaign, "site_enumeration", ("retrieval", "mlip"), "sites", body)


def pair_enumeration(campaign: str) -> Dict[str, Any]:
    """The symmetry-distinct pairs, A at its initial-state site and B inside [1.5 d, upper] Å, nearest first."""
    def body(c: Campaign):
        c.run.step = "3.2"
        c.pairs()
        e = c.one("sites", SiteEnumeration)
        pairs = c.many("pairs", Pair)
        a = c.one("A_base", Candidate).site_A
        return {"A_site": {"site": a, "label": e.sites[a].label}, "count": len(pairs),
                "window_A": [round(x, 3) for x in pairs[0].window_A] if pairs else None, "d_bond_A": round(pairs[0].d_bond_A, 3) if pairs else None,
                "pairs": [{"id": p.candidate_id, "B_site": e.sites[p.site_B].label, "site_graph_distance": p.site_graph_distance,
                           "in_plane_A": round(p.in_plane_distance_A, 2)} for p in pairs]}
    return _call(campaign, "pair_enumeration", ("sites",), "pairs", body)


def adsorbate_placement(campaign: str) -> Dict[str, Any]:
    """B on the site of every pair, every orientation its site group allows, 2 Å up, displaced by the locked amplitude."""
    def body(c: Campaign):
        c.run.step = "4"
        c.place()
        return {"placed": [x.id for x in c.many("placed", Candidate)], "count": len(c.data["placed"])}
    return _call(campaign, "adsorbate_placement", ("pairs",), "placed", body)


# ---- 3.3, 3.4, 3.6
def pull_force_screen(campaign: str) -> Dict[str, Any]:
    """One force call per placed pair; a pull on B towards A above the threshold queues the pair last."""
    def body(c: Campaign):
        c.run.step = "3.3"
        c.screen()
        return {"queue": [{"id": x.candidate_id, "force_on_B_towards_A_eV_per_A": round(x.force_on_B_along_AB_eV_per_A, 3), "flagged": x.flagged}
                          for x in c.many("screens", ForceScreen)]}
    return _call(campaign, "pull_force_screen", ("placed",), "screens", body)


def descriptor_card(campaign: str, candidate_ids: Optional[List[str]] = None, stage: str = "placed") -> Dict[str, Any]:
    """The text cards of candidates, the only view of geometry an agent gets: stage placed, before relaxation, or
    relaxed, with the gate's verdicts once anomaly_filter has run. All candidates when no ids are given."""
    def body(c: Campaign):
        c.run.step = "3.4" if stage == "placed" else "5"
        sites = c.one("sites", SiteEnumeration)
        if stage == "placed":
            pool = {x.id: x for x in c.many("placed", Candidate)}
            gates: Dict[str, GateResult] = {}
        elif stage == "relaxed":
            if "relaxed" not in c.data:
                return {"blocked": "nothing is relaxed yet", "run_first": ["relaxation"]}
            pool = c.relaxed_candidates()
            gates = {g.candidate_id: g for g in c.many("gates", GateResult)}
        else:
            return {"error": "ValueError", "message": "stage is placed or relaxed"}
        ids = candidate_ids or list(pool)
        unknown = [k for k in ids if k not in pool]
        if unknown:
            return {"error": "ValueError", "message": f"unknown candidates {unknown}; known: {list(pool)}"}
        return {"cards": {k: tool("descriptor_card")(pool[k], gates.get(k), sites).text() for k in ids}}
    return _call(campaign, "descriptor_card", ("placed",), None, body)


def minima_hopping(campaign: str, n_hops: int = 5) -> Dict[str, Any]:
    """The alternative generator: minima hopping with the chosen potential from the first queued pair."""
    def body(c: Campaign):
        c.run.step = "3.6"
        c.data.setdefault("options", {})["n_hops"] = int(n_hops)
        c.hopping()
        return {"minima": [{"id": x.id, "energy_eV": x.structure.energy_eV} for x in c.many("hopped", Candidate)]}
    return _call(campaign, "minima_hopping", ("screens",), None, body)


# ---- 4 to 8 and the solution
def relaxation(campaign: str, order: Optional[List[str]] = None, reason: str = "", decided_by: str = "surface-chemist") -> Dict[str, Any]:
    """Relax every placed pair with the chosen potential and the locked settings. order is the surface-chemist's
    ordering, first in the queue, the pull-force queue after it; no candidate is ever dropped."""
    def body(c: Campaign):
        c.run.step = "4"
        placed = [x.id for x in c.many("placed", Candidate)]
        if order:
            unknown = [k for k in order if k not in placed]
            if unknown:
                return {"error": "ValueError", "message": f"unknown candidates {unknown}"}
            c.put("order", list(order))
            c.note(decided_by, f"relaxation order {', '.join(order)}, the queue after them: {reason}")
        c.relax()
        results = c.many("relaxed", RelaxationResult)
        return {"order": [x.id for x in c.ordered()], "slab_energy_eV": round(c.one("slab_relaxed", RelaxationResult).energy_eV, 4),
                "results": [{"id": r.candidate_id, "energy_eV": round(r.energy_eV, 4), "steps": r.steps, "converged": r.converged,
                             "cache_hit": r.cache_hit} for r in results]}
    return _call(campaign, "relaxation", ("screens",), "relaxed", body)


def anomaly_filter(campaign: str) -> Dict[str, Any]:
    """The gate on every relaxed pair: eleven checks, each with its measured value; a failing pair is never kept."""
    def body(c: Campaign):
        c.run.step = "5"
        c.gate()
        c.cards()
        gates = c.many("gates", GateResult)
        return {"passed": [g.candidate_id for g in gates if g.passed],
                "rejected": {g.candidate_id: [f"check {v.check_id} {v.name}{' ' + v.fragment if v.fragment else ''}: {v.reason}" for v in g.verdicts if not v.passed]
                             for g in gates if not g.passed},
                "not_checked": sorted({f"check {v.check_id} {v.name}: {v.reason}" for g in gates for v in g.verdicts if "not checked" in v.reason})}
    return _call(campaign, "anomaly_filter", ("relaxed",), "gates", body)


def soap_clustering(campaign: str) -> Dict[str, Any]:
    """Cluster the survivors by SOAP; keep the nearest and the lowest per cluster; nearest first."""
    def body(c: Campaign):
        c.run.step = "6"
        c.cluster()
        return {"clusters": c.data["clusters"], "kept": c.data["kept"]}
    return _call(campaign, "soap_clustering", ("gates",), "kept", body)


def uncertainty_estimation(campaign: str) -> Dict[str, Any]:
    """Committee doubt on every kept state; magnetic metals and unseen chemistry always escalate. The
    mlip-specialist reads the flags and leaves its decision, trust, repair or escalate, as a note."""
    def body(c: Campaign):
        c.run.step = "7"
        c.doubt()
        flags = c.many("flags", DoubtFlag)
        return {"flags": [f.model_dump() for f in flags], "escalated": [f"{f.candidate_id} {f.trigger}" for f in flags if f.escalate], **_due(c)}
    return _call(campaign, "uncertainty_estimation", ("kept",), "flags", body)


def ranking(campaign: str) -> Dict[str, Any]:
    """The kept states the human did not drop at the review, nearest first, then by energy, each with its card."""
    def body(c: Campaign):
        c.run.step = "8"
        c.cards_kept()
        c.rank()
        cards = {x.candidate_id: x.text() for x in c.many("cards_kept", DescriptorCard)}
        return {"ranked": [{"rank": r.rank, "id": r.candidate_id, "reason": r.reason, "card": cards[r.candidate_id]}
                           for r in c.many("ranked", RankedCandidate)], **_due(c)}
    return _call(campaign, "ranking", ("flags",), "ranked", body)


def reference_energies(campaign: str) -> Dict[str, Any]:
    """E(FS ∞) of each state the human picked, each fragment alone on the slab, and the lateral interaction."""
    def body(c: Campaign):
        c.run.step = "solution"
        c.references()
        return {"final_states": [f.model_dump() for f in c.many("final_states", FinalState)]}
    return _call(campaign, "reference_energies", ("ranked",), "final_states", body)


def report(campaign: str) -> Dict[str, Any]:
    """Write report.md and report.json, with the agents' notes at the end; call again after the critic's note."""
    def body(c: Campaign):
        c.run.step = "solution"
        c.report()
        r = c.data["report"]
        return {"report_md": str(c.run.dir / "report.md"), "final_states": r["final_states"], "rejected": len(r["rejected"]),
                "recombination_rate": r["recombination_rate"], "by_shell": r["recombination_rate_by_shell"], **_due(c)}
    return _call(campaign, "report", ("final_states",), None, body)


def dft_single_points(campaign: str) -> Dict[str, Any]:
    """Extension: DFT single points on the picked states; not available until the team decides D2."""
    return {"unavailable": "dft_single_points is an extension: it needs a DFT code and compute, decision D2"}


def active_learning(campaign: str) -> Dict[str, Any]:
    """Extension: DFT labels to a fine-tuned potential; not available until the team decides D2."""
    return {"unavailable": "active_learning is an extension: it needs DFT labels, decision D2"}


FUNCTIONS: Dict[str, Callable[..., Dict[str, Any]]] = {name: globals()[name] for name in list(BY_NAME) + ["campaign_status", "note"]}
