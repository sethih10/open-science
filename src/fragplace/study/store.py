"""The study's records and what each tool call is given: Study binds each tool's inputs from the run's artifacts
and keeps the outputs later steps need, for the orchestrator's calls in calls.py and for the test harness of
rollout.py alike.

Inputs come from runs/<study>/artifacts.json, which holds the supplied inputs and every output a later step
reads, from PROJECT.md, and from the human's choices at the checkpoints. Nothing here places atoms or computes an
energy; it reads records, looks up sites and calls tools. Where the board's order and the code's differ: B is
placed right after pair_enumeration, since the pull-force screen of 3.3 needs structures, so step 4's placement
call finds nothing left to place; at 3.2 d is a published value the human verified when there is one, else the
bond length measured as the team's d_definition says; the surface-chemist's ordering at 3.4 is an LLM's, so the
test harness keeps the screen's queue and says so in the trace.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ..errors import FragPlaceError, OpenDecision
from ..execution import pool
from ..registry.agents import CHECKPOINTS
from ..registry.tools import runs_dft
from ..memory.casebank import CaseBank
from ..runtime import artifacts, checkpoints, geometry, project
from ..runtime import state as run_state
from ..runtime.journal import Run, _jsonable, log, set_run
from ..schemas.records import (Candidate, Case, DescriptorCard, DoubtFlag, FinalState, GasReference, GateResult, HumanChoice,
                               LiteratureValue, Pair, RankedCandidate, RelaxationResult, Settings, SiteEnumeration, StructureRef)
from ..tools import get as tool
from ..tools.placement import HEIGHT_RANGE_A, orientations
from ..tools.relaxation import MAX_STEPS
from ..tools.structure import composition, initial_state_in_cell
from ..tools.uncertainty import system_class_of
from . import summary

WINDOW_LOWER_D = 1.5           # the board's window, [1.5 d, upper] Å
HEIGHT_A = HEIGHT_RANGE_A[0]   # B starts at the lower end of the docs' 2 to 3 Å
LITERATURE_SOURCES = ["cmr_catapp", "catalysis_hub"]   # offline first; Catalysis-Hub answers only with a personal key
QUANTITY_OF = {"AB": "E_ads", "A": "E_ads", "B": "E_ads", "reaction": "reaction_energy"}


class Study:
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
    def species(self) -> Dict[str, str]:
        """The study's species as literature_lookup reads them: AB, A and B on the surface, and the reaction."""
        s = self.settings(locked=False)
        surface = f"{s.metal}({s.facet})"
        return {"AB": f"{surface} {s.adsorbate}", "A": f"{surface} {s.product[0]}", "B": f"{surface} {s.product[1]}",
                "reaction": f"{surface} {s.adsorbate}->{s.product[0]}+{s.product[1]}"}

    def lookup(self, quantity: str, which: List[str], sources: List[str], reported: Optional[List[LiteratureValue]] = None) -> tuple:
        """Published values of one quantity for the named species, added to the study's list unverified; returns the
        new values and, for each species that gave none, why."""
        found, why = [], []
        for key in which:
            try:
                found += tool("literature_lookup")(self.species()[key], quantity, sources, reported)
            except (LookupError, ValueError) as e:
                why.append(f"{key}: {e}")
        values = self.many("literature", LiteratureValue)
        held = {(v.source, v.quantity, v.value) for v in values}
        new = [v for v in found if (v.source, v.quantity, v.value) not in held]
        self.put("literature", values + new)
        return new, why

    def literature(self) -> None:
        for key, quantity in QUANTITY_OF.items():
            new, why = self.lookup(quantity, [key], LITERATURE_SOURCES)
            for line in why:
                log("literature_lookup", f"no published {quantity} for {line}")
        if not any(v.quantity == "E_ads" for v in self.many("literature", LiteratureValue)):
            log("literature_lookup", "no published E_ads: check 7 will have no prior")

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
            raise OpenDecision("PROJECT.md names no protocol and reason: the computational chemist picks mlip when the study runs no DFT, "
                               "else aiida_common_workflows, sssp or oc20, and says why")
        self.propose(self.prepared(s), {}, s.protocol, s.protocol_reason)

    def prepared(self, s: Settings) -> Settings:
        """The settings as read from the inputs: the selected cell, and a gas reference from each supplied structure in
        vacuum, AB and when given A and B, with the file's own calculator, when the team lists a species of the same
        composition and PROJECT.md gives no energy for it. The reference keeps the team's name, OH for a file whose
        formula reads HO."""
        from ase.formula import Formula

        def composition(species: str) -> Optional[Dict[str, int]]:
            try:
                return Formula(species).count()
            except ValueError:
                return None
        s.cell_repeat = tuple(self.data["retrieval"]["cell_repeat"])
        cell = artifacts.read(StructureRef.model_validate(self.data["retrieval"]["structures"][0])).cell.lengths()
        s.cell_A = (round(float(cell[0]), 3), round(float(cell[1]), 3))
        wanted = s.decisions.get("calculation_protocol.gas_references") or []
        held = [composition(g.species) for g in s.gas_references]
        for key in ("adsorbate_vacuum", "fragment_A_vacuum", "fragment_B_vacuum"):
            if key not in self.data["inputs"]:
                continue
            ref = StructureRef.model_validate(self.data["inputs"][key])
            have = artifacts.read(ref).symbols.formula.count()
            species = next((w for w in wanted if composition(w) == have), None)
            if species is not None and have not in held and ref.energy_eV is not None:
                s.gas_references.append(GasReference(species=species, energy_eV=ref.energy_eV, note=f"the supplied {key.replace('_', ' ')}",
                                                     calculator=ref.calculator))
                held.append(have)
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
        elements = [set(artifacts.read(StructureRef.model_validate(inp[k])).get_chemical_symbols()) for k in ("slab", "adsorbate_vacuum")]
        out = tool("mlip_selection")(list(project.decision("mlip_selection", "candidates", s)), system_class_of(*elements), labels)
        used = s.mlip or out["chosen"]
        committee = s.mlip_committee or out["committee"]
        if s.mlip:
            reason = "locked in PROJECT.md by the human"
        elif len(out["committee"]) == 1:
            reason = "the only candidate that runs on this system"
        else:
            reason = f"{summary.benchmark_rule(out['benchmark'])} on the supplied inputs"
        if not s.mlip and out["benchmark"].get(used, {}).get("circular"):
            reason += f", on labels computed with {used} itself, so the score is circular"
        self.put("mlip", {**out, "calculator": used, "committee_used": committee, "reason": reason})
        log("mlip_selection", f"study uses {used}, {reason}; committee {committee}")
        self.gas()

    GAS_INPUTS = ("adsorbate_vacuum", "fragment_A_vacuum", "fragment_B_vacuum")

    def gas(self) -> None:
        """In a study without DFT, the gas references of the lock's species, each its supplied structure in vacuum
        relaxed by the chosen potential, written beside PROJECT.md with that potential as calculator. Run again only
        when the potential changes. The files' own energies stay the files' and are never used here."""
        s = self.settings()
        if runs_dft(s.protocol):
            return
        calculator = self.calculator
        if self.data.get("gas_references_by") == calculator:
            return
        inputs = self.data["inputs"]
        by_formula = {}
        for key in self.GAS_INPUTS:
            if key in inputs:
                ref = StructureRef.model_validate(inputs[key])
                by_formula.setdefault(tuple(sorted(artifacts.read(ref).symbols.formula.count().items())), (key, ref))
        refs = []
        for species in project.decision("calculation_protocol", "gas_references", s) or []:
            count = composition(species)
            found = by_formula.get(tuple(sorted(count.items()))) if count else None
            if found is None:
                raise FragPlaceError(f"gas reference {species}: no supplied structure in vacuum of that composition; give it as the adsorbate "
                                     "in vacuum or as fragment A or B in vacuum, with fragplace init --fragment-a or --fragment-b")
            key, ref = found
            start = Candidate(id=f"gas-{species}", structure=ref, generator="reference")
            r = tool("relaxation")([start], calculator, s.force_threshold_eV_per_A, int(self.options.get("max_steps", MAX_STEPS)))[0]
            refs.append(GasReference(species=species, energy_eV=r.energy_eV, calculator=calculator,
                                     note=f"the supplied {key.replace('_', ' ')} relaxed with {calculator}"))
        project.write_potential_gas(self.run.dir, refs)
        self.put("gas_references_by", calculator)
        log("mlip_selection", "gas references with " + calculator + ": " + (", ".join(f"{g.species} {g.energy_eV:.4f} eV" for g in refs) or "none listed"))

    # 1*: the compute plan; the timing is measured once per potential and kept as compute_timing for the server
    def compute(self, rules: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, Any]:
        """compute_plan on the selected cell with the adsorbate and the chosen potential: the estimate per heavy step,
        and with rules the rules checked. Records the timing only; calls.compute_plan records a proposal."""
        inp, r = self.data["inputs"], self.data["retrieval"]
        out = tool("compute_plan")(self.calculator, StructureRef.model_validate(r["structures"][0]), StructureRef.model_validate(inp["adsorbate_vacuum"]),
                                   self.heavy_items(), rules, self.data.get("compute_timing"))
        self.put("compute_timing", out["timing"])
        return out

    def heavy_items(self) -> Dict[str, Optional[int]]:
        """The items of each heavy step's call, where the step before has made them; None where not yet."""
        d = self.data
        picked = next((len(x.chosen) for x in checkpoints.passed(self.run.dir) if x.checkpoint == "pick up to five final states"), None)
        committee = len(d.get("mlip", {}).get("committee_used") or []) or 1
        passed = [g for g in d.get("gates_before", []) if g.get("passed")]
        return {"site_enumeration": 1, "pull_force_screen": len(d["placed"]) if "placed" in d else None,
                "minima_hopping": self.options.get("n_hops"), "anomaly_filter": len(d["placed"]) if "placed" in d else None,
                "relaxation": len(passed) if "gates_before" in d else None, "soap_clustering": len(d["relaxed"]) if "relaxed" in d else None,
                "uncertainty_estimation": len(d["kept"]) * committee if "kept" in d else None, "reference_energies": picked}

    # 2
    def sites(self) -> None:
        self.put("sites", tool("site_enumeration")(StructureRef.model_validate(self.data["inputs"]["slab"]), tuple(self.data["retrieval"]["cell_repeat"])))

    # 3.2: d, a published value the human verified or the measured bond, A at its initial-state site, the pairs, then B
    def literature_d(self) -> None:
        new, why = self.lookup("bond_length_d", ["AB"], LITERATURE_SOURCES)
        log("literature_lookup", f"published d: {len(new)} found, none verified by a human in this run" if new else f"no published d: {'; '.join(why)}")

    def bond_d(self, s: Settings) -> tuple:
        """d and where it comes from: a published bond length the human verified, else the bond measured as the team's
        d_definition says."""
        verified = [v for v in self.many("literature", LiteratureValue) if v.quantity == "bond_length_d" and v.verified_by_human]
        if verified:
            return verified[0].value, f"published, {verified[0].source}, verified by the human"
        definition = project.decision("pair_enumeration", "d_definition", s)
        return bond_length(self.data["inputs"], definition), f"measured on the {definition} structure"

    def pairs(self) -> None:
        s = self.settings()
        if not project.decision("adsorbate_placement", "fragment_A_fixed_at_old_site", s):
            raise OpenDecision("step 3.5 is deferred: A stays at its initial-state site, so adsorbate_placement.fragment_A_fixed_at_old_site must be true")
        sites = self.one("sites", SiteEnumeration)
        base_ref = StructureRef.model_validate(self.data["retrieval"]["structures"][1])
        atoms = artifacts.read(base_ref)
        site, off = geometry.nearest_site(sites, atoms.positions[artifacts.binding_index(atoms, "A")], atoms.cell.array)
        log("pair_enumeration", f"A holds site {site.index}, {site.label}, {off:.2f} Å off it, at its initial-state position")
        d, source = self.bond_d(s)
        self.put("d", {"value": d, "source": source})
        log("pair_enumeration", f"d = {d:.3f} Å, {source}")
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

    def placement_with_pairs(self) -> None:
        log("adsorbate_placement", "B is placed by pair_enumeration's handler, right after the pairs it places it on")

    def gate_before(self) -> None:
        """The gate on the placed structures, before any relaxation, with the checks the team listed; a candidate that
        fails one is not relaxed and is reported with its reason."""
        s = self.settings()
        self.gas()
        slab = self.one("sites", SiteEnumeration).slab
        gate = tool("anomaly_filter")
        self.put("gates_before", [gate(c, c, slab, s, None, None) for c in self.queued()])

    def relax(self) -> None:
        s = self.settings()
        if "gates_before" not in self.data:
            self.gate_before()
        sites = self.one("sites", SiteEnumeration)
        steps = int(self.options.get("max_steps", MAX_STEPS))
        relax = tool("relaxation")
        with pool.using(approved_rule(self, "relaxation").get("workers")):
            slab = relax([Candidate(id="slab", structure=sites.slab, generator="reference")], self.calculator, s.force_threshold_eV_per_A, steps)[0]
            self.put("slab_relaxed", slab)
            self.put("relaxed", relax(self.ordered(), self.calculator, s.force_threshold_eV_per_A, steps))

    def queued(self) -> List[Candidate]:
        """Every placed candidate in the relaxation order: the surface-chemist's order when it gave one, the pull-force
        queue for the rest, then the minima of 3.6."""
        by_id = {c.id: c for c in self.many("placed", Candidate)}
        first = [k for k in self.data.get("order", []) if k in by_id]
        return [by_id[k] for k in first + [k for k in self.data["queue"] if k not in first]] + self.many("hopped", Candidate)

    def ordered(self) -> List[Candidate]:
        """The candidates relaxation takes, in order: the queue less those the gate rejected before relaxation."""
        rejected = {g["candidate_id"] for g in self.data.get("gates_before", []) if not g["passed"]}
        return [c for c in self.queued() if c.id not in rejected]

    def relaxed_candidates(self) -> Dict[str, Candidate]:
        results = {r.candidate_id: r for r in self.many("relaxed", RelaxationResult)}
        return {c.id: c.model_copy(update={"structure": results[c.id].structure}) for c in self.ordered()}

    # 5
    def gate(self) -> None:
        s = self.settings()
        self.gas()
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
        """E(FS ∞) and the lateral interaction of every picked state, each fragment's adsorption energy when the tool
        gives it, and E(FS near) - E(IS) with the initial state in the selected cell, relaxed by the same potential with
        the locked settings: a final state minus an initial state of another cell is no reaction energy. No pick, no
        state: a study whose candidates were all rejected still gets its report."""
        chosen = checkpoints.require(self.run.dir, "pick up to five final states").chosen
        slab = self.one("slab_relaxed", RelaxationResult).structure
        relaxed = {r.candidate_id: r for r in self.many("relaxed", RelaxationResult)}
        cards = {c.candidate_id: c for c in self.many("cards_kept", DescriptorCard)}
        inputs = self.data["inputs"]
        gas = tuple(StructureRef.model_validate(inputs[k]) for k in ("fragment_A_vacuum", "fragment_B_vacuum")) \
            if all(k in inputs for k in ("fragment_A_vacuum", "fragment_B_vacuum")) else None
        e_is = None
        if chosen:
            s = self.settings()
            start = Candidate(id="initial-state", structure=self.initial_state_used(), generator="reference")
            e_is = tool("relaxation")([start], self.calculator, s.force_threshold_eV_per_A, int(self.options.get("max_steps", MAX_STEPS)))[0].energy_eV
            log("reference_energies", f"E(IS) {e_is:.4f} eV, {self.data['initial_state_used']['how']}")
        states = []
        for cid in chosen:
            r = relaxed[cid]
            with pool.using(approved_rule(self, "reference_energies").get("workers")):
                e = tool("reference_energies")(slab, (r.structure, r.structure), self.calculator, gas)
            same = e_is is not None and len(artifacts.read(r.structure)) == self.data["initial_state_used"]["atoms"]
            if e_is is not None and not same:
                log("reference_energies", f"{cid}: no reaction energy, the final state and the initial state hold different atom counts")
            states.append(FinalState(candidate_id=cid, E_near_eV=r.energy_eV, E_inf_eV=e["E_inf_eV"], lateral_interaction_eV=r.energy_eV - e["E_inf_eV"],
                                     AB_distance_A=cards[cid].AB_distance_A, site_graph_distance=cards[cid].site_graph_distance,
                                     E_ads_A_eV=e.get("E_ads_A_eV"), E_ads_B_eV=e.get("E_ads_B_eV"),
                                     reaction_energy_eV=r.energy_eV - e_is if same else None))
        self.put("final_states", states)

    def initial_state_used(self) -> StructureRef:
        """The initial state E(IS) is taken from: the supplied one when the selected cell is the supplied cell, else the
        selected slab with the supplied adsorbate at its place, built by code. Recorded as initial_state_used with
        its cell, atom count and how it was made."""
        inputs, retrieval = self.data["inputs"], self.data["retrieval"]
        repeat = tuple(retrieval["cell_repeat"])
        supplied = StructureRef.model_validate(inputs["initial_state"])
        if repeat == (1, 1):
            ref, how = supplied, "the supplied initial state, since the selected cell is the supplied one, 1×1"
        else:
            ref = initial_state_in_cell(StructureRef.model_validate(retrieval["structures"][0]), StructureRef.model_validate(inputs["slab"]), supplied)
            how = (f"the initial state in the selected cell, {repeat[0]}×{repeat[1]}: the selected slab with the adsorbate of the supplied "
                   "initial state at its place, built by code")
        atoms = len(artifacts.read(ref))
        self.put("initial_state_used", {"structure": ref, "cell_repeat": list(repeat), "atoms": atoms, "how": f"{how}, {atoms} atoms"})
        return ref

    def report(self) -> None:
        rejected = [g for g in self.many("gates_before", GateResult) + self.many("gates", GateResult) if not g.passed]
        self.put("report", tool("report")(self.run.study, self.many("final_states", FinalState), rejected, self.many("flags", DoubtFlag), {}))
        brief = summary.full(self).split("\n", 1)[-1]
        if brief.strip():
            path = self.run.dir / "report.md"
            head, sep, rest = path.read_text().partition("\n## ")
            path.write_text(head + "\n## Steps in brief\n\nThe summary.md of the study, one block per step, as each step wrote it.\n"
                            + brief.replace("\n## ", "\n### ") + "\n" + sep + rest)
        notes = self.data.get("notes", [])
        if notes:
            with (self.run.dir / "report.md").open("a") as f:
                f.write("\n## What the agents said\n\nTheir words, not tool outputs; each is in the trace under its author.\n\n"
                        + "".join(f"- **{n['author']}**: {n['text']}\n" for n in notes))


