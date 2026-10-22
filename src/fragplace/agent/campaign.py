"""The campaign: the invoke of agent.pipeline, which binds each tool's inputs from the run's artifacts and keeps
the outputs later steps need.

pipeline.run decides which step and which tools run next; this module answers what each call is given. Inputs
come from runs/<campaign>/artifacts.json, which holds the supplied inputs and every output a later step reads,
from PROJECT.md, and from the human's choices at the checkpoints. Nothing here places atoms or computes an
energy; it reads records, looks up sites and calls tools. Where the board's order and the code's differ: B is
placed right after pair_enumeration, since the pull-force screen of 3.3 needs structures, so step 4's placement
call finds nothing left to place; literature_lookup at 3.2 is not called, since d comes from the structures as
the team's d_definition says; the surface-chemist's reordering at 3.4 is an LLM's, so the rollout keeps the
screen's queue and says so in the trace.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ..errors import FragPlaceError, OpenDecision
from ..registry.agents import CHECKPOINTS
from ..memory.casebank import CaseBank
from ..runtime import artifacts, checkpoints, geometry, project
from ..runtime import state as run_state
from ..runtime.journal import Run, _jsonable, log, set_run
from ..schemas.records import (Candidate, Case, DescriptorCard, DoubtFlag, FinalState, GasReference, GateResult, HumanChoice,
                               LiteratureValue, Pair, RankedCandidate, RelaxationResult, Settings, SiteEnumeration, StructureRef)
from ..tools import get as tool
from ..tools.placement import HEIGHT_RANGE_A, orientations
from ..tools.relaxation import MAX_STEPS

WINDOW_LOWER_D = 1.5           # the board's window, [1.5 d, upper] Å
HEIGHT_A = HEIGHT_RANGE_A[0]   # B starts at the lower end of the docs' 2 to 3 Å
LITERATURE_SOURCES = ["catalysis_hub"]


class Campaign:
    """One run directory and its artifacts; invoke(tool, step) is what pipeline.run calls."""

    def __init__(self, root: Path, name: str):
        self.run = Run(Path(root), name)
        self.root = Path(root)
        set_run(self.run)
        self.path = self.run.dir / "artifacts.json"
        self.data: Dict[str, Any] = json.loads(self.path.read_text()) if self.path.exists() else {}

    # ---- artifacts
    def put(self, key: str, value: Any) -> None:
        self.data[key] = _jsonable(value)
        self.path.write_text(json.dumps(self.data, indent=1, ensure_ascii=False, default=str))

    def one(self, key: str, model):
        return model.model_validate(self.data[key])

    def many(self, key: str, model) -> list:
        return [model.model_validate(x) for x in self.data.get(key, [])]

    @property
    def options(self) -> Dict[str, Any]:
        return self.data.get("options", {})

    def settings(self, locked: bool = True) -> Settings:
        s = project.read(self.run.dir / "PROJECT.md")
        return project.require_locked(s) if locked else s

    @property
    def calculator(self) -> str:
        return self.data["mlip"]["calculator"]

    # ---- the rollout's callback
    def invoke(self, tool_name: str, step: str) -> None:
        handler: Optional[Callable[[], None]] = HANDLERS.get((step, tool_name))
        if handler is None:
            raise FragPlaceError(f"no binding for {tool_name} at step {step}")
        self.run.step = step
        try:
            handler(self)
        finally:
            self.run.step = None

    # prompt: published values for the human to verify; a lookup that fails leaves no prior and the run goes on
    def literature(self) -> None:
        s = self.settings(locked=False)
        try:
            values = tool("literature_lookup")(f"{s.metal}({s.facet}) {s.adsorbate}", "E_ads", LITERATURE_SOURCES)
        except Exception as e:  # noqa: BLE001 - the prior is advisory; check 7 then reports not checked
            values = []
            log("literature_lookup", f"no published value: {type(e).__name__}: {e}; check 7 will have no prior")
        self.put("literature", values)

    # 1: cleave, choose the cell, propose the lock
    def retrieval(self) -> None:
        inp = self.data["inputs"]
        out = tool("structure_retrieval")(StructureRef.model_validate(inp["slab"]), StructureRef.model_validate(inp["adsorbate_vacuum"]),
                                          StructureRef.model_validate(inp["initial_state"]), tuple(inp["bond_to_break"]))
        self.put("retrieval", out)

    def protocol(self) -> None:
        s = self.settings(locked=False)
        if s.locked:
            log("calculation_protocol", "PROJECT.md is already locked; nothing to propose")
            return
        if not s.protocol or not s.protocol_reason:
            raise OpenDecision("PROJECT.md names no protocol and reason: the computational chemist picks aiida_common_workflows, sssp or oc20 and says why")
        self.propose(self.prepared(s), {}, s.protocol, s.protocol_reason)

    def prepared(self, s: Settings) -> Settings:
        """The settings as read from the inputs: the selected cell, and the adsorbate's gas reference from the supplied
        relaxed adsorbate in vacuum when the team lists it and PROJECT.md gives no energy for it."""
        s.cell_repeat = tuple(self.data["retrieval"]["cell_repeat"])
        wanted = s.decisions.get("calculation_protocol.gas_references") or []
        vacuum = StructureRef.model_validate(self.data["inputs"]["adsorbate_vacuum"])
        if s.adsorbate in wanted and s.adsorbate not in {g.species for g in s.gas_references} and vacuum.energy_eV is not None:
            s.gas_references.append(GasReference(species=s.adsorbate, energy_eV=vacuum.energy_eV, note="the supplied relaxed adsorbate in vacuum"))
        return s

    def propose(self, s: Settings, physics_choices: Dict[str, Any], protocol: str, reason: str) -> Settings:
        """calculation_protocol on the settings as read from the inputs; the proposal makes approve settings due."""
        out = tool("calculation_protocol")(s, physics_choices, protocol, reason)
        self.put("protocol_proposed", project.settings_hash(out))
        return out

    # what agents say: a decision or a review with its reason, under the agent's name
    def note(self, author: str, text: str) -> None:
        self.put("notes", self.data.get("notes", []) + [{"author": author, "text": text}])
        self.run.event(self.run.step or "note", "note", author, {"text": text}, "", message=text)

    # 1*: benchmark the candidates on the supplied inputs; PROJECT.md's potential wins when the human locked one
    def mlip(self) -> None:
        s = self.settings()
        inp = self.data["inputs"]
        labels = [StructureRef.model_validate(inp[k]) for k in ("slab", "adsorbate_vacuum", "initial_state")]
        labels += [StructureRef.model_validate(x) for x in self.data.get("labels", [])]
        out = tool("mlip_selection")(list(project.decision("mlip_selection", "candidates", s)), system_class(labels), labels)
        used = s.mlip or out["chosen"]
        committee = s.mlip_committee or out["committee"]
        reason = "locked in PROJECT.md by the human" if s.mlip else "smallest absolute E_ads error on the supplied inputs"
        self.put("mlip", {**out, "calculator": used, "committee_used": committee, "reason": reason})
        log("mlip_selection", f"campaign uses {used}, {reason}; committee {committee}")

    # 2
    def sites(self) -> None:
        self.put("sites", tool("site_enumeration")(StructureRef.model_validate(self.data["inputs"]["slab"]), tuple(self.data["retrieval"]["cell_repeat"])))

    # 3.2: d from the structures, A at its initial-state site, the pairs, then B placed on each
    def skip_literature(self) -> None:
        log("literature_lookup", f"not called at 3.2: d is the {self.settings().decisions.get('pair_enumeration.d_definition')} bond length, "
                                 "measured on the supplied structures")

    def pairs(self) -> None:
        s = self.settings()
        if not project.decision("adsorbate_placement", "fragment_A_fixed_at_old_site", s):
            raise OpenDecision("step 3.5 is deferred: A stays at its initial-state site, so adsorbate_placement.fragment_A_fixed_at_old_site must be true")
        sites = self.one("sites", SiteEnumeration)
        base_ref = StructureRef.model_validate(self.data["retrieval"]["structures"][1])
        atoms = artifacts.read(base_ref)
        site, off = geometry.nearest_site(sites, atoms.positions[geometry.lowest(atoms, artifacts.fragment_indices(atoms, "A"))], atoms.cell.array)
        log("pair_enumeration", f"A holds site {site.index}, {site.label}, {off:.2f} Å off it, at its initial-state position")
        d = bond_length(self.data["inputs"], project.decision("pair_enumeration", "d_definition", s))
        base = Candidate(id=f"A{site.index:03d}", structure=base_ref, site_A=site.index, generator="enumeration")
        out = tool("pair_enumeration")(sites, d, (WINDOW_LOWER_D, float(project.decision("pair_enumeration", "upper_bound_A", s))), site.index)
        self.put("A_base", base)
        self.put("pairs", out["pairs"])

    def place(self) -> None:
        """B on the site of every pair, in every orientation its site group allows, on the slab with A."""
        s = self.settings()
        sites = self.one("sites", SiteEnumeration)
        base = self.one("A_base", Candidate)
        frag_ref = StructureRef.model_validate(self.data["retrieval"]["fragment_B"])
        frag = artifacts.read(frag_ref)
        cell = artifacts.read(sites.slab).cell.array
        amplitude = float(project.decision("adsorbate_placement", "displacement_amplitude_A", s))
        placed = []
        for p in self.many("pairs", Pair):
            for k in range(len(orientations(frag, sites, p.site_B, cell))):
                placed.append(tool("adsorbate_placement")(sites, frag_ref, p.site_B, k, HEIGHT_A, amplitude, base))
        self.put("placed", placed)

    def pairs_and_place(self) -> None:
        self.pairs()
        self.place()

    # 3.3
    def screen(self) -> None:
        screens = tool("pull_force_screen")(self.many("placed", Candidate), self.calculator)
        self.put("screens", screens)
        self.put("queue", [x.candidate_id for x in screens])

    # 3.4: cards of the enumerated candidates; the rollout keeps the queue
    def cards_placed(self) -> None:
        sites = self.one("sites", SiteEnumeration)
        by_id = {c.id: c for c in self.many("placed", Candidate)}
        self.put("cards_placed", [tool("descriptor_card")(by_id[k], None, sites) for k in self.data["queue"]])
        log("descriptor_card", "the deterministic rollout has no surface-chemist; the pull-force queue stands")

    # 3.6, only with --minima-hopping
    def hopping(self) -> None:
        sites = self.one("sites", SiteEnumeration)
        first = {c.id: c for c in self.many("placed", Candidate)}[self.data["queue"][0]]
        found = tool("minima_hopping")(sites.slab, (StructureRef.model_validate(self.data["retrieval"]["fragment_A"]), first.structure),
                                       self.calculator, int(self.options.get("n_hops", 5)))
        self.put("hopped", found)

    # 4
    def placement_done(self) -> None:
        log("adsorbate_placement", f"{len(self.data.get('placed', []))} candidates were placed at 3.2, before the screen")

    def relax(self) -> None:
        s = self.settings()
        sites = self.one("sites", SiteEnumeration)
        steps = int(self.options.get("max_steps", MAX_STEPS))
        relax = tool("relaxation")
        slab = relax([Candidate(id="slab", structure=sites.slab, generator="reference")], self.calculator, s.force_threshold_eV_per_A, steps)[0]
        self.put("slab_relaxed", slab)
        self.put("relaxed", relax(self.ordered(), self.calculator, s.force_threshold_eV_per_A, steps))

    def ordered(self) -> List[Candidate]:
        """The relaxation order: the surface-chemist's order when it gave one, the pull-force queue for the rest."""
        by_id = {c.id: c for c in self.many("placed", Candidate)}
        first = [k for k in self.data.get("order", []) if k in by_id]
        return [by_id[k] for k in first + [k for k in self.data["queue"] if k not in first]] + self.many("hopped", Candidate)

    def relaxed_candidates(self) -> Dict[str, Candidate]:
        results = {r.candidate_id: r for r in self.many("relaxed", RelaxationResult)}
        return {c.id: c.model_copy(update={"structure": results[c.id].structure}) for c in self.ordered()}

    # 5
    def gate(self) -> None:
        s = self.settings()
        slab = self.one("slab_relaxed", RelaxationResult).structure
        relaxed = self.relaxed_candidates()
        prior = self.prior()
        self.put("gates", [tool("anomaly_filter")(relaxed[c.id], c, slab, s, prior, None) for c in self.ordered()])

    def prior(self) -> Optional[float]:
        values = [v for v in self.many("literature", LiteratureValue) if v.verified_by_human]
        return values[0].value if values else None

    def cards(self) -> None:
        sites = self.one("sites", SiteEnumeration)
        relaxed = self.relaxed_candidates()
        self.put("cards", [tool("descriptor_card")(relaxed[g.candidate_id], g, sites) for g in self.many("gates", GateResult)])

    # 6
    def cluster(self) -> None:
        relaxed = self.relaxed_candidates()
        passed = [g.candidate_id for g in self.many("gates", GateResult) if g.passed]
        energies = [r for r in self.many("relaxed", RelaxationResult) if r.candidate_id in passed]
        out = tool("soap_clustering")([relaxed[k] for k in passed], energies, self.many("pairs", Pair))
        self.put("clusters", out["clusters"])
        self.put("kept", out["kept"])

    # 7
    def doubt(self) -> None:
        relaxed = self.relaxed_candidates()
        labels = [StructureRef.model_validate(x) for x in self.data.get("doubt_labels", [])] or None
        self.put("flags", tool("uncertainty_estimation")([relaxed[k] for k in self.data["kept"]], self.data["mlip"]["committee_used"], labels))

    # 8: the human may drop a flagged candidate at the review; a tool never does
    def reviewed(self) -> List[str]:
        chosen = checkpoints.require(self.run.dir, "review flagged cases").chosen
        return [k for k in self.data["kept"] if not chosen or k in chosen]

    def cards_kept(self) -> None:
        sites = self.one("sites", SiteEnumeration)
        relaxed = self.relaxed_candidates()
        gates = {g.candidate_id: g for g in self.many("gates", GateResult)}
        self.put("cards_kept", [tool("descriptor_card")(relaxed[k], gates[k], sites) for k in self.reviewed()])

    def rank(self) -> None:
        self.put("ranked", tool("ranking")(self.reviewed(), self.many("cards_kept", DescriptorCard), self.many("flags", DoubtFlag), self.many("pairs", Pair)))

    # solution: the separated product of every picked state, then the report
    def references(self) -> None:
        chosen = checkpoints.require(self.run.dir, "pick up to five final states").chosen
        slab = self.one("slab_relaxed", RelaxationResult).structure
        relaxed = {r.candidate_id: r for r in self.many("relaxed", RelaxationResult)}
        cards = {c.candidate_id: c for c in self.many("cards_kept", DescriptorCard)}
        states = []
        for cid in chosen:
            r = relaxed[cid]
            e = tool("reference_energies")(slab, (r.structure, r.structure), self.calculator)
            states.append(FinalState(candidate_id=cid, E_near_eV=r.energy_eV, E_inf_eV=e["E_inf_eV"], lateral_interaction_eV=r.energy_eV - e["E_inf_eV"],
                                     AB_distance_A=cards[cid].AB_distance_A, site_graph_distance=cards[cid].site_graph_distance))
        self.put("final_states", states)

    def report(self) -> None:
        rejected = [g for g in self.many("gates", GateResult) if not g.passed]
        self.put("report", tool("report")(self.run.campaign, self.many("final_states", FinalState), rejected, self.many("flags", DoubtFlag), {}))
        notes = self.data.get("notes", [])
        if notes:
            with (self.run.dir / "report.md").open("a") as f:
                f.write("\n## What the agents said\n\nTheir words, not tool outputs; each is in the trace under its author.\n\n"
                        + "".join(f"- **{n['author']}**: {n['text']}\n" for n in notes))


