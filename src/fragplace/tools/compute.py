"""Where the heavy calls run and with what; the hpc-specialist's tool. Tools: compute_plan. Defined in fragplace.registry."""
from __future__ import annotations

import statistics
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .. import calculators
from ..execution.batch import hms, seconds
from ..execution.srun import BATCH_ABOVE_MIN, NEVER, RULE_LANES, recommend
from ..runtime import artifacts
from ..runtime.journal import log, traced
from ..schemas.records import StructureRef

# The force calls one item of each heavy step costs, in the order the steps run. Every number but the screen's one
# call is inferred, not measured, and gives way to a measured time.
FORCE_CALLS_PER_RELAXATION = 150          # BFGS to the study's fmax, well below the step cap of 500; inferred
FORCE_CALLS_PER_HOP = 2000                # the molecular dynamics and the relaxation of one hop; inferred
REFERENCE_RELAXATIONS = 3                 # A alone, B alone and the slab, for each picked state; an upper bound
HEAVY_STEPS: Tuple[Tuple[str, str, str], ...] = (
    ("site_enumeration", "2", "no force call: symmetry and ACAT's site graph"),
    ("pull_force_screen", "3.3", "one force call per placed candidate"),
    ("minima_hopping", "3.6", f"about {FORCE_CALLS_PER_HOP} force calls per hop, inferred"),
    ("anomaly_filter", "5", "the frequencies of check 5, six force calls per adsorbate atom and one more, per candidate"),
    ("relaxation", "4", f"about {FORCE_CALLS_PER_RELAXATION} force calls per candidate, inferred"),
    ("soap_clustering", "6", "no force call: SOAP descriptors"),
    ("uncertainty_estimation", "7", "one force call per kept state and committee member"),
    ("reference_energies", "solution", f"{REFERENCE_RELAXATIONS} relaxations per picked state, an upper bound"),
)
HEAVY_TOOLS = tuple(name for name, _, _ in HEAVY_STEPS)
RULE_KEYS = ("lane", "batch_above_min", "cpus", "mem_GB", "time", "workers", "partition")
NEEDED = ("lane", "cpus", "mem_GB", "time")
# Triton's CPU partitions, from skills/triton-hpc section 1: cores and memory per node, and the longest job.
PARTITIONS = {"interactive": (40, 191, 86400), "batch-skl": (40, 191, 5 * 86400), "batch-csl": (40, 191, 5 * 86400),
              "batch-milan": (128, 510, 5 * 86400)}
LARGEST = (max(p[0] for p in PARTITIONS.values()), max(p[1] for p in PARTITIONS.values()), max(p[2] for p in PARTITIONS.values()))
GAP_A = 2.0          # the adsorbate's lowest atom above the slab's highest, for the timing structure
REPEATS = 3          # timed force calls after one that loads the potential; the median is kept


