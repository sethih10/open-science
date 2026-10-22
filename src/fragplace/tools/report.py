"""The study report. Tools: report. Defined in fragplace.registry."""
from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any, Dict, List, Optional

from ..registry.tools import OPEN, asked_decisions, open_decisions, runs_dft
from ..runtime import artifacts, checkpoints, geometry, project
from ..runtime.journal import current_run, log, traced
from ..schemas.records import DoubtFlag, FinalState, GateResult, HumanChoice, Report, StructureRef
from .filtering import not_checked

NEAR_RECOMBINED_A = 0.5      # a survivor this close above check 10's threshold is named beside the recombination rate
EXAMPLE = re.compile(r"^> \*\*Example (study|campaign)\.\*\*", re.M)     # the line build_example puts at the top of PROJECT.md
# The team's decisions of AGENTS.md section 10, and the charge the code does not model; each is open until
# PROJECT.md's Decisions table says otherwise.
TEAM_DECISIONS = (("D1", "D1 first system and product: *OH → *O + *H on Pt(111)"), ("D2", "D2 DFT code, compute, GPU; any DFT at all"),
                  ("D3", "D3 OC20NEB subset as ground truth; pass criterion"), ("D4", "D4 headline claim"),
                  ("D5", "D5 final-state rules: distance metric, A fixed or enumerated, nearest or lowest within one hop"),
                  ("charge", "charge: no setting or check models the net charge of the fragments"))
DFT_SETTINGS = ("pseudopotential_family", "pseudopotential_version", "cutoff_eV", "kmesh", "smearing", "sigma_eV", "layers", "fixed_layers", "vacuum_A")
COST = {"relaxations": "Relaxations in the trace", "reference_relaxations": "Of them, reference relaxations for E(FS ∞) and E_ads",
        "relaxation_steps": "Optimiser steps, cache hits not counted", "cache_hits": "Cache hits", "force_screens": "Pull-force screens",
        "gates_before_relaxation": "Gates before relaxation", "gates": "Gates after relaxation"}


@traced(step="solution", tool="report")
def report(study: str, final_states: List[FinalState], rejected: List[GateResult], flags: List[DoubtFlag], comparison: Optional[Dict[str, float]] = None) -> Report:
    """One auditable record per study: final states with both energies, rejections with reasons, the recombination rate, doubt, the OC20NEB comparison, cost and the decision trace.

    Board steps: solution. Status: core. Lane: laptop. Allowed roles: solution-planner, scientific-critic.

    Inputs:
        study: str
        final_states: list[FinalState]
        rejected: list[GateResult]
        flags: list[DoubtFlag]
        comparison: dict
    Outputs:
        report: Report, written to runs/<study>/report.md and report.json
    Checks:
        - every number traces to a tool output
        - the scientific critic reads the draft with the general-peer-review skill
    Thresholds:
        none
    Wraps:
        - AtomisticSkills hyperparameter logging pattern
    Logs: the full trace path.

    The recombination rate, the survivors and the cost are read from the outputs the trace stores: every gate,
    with check 10 as recombination, counted per site-graph shell of the pair it gated; every relaxation, the
    reference relaxations of reference_energies among them; every force screen. The rate is that of the nearest
    shell gated, printed with check 10's threshold and the survivors within 0.5 Å above it. Every survivor of
    the gate is listed with its status, so none is hidden; the cell and the coverage come from
    structure_retrieval's slab; every open decision of the registry is listed with its value. An example study,
    whose PROJECT.md says so in its first quoted line, opens with a banner that its numbers support no chemical
    claim. The draft is for the scientific critic and the human; a number that would print as zero but is not
    keeps three significant figures.
    """
    run = current_run()
    if run is None or run.study != study:
        raise ValueError(f"report needs the run of study {study} to be current")
    settings = project.current_settings()
    outputs = _outputs(run)
    shells = {p["candidate_id"]: p["site_graph_distance"] for out in outputs.get("pair_enumeration", []) for p in out["pairs"]}
    gated: Dict[str, GateResult] = {}
    before: Dict[str, GateResult] = {}
    for out in outputs.get("anomaly_filter", []):
        g = GateResult.model_validate(out)
        (gated if g.stage == "after_relaxation" else before)[g.candidate_id] = g
    shells.update({cid: shells[_pair_id(cid)] for cid in gated if _pair_id(cid) in shells})
    tally: Dict[int, List[int]] = {}
    for cid, g in gated.items():
        if cid in shells:
            recombined = any(v.check_id == 10 and not v.passed for v in g.verdicts)
            tally.setdefault(shells[cid], []).append(int(recombined))
    by_shell = {k: sum(v) / len(v) for k, v in sorted(tally.items())}
    rate = by_shell[min(by_shell)] if by_shell else 0.0
    relaxations = [r for out in outputs.get("relaxation", []) for r in out]
    cost = {"relaxations": float(len(relaxations)),
            "reference_relaxations": float(sum((r.get("structure") or {}).get("role") == "reference" for r in relaxations)),
            "relaxation_steps": float(sum(r["steps"] for r in relaxations if not r["cache_hit"])),
            "cache_hits": float(sum(r["cache_hit"] for r in relaxations)),
            "force_screens": float(sum(len(out) for out in outputs.get("pull_force_screen", []))),
            "gates_before_relaxation": float(len(before)), "gates": float(len(gated))}
    rep = Report(study=study, final_states=final_states, rejected=rejected, recombination_rate=rate, recombination_rate_by_shell=by_shell,
                 doubt=flags, comparison_oc20neb=comparison or {}, cost=cost, trace_path=str(run.trace_path.relative_to(run.dir)),
                 settings_hash=project.settings_hash(settings))
    (run.dir / "report.json").write_text(rep.model_dump_json(indent=1))
    path = run.dir / "PROJECT.md"
    text = path.read_text() if path.exists() else ""
    choices = checkpoints.passed(run.dir)
    survivors = _survivors(gated, relaxations, outputs, flags, final_states, choices, shells)
    (run.dir / "report.md").write_text(_markdown(rep, settings, text, outputs, gated, before, shells, relaxations, survivors, choices,
                                                           references_used(run)))
    log("report", f"report.md and report.json written; trace {rep.trace_path}")
    return rep