HANDLERS: Dict[tuple, Callable[[Campaign], None]] = {
    ("prompt", "literature_lookup"): Campaign.literature,
    ("1", "structure_retrieval"): Campaign.retrieval,
    ("1", "calculation_protocol"): Campaign.protocol,
    ("1*", "mlip_selection"): Campaign.mlip,
    ("2", "site_enumeration"): Campaign.sites,
    ("3.2", "literature_lookup"): Campaign.skip_literature,
    ("3.2", "pair_enumeration"): Campaign.pairs_and_place,
    ("3.3", "pull_force_screen"): Campaign.screen,
    ("3.4", "descriptor_card"): Campaign.cards_placed,
    ("3.6", "minima_hopping"): Campaign.hopping,
    ("4", "adsorbate_placement"): Campaign.placement_done,
    ("4", "relaxation"): Campaign.relax,
    ("5", "anomaly_filter"): Campaign.gate,
    ("5", "descriptor_card"): Campaign.cards,
    ("6", "soap_clustering"): Campaign.cluster,
    ("7", "uncertainty_estimation"): Campaign.doubt,
    ("8", "descriptor_card"): Campaign.cards_kept,
    ("8", "ranking"): Campaign.rank,
    ("solution", "reference_energies"): Campaign.references,
    ("solution", "report"): Campaign.report,
}