HANDLERS: Dict[tuple, Callable[[Study], None]] = {
    ("prompt", "literature_lookup"): Study.literature,
    ("1", "structure_retrieval"): Study.retrieval,
    ("1", "calculation_protocol"): Study.protocol,
    ("1*", "mlip_selection"): Study.mlip,
    ("1*", "compute_plan"): Study.compute,
    ("2", "site_enumeration"): Study.sites,
    ("3.2", "literature_lookup"): Study.literature_d,
    ("3.2", "adsorbate_placement"): Study.placement_with_pairs,
    ("3.2", "pair_enumeration"): Study.pairs_and_place,
    ("3.3", "pull_force_screen"): Study.screen,
    ("3.4", "descriptor_card"): Study.cards_placed,
    ("3.6", "minima_hopping"): Study.hopping,
    ("4", "relaxation"): Study.relax,
    ("5", "anomaly_filter"): Study.gate,
    ("5", "descriptor_card"): Study.cards,
    ("6", "soap_clustering"): Study.cluster,
    ("7", "uncertainty_estimation"): Study.doubt,
    ("8", "descriptor_card"): Study.cards_kept,
    ("8", "ranking"): Study.rank,
    ("solution", "reference_energies"): Study.references,
    ("solution", "report"): Study.report,
}