def _pair_id(candidate_id: str) -> str:
    """The pair a candidate was placed for: A002-B015o1 is orientation 1 of pair A002-B015."""
    return re.sub(r"o\d+$", "", candidate_id)


def _outputs(run) -> Dict[str, List[Any]]:
    """Every stored tool output of the run, by tool, in trace order, each once."""
    out: Dict[str, List[Any]] = {}
    seen = set()
    for ev in run.events():
        if ev.outputs_ref and ev.outputs_ref not in seen:
            seen.add(ev.outputs_ref)
            out.setdefault(ev.tool, []).append(json.loads((run.dir / ev.outputs_ref).read_text()))
    return out


def references_used(run) -> Dict[str, List[str]]:
    """What the energies of the final states were taken against, read from the lines reference_energies wrote in
    the trace: "gas", the gas references of E_ads(A*) and E_ads(B*) with their energies, and "initial_state", the
    initial state of E(IS); each distinct line once, in trace order."""
    used: Dict[str, List[str]] = {"gas": [], "initial_state": []}
    for ev in run.events():
        if ev.tool != "reference_energies" or ev.actor != "tool" or not ev.message:
            continue
        key, text = None, None
        if "; gas references " in ev.message:
            key, text = "gas", ev.message.split("; gas references ", 1)[1]
        elif ev.message.startswith("E(IS) "):
            key, text = "initial_state", ev.message.split(", ", 1)[-1]
        if key and text not in used[key]:
            used[key].append(text)
    return used


def ads_against(used: Dict[str, List[str]]) -> str:
    """The reference of E_ads(A*) and E_ads(B*) in words, as reference_energies used it; more than one only when
    calls differed, and then each is named."""
    gas = used["gas"]
    if not gas:
        return "not computed: reference_energies wrote no gas reference in the trace"
    return "; and in another call, ".join(gas)


def _num(x: Optional[float], places: int, sign: bool = False, none: str = "not computed") -> str:
    """x to `places` decimals; a value that would print as zero but is not keeps three significant figures."""
    if x is None:
        return none
    plus = "+" if sign else ""
    text = f"{x:{plus}.{places}f}"
    return f"{x:{plus}.3g}" if x != 0 and float(text) == 0 else text