def system_class(labels: List[StructureRef]) -> str:
    """metal, oxide or organometallic, from the slab and the adsorbate of the supplied inputs."""
    roles = {r.role.value: r for r in labels}
    slab = set(artifacts.read(roles["slab"]).get_chemical_symbols())
    ads = set(artifacts.read(roles["adsorbate_vacuum"]).get_chemical_symbols())
    if "O" in slab:
        return "oxide"
    return "organometallic" if ads - {"H", "C", "N", "O", "S", "P", "F", "Cl", "Br", "I"} else "metal"


def bond_length(inputs: Dict[str, Any], definition: str) -> float:
    """d, the length of the bond to break, measured on the adsorbate in vacuum or on the initial state."""
    i, j = inputs["bond_to_break"]
    if definition == "vacuum":
        return geometry.distance(artifacts.read(StructureRef.model_validate(inputs["adsorbate_vacuum"])), i, j)
    if definition == "adsorbed":
        n = len(artifacts.read(StructureRef.model_validate(inputs["slab"])))
        return geometry.distance(artifacts.read(StructureRef.model_validate(inputs["initial_state"])), n + i, n + j)
    raise OpenDecision(f"pair_enumeration.d_definition is {definition!r}; it must be vacuum or adsorbed")


# ---- the human's side: what each checkpoint shows, and recording the choice
DUE_WHEN = {   # the output a checkpoint reviews; once it exists, the checkpoint is due
    "approve settings": "protocol_proposed", "approve the plan": "mlip", "review flagged cases": "flags",
    "pick up to five final states": "ranked", "interpret results": "report",
}