@traced(step="1*", tool="compute_plan")
def compute_plan(calculator: str, slab: StructureRef, adsorbate: StructureRef, items: Dict[str, Optional[int]],
                 rules: Optional[Dict[str, Dict[str, Any]]], timing: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Measure the seconds per force call of the chosen potential once, on the selected cell with the adsorbate, and estimate per heavy step the minutes per item, the total when the items are known, and the lane the code's table recommends; with rules, check each proposed rule.

    Board steps: 1*. Status: core. Lane: gpu. Allowed roles: hpc-specialist.

    Inputs:
        calculator: str, the potential chosen at mlip_selection
        slab: StructureRef, the selected cell
        adsorbate: StructureRef, the adsorbate in vacuum, set on the slab for the timing
        items: dict heavy tool -> int | None, the items of its call when known
        rules: dict heavy tool -> rule | None; a rule: lane worker | batch | auto, batch_above_min, cpus, mem_GB, time HH:MM:SS, workers, partition optional
        timing: dict | None, the measurement cached for the study; measured again when None or for another potential or size
    Outputs:
        timing: dict: calculator, atoms, s_per_force_call, force_calls_per_item
        estimates: dict heavy tool -> force calls and minutes per item, items, total minutes, lane and why
        rules: dict heavy tool -> rule, checked; None without rules
        warnings: list[str], a rule whose time is shorter than its estimate
    Checks:
        - the force call runs in a lane, never on a login node
        - a rule names a heavy tool, a lane of worker, batch or auto, and sets cpus, mem_GB and time
        - cores, memory and time within the partition's limits; no GPU partition while torch is CPU only
        - workers no more than cpus
    Thresholds:
        batch_above_min: 70, inferred from about 1.5 s per MACE-MP-small force call on 146 atoms with 2 CPUs
        batch_cpus: 8 to 16, inferred
        force_calls_per_relaxation: 150, inferred: BFGS to the study's fmax, below the step cap of 500
    Wraps:
        - fragplace.calculators
        - fragplace.execution.srun.TABLE
        - skills/triton-hpc decision table
    Logs: the measured seconds per force call; the estimate per heavy step; every rule refused, with its reason.

    The timing structure is the selected cell with the whole adsorbate set GAP_A above its highest atom, the size
    every candidate of the study has. One force call loads the potential; the median of REPEATS more, each on a
    slightly moved copy so no calculator answers from its cache, is the seconds per force call. A timing passed in
    for the same potential and the same number of atoms is used as it is, so a study measures once. The minutes of
    one item are its force calls times that time; the total is known only once the step before has made the items,
    and until then the table's lane is auto. A rule is refused, with every reason at once, when it names a tool
    that is not a heavy step, a lane that is not worker, batch or auto, or leaves out cpus, mem_GB or time; when
    auto has no batch_above_min; when its cores, memory or time pass the partition's limits, or the largest
    partition's when it names none; when it names a GPU partition; and when workers exceed cpus.
    """
    atoms = timing_structure(artifacts.read(slab), artifacts.read(adsorbate))
    if timing and timing.get("calculator") == calculator and timing.get("atoms") == len(atoms) and timing.get("s_per_force_call"):
        per_call = float(timing["s_per_force_call"])
        log("compute_plan", f"{calculator} on {len(atoms)} atoms: {per_call:.4g} s per force call, as measured before")
    else:
        per_call = measure(calculator, atoms)
        log("compute_plan", f"{calculator} on {len(atoms)} atoms: {per_call:.4g} s per force call, the median of {REPEATS} calls")
    n_ads = len(artifacts.read(adsorbate))
    estimates = {}
    for name, step, basis in HEAVY_STEPS:
        calls = force_calls(name, n_ads)
        per_item = calls * per_call / 60
        count = items.get(name)
        total = per_item * count if count is not None else None
        lane, why = recommend(total)
        estimates[name] = {"step": step, "force_calls_per_item": calls, "basis": basis, "minutes_per_item": round(per_item, 3), "items": count,
                           "total_minutes": None if total is None else round(total, 2), "lane": lane, "why": why}
        log("compute_plan", f"{name}: {per_item:.3g} min per item" + (f", {total:.3g} min for {count}" if total is not None else ", items not known yet")
            + f"; the table says {lane}")
    out_timing = {"calculator": calculator, "atoms": len(atoms), "s_per_force_call": per_call, "force_calls_per_item": FORCE_CALLS_PER_RELAXATION}
    checked, warnings = None, []
    if rules is not None:
        checked, problems, warnings = check_rules(rules, estimates)
        if problems:
            for p in problems:
                log("compute_plan", f"rule refused: {p}")
            raise ValueError("; ".join(problems))
    return {"timing": out_timing, "estimates": estimates, "rules": checked, "warnings": warnings, "never": NEVER}


def timing_structure(slab, adsorbate):
    """The selected cell with the whole adsorbate centred over it, its lowest atom GAP_A above the highest slab atom."""
    ads = adsorbate.copy()
    ads.set_constraint()
    ads.set_cell(slab.cell)
    ads.set_pbc(slab.pbc)
    centre = (slab.cell[0] + slab.cell[1]) / 2
    ads.positions += np.array([centre[0], centre[1], slab.positions[:, 2].max() + GAP_A]) - np.array(
        [*ads.positions[:, :2].mean(axis=0), ads.positions[:, 2].min()])
    return slab + ads


def measure(calculator: str, atoms) -> float:
    """Seconds per force call: one call to load the potential, then the median of REPEATS on slightly moved copies."""
    adapter = calculators.get(calculator)
    adapter.energy_forces(atoms)
    rng = np.random.default_rng(0)
    times = []
    for _ in range(REPEATS):
        moved = atoms.copy()
        moved.positions = moved.positions + rng.normal(0.0, 0.01, moved.positions.shape)
        start = time.perf_counter()
        adapter.energy_forces(moved)
        times.append(time.perf_counter() - start)
    return float(statistics.median(times))


def force_calls(name: str, adsorbate_atoms: int) -> int:
    """The force calls of one item of a heavy step, as HEAVY_STEPS says."""
    return {"site_enumeration": 0, "soap_clustering": 0, "pull_force_screen": 1, "uncertainty_estimation": 1,
            "minima_hopping": FORCE_CALLS_PER_HOP, "anomaly_filter": 6 * adsorbate_atoms + 1, "relaxation": FORCE_CALLS_PER_RELAXATION,
            "reference_energies": REFERENCE_RELAXATIONS * FORCE_CALLS_PER_RELAXATION}[name]


def check_rules(rules: Dict[str, Dict[str, Any]], estimates: Dict[str, Dict[str, Any]]) -> Tuple[Dict[str, Dict[str, Any]], List[str], List[str]]:
    """(rules as checked, problems, warnings): the rules with numbers as numbers and time as HH:MM:SS, every reason a
    rule is refused, and every rule whose time is shorter than its step's known total over its workers."""
    checked: Dict[str, Dict[str, Any]] = {}
    problems: List[str] = []
    warnings: List[str] = []
    if not isinstance(rules, dict) or not rules:
        return checked, ["rules: give one rule per heavy tool, keyed by the tool's name"], warnings
    for name, rule in rules.items():
        bad = len(problems)
        if name not in HEAVY_TOOLS:
            problems.append(f"{name}: not a heavy step; rules go to {', '.join(HEAVY_TOOLS)}")
            continue
        if not isinstance(rule, dict):
            problems.append(f"{name}: a rule is a dict of {', '.join(RULE_KEYS)}")
            continue
        unknown = [k for k in rule if k not in RULE_KEYS]
        missing = [k for k in NEEDED if rule.get(k) in (None, "")]
        if unknown:
            problems.append(f"{name}: unknown fields {', '.join(unknown)}; a rule takes {', '.join(RULE_KEYS)}")
        if missing:
            problems.append(f"{name}: set {', '.join(missing)}; Triton's defaults, 15 min and 500 MB per CPU, end a relaxation early")
        lane = rule.get("lane")
        if lane is not None and lane not in RULE_LANES:
            problems.append(f"{name}: lane {lane!r}; a rule's lane is {', '.join(RULE_LANES)}")
        out: Dict[str, Any] = {"lane": lane}
        out["batch_above_min"] = _number(rule.get("batch_above_min"), name, "batch_above_min", problems, float)
        if lane == "auto" and out["batch_above_min"] is None and "batch_above_min" not in missing:
            problems.append(f"{name}: lane auto needs batch_above_min, the expected minutes above which the call goes to batch; "
                            f"the table's is {BATCH_ABOVE_MIN:g}, inferred")
        out["cpus"] = _number(rule.get("cpus"), name, "cpus", problems, int)
        out["mem_GB"] = _number(rule.get("mem_GB"), name, "mem_GB", problems, float)
        out["workers"] = _number(rule.get("workers", 1), name, "workers", problems, int)
        wall = None
        if rule.get("time") not in (None, ""):
            try:
                wall = seconds(rule["time"])
                out["time"] = hms(wall)
            except ValueError as e:
                problems.append(f"{name}: {e}")
        partition = rule.get("partition")
        out["partition"] = partition or None
        if partition and str(partition).startswith("gpu"):
            problems.append(f"{name}: partition {partition}: the .venv's torch is CPU only, so no GPU rule for now")
        elif partition and partition not in PARTITIONS:
            problems.append(f"{name}: partition {partition!r}; Triton's CPU partitions are {', '.join(PARTITIONS)}")
        cores, mem, longest = PARTITIONS.get(partition, LARGEST) if partition else LARGEST
        where = f"partition {partition}" if partition else "the largest CPU partition"
        if out["cpus"] is not None and out["cpus"] > cores:
            problems.append(f"{name}: {out['cpus']} CPUs; {where} has {cores} per node")
        if out["mem_GB"] is not None and out["mem_GB"] > mem:
            problems.append(f"{name}: {out['mem_GB']:g} GB; {where} has {mem} GB per node")
        if wall is not None and (wall <= 0 or wall > longest):
            problems.append(f"{name}: time {rule['time']}; {where} runs a job at most {hms(longest)}")
        if out["workers"] is not None and out["cpus"] is not None and out["workers"] > out["cpus"]:
            problems.append(f"{name}: {out['workers']} workers on {out['cpus']} CPUs; size the pool to the cores")
        total = estimates.get(name, {}).get("total_minutes")
        if wall is not None and total is not None and out["workers"]:
            need = total / out["workers"]
            if wall < need * 60:
                warnings.append(f"{name}: time {out['time']} is shorter than the estimate, {need:.0f} min over {out['workers']} worker(s)")
        if len(problems) == bad:
            checked[name] = {k: v for k, v in out.items() if v is not None}
    return checked, problems, warnings


def _number(value: Any, name: str, key: str, problems: List[str], kind) -> Any:
    """value as an int or a float above zero, or None when not given; a problem otherwise."""
    if value is None or value == "":
        return None
    try:
        number = kind(value)
    except (TypeError, ValueError):
        problems.append(f"{name}: {key} {value!r} is not a number")
        return None
    if isinstance(value, bool) or number <= 0 or (kind is int and number != float(value)):
        problems.append(f"{name}: {key} {value!r}; give a {'whole ' if kind is int else ''}number above zero")
        return None
    return number