def bond_length(inputs: Dict[str, Any], definition: str) -> float:
    """d, the length of the bond to break, measured on the adsorbate in vacuum or on the initial state."""
    i, j = inputs["bond_to_break"]
    if definition == "vacuum":
        return geometry.distance(artifacts.read(StructureRef.model_validate(inputs["adsorbate_vacuum"])), i, j)
    if definition == "adsorbed":
        n = len(artifacts.read(StructureRef.model_validate(inputs["slab"])))
        return geometry.distance(artifacts.read(StructureRef.model_validate(inputs["initial_state"])), n + i, n + j)
    raise OpenDecision(f"pair_enumeration.d_definition is {definition!r}; it must be vacuum or adsorbed")


def approved_rule(c: Study, tool_name: str) -> Dict[str, Any]:
    """The compute plan's rule for a tool once the human has passed approve the plan; empty before it, or when the plan
    leaves the tool to the default lane. mcp.server routes the call by it; relax and references size the pool by it."""
    plan = c.data.get("compute_plan") or {}
    if not plan or "approve the plan" not in {x.checkpoint for x in checkpoints.passed(c.run.dir)}:
        return {}
    return dict((plan.get("rules") or {}).get(tool_name) or {})


# ---- the human's side: what each checkpoint shows, and recording the choice
DUE_WHEN = {   # the output a checkpoint reviews; once it exists, the checkpoint is due
    "approve settings": "protocol_proposed", "approve the plan": "mlip", "review flagged cases": "flags",
    "pick up to five final states": "ranked", "interpret results": "report",
}