def _survivors(gated: Dict[str, GateResult], relaxations, outputs, flags: List[DoubtFlag], final_states: List[FinalState],
               choices: List[HumanChoice], shells: Dict[str, int]) -> List[Dict[str, Any]]:
    """Every candidate that passed the gate after relaxation, nearest first, with what became of it."""
    result = {r["candidate_id"]: r for r in relaxations}
    clustered = outputs.get("soap_clustering")
    kept = set(clustered[-1]["kept"]) if clustered else None
    by_checkpoint = {c.checkpoint: c for c in choices}
    pick = by_checkpoint.get("pick up to five final states")
    picked = {f.candidate_id for f in final_states} | set(pick.chosen if pick else [])
    review = by_checkpoint.get("review flagged cases")
    dropped = (kept or set()) - set(review.chosen) if review and review.chosen else set()
    doubt: Dict[str, List[DoubtFlag]] = {}
    for f in flags:
        doubt.setdefault(f.candidate_id, []).append(f)
    rows = []
    for cid, g in gated.items():
        if not g.passed:
            continue
        if cid in picked:
            status = "picked"
        elif kept is not None and cid not in kept:
            status = "not kept by clustering"
        elif cid in dropped:
            status = "dropped at the review"
        elif pick:
            status = "kept, not picked"
        else:
            status = "kept" if kept is not None else "survived the gate"
        r = result.get(cid)
        rows.append({"id": cid, "AB_A": next((v.measured for v in g.verdicts if v.check_id == 10), None), "shell": shells.get(cid),
                     "energy": r["energy_eV"] if r else None, "converged": r["converged"] if r else None, "steps": r["steps"] if r else None,
                     "doubt": "; ".join(f"flagged: {f.trigger}" + (", escalated" if f.escalate else "") for f in doubt.get(cid, [])) or "none",
                     "status": status})
    far = float("inf")
    return sorted(rows, key=lambda x: (x["shell"] if x["shell"] is not None else far, x["AB_A"] if x["AB_A"] is not None else far))


def _cell(settings, outputs) -> List[str]:
    """The selected cell and the coverage of each fragment, one of each per cell, from structure_retrieval's slab."""
    found = outputs.get("structure_retrieval")
    if not found:
        return ["Not recorded: structure_retrieval has no output in this trace."]
    out = found[-1]
    slab = artifacts.read(next(StructureRef.model_validate(x) for x in out["structures"] if x["role"] == "slab"))
    n = len(artifacts.surface_indices(slab))
    cover = f"1/{n} = {_num(1 / n, 4)}" if n else "unknown: no atom is tagged as the top layer"
    a, b = settings.product
    return ["One A and one B per cell; the coverage of each is 1 over the surface atoms of the cell.", "",
            "| Quantity | Value |", "|---|---|",
            f"| Repeat of the supplied cell | {' × '.join(str(k) for k in out['cell_repeat'])} |",
            "| In-plane cell lengths, Å | " + " × ".join(f"{x:.2f}" for x in slab.cell.lengths()[:2]) + " |",
            f"| Shortest in-plane translation, Å | {geometry.shortest_translation(slab.cell.array):.2f} |",
            f"| Surface atoms in the cell | {n} |", f"| Coverage of A, {a}\\*, ML | {cover} |", f"| Coverage of B, {b}\\*, ML | {cover} |"]


def _open(settings, text: str, example: bool, used: Dict[str, List[str]]) -> List[str]:
    """Every open decision of the registry with its value in the lock; D1 to D5 and the charge, with their status in
    PROJECT.md's Decisions table, open when it has no row for them; the DFT settings the lock leaves unset, or, in a
    study that runs no DFT, that it holds none and which decisions were not asked. The lock's gas references are
    followed by what E_ads was in fact computed against, so the two are never read as one."""
    def shown(value) -> str:
        return "not set" if value is None else value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    status = {m.group(1): m.group(2).strip() for m in re.finditer(r"^\|\s*(D\d)\b[^|]*\|\s*([^|]*)\|", text, re.M)}
    dft = runs_dft(settings.protocol)
    asked = asked_decisions(dft)
    unset = [f for f in DFT_SETTINGS if getattr(settings, f) is None]
    return [("The registry marks every value below open: team decision. Each was set for this study under decisions in PROJECT.md, "
             + ("as a test value from tests/conftest.py; none is a team decision." if example else "and none is settled for other studies.")), "",
            "| Decision | Value in PROJECT.md |", "|---|---|"] + [
            f"| {k} | {shown(settings.decisions.get(k)) if k in asked or settings.decisions.get(k) is not None else 'not asked: no DFT runs'} |"
            for k in open_decisions()] + [
            "", "| Team decision | Status |", "|---|---|"] + [f"| {label} | {status.get(key) or OPEN} |" for key, label in TEAM_DECISIONS] + [
            "", ("Settings the lock leaves unset: " + (", ".join(unset) + "." if unset else "none.")) if dft else
            "No DFT runs in this study: the potential computes every energy, and the lock holds no DFT setting. Gas references, computed "
            "with the potential: " + (", ".join(f"{g.species} {g.energy_eV:.4f} eV with {g.calculator}" for g in project.gas_references(settings)) or "none") + ".",
            "", f"E_ads(A\\*) and E_ads(B\\*) in Final states are against {ads_against(used)}, as reference_energies used them; the gas "
            "references above are the lock's and enter no E_ads unless they are these same structures."]