def due_checkpoint(c: Campaign) -> Optional[str]:
    """The first checkpoint not yet passed, when the output it reviews exists; an agent calls the tools in its own
    order, so this, not state.json, says where the human is owed a choice."""
    passed = {x.checkpoint for x in checkpoints.passed(c.run.dir)}
    for name in CHECKPOINTS:
        if name not in passed:
            return name if DUE_WHEN[name] in c.data else None
    return None


def record_decision(root: Path, name: str, key: str, value: Any, who: str, reason: str) -> None:
    """Set one open decision in the campaign's PROJECT.md, before the lock: a value the human gave, with who gave it
    and why, in the trace. A locked PROJECT.md is never changed."""
    from ..registry.tools import open_decisions
    c = Campaign(root, name)
    path = c.run.dir / "PROJECT.md"
    s = project.read(path)
    if s.locked:
        raise FragPlaceError(f"{path} is locked; a new value means a new campaign")
    if key not in open_decisions():
        raise FragPlaceError(f"{key} is not an open decision; known: {', '.join(open_decisions())}")
    if not reason.strip():
        raise FragPlaceError("a decision needs its reason")
    s.decisions[key] = value
    project.write(path, s)
    c.run.event("decision", key, who, {"value": value}, "", message=f"{who} set {key} = {value!r}: {reason}")