def due_checkpoint(c: Study) -> Optional[str]:
    """The first checkpoint not yet passed, when the output it reviews exists; an agent calls the tools in its own
    order, so this, not state.json, says where the human is owed a choice."""
    passed = {x.checkpoint for x in checkpoints.passed(c.run.dir)}
    for name in CHECKPOINTS:
        if name not in passed:
            return name if DUE_WHEN[name] in c.data else None
    return None


PLACEHOLDER = re.compile(r"<[^<>]*>")   # "<your name>", "<your reason>": a template copied without filling it in


def _attributed(who: str, reason: str) -> None:
    """A record names a real person and says why; text left as a template placeholder is refused."""
    if not who.strip() or PLACEHOLDER.search(who):
        raise FragPlaceError(f"who is {who!r}: give the name of the person deciding")
    if not reason.strip() or PLACEHOLDER.fullmatch(reason.strip()):
        raise FragPlaceError(f"the reason is {reason!r}: say why, in the person's words")


def record_decision(root: Path, name: str, key: str, value: Any, who: str, reason: str) -> None:
    """Set one open decision in the study's PROJECT.md, before the lock: a value the human gave, with who gave it
    and why, in the trace. A locked PROJECT.md is never changed."""
    from ..registry.tools import open_decisions
    c = Study(root, name)
    path = c.run.dir / "PROJECT.md"
    s = project.read(path)
    if s.locked:
        raise FragPlaceError(f"{path} is locked; a new value means a new study")
    if key not in open_decisions():
        raise FragPlaceError(f"{key} is not an open decision; known: {', '.join(open_decisions())}")
    _attributed(who, reason)
    s.decisions[key] = value
    project.write(path, s)
    c.run.event("decision", key, who, {"value": value}, "", message=f"{who} set {key} = {value!r}: {reason}")


