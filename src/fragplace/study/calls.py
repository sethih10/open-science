"""The tools as the agents call them: by study name and candidate id, never by record; each answers with a
summary an LLM can read. mcp/server.py publishes these under the registry's names.

The records stay on disk in runs/<study>/, and these functions reach the same Study handlers as the test harness
of rollout.py, so both paths compute the same thing. A call that cannot run says why instead of raising: a
checkpoint the human has not passed comes back with the question box to ask, an open decision with its key and
meaning, a missing earlier step with the tool that makes it. A choice an agent makes, an order, a potential, a
protocol, a review, travels as an argument and lands in the trace under the agent's name. A step whose results
the human already passed at a checkpoint is not run again: a new value then means a new study. After every step
that ran, code writes the step's geometry files and its block of summary.md, and the answer carries both.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..errors import FragPlaceError, OpenDecision
from ..registry.agents import AGENTS
from ..registry.steps import PIPELINE
from ..registry.tools import BY_NAME, open_decisions, runs_dft
from ..runtime import artifacts, checkpoints, project
from ..runtime.journal import default_root, log
from ..schemas.records import (Candidate, DescriptorCard, DoubtFlag, FinalState, ForceScreen, GateResult, LiteratureValue, Pair, RankedCandidate,
                               RelaxationResult, SiteEnumeration, StructureRef)
from ..tools import get as tool
from . import summary, views
from .human import checkpoint_box, decision_question, interview_boxes, verify_box
from .store import DUE_WHEN, LITERATURE_SOURCES, QUANTITY_OF, Study, due_checkpoint

# The artifacts in the order the steps make them, and the tool that makes each one.
MADE_BY: List[Tuple[str, str]] = [
    ("retrieval", "structure_retrieval"), ("protocol_proposed", "calculation_protocol"), ("mlip", "mlip_selection"),
    ("sites", "site_enumeration"), ("pairs", "pair_enumeration"), ("placed", "adsorbate_placement"), ("screens", "pull_force_screen"),
    ("gates_before", "anomaly_filter"), ("relaxed", "relaxation"), ("gates", "anomaly_filter"), ("kept", "soap_clustering"), ("flags", "uncertainty_estimation"),
    ("ranked", "ranking"), ("final_states", "reference_energies"), ("report", "report"),
]
NOTE_CHARS = 300   # a status stays far below what Claude Code accepts from one tool; the rest is in the files
DOWNSTREAM = {"pairs": ["A_base"], "screens": ["queue", "order", "cards_placed"], "relaxed": ["slab_relaxed"], "gates": ["cards"],
              "kept": ["clusters"], "ranked": ["cards_kept"]}
NOT_DONE = ("blocked", "error", "open_decision", "unavailable")
NEW_STUDY = ("ask the human for the input files, then run: fragplace init {study} --slab <file> --adsorbate <file> --initial-state <file> "
             "--bond <i,j>, adding --fragment-a and --fragment-b for the two fragments in vacuum when supplied; or fragplace init {study} --example")


def root() -> Path:
    return default_root()


def _ask(c: Study, checkpoint: Optional[str]) -> Dict[str, Any]:
    """What the orchestrator asks at a due checkpoint: the question box, ready for AskUserQuestion."""
    if not checkpoint:
        return {}
    return {"checkpoint_due": checkpoint, "ask_human": checkpoint_box(c, checkpoint),
            "how": "show the human the step's pictures with show_structures, then ask this box as given; the answer is recorded by code"}


def _call(study: str, tool_name: str, needs: Tuple[str, ...], makes: Optional[str], body: Callable[[Study], Dict[str, Any]]) -> Dict[str, Any]:
    """Run one agent-facing call: the study exists, the tool's checkpoint gate has passed, the steps it needs have
    run, its results are not ones the human already passed on; then the body, with typed failures turned into
    answers, and the step's geometry files and summary block written after it."""
    c = Study(root(), study)
    if "inputs" not in c.data:
        return {"blocked": f"study {study} has no inputs", "next": NEW_STUDY.format(study=study)}
    passed = {x.checkpoint for x in checkpoints.passed(c.run.dir)}
    gate = BY_NAME[tool_name].checkpoint_gate if tool_name in BY_NAME else None
    if gate and gate not in passed:
        return {"blocked": f"{tool_name} needs the '{gate}' checkpoint, which the human has not passed", **_ask(c, due_checkpoint(c))}
    missing = [k for k in needs if k not in c.data]
    if missing:
        made = dict(MADE_BY)
        return {"blocked": "an earlier step has not run", "run_first": [made.get(k, k) for k in missing]}
    if makes:
        keys = [k for k, _ in MADE_BY]
        later = keys[keys.index(makes):]
        reviewed = [cp for cp, key in DUE_WHEN.items() if cp in passed and key in later and key in c.data]
        if reviewed:
            return {"blocked": f"the human passed '{reviewed[0]}' on results this step would replace; a new value means a new study"}
        for k in later:
            for key in [k] + DOWNSTREAM.get(k, []):
                c.data.pop(key, None)
    try:
        out = body(c)
        if not any(k in out for k in NOT_DONE):
            key = f"{tool_name}_before" if out.get("stage") == "before_relaxation" else tool_name
            out.update(_outputs(c, key, c.run.step or BY_NAME[tool_name].board_steps[0], out))
        return out
    except OpenDecision as e:
        named = [k for k in open_decisions() if k in str(e)]       # a DFT lock asks what PROJECT.md, before it, does not yet need
        missing = named + [k for k in project.missing_decisions(c.settings(locked=False)) if k not in named]
        return {"open_decision": str(e), "ask_human": {"questions": [decision_question(study, k, _meaning(k)) for k in missing[:4]]},
                "how": "add two to four values from AGENTS.md or the protocol table to each question, each with its source, and ask; "
                       "the human may write another under Other; the answer is recorded by code. Ask again for the rest."}
    except FragPlaceError as e:
        return {"error": type(e).__name__, "message": str(e)}
    finally:
        c.run.step = None