def record_choice(root: Path, name: str, checkpoint: str, chosen: List[str], reason: str, who: str, casebank: Optional[Path] = None) -> HumanChoice:
    """Record the human's choice at the pending checkpoint, after the checks that belong to it: the lock at approve
    settings, the shortlist at the pick. The choice and its reason go to the case bank at the two checkpoints
    that change what is kept."""
    c = Campaign(root, name)
    pending = run_state.load(c.run.dir, name).pending_checkpoint or due_checkpoint(c)
    if checkpoint != pending:
        raise FragPlaceError(f"the pending checkpoint is {pending!r}, not {checkpoint!r}")
    if not reason.strip():
        raise FragPlaceError("a choice needs its reason")
    bank = CaseBank(casebank or Path(root) / "lessons.md")
    s = c.settings(locked=False)
    system = f"{s.metal}({s.facet}) {s.adsorbate}"
    if checkpoint == "approve settings":
        missing = project.missing_decisions(s)
        if missing:
            raise OpenDecision("set before the lock: " + ", ".join(missing))
        values = c.many("literature", LiteratureValue)
        for item in chosen:
            m = re.fullmatch(r"lit:(\d+)", item)
            if not m or int(m.group(1)) >= len(values):
                raise FragPlaceError(f"{item}: approve settings takes lit:<index> for each published value the human verified")
            values[int(m.group(1))].verified_by_human = True
        c.put("literature", values)
        project.write(c.run.dir / "PROJECT.md", project.lock(s, approved_by=who))
    elif checkpoint == "pick up to five final states":
        ranked = [r.candidate_id for r in c.many("ranked", RankedCandidate)]
        limit = int(project.decision("ranking", "shortlist_size", s))
        unknown = [k for k in chosen if k not in ranked]
        if unknown or not 1 <= len(chosen) <= limit:
            raise FragPlaceError(f"pick 1 to {limit} of the ranked candidates {ranked}; got {chosen}")
        cards = {x.candidate_id: x.text() for x in c.many("cards_kept", DescriptorCard)}
        bank.add(Case(system=system, card="\n\n".join(cards[k] for k in chosen), correction=f"picked {', '.join(chosen)} of {', '.join(ranked)}",
                      reason=reason, source_checkpoint=checkpoint))
    elif checkpoint == "review flagged cases":
        unknown = [k for k in chosen if k not in c.data.get("kept", [])]
        if unknown:
            raise FragPlaceError(f"keep only kept candidates {c.data.get('kept', [])}; got {unknown}; name none to keep all")
        escalated = [f for f in c.many("flags", DoubtFlag) if f.escalate]
        if escalated:
            cards = {x.candidate_id: x.text() for x in c.many("cards", DescriptorCard)}
            bank.add(Case(system=system, card="\n\n".join(cards.get(f.candidate_id, f.candidate_id) for f in escalated),
                          correction=f"reviewed {len(escalated)} escalated flag(s): {', '.join(sorted({f.trigger for f in escalated}))}; kept {', '.join(chosen) or 'all'}",
                          reason=reason, source_checkpoint=checkpoint))
    choice = HumanChoice(checkpoint=checkpoint, chosen=list(chosen), reason=reason, who=who)
    checkpoints.record(c.run.dir, choice)
    c.run.event("checkpoint", checkpoint, "human", choice, "", message=f"{who}: {', '.join(chosen) or 'approved'}; {reason}")
    return choice