def record_interview(root: Path, name: str, row: int, answer: str, who: str) -> None:
    """Write the human's answer into row `row`, 1 to 5, of the Interview table of the study's PROJECT.md, word for
    word, before the lock; the trace keeps who answered."""
    c = Study(root, name)
    path = c.run.dir / "PROJECT.md"
    if project.read(path).locked:
        raise FragPlaceError(f"{path} is locked; the interview comes before the settings")
    head, sep, rest = path.read_text().partition("## Interview")
    if not sep:
        raise FragPlaceError(f"{path} has no Interview section")
    section, nxt, tail = rest.partition("\n## ")
    lines = section.split("\n")
    rows = [k for k, line in enumerate(lines) if line.startswith("|") and not line.startswith("|---")][1:]
    if not 1 <= row <= len(rows):
        raise FragPlaceError(f"interview row {row}; the table has {len(rows)}")
    question = lines[rows[row - 1]].strip().strip("|").split("|", 1)[0].strip()
    text = " ".join(answer.replace("|", "/").split())
    lines[rows[row - 1]] = f"| {question} | {text} |"
    path.write_text(head + sep + "\n".join(lines) + nxt + tail)
    c.run.event("prompt", "interview", "human", {"row": row, "answer": text}, "", message=f"{who} answered interview question {row}: {text}")


