"""The study in brief: one short block per step in runs/<study>/summary.md, written by code from the tool's own
answer, so every number in it is one a tool returned. The orchestrator shows the block after the step and the
whole file at the end; report.md opens with it.

A block has a heading with the step and what it did, one or two sentences on what came out, at most one small
table, the question the human is asked next when one is due, and a last line naming the tool and the pictures the
step wrote. A step run again replaces its block, so the file always reads in the order of the pipeline; the gate
before relaxation has a block of its own, keyed anomaly_filter_before. A block written from an answer whose keys
have changed says so and lists the keys it got; a summary never fails the step it summarises.
"""
from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Optional, Sequence

ORDER = ("literature_lookup", "structure_retrieval", "calculation_protocol", "mlip_selection", "compute_plan", "site_enumeration", "pair_enumeration",
         "adsorbate_placement", "pull_force_screen", "minima_hopping", "anomaly_filter_before", "relaxation", "anomaly_filter",
         "soap_clustering", "uncertainty_estimation", "ranking", "reference_energies", "report")
TITLES = {"literature_lookup": "Published values", "structure_retrieval": "Inputs, fragments and the selected cell",
          "calculation_protocol": "Settings proposed for the lock", "mlip_selection": "Potential chosen", "compute_plan": "Compute plan",
          "site_enumeration": "Adsorption sites",
          "pair_enumeration": "Pairs in the window", "adsorbate_placement": "B placed on each pair", "pull_force_screen": "Pull-force screen",
          "minima_hopping": "Minima hopping", "anomaly_filter_before": "Gate before relaxation", "relaxation": "Relaxation",
          "anomaly_filter": "Gate after relaxation", "soap_clustering": "SOAP clustering", "uncertainty_estimation": "Uncertainty",
          "ranking": "Ranking", "reference_energies": "Final states and the separated limit", "report": "Report"}
STEPS = {"prompt": "Input prompt", "solution": "Solution"}
ASKED = {"approve settings": "approve the settings", "approve the plan": "approve the plan", "review flagged cases": "review the flagged cases",
         "pick up to five final states": "pick up to five final states", "interpret results": "interpret the results"}
FIRST_LOOK = ("sheet.png", "sites.png", "inputs.png", "rejected.png", "passed.png")
MARK = re.compile(r"<!-- step:(\w+) -->\n?")
NEXT = re.compile(r"^Next: you are asked to .*\n", re.MULTILINE)
ROWS = 8     # a longer table shows its first rows and says how many it left out
REFERENCE_LEVEL = ("Every energy in this study comes from the potential chosen at 1*; DFT runs only through dft_single_points, an "
                   "extension not built yet. These settings name the level of theory the inputs and the published values are compared at.")
NO_DFT_LINE = "No DFT runs in this study: the potential chosen at 1* computes every energy, so the lock holds no DFT setting."


# ---- the parts of a block
def _cell(x: Any) -> str:
    if x is None:
        return ""
    if isinstance(x, float):
        return f"{x:g}"
    if isinstance(x, (list, tuple)):
        return " × ".join(_cell(v) for v in x)
    return str(x).replace("|", "/").replace("\n", " ")


