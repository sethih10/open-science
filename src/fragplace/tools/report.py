"""The campaign report. Tools: report. Defined in fragplace.registry."""
from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any, Dict, List, Optional

from ..runtime import checkpoints, project
from ..runtime.journal import current_run, log, traced
from ..schemas.records import DoubtFlag, FinalState, GateResult, Report


@traced(step="solution", tool="report")
def report(campaign: str, final_states: List[FinalState], rejected: List[GateResult], flags: List[DoubtFlag], comparison: Optional[Dict[str, float]] = None) -> Report:
    """One auditable record per campaign: final states with both energies, rejections with reasons, the recombination rate, doubt, the OC20NEB comparison, cost and the decision trace.

    Board steps: solution. Status: core. Lane: laptop. Allowed roles: solution-planner, scientific-critic.

    Inputs:
        campaign: str
        final_states: list[FinalState]
        rejected: list[GateResult]
        flags: list[DoubtFlag]
        comparison: dict
    Outputs:
        report: Report, written to runs/<campaign>/report.md and report.json
    Checks:
        - every number traces to a tool output
        - the scientific critic reads the draft with the general-peer-review skill
    Thresholds:
        none
    Wraps:
        - AtomisticSkills hyperparameter logging pattern
    Logs: the full trace path.

    The recombination rate and the cost are read from the outputs the trace stores: every gate after
    relaxation, with check 10 as recombination, counted per site-graph shell of the pair it gated, and every
    relaxation and force screen. The rate is that of the nearest shell gated. The draft is for the scientific
    critic and the human; numbers are printed as the tools reported them.
    """
    run = current_run()
    if run is None or run.campaign != campaign:
        raise ValueError(f"report needs the run of campaign {campaign} to be current")
    settings = project.current_settings()
    outputs = _outputs(run)
    shells = {p["candidate_id"]: p["site_graph_distance"] for out in outputs.get("pair_enumeration", []) for p in out["pairs"]}
    gated: Dict[str, GateResult] = {}
    for out in outputs.get("anomaly_filter", []):
        g = GateResult.model_validate(out)
        if g.stage == "after_relaxation":
            gated[g.candidate_id] = g
    shells.update({cid: shells[_pair_id(cid)] for cid in gated if _pair_id(cid) in shells})
    tally: Dict[int, List[int]] = {}
    for cid, g in gated.items():
        if cid in shells:
            recombined = any(v.check_id == 10 and not v.passed for v in g.verdicts)
            tally.setdefault(shells[cid], []).append(int(recombined))
    by_shell = {k: sum(v) / len(v) for k, v in sorted(tally.items())}
    rate = by_shell[min(by_shell)] if by_shell else 0.0
    relaxations = [r for out in outputs.get("relaxation", []) for r in out]
    cost = {"relaxations": float(len(relaxations)), "relaxation_steps": float(sum(r["steps"] for r in relaxations if not r["cache_hit"])),
            "cache_hits": float(sum(r["cache_hit"] for r in relaxations)),
            "force_screens": float(sum(len(out) for out in outputs.get("pull_force_screen", []))),
            "gates": float(len(gated))}
    rep = Report(campaign=campaign, final_states=final_states, rejected=rejected, recombination_rate=rate, recombination_rate_by_shell=by_shell,
                 doubt=flags, comparison_oc20neb=comparison or {}, cost=cost, trace_path=str(run.trace_path.relative_to(run.dir)),
                 settings_hash=project.settings_hash(settings))
    (run.dir / "report.json").write_text(rep.model_dump_json(indent=1))
    potentials = sorted({r["calculator"] for r in relaxations})
    (run.dir / "report.md").write_text(_markdown(rep, gated, shells, settings, potentials, checkpoints.passed(run.dir)))
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


def _markdown(rep: Report, gated: Dict[str, GateResult], shells: Dict[str, int], settings, potentials: List[str], choices) -> str:
    lines = [f"# Report: {rep.campaign}", "",
             f"{settings.adsorbate}* → {settings.product[0]}* + {settings.product[1]}* on {settings.metal}({settings.facet}). "
             f"Every energy below is from {', '.join(potentials) or 'no relaxation'}, the potential that relaxed the candidates; the settings "
             f"record, `{rep.settings_hash}`, is the lock in PROJECT.md. Decision trace `{rep.trace_path}`. Draft for the scientific critic and the human.", "",
             "## Final states", "",
             "Lateral interaction = E(FS near) − E(FS ∞), with E(FS ∞) = E(A\\*) + E(B\\*) − E(slab), each fragment alone on the slab.", "",
             "| Candidate | E(FS near), eV | E(FS ∞), eV | Lateral interaction, eV | A–B distance, Å | Site-graph distance |",
             "|---|---|---|---|---|---|"]
    lines += [f"| {f.candidate_id} | {f.E_near_eV:.4f} | {f.E_inf_eV:.4f} | {f.lateral_interaction_eV:+.4f} | {f.AB_distance_A:.2f} | {f.site_graph_distance} |"
              for f in rep.final_states] or ["| none picked | | | | | |"]
    lines += ["", "## Rejected pairs", "", "| Candidate | Stage | Failed checks |", "|---|---|---|"]
    lines += [f"| {g.candidate_id} | {g.stage} | " + "; ".join(f"{v.check_id} {v.name}{' ' + v.fragment if v.fragment else ''}: {v.reason}"
                                                           for v in g.verdicts if not v.passed) + " |" for g in rep.rejected] or ["| none | | |"]
    lines += ["", "## Recombination rate", "",
              f"Nearest shell gated: {rep.recombination_rate:.2f}, the share of its pairs whose A–B bond re-formed in relaxation, check 10.", "",
              "| Site-graph shell | Pairs gated | Recombination rate |", "|---|---|---|"]
    counts = Counter(shells[c] for c in gated if c in shells)
    lines += [f"| {k} | {counts[k]} | {v:.2f} |" for k, v in rep.recombination_rate_by_shell.items()] or ["| none | | |"]
    lines += ["", "## Doubt", "", "| Candidate | Trigger | Committee spread, eV | Calibrated error, eV | Escalated |", "|---|---|---|---|---|"]
    lines += [f"| {f.candidate_id} | {f.trigger} | {f.committee_spread_eV:.4f} | {f.calibrated_error_eV if f.calibrated_error_eV is not None else 'uncalibrated'} | "
              f"{'yes' if f.escalate else 'no'} |" for f in rep.doubt] or ["| none | | | | |"]
    lines += ["", "## The human's choices", "", "| Checkpoint | Who | Chosen | Reason |", "|---|---|---|---|"]
    lines += [f"| {c.checkpoint} | {c.who} | {', '.join(c.chosen) or 'approved'} | {c.reason} |" for c in choices] or ["| none yet | | | |"]
    lines += ["", "## Comparison with OC20NEB", ""]
    lines += [f"- {k}: {v}" for k, v in rep.comparison_oc20neb.items()] or ["Not run: the subset and the pass criterion are open: team decision, D3."]
    lines += ["", "## Cost", ""] + [f"- {k.replace('_', ' ')}: {v:g}" for k, v in rep.cost.items()]
    unchecked = Counter(f"check {v.check_id} {v.name}: {v.reason}" for g in gated.values() for v in g.verdicts if v.reason.startswith("not checked")
                        or v.reason.endswith("not checked"))
    lines += ["", "## Not checked", ""] + ([f"- {k}, {n} structure(s)" for k, n in sorted(unchecked.items())] or ["Every check ran on every gated structure."])
    return "\n".join(lines) + "\n"