def record_verified(root: Path, name: str, chosen: List[str], who: str) -> List[str]:
    """Mark published values, lit:<index>, as checked by the human against their source, outside a checkpoint: a d
    the literature-reader found at 3.2. Values checked at approve settings go in with that checkpoint instead."""
    c = Study(root, name)
    _attributed(who, "checked against the source")
    values = c.many("literature", LiteratureValue)
    marked = []
    for item in chosen:
        m = re.fullmatch(r"lit:(\d+)", item)
        if not m or int(m.group(1)) >= len(values):
            raise FragPlaceError(f"{item}: name a published value as lit:<index>, of {len(values)}")
        values[int(m.group(1))].verified_by_human = True
        marked.append(item)
    c.put("literature", values)
    c.run.event("chat", "verify", "human", {"chosen": marked}, "", message=f"{who} checked {', '.join(marked)} against their sources")
    return marked


def record_choice(root: Path, name: str, checkpoint: str, chosen: List[str], reason: str, who: str, casebank: Optional[Path] = None) -> HumanChoice:
    """Record the human's choice at the pending checkpoint, after the checks that belong to it: the lock at approve
    settings, the shortlist at the pick. The choice and its reason go to the case bank at the two checkpoints
    that change what is kept, except in an example study, whose test values teach the bank nothing."""
    c = Study(root, name)
    pending = run_state.load(c.run.dir, name).pending_checkpoint or due_checkpoint(c)
    if checkpoint != pending:
        raise FragPlaceError(f"the pending checkpoint is {pending!r}, not {checkpoint!r}")
    _attributed(who, reason)
    bank = CaseBank(casebank or Path(root) / "lessons.md") if not c.options.get("example") else _NoBank(c)
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
        if unknown or not (1 if ranked else 0) <= len(chosen) <= limit:
            raise FragPlaceError(f"pick 1 to {limit} of the ranked candidates {ranked}; got {chosen}" if ranked else
                                 f"no candidate survived to the ranking; the pick is empty, got {chosen}")
        cards = {x.candidate_id: x.text() for x in c.many("cards_kept", DescriptorCard)}
        bank.add(Case(system=system, card="\n\n".join(cards[k] for k in chosen) or "no candidate survived",
                      correction=f"picked {', '.join(chosen) or 'none'} of {', '.join(ranked) or 'none ranked'}", reason=reason, source_checkpoint=checkpoint))
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
    if checkpoint == "interpret results" and (c.run.dir / "report.md").exists():
        with (c.run.dir / "report.md").open("a") as f:
            f.write(f"\n## The human's interpretation\n\n{who}, at interpret results: {reason}\n")
    return choice