def _table(head: Sequence[str], rows: Sequence[Sequence[Any]], what: str = "rows", limit: int = ROWS) -> List[str]:
    lines = ["", "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    lines += ["| " + " | ".join(_cell(x) for x in r) + " |" for r in rows[:limit]]
    if len(rows) > limit:
        lines += ["", f"{len(rows) - limit} more {what} are in the step's answer and the trace."]
    return lines + [""]


def _num(x: Any, digits: int, sign: bool = False) -> str:
    if not isinstance(x, (int, float)):
        return "" if x is None else str(x)
    return f"{x:+.{digits}f}" if sign else f"{x:.{digits}f}"


def _ids(ids: Sequence[str], most: int = 6) -> str:
    ids = list(ids)
    return ", ".join(ids[:most]) + (f" and {len(ids) - most} more" if len(ids) > most else "")


def _n(count: Any, noun: str, plural: Optional[str] = None) -> str:
    """A count with its noun: 1 pair, 2 pairs."""
    return f"{count} {noun if count == 1 else plural or noun + 's'}"


def _v(count: Any, one: str, many: str) -> str:
    return one if count == 1 else many


def benchmark_text(v: Optional[Dict[str, Any]]) -> str:
    """One potential's benchmark at 1* in words: why it is unavailable, or its E_ads error when the labels carry
    energies, how far an adsorbate atom moved when it relaxed the initial state, and the residual fmax at the
    supplied geometries."""
    v = v or {}
    if not v.get("available", True):
        return "; ".join(v.get("anomalies") or []) or "unavailable"
    parts = ["circular: scored on labels computed with this potential"] if v.get("circular") else []
    parts += [f"E_ads error {v['error_eV']:.3f} eV"] if v.get("error_eV") is not None else []
    if v.get("max_adsorbate_displacement_A") is not None:
        parts.append(f"an adsorbate atom moved up to {v['max_adsorbate_displacement_A']:.3f} Å")
    if v.get("residual_fmax_eV_per_A") is not None:
        parts.append(f"residual fmax {v['residual_fmax_eV_per_A']:.3f} eV/Å")
    parts += [a for a in v.get("anomalies") or [] if not (v.get("circular") and "circular" in a)]
    return "; ".join(parts) or "no benchmark"


def benchmark_rule(bench: Dict[str, Any]) -> str:
    """The rule the choice at 1* followed: the E_ads error when the labels carry energies, else the geometry."""
    if any((v or {}).get("benchmark") == "geometric" for v in bench.values()):
        return "the least adsorbate displacement, then the smaller residual fmax"
    return "the smallest E_ads error"


def _asks(out: Dict[str, Any]) -> List[str]:
    due = out.get("checkpoint_due")
    return ["", f"Next: you are asked to {ASKED.get(due, due)}."] if due else []


def _settings(c):
    try:
        return c.settings(locked=False)
    except Exception:  # noqa: BLE001 - the summary reads PROJECT.md only for names
        return None


# ---- one formatter per tool, from the dict calls.<tool> returns
def _literature(c, out):
    values = out.get("values") or []
    found = out.get("found")
    new = len(found) if isinstance(found, list) else int(found or 0)
    missing = sorted({str(x).split(":", 1)[0] for x in out.get("none_for") or []})
    if not values:
        return [f"No published value found{' for ' + ', '.join(missing) if missing else ''}; check 7 runs without a prior, and d comes from the "
                "structures."]
    checked = sum(1 for v in values if v.get("verified"))
    added = "Rewritten after the human's checks." if out.get("after_verify") else \
        f"This lookup added {new or 'none'}" + (f" and found nothing for {', '.join(missing)}." if missing else ".")
    rows = [[v["index"] if str(v.get("index", "")).startswith("lit:") else f"lit:{v.get('index')}", v.get("quantity"), v.get("system"),
             f"{_cell(v.get('value'))} {v.get('unit') or ''}".strip(), v.get("functional") or "", v.get("site") or "", "yes" if v.get("verified") else "no",
             v.get("source")] for v in values]
    return [f"{_n(len(values), 'published value')} on the study's list, {checked or 'none'} checked by the human against its source; nothing "
            "unchecked is used.",
            added] + _table(
        ["Ref", "Quantity", "System", "Value", "Functional", "Site", "Checked", "Source"], rows, "values")


def _retrieval(c, out):
    s = _settings(c)
    rep, cell = out.get("cell_repeat") or ["?", "?"], out.get("cell_A") or ["?", "?"]
    return [f"{s.adsorbate if s else 'The adsorbate'} cleaved into A = {out.get('fragment_A')}, which keeps the binding atom, and "
            f"B = {out.get('fragment_B')}.",
            f"Selected cell: {rep[0]} × {rep[1]} of the supplied slab, {_cell(cell[0])} × {_cell(cell[1])} Å with {out.get('atoms_in_cell')} atoms, "
            "so the pair stays clear of its periodic images."]


def _protocol(c, out):
    p = out.get("proposed") or {}
    dft = out.get("dft", "functional" in p)
    names = ((("functional", "Functional"), ("dispersion", "Dispersion"), ("pseudopotential_family", "Pseudopotentials"), ("cutoff_eV", "Cutoff, eV"),
              ("kmesh", "k-mesh"), ("smearing", "Smearing"), ("sigma_eV", "σ, eV"), ("layers", "Layers")) if dft else ()) + (
             ("cell_repeat", "Cell repeat"), ("force_threshold_eV_per_A", "Force threshold, eV/Å"), ("gas_references", "Gas references")) + (
             (("convergence_target_meV", "Convergence target, meV"),) if dft else ())
    origins = out.get("origins") or {}
    rows = [[name, _setting(p.get(key)), origins.get(key, "")] for key, name in names if key in p]
    reason = str(p.get("protocol_reason") or "no reason given").rstrip()
    chosen = ["Settings from a physics choice were passed by the computational-chemist from the human's answers; approving confirms them."] \
        if "physics choice" in origins.values() else []
    return [f"Protocol {p.get('protocol')}: {reason}{'' if reason.endswith(('.', '!', '?')) else '.'} Nothing is locked until the human approves."] + _table(
        ["Setting", "Value", "From"], rows, "settings", limit=len(names)) + [REFERENCE_LEVEL if dft else NO_DFT_LINE] + chosen + _asks(out)


def _setting(value: Any) -> Any:
    """A proposed setting as the table shows it: a gas reference as its species and energy."""
    if value is None:
        return "not set"
    if isinstance(value, list) and value and isinstance(value[0], dict) and "species" in value[0]:
        return ", ".join(f"{g['species']} {_cell(g.get('energy_eV'))} eV" for g in value)
    return value if value != [] else "none"


def _mlip(c, out):
    bench = out.get("benchmark") or {}
    rows = [[k, benchmark_text(v)] for k, v in bench.items()]
    using, best, rule = out.get("using"), out.get("best"), benchmark_rule(bench)
    committee = out.get("committee") or []
    why = f"; {best} scored best by {rule}" if best and best != using else f", {rule} on the supplied inputs" if best else ""
    lines = [f"Using {using}{why}. Committee for step 7: {', '.join(committee) or 'none'}."]
    if (bench.get(using) or {}).get("circular"):
        lines.append(f"Its score is circular: the labels were computed with {using} itself, so it says nothing about {using}'s error.")
    if len(committee) == 1:
        lines.append("A committee of one measures no disagreement, so step 7 cannot calibrate doubt.")
    return lines + _table(
        ["Potential", "Benchmark on the supplied inputs"], rows, "potentials") + _asks(out)


def plan_rows(data: Dict[str, Any]) -> List[tuple]:
    """The compute plan as the approve-the-plan box and the briefing show it: per heavy tool its lane, threshold, CPUs,
    memory, time and workers, then the measured seconds per force call; one row for the default lane without a plan."""
    plan, timing = data.get("compute_plan") or {}, data.get("compute_timing") or {}
    rows = []
    for name, r in (plan.get("rules") or {}).items():
        lane = r.get("lane")
        if lane == "auto":
            lane = f"auto, batch above {_cell(r.get('batch_above_min'))} min"
        rows.append((name, f"{lane}; {r.get('cpus')} CPUs, {_cell(r.get('mem_GB'))} GB, {r.get('time')}, {_n(r.get('workers', 1), 'worker')}"
                           + (f", partition {r['partition']}" if r.get("partition") else "")))
    if not rows:
        rows.append(("Compute plan", "none proposed: the heavy tools run in the default lane"))
    elif plan.get("reason"):
        rows.append(("Why", plan["reason"]))
    if timing:
        rows.append(("Force call", f"{_num(timing.get('s_per_force_call'), 4)} s with {timing.get('calculator')} on {timing.get('atoms')} atoms, measured"))
    return rows


def _compute(c, out):
    timing, est, rules = out.get("timing") or {}, out.get("estimates") or {}, out.get("proposed") or {}
    first = (f"One force call of {timing.get('calculator')} on {timing.get('atoms')} atoms, the selected cell with the adsorbate, takes "
             f"{_num(timing.get('s_per_force_call'), 4)} s, measured once for the study.")
    rows = [[k, e.get("force_calls_per_item"), _num(e.get("minutes_per_item"), 2), "" if e.get("items") is None else e.get("items"),
             "not known yet" if e.get("total_minutes") is None else _num(e.get("total_minutes"), 1), e.get("lane"),
             (rules.get(k) or {}).get("lane", "")] for k, e in est.items()]
    lines = [first, "Every count of force calls but the screen's is inferred, and gives way to a measured time."]
    lines += _table(["Heavy step", "Force calls per item", "Min per item", "Items", "Total, min", "Table says", "Proposed"], rows, "steps", limit=len(rows))
    if rules:
        why = str(out.get("reason") or "no reason given").rstrip()
        lines += [f"The hpc-specialist proposed {_n(len(rules), 'rule')}: {why}{'' if why.endswith(('.', '!', '?')) else '.'} The human approves them "
                  "with the plan."]
    else:
        lines += ["No rule proposed yet: an estimate only, and the heavy tools run in the default lane."]
    lines += [f"Warning: {w}" for w in out.get("warnings") or []]
    return lines + _asks(out)


def _sites(c, out):
    kinds = out.get("inequivalent") or []
    burnside, count = out.get("burnside_count"), out.get("count")
    rows = [[k.get("site"), k.get("label"), k.get("group"), k.get("coordination"), k.get("atom_beneath") or "none", k.get("copies")] for k in kinds]
    return [f"{_n(count, 'inequivalent site')} of {out.get('sites_in_cell')} in the cell, group {out.get('symmetry')}; the Burnside count "
            + ("agrees." if burnside == count else f"gives {burnside}.")
            + f" pymatgen's finder, which labels fcc and hcp both hollow, finds {out.get('pymatgen_baseline')}."] + _table(
        ["Site", "Kind", "Group", "Coordination", "Atom beneath", "In the cell"], rows, "sites")


def _pairs(c, out):
    a, window, pairs = out.get("A_site") or {}, out.get("window_A"), out.get("pairs") or []
    first = f"A stays at its initial-state site, {a.get('label')} site {a.get('site')}."
    if window:
        first += f" d = {_cell(out.get('d_bond_A'))} Å, {out.get('d_source') or 'measured'}; B goes {_cell(window[0])} to {_cell(window[1])} Å from A."
    if not pairs:
        return [first, "No B site lies in the window."]
    rows = [[p.get("id"), p.get("B_site"), p.get("site_graph_distance"), _num(p.get("in_plane_A"), 2)] for p in pairs]
    return [first, f"{_n(len(pairs), 'symmetry-distinct pair')}, nearest first."] + _table(["Pair", "B site", "Site-graph shell", "In plane, Å"], rows, "pairs")


def _placement(c, out):
    n = out.get("count") if out.get("count") is not None else len(out.get("placed") or [])
    pairs = len(c.data.get("pairs", [])) if hasattr(c, "data") else None
    return [f"{_n(n, 'candidate')} from {_n(pairs, 'pair')}: B on each pair's site in every orientation the site allows, with a small random "
            "displacement; nothing is relaxed yet."]


def _screen(c, out):
    q = out.get("queue") or []
    flagged = [x.get("id") for x in q if x.get("flagged")]
    rows = [[k, x.get("id"), _num(x.get("force_on_B_towards_A_eV_per_A"), 3), "yes" if x.get("flagged") else "no"] for k, x in enumerate(q, start=1)]
    return [f"{_n(len(q), 'placed candidate')} screened, one force call each. Pulled back towards A above the threshold, so last in the "
            f"queue: {_ids(flagged) if flagged else 'none'}. No candidate is dropped."] + _table(
        ["Queue", "Candidate", "Force on B towards A, eV/Å", "Pulled back"], rows, "candidates")


def _hopping(c, out):
    minima = out.get("minima") or []
    rows = [[x.get("id"), _num(x.get("energy_eV"), 3)] for x in minima]
    return [f"{_n(len(minima), 'minimum', 'minima')} found by minima hopping from the first queued pair, for the relaxation queue."] + (
        _table(["Minimum", "E, eV"], rows, "minima") if rows else [])


def _gate_before(c, out):
    passed, rejected = out.get("passed") or [], out.get("rejected") or {}
    s = _settings(c)
    listed = (s.decisions.get("anomaly_filter.checks_before_relaxation") if s else None) or []
    checks = f", checks {', '.join(str(k) for k in listed)}" if listed else ""
    first = (f"{len(passed)} of {_n(len(passed) + len(rejected), 'placed candidate')} {_v(len(passed), 'passes', 'pass')} the gate before "
             f"relaxation{checks}; " + (f"{len(rejected)} {_v(len(rejected), 'fails and is', 'fail and are')} not relaxed." if rejected
                                        else "all go on to relaxation."))
    rows = [[k, "; ".join(v) if isinstance(v, list) else v] for k, v in rejected.items()]
    return [first] + (_table(["Not relaxed", "Failed checks"], rows, "candidates") if rows else [])


def _relaxation(c, out):
    res = [r for r in out.get("results") or [] if isinstance(r.get("energy_eV"), (int, float))]
    calc = (c.data.get("mlip") or {}).get("calculator") if hasattr(c, "data") else None
    stuck = [r.get("id") for r in res if not r.get("converged", True)]
    hits = sum(1 for r in res if r.get("cache_hit"))
    first = (f"{_n(len(res), 'candidate')} relaxed with {calc or 'the chosen potential'}: {len(res) - len(stuck)} converged"
             + (f", {len(stuck)} did not: {_ids(stuck)}" if stuck else "") + (f"; {hits} came from the cache" if hits else "") + ".")
    if not res:
        return [first]
    ranked = sorted(res, key=lambda r: r["energy_eV"])
    low = ranked[0]
    rows = [[r.get("id"), _num(r["energy_eV"], 3), _num(r["energy_eV"] - low["energy_eV"], 3, sign=True), r.get("steps"),
             "yes" if r.get("converged", True) else "no"] for r in ranked]
    return [first, f"Lowest energy: {low.get('id')}; ΔE is measured from it."] + _table(["Candidate", "E, eV", "ΔE, eV", "Steps", "Converged"], rows,
                                                                                         "candidates")


def _gate(c, out):
    passed, rejected = out.get("passed") or [], out.get("rejected") or {}
    first = (f"{len(passed)} of {_n(len(passed) + len(rejected), 'relaxed candidate')} {_v(len(passed), 'passes', 'pass')} every check; "
             + (f"{len(rejected)} {_v(len(rejected), 'fails and is', 'fail and are')} never kept." if rejected else "none fails."))
    rows = [[k, "; ".join(v) if isinstance(v, list) else v] for k, v in rejected.items()]
    lines = [first] + (_table(["Rejected", "Failed checks"], rows, "candidates") if rows else [])
    if out.get("not_checked"):
        lines += ["", "Not checked: " + "; ".join(str(x).replace(": not checked: ", ": ") for x in out["not_checked"]) + "."]
    return lines


def _cluster(c, out):
    clusters, kept = out.get("clusters") or [], out.get("kept") or []
    rows = [[k.get("id"), len(k.get("members") or []), k.get("nearest"), k.get("lowest")] for k in clusters if isinstance(k, dict)]
    return [f"{_n(len(clusters), 'SOAP cluster')} of the candidates that passed; {len(kept)} kept, the nearest and the lowest of each, "
            f"nearest first: {_ids(kept)}."] + (_table(["Cluster", "Members", "Nearest", "Lowest"], rows, "clusters") if rows else [])


def _doubt(c, out):
    flags = out.get("flags") or []
    escalated = [f.get("candidate_id") for f in flags if f.get("escalate")]
    rows = [[f.get("candidate_id"), "not measured" if f.get("trigger") == "unmeasured" else _num(f.get("committee_spread_eV"), 4),
             f.get("trigger"), "yes" if f.get("escalate") else "no"] for f in flags]
    return [f"{_n(len(flags), 'kept state')} checked against the committee; {len(escalated)} escalated to the human"
            + (f": {_ids(escalated)}." if escalated else ".")] + _table(["Candidate", "Committee spread, eV", "Trigger", "Escalated"], rows, "flags") + _asks(out)


def _ranking(c, out):
    ranked = out.get("ranked") or []
    rows = [[r.get("rank"), r.get("id"), r.get("reason")] for r in ranked]
    return [f"{_n(len(ranked), 'state')} ranked, nearest first, then by energy; the human picks the final states from them."] + _table(
        ["Rank", "Candidate", "Why"], rows, "candidates") + _asks(out)


def _references(c, out):
    states = out.get("final_states") or []
    rows = [[f.get("candidate_id"), _num(f.get("E_near_eV"), 3), _num(f.get("E_inf_eV"), 3), _num(f.get("lateral_interaction_eV"), 3, sign=True),
             _num(f.get("AB_distance_A"), 2), f.get("site_graph_distance")] for f in states]
    from ..tools.report import ads_against, references_used
    used = references_used(c.run)
    reaction = (" The reaction energy is E(FS near) − E(IS), with E(IS) from " + "; and in another call, ".join(used["initial_state"]) + "."
                if used["initial_state"] else "")
    return [f"{_n(len(states), 'final state')} the human picked. E(FS ∞) puts each fragment alone on the slab; the lateral interaction is "
            f"E(FS near) − E(FS ∞). E_ads(A*) and E_ads(B*) are against {ads_against(used)}.{reaction}"] + _table(["Candidate", "E(FS near), eV", "E(FS ∞), eV", "Lateral, eV", "A–B, Å", "Shell"], rows, "states")


def _report(c, out):
    rate, shells = out.get("recombination_rate"), out.get("by_shell") or {}
    states = out.get("final_states")
    n = len(states) if isinstance(states, list) else states
    first = (f"report.md holds {_n(n, 'final state')} and {_n(out.get('rejected'), 'rejected candidate')} with their reasons"
             + (f"; {rate:.0%} of the nearest shell gated recombined." if isinstance(rate, (int, float)) else "."))
    rows = [[k, f"{v:.0%}" if isinstance(v, (int, float)) else v] for k, v in shells.items()]
    return [first] + (_table(["Site-graph shell", "Recombined"], rows, "shells") if rows else []) + _asks(out)


FORMATS: Dict[str, Callable[[Any, Dict[str, Any]], List[str]]] = {
    "literature_lookup": _literature, "structure_retrieval": _retrieval, "calculation_protocol": _protocol, "mlip_selection": _mlip,
    "compute_plan": _compute,
    "site_enumeration": _sites, "pair_enumeration": _pairs, "adsorbate_placement": _placement, "pull_force_screen": _screen,
    "minima_hopping": _hopping, "anomaly_filter_before": _gate_before, "relaxation": _relaxation, "anomaly_filter": _gate,
    "soap_clustering": _cluster, "uncertainty_estimation": _doubt, "ranking": _ranking, "reference_energies": _references, "report": _report,
}


def _files(tool_name: str, files: Sequence[str]) -> str:
    """The block's last line: the tool, the folder of the step's files and the picture to open first."""
    tool = f"`{tool_name.removesuffix('_before')}`" + (" before relaxation" if tool_name.endswith("_before") else "")
    if tool_name == "report":
        return f"Tool {tool}; open [report.md](report.md)."
    if not files:
        return f"Tool {tool}."
    pictures = [f for f in files if f.endswith(".png")]
    first = next((f for name in FIRST_LOOK for f in pictures if f.rsplit("/", 1)[-1] == name), pictures[0] if pictures else files[0])
    folder = first.rsplit("/", 1)[0] + "/" if "/" in first else ""
    return f"Tool {tool}; {_n(len(files), 'file')} in `{folder}`, open [{first.rsplit('/', 1)[-1]}]({first}) first."


def _head(c) -> str:
    s = _settings(c)
    system = f"{s.adsorbate}* → {s.product[0]}* + {s.product[1]}* on {s.metal}({s.facet}). " if s else ""
    return (f"# {c.run.study} in brief\n\n{system}One block per step, in the order of the pipeline, written by code from the tool's answer; "
            "the pictures and .xyz files are under geometries/.\n")


def write(c, tool_name: str, step: Optional[str], out: Dict[str, Any], files: List[str]) -> str:
    """Write or replace the step's block in summary.md and return it without its marker; empty for a tool that
    makes no summary."""
    if tool_name not in FORMATS:
        return ""
    try:
        lines = FORMATS[tool_name](c, out or {})
    except Exception as e:  # noqa: BLE001 - an answer with other keys than the formatter knows
        lines = [f"This block could not be read from the tool's answer, {type(e).__name__}: {e}. The answer had: {', '.join(sorted(out or {}))}."]
    heading = f"## {STEPS.get(step or '', f'Step {step}')} · {TITLES[tool_name]}"
    block = "\n".join([f"<!-- step:{tool_name} -->", heading, "", *lines, "", _files(tool_name, files)])
    block = re.sub(r"\n{3,}", "\n\n", block).strip() + "\n"
    path = c.run.dir / "summary.md"
    blocks = _blocks(path.read_text() if path.exists() else "")
    blocks[tool_name] = block
    order = sorted(blocks, key=lambda k: ORDER.index(k) if k in ORDER else len(ORDER))
    path.write_text(_head(c) + "".join("\n" + blocks[k] for k in order))
    return block.split("\n", 1)[1]


def _blocks(text: str) -> Dict[str, str]:
    marks = list(MARK.finditer(text))
    return {m.group(1): text[m.start():marks[k + 1].start() if k + 1 < len(marks) else len(text)].rstrip() + "\n" for k, m in enumerate(marks)}


def refresh_literature(c) -> None:
    """Rewrite the published-values block once the human ticked values at Verify, so the block says which are checked."""
    from ..schemas.records import LiteratureValue
    keys = {"quantity", "system", "value", "unit", "functional", "site", "source"}
    values = [{"index": f"lit:{k}", "verified": v.verified_by_human, **v.model_dump(include=keys)}
              for k, v in enumerate(c.many("literature", LiteratureValue))]
    write(c, "literature_lookup", "prompt", {"values": values, "after_verify": True}, [])


def full(c) -> str:
    """The whole summary for the end of the study and the head of the report: without the markers, and without the
    lines that said which question came next, since by then every one was asked."""
    path = c.run.dir / "summary.md"
    if not path.exists():
        return ""
    return re.sub(r"\n{3,}", "\n\n", NEXT.sub("", MARK.sub("", path.read_text())))