def _markdown(rep: Report, settings, text: str, outputs, gated: Dict[str, GateResult], before: Dict[str, GateResult], shells: Dict[str, int],
              relaxations, survivors: List[Dict[str, Any]], choices: List[HumanChoice], used: Dict[str, List[str]]) -> str:
    example = bool(EXAMPLE.search(text))
    potentials = sorted({r["calculator"] for r in relaxations})
    lines = [f"# Report: {rep.study}", ""]
    if example:
        lines += [f"> **Example study.** Every number in this report comes from a test potential, {', '.join(potentials) or 'not yet run'}, and "
                  "from the test values under `decisions` in PROJECT.md; it supports no chemical claim.", ""]
    lines += [f"{settings.adsorbate}* → {settings.product[0]}* + {settings.product[1]}* on {settings.metal}({settings.facet}). "
              f"Every energy below is from {', '.join(potentials) or 'no relaxation'}, the potential that relaxed the candidates; the settings "
              f"record, `{rep.settings_hash}`, is the lock in PROJECT.md. Decision trace `{rep.trace_path}`. Draft for the scientific critic and the human.", "",
              "## Final states", "",
              "Lateral interaction = E(FS near) − E(FS ∞), with E(FS ∞) = E(A\\*) + E(B\\*) − E(slab), each fragment alone on the slab. "
              f"E_ads(A\\*) and E_ads(B\\*) are against {ads_against(used)}, as reference_energies used them, each relaxed with the same "
              "potential. The reaction energy is "
              "E(FS near) − E(IS), with E(IS) from "
              + ("; and in another call, ".join(used["initial_state"]) if used["initial_state"] else "no initial state: none was relaxed")
              + "; it is given only when the initial state and the final state hold the same atoms in the same cell.", "",
              "| Candidate | E(FS near), eV | E(FS ∞), eV | Lateral interaction, eV | E_ads(A\\*), eV | E_ads(B\\*), eV | Reaction energy, eV | "
              "A–B distance, Å | Site-graph distance |", "|---|---|---|---|---|---|---|---|---|"]
    lines += [f"| {f.candidate_id} | {_num(f.E_near_eV, 4)} | {_num(f.E_inf_eV, 4)} | {_num(f.lateral_interaction_eV, 4, sign=True)} | "
              f"{_num(f.E_ads_A_eV, 4)} | {_num(f.E_ads_B_eV, 4)} | {_num(f.reaction_energy_eV, 4, sign=True)} | {_num(f.AB_distance_A, 2)} | "
              f"{f.site_graph_distance} |" for f in rep.final_states] or ["| none picked | | | | | | | | |"]
    lines += ["", "## Every survivor of the gate", "",
              "Each candidate that passed the gate after relaxation, picked or not, nearest first. A relaxation that stopped at the step cap is "
              "not converged.", "",
              "| Candidate | A–B distance, Å | Site-graph shell | Energy, eV | Converged | Steps | Doubt | Status |", "|---|---|---|---|---|---|---|---|"]
    lines += [f"| {x['id']} | {_num(x['AB_A'], 2, none='one fragment')} | {x['shell'] if x['shell'] is not None else 'unknown'} | "
              f"{_num(x['energy'], 4, none='no relaxation record')} | "
              f"{'unknown' if x['converged'] is None else 'yes' if x['converged'] else 'no, stopped at the step cap'} | "
              f"{x['steps'] if x['steps'] is not None else 'unknown'} | {x['doubt']} | {x['status']} |" for x in survivors] or ["| none | | | | | | | |"]
    lines += ["", "## Cell and coverage", ""] + _cell(settings, outputs)
    lines += ["", "## Rejected pairs", "", "| Candidate | Stage | Failed checks |", "|---|---|---|"]
    lines += [f"| {g.candidate_id} | {g.stage} | " + "; ".join(f"{v.check_id} {v.name}{' ' + v.fragment if v.fragment else ''}: {v.reason}"
                                                           for v in g.verdicts if not v.passed) + " |" for g in rep.rejected] or ["| none | | |"]
    limit = settings.decisions.get("anomaly_filter.AB_bond_reformed_A")
    limit = float(limit) if limit is not None else None
    near = [x for x in survivors if limit is not None and x["AB_A"] is not None and limit <= x["AB_A"] < limit + NEAR_RECOMBINED_A]
    lines += ["", "## Recombination rate", "",
              f"Nearest shell gated: {_num(rep.recombination_rate, 2)}, the share of its pairs whose A–B bond re-formed in relaxation, check 10. "
              f"Check 10 fails below an A–B distance of {limit if limit is not None else 'an unset threshold'} Å, "
              "anomaly_filter.AB_bond_reformed_A in PROJECT.md, open: team decision; the rate depends on it.", "",
              "| Site-graph shell | Pairs gated | Recombination rate |", "|---|---|---|"]
    counts = Counter(shells[c] for c in gated if c in shells)
    lines += [f"| {k} | {counts[k]} | {_num(v, 2)} |" for k, v in rep.recombination_rate_by_shell.items()] or ["| none | | |"]
    lines += ["", f"Survivors within {NEAR_RECOMBINED_A} Å above the threshold: near recombination, though they pass check 10.", "",
              "| Candidate | A–B distance, Å | Above the threshold, Å | Status |", "|---|---|---|---|"]
    lines += [f"| {x['id']} | {_num(x['AB_A'], 2)} | {_num(x['AB_A'] - limit, 2)} | {x['status']} |" for x in near] or ["| none | | | |"]
    unmeasured = {f.candidate_id for f in rep.doubt if f.trigger == "unmeasured"}
    lines += ["", "## Doubt", "", "| Candidate | Trigger | Committee spread, eV | Calibrated error, eV | Escalated |", "|---|---|---|---|---|"]
    lines += [f"| {f.candidate_id} | {f.trigger} | {'not measured' if f.candidate_id in unmeasured else _num(f.committee_spread_eV, 4)} | "
              f"{_num(f.calibrated_error_eV, 4, none='uncalibrated')} | {'yes' if f.escalate else 'no'} |" for f in rep.doubt] or ["| none | | | | |"]
    lines += ["", "## Open decisions", ""] + _open(settings, text, example, used)
    lines += ["", "## The human's choices", "", "| Checkpoint | Who | Chosen | Reason |", "|---|---|---|---|"]
    lines += [f"| {c.checkpoint} | {c.who} | {', '.join(c.chosen) or 'approved'} | {c.reason} |" for c in choices] or ["| none yet | | | |"]
    lines += ["", "## Comparison with OC20NEB", ""]
    lines += [f"- {k}: {v}" for k, v in rep.comparison_oc20neb.items()] or ["Not run: the subset and the pass criterion are open: team decision, D3."]
    lines += ["", "## Cost", "", "| Item | Count |", "|---|---|"] + [f"| {COST.get(k, k)} | {v:g} |" for k, v in rep.cost.items()]
    unchecked = Counter(f"check {v.check_id} {v.name}: {v.reason}" for g in gated.values() for v in g.verdicts if not_checked(v))
    lines += ["", "## Not checked", ""] + ([f"- {k}, {n} structure(s)" for k, n in sorted(unchecked.items())]
                                          or ["- Every check ran on every structure gated after relaxation."])
    if before:
        listed = settings.decisions.get("anomaly_filter.checks_before_relaxation")
        listed = ", ".join(str(k) for k in listed) if isinstance(listed, (list, tuple)) else str(listed)
        lines.append(f"- Before relaxation, {len(before)} placed structure(s) were gated on checks {listed} only, as "
                     "anomaly_filter.checks_before_relaxation says; every other check was not run before relaxation.")
    stuck = [x["id"] for x in survivors if x["converged"] is False]
    lines.append("- Convergence: the gate does not read it, so a relaxation that stopped at the step cap is gated on its last structure"
                 + (f"; not converged among the survivors: {', '.join(stuck)}." if stuck else "; every survivor converged."))
    return "\n".join(lines) + "\n"