class _NoBank:
    """The case bank of an example study: nothing is added; the trace says why."""

    def __init__(self, c: Study):
        self.c = c

    def add(self, case: Case) -> None:
        log("report", f"example study: not added to the case bank, {case.correction}")


def briefing(root: Path, name: str, checkpoint: Optional[str]) -> str:
    """What the human looks at before choosing at a checkpoint, as text."""
    c = Study(root, name)
    d = c.data
    out = []
    if checkpoint == "approve settings":
        s = c.settings(locked=False)
        out += [f"PROJECT.md: {c.run.dir / 'PROJECT.md'}", f"  {s.adsorbate}* -> {s.product[0]}* + {s.product[1]}* on {s.metal}({s.facet}); "
                f"protocol {s.protocol}: {s.protocol_reason}",
                f"  cell repeat {s.cell_repeat}; force threshold {s.force_threshold_eV_per_A} eV/Å; "
                + (f"functional {s.functional}; cutoff {s.cutoff_eV}; " if runs_dft(s.protocol) else "no DFT runs, the potential computes every energy; ")
                + f"{len(s.decisions)} decisions set, missing: {project.missing_decisions(s) or 'none'}"]
        lit = c.many("literature", LiteratureValue)
        out += ["Published values to verify, chosen as lit:<index>:"] + [f"  lit:{k} {v.quantity} {v.value} {v.unit}, {v.functional}, site {v.site}: {v.source}"
                                                                          for k, v in enumerate(lit)] if lit else ["No published value was found; check 7 will report not checked."]
    elif checkpoint == "approve the plan":
        m = d.get("mlip", {})
        out += [f"Potential: {m.get('calculator')} ({m.get('reason')}); committee {m.get('committee_used')}"]
        out += [f"  {k}: {summary.benchmark_text(v)}" for k, v in m.get("benchmark", {}).items()]
        out += ["Compute plan:"] + [f"  {k}: {v}" for k, v in summary.plan_rows(d)]
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