def _outputs(c: Study, tool_name: str, step: str, out: Dict[str, Any]) -> Dict[str, Any]:
    """The step's geometry files and its block of summary.md; a picture that fails to draw never fails the step."""
    try:
        files = views.after_step(c, tool_name)
    except Exception as e:  # noqa: BLE001 - the pictures are for the human; the result stands without them
        files = []
        log(tool_name, f"geometry files not written: {type(e).__name__}: {e}")
    block = summary.write(c, tool_name, step, out, files)
    return {k: v for k, v in (("summary", block), ("files", files)) if v}


def _meaning(key: str) -> str:
    tool_name, name = key.split(".", 1)
    return BY_NAME[tool_name].thresholds[name]


def _due(c: Study) -> Dict[str, Any]:
    return _ask(c, due_checkpoint(c))


# ---- the study as a whole
def study_status(study: str) -> Dict[str, Any]:
    """Where the study stands: what has run, the next tool, the question box to ask when a checkpoint is due, the
    interview and the open decisions still missing, the last block of the summary, the notes the agents left."""
    c = Study(root(), study)
    if "inputs" not in c.data:
        return {"study": study, "inputs": False, "next": NEW_STUDY.format(study=study)}
    s = c.settings(locked=False)
    passed = [x.checkpoint for x in checkpoints.passed(c.run.dir)]
    done = [t for k, t in MADE_BY if k in c.data]
    nxt = next((t for k, t in MADE_BY if k not in c.data), None)
    gate = BY_NAME[nxt].checkpoint_gate if nxt else None
    brief = summary.full(c)
    step = next((p for p in PIPELINE if nxt in p.tools), None) if nxt else None
    out = {"study": study, "system": f"{s.adsorbate}* -> {s.product[0]}* + {s.product[1]}* on {s.metal}({s.facet})",
           "next_step": {"step": step.key, "tools": list(step.tools), "agents": list(step.agents), "checkpoint_after": step.checkpoint} if step else None,
           "project_md": str(c.run.dir / "PROJECT.md"), "settings_locked": s.locked, "potential": c.data.get("mlip", {}).get("calculator"),
           "done": done, "passed_checkpoints": passed,
           "next": f"wait: the human passes '{gate}'" if gate and gate not in passed else nxt or "nothing: the study is complete",
           "summary_md": str(c.run.dir / "summary.md"), "last_summary": brief.rsplit("\n## ", 1)[-1][:1500] if brief else "",
           "notes_total": len(c.data.get("notes", [])),
           "notes": [{"author": n["author"], "text": n["text"][:NOTE_CHARS] + (" …" if len(n["text"]) > NOTE_CHARS else "")}
                     for n in c.data.get("notes", [])[-10:]],
           "full_notes_and_trace": str(c.run.dir / "trace.jsonl"), **_due(c)}
    if not s.locked:
        out["open_decisions_missing"] = {k: _meaning(k) for k in project.missing_decisions(s)}
        boxes = interview_boxes(c)
        if boxes:
            out["interview_unanswered"] = boxes
    return out