def briefing(root: Path, name: str, checkpoint: Optional[str]) -> str:
    """What the human looks at before choosing at a checkpoint, as text."""
    c = Campaign(root, name)
    d = c.data
    out = []
    if checkpoint == "approve settings":
        s = c.settings(locked=False)
        out += [f"PROJECT.md: {c.run.dir / 'PROJECT.md'}", f"  {s.adsorbate}* -> {s.product[0]}* + {s.product[1]}* on {s.metal}({s.facet}); "
                f"protocol {s.protocol}: {s.protocol_reason}", f"  cell repeat {s.cell_repeat}; functional {s.functional}; "
                f"cutoff {s.cutoff_eV}; {len(s.decisions)} decisions set, missing: {project.missing_decisions(s) or 'none'}"]
        lit = c.many("literature", LiteratureValue)
        out += ["Published values to verify, chosen as lit:<index>:"] + [f"  lit:{k} {v.quantity} {v.value} {v.unit}, {v.functional}, site {v.site}: {v.source}"
                                                                          for k, v in enumerate(lit)] if lit else ["No published value was found; check 7 will report not checked."]
    elif checkpoint == "approve the plan":
        m = d.get("mlip", {})
        out += [f"Potential: {m.get('calculator')} ({m.get('reason')}); committee {m.get('committee_used')}"]
        out += [f"  {k}: E_ads error {v.get('error_eV')} eV; anomalies {v.get('anomalies')}" for k, v in m.get("benchmark", {}).items()]
        out += ["Next: sites, pairs in the window, the pull-force screen, relaxation, the gate, SOAP clustering, then the doubt review."]
    elif checkpoint == "review flagged cases":
        flags = c.many("flags", DoubtFlag)
        gates = c.many("gates", GateResult)
        out += [f"{sum(g.passed for g in gates)} of {len(gates)} candidates passed the gate; kept after clustering: {', '.join(d.get('kept', []))}"]
        out += [f"  {f.candidate_id} {f.trigger}: spread {f.committee_spread_eV:.4f} eV" + (" ESCALATED" if f.escalate else "") for f in flags]
        out += ["Rejected:"] + [f"  {g.candidate_id}: " + "; ".join(f"check {v.check_id} {v.name}: {v.reason}" for v in g.verdicts if not v.passed)
                                for g in gates if not g.passed]
    elif checkpoint == "pick up to five final states":
        cards = {x.candidate_id: x for x in c.many("cards_kept", DescriptorCard)}
        for r in c.many("ranked", RankedCandidate):
            out += [f"#{r.rank} {r.candidate_id}: {r.reason}", "    " + cards[r.candidate_id].text().replace("\n", "\n    ")]
    elif checkpoint == "interpret results":
        out += [f"Report: {c.run.dir / 'report.md'}", (c.run.dir / "report.md").read_text() if (c.run.dir / "report.md").exists() else ""]
    return "\n".join(out)