def note(study: str, author: str, text: str) -> Dict[str, Any]:
    """An agent's decision or review with its reason, into the trace and the report under the agent's name."""
    if author not in AGENTS:
        return {"error": "ValueError", "message": f"author {author!r} is not an agent of the roster: {', '.join(AGENTS)}"}
    c = Study(root(), study)
    c.note(author, text)
    return {"noted": len(c.data["notes"]), "author": author}


def show_structures(study: str, stage: str = "relaxed", candidate_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """Pictures and .xyz files of candidates at one stage, inputs, placed, relaxed, kept, ranked or final, for the
    human to look at before answering; open the returned PNG for the human. All candidates of the stage when no
    ids are given."""
    c = Study(root(), study)
    if "inputs" not in c.data:
        return {"blocked": f"study {study} has no inputs", "next": NEW_STUDY.format(study=study)}
    try:
        out = views.show(c, candidate_ids, stage)
    except (ValueError, KeyError) as e:
        return {"error": type(e).__name__, "message": str(e)}
    return {**out, "folder": str(c.run.dir), "open_with": f"code {c.run.dir / out['open']}"}


# ---- prompt and 1: published values, the cleaved fragments and the cell, the proposed lock
def literature_lookup(study: str, quantity: str = "E_ads", species: Optional[List[str]] = None, sources: Optional[List[str]] = None,
                      reported: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Published values for the human to verify, each with its source; never a value from memory. quantity is E_ads,
    reaction_energy or bond_length_d; species names AB, A, B or reaction, by default all that the quantity has. A
    value the literature-reader read in a paper goes in as reported, each with species, quantity, value, unit,
    functional, site and source, a DOI or URL; the source is then papers."""
    def body(c: Study):
        which = species or ([k for k, q in QUANTITY_OF.items() if q == quantity] if quantity != "bond_length_d" else ["AB"])
        named = [v.get("species") for v in reported or []]
        unknown = [k for k in which + [k for k in named if k is not None] if k not in c.species()]
        if unknown:
            return {"error": "ValueError", "message": f"species {unknown}; known: {', '.join(c.species())}"}
        if len(which) > 1 and None in named:
            return {"error": "ValueError", "message": f"the lookup covers {', '.join(which)}: each reported value names its species"}
        papers = [LiteratureValue.model_validate({"system": c.species()[name] if name else "", "unit": "eV",
                                                  **{k: x for k, x in v.items() if k not in ("species", "system")}})
                  for v, name in zip(reported or [], named)]
        new, why = c.lookup(quantity, which, sources or (["papers"] if papers else LITERATURE_SOURCES), papers or None)
        values = c.many("literature", LiteratureValue)
        box = verify_box(c, "bond_length_d") if quantity == "bond_length_d" and new else {}
        return {"found": len(new), "none_for": why, **({"ask_human": box} if box.get("questions") else {}),
                "values": [{"index": f"lit:{k}", "verified": v.verified_by_human, **v.model_dump(include={"quantity", "system", "value", "unit",
                                                                                                     "functional", "site", "source"})}
                           for k, v in enumerate(values)],
                "verify": "the human checks each value against its source: E_ads and reaction energies at approve settings, in the Verify "
                          "question of that box; a d found at 3.2 with a Verify question of its own. Only a checked value is used."}
    return _call(study, "literature_lookup", (), None, body)


def structure_retrieval(study: str) -> Dict[str, Any]:
    """Cleave the named bond into A, which keeps the binding atom, and B; choose the surface cell."""
    def body(c: Study):
        c.run.step = "1"
        c.retrieval()
        r = c.data["retrieval"]
        frag = {k: artifacts.read(StructureRef.model_validate(r[k])).get_chemical_formula() for k in ("fragment_A", "fragment_B")}
        slab = artifacts.read(StructureRef.model_validate(r["structures"][0]))
        return {"fragment_A": frag["fragment_A"], "fragment_B": frag["fragment_B"], "cell_repeat": r["cell_repeat"],
                "cell_A": [round(float(x), 2) for x in slab.cell.lengths()[:2]], "atoms_in_cell": len(slab)}
    return _call(study, "structure_retrieval", (), "retrieval", body)


def calculation_protocol(study: str, protocol: str, protocol_reason: str, physics_choices: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Propose the lock: the inputs' settings, the human's physics choices and the protocol the computational
    chemist picked, with its reason: mlip when the study runs no DFT, the default until dft_single_points is built,
    and then the answer shows only the run's settings. Every open decision the study needs must be set; the human
    locks at approve settings."""
    def body(c: Study):
        c.run.step = "1"
        s = c.settings(locked=False)
        if s.locked:
            return {"blocked": "PROJECT.md is locked; a new value means a new study"}
        out = c.propose(c.prepared(s), physics_choices or {}, protocol, protocol_reason)
        shown = {"cell_repeat", "cell_A", "force_threshold_eV_per_A", "gas_references", "protocol", "protocol_reason"}
        if runs_dft(protocol):
            shown |= {"functional", "dispersion", "pseudopotential_family", "cutoff_eV", "kmesh", "smearing", "sigma_eV", "layers", "convergence_target_meV"}
        proposed = out.model_dump(include=shown)
        if not runs_dft(protocol):
            proposed["gas_references"] = ", ".join(out.decisions.get("calculation_protocol.gas_references") or []) + ", computed with the potential chosen at 1*"
        return {"proposed": proposed, "dft": runs_dft(protocol),
                "origins": getattr(out, "origins", {}), "project_md": str(c.run.dir / "PROJECT.md"), **_due(c)}
    return _call(study, "calculation_protocol", ("retrieval",), "protocol_proposed", body)


# ---- 1*: the potential
def mlip_selection(study: str, reason: str, choose: Optional[str] = None) -> Dict[str, Any]:
    """Benchmark the locked candidate potentials on the supplied inputs. The mlip-specialist may choose another
    member of the committee than the smallest error, and states why; PROJECT.md wins when the human locked one."""
    def body(c: Study):
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
            c.gas()                     # the gas references follow the potential the study uses
        c.note("mlip-specialist", f"potential {m['calculator']}: {reason}")
        return {"benchmark": m["benchmark"], "best": m["chosen"], "using": m["calculator"], "committee": m["committee_used"], **_due(c)}
    return _call(study, "mlip_selection", ("retrieval",), "mlip", body)


def compute_plan(study: str, rules: Optional[Dict[str, Dict[str, Any]]] = None, reason: Optional[str] = None) -> Dict[str, Any]:
    """Without rules, the estimate: the seconds per force call of the chosen potential, measured once on the selected
    cell with the adsorbate, and per heavy step the minutes per item, the total when the items are known and the lane
    the code's table recommends. With rules and a reason, the hpc-specialist's proposal, one rule per heavy tool:
    lane worker, batch or auto, batch_above_min, cpus, mem_GB, time HH:MM:SS, workers, and partition when needed;
    checked, recorded as the study's compute plan and shown in the approve-the-plan box. Refused once that box has
    passed."""
    def body(c: Study):
        c.run.step = "1*"
        if rules is not None:
            if "approve the plan" in {x.checkpoint for x in checkpoints.passed(c.run.dir)}:
                return {"blocked": "the human passed 'approve the plan'; the compute plan no longer changes, and a new plan means a new study"}
            if not (reason or "").strip():
                return {"error": "ValueError", "message": "a proposal needs a reason: one sentence per rule, from the estimate and the decision table"}
        try:
            out = c.compute(rules)
        except ValueError as e:
            return {"error": "ValueError", "message": f"compute plan refused: {e}"}
        answer = {"timing": out["timing"], "estimates": out["estimates"], "never": out["never"]}
        if rules is not None:
            plan = {"rules": out["rules"], "reason": reason.strip(), "estimates": out["estimates"]}
            c.put("compute_plan", plan)
            c.note("hpc-specialist", "compute plan: " + "; ".join(f"{k} {v}" for k, v in summary.plan_rows(c.data) if k in plan["rules"]) + f". Why: {plan['reason']}")
            answer.update(proposed=out["rules"], reason=plan["reason"], warnings=out["warnings"])
        elif "compute_plan" in c.data:
            answer.update(proposed=c.data["compute_plan"]["rules"], reason=c.data["compute_plan"]["reason"])
        return {**answer, **_due(c)}
    return _call(study, "compute_plan", ("retrieval", "mlip"), None, body)


# ---- 2, 3.2 and the placement of B
def site_enumeration(study: str) -> Dict[str, Any]:
    """Every symmetry-inequivalent site of the selected cell, fcc and hcp apart, counted and checked by Burnside."""
    def body(c: Study):
        c.run.step = "2"
        c.sites()
        e = c.one("sites", SiteEnumeration)
        reps = sorted({s.orbit for s in e.sites})
        return {"count": e.count, "burnside_count": e.burnside_count, "pymatgen_baseline": e.baseline_count, "symmetry": e.symmetry_group,
                "sites_in_cell": e.total_sites,
                "inequivalent": [{"site": r, "label": e.sites[r].label, "group": e.sites[r].point_group, "coordination": e.sites[r].coordination,
                                  "atom_beneath": e.sites[r].atom_beneath, "copies": sum(1 for s in e.sites if s.orbit == r)} for r in reps]}
    return _call(study, "site_enumeration", ("retrieval", "mlip"), "sites", body)


def pair_enumeration(study: str) -> Dict[str, Any]:
    """The symmetry-distinct pairs, A at its initial-state site and B inside [1.5 d, upper] Å, nearest first."""
    def body(c: Study):
        c.run.step = "3.2"
        c.pairs()
        e = c.one("sites", SiteEnumeration)
        pairs = c.many("pairs", Pair)
        a = c.one("A_base", Candidate).site_A
        return {"A_site": {"site": a, "label": e.sites[a].label}, "count": len(pairs), "d_source": c.data.get("d", {}).get("source"),
                "window_A": [round(x, 3) for x in pairs[0].window_A] if pairs else None, "d_bond_A": round(pairs[0].d_bond_A, 3) if pairs else None,
                "pairs": [{"id": p.candidate_id, "B_site": e.sites[p.site_B].label, "site_graph_distance": p.site_graph_distance,
                           "in_plane_A": round(p.in_plane_distance_A, 2)} for p in pairs]}
    return _call(study, "pair_enumeration", ("sites",), "pairs", body)


def adsorbate_placement(study: str) -> Dict[str, Any]:
    """B on the site of every pair, every orientation its site group allows, 2 Å up, displaced by the locked amplitude."""
    def body(c: Study):
        c.run.step = "3.2"
        c.place()
        return {"placed": [x.id for x in c.many("placed", Candidate)], "count": len(c.data["placed"])}
    return _call(study, "adsorbate_placement", ("pairs",), "placed", body)


# ---- 3.3, 3.4, 3.6
def pull_force_screen(study: str) -> Dict[str, Any]:
    """One force call per placed pair; a pull on B towards A above the threshold queues the pair last."""
    def body(c: Study):
        c.run.step = "3.3"
        c.screen()
        return {"queue": [{"id": x.candidate_id, "force_on_B_towards_A_eV_per_A": round(x.force_on_B_along_AB_eV_per_A, 3), "flagged": x.flagged}
                          for x in c.many("screens", ForceScreen)]}
    return _call(study, "pull_force_screen", ("placed",), "screens", body)


def descriptor_card(study: str, candidate_ids: Optional[List[str]] = None, stage: str = "placed") -> Dict[str, Any]:
    """The text cards of candidates, the only view of geometry an agent gets: stage placed, before relaxation, or
    relaxed, with the gate's verdicts once anomaly_filter has run. All candidates when no ids are given."""
    def body(c: Study):
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
    return _call(study, "descriptor_card", ("placed",), None, body)


def minima_hopping(study: str, n_hops: int = 5) -> Dict[str, Any]:
    """The alternative generator: minima hopping with the chosen potential from the first queued pair."""
    def body(c: Study):
        c.run.step = "3.6"
        c.data.setdefault("options", {})["n_hops"] = int(n_hops)
        c.hopping()
        return {"minima": [{"id": x.id, "energy_eV": x.structure.energy_eV} for x in c.many("hopped", Candidate)]}
    return _call(study, "minima_hopping", ("screens",), None, body)


# ---- 4 to 8 and the solution
def relaxation(study: str, order: Optional[List[str]] = None, reason: str = "", decided_by: str = "surface-chemist") -> Dict[str, Any]:
    """Relax every placed pair with the chosen potential and the locked settings. order is the surface-chemist's
    ordering, first in the queue, the pull-force queue after it; no candidate is ever dropped."""
    def body(c: Study):
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
    return _call(study, "relaxation", ("screens", "gates_before"), "relaxed", body)


def anomaly_filter(study: str, stage: str = "after_relaxation") -> Dict[str, Any]:
    """The gate: eleven checks, each with its measured value; a failing pair is never kept. Before relaxation it runs
    on the placed structures with the checks the team listed in anomaly_filter.checks_before_relaxation, and a
    candidate that fails is not relaxed; after relaxation it runs every check on every relaxed pair."""
    if stage == "before_relaxation":
        def before(c: Study):
            c.run.step = "5"
            c.gate_before()
            gates = c.many("gates_before", GateResult)
            return {"stage": stage, "passed": [g.candidate_id for g in gates if g.passed],
                    "rejected": {g.candidate_id: [f"check {v.check_id} {v.name}: {v.reason}" for v in g.verdicts if not v.passed] for g in gates if not g.passed}}
        return _call(study, "anomaly_filter", ("screens",), "gates_before", before)
    if stage != "after_relaxation":
        return {"error": "ValueError", "message": "stage is before_relaxation or after_relaxation"}

    def body(c: Study):
        c.run.step = "5"
        c.gate()
        c.cards()
        gates = c.many("gates", GateResult)
        return {"passed": [g.candidate_id for g in gates if g.passed],
                "rejected": {g.candidate_id: [f"check {v.check_id} {v.name}{' ' + v.fragment if v.fragment else ''}: {v.reason}" for v in g.verdicts if not v.passed]
                             for g in gates if not g.passed},
                "not_checked": sorted({f"check {v.check_id} {v.name}: {v.reason}" for g in gates for v in g.verdicts if "not checked" in v.reason})}
    return _call(study, "anomaly_filter", ("relaxed",), "gates", body)


def soap_clustering(study: str) -> Dict[str, Any]:
    """Cluster the survivors by SOAP; keep the nearest and the lowest per cluster; nearest first."""
    def body(c: Study):
        c.run.step = "6"
        c.cluster()
        return {"clusters": c.data["clusters"], "kept": c.data["kept"]}
    return _call(study, "soap_clustering", ("gates",), "kept", body)


def uncertainty_estimation(study: str) -> Dict[str, Any]:
    """Committee doubt on every kept state; magnetic metals and unseen chemistry always escalate. The
    mlip-specialist reads the flags and leaves its decision, trust, repair or escalate, as a note."""
    def body(c: Study):
        c.run.step = "7"
        c.doubt()
        flags = c.many("flags", DoubtFlag)
        return {"flags": [f.model_dump() for f in flags], "escalated": [f"{f.candidate_id} {f.trigger}" for f in flags if f.escalate], **_due(c)}
    return _call(study, "uncertainty_estimation", ("kept",), "flags", body)


def ranking(study: str) -> Dict[str, Any]:
    """The kept states the human did not drop at the review, nearest first, then by energy, each with its card."""
    def body(c: Study):
        c.run.step = "8"
        c.cards_kept()
        c.rank()
        cards = {x.candidate_id: x.text() for x in c.many("cards_kept", DescriptorCard)}
        return {"ranked": [{"rank": r.rank, "id": r.candidate_id, "reason": r.reason, "card": cards[r.candidate_id]}
                           for r in c.many("ranked", RankedCandidate)], **_due(c)}
    return _call(study, "ranking", ("flags",), "ranked", body)


def reference_energies(study: str) -> Dict[str, Any]:
    """E(FS ∞) of each state the human picked, each fragment alone on the slab, and the lateral interaction."""
    def body(c: Study):
        c.run.step = "solution"
        c.references()
        return {"final_states": [f.model_dump() for f in c.many("final_states", FinalState)]}
    return _call(study, "reference_energies", ("ranked",), "final_states", body)


def report(study: str) -> Dict[str, Any]:
    """Write report.md and report.json, with the agents' notes at the end; call again after the critic's note."""
    def body(c: Study):
        c.run.step = "solution"
        c.report()
        r = c.data["report"]
        return {"report_md": str(c.run.dir / "report.md"), "final_states": r["final_states"], "rejected": len(r["rejected"]),
                "recombination_rate": r["recombination_rate"], "by_shell": r["recombination_rate_by_shell"], **_due(c)}
    return _call(study, "report", ("final_states",), None, body)


def dft_single_points(study: str) -> Dict[str, Any]:
    """Extension: DFT single points on the picked states; not available until the team decides D2."""
    return {"unavailable": "dft_single_points is an extension: it needs a DFT code and compute, decision D2"}


def active_learning(study: str) -> Dict[str, Any]:
    """Extension: DFT labels to a fine-tuned potential; not available until the team decides D2."""
    return {"unavailable": "active_learning is an extension: it needs DFT labels, decision D2"}


FUNCTIONS: Dict[str, Callable[..., Dict[str, Any]]] = {name: globals()[name] for name in list(BY_NAME) + ["study_status", "note", "show_structures"]}
