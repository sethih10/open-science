"""compute_plan as the hpc-specialist calls it at 1*: the estimate from one measured force call, a proposal checked
and recorded with its reason, a rule refused with every reason, no change once the human has approved the plan, and
the plan in the approve-the-plan box. The example study with EMT, driven through calls as the orchestrator drives it."""
import inspect

import pytest

from fragplace.registry.tools import BY_NAME
from fragplace.runtime import artifacts
from fragplace.runtime.journal import set_run
from fragplace.schemas.records import StructureRef
from fragplace.study import calls, human
from fragplace.study.store import Study, briefing, record_choice
from fragplace.tools.compute import HEAVY_TOOLS, check_rules, compute_plan

pytest.importorskip("ase")
pytest.importorskip("acat")

from fragplace.study.example import build_example  # noqa: E402
from test_tool_fixes import docstring_head  # noqa: E402

C = "planned"
RULES = {"relaxation": {"lane": "auto", "batch_above_min": 70, "cpus": 8, "mem_GB": 16, "time": "4:00:00", "workers": 8},
         "pull_force_screen": {"lane": "worker", "cpus": 2, "mem_GB": 4, "time": "00:30:00"}}


@pytest.fixture
def root(tmp_path, monkeypatch):
    from fragplace.tools.literature import CatalysisHub, CMRCatApp

    def offline(self, *args):
        raise OSError("offline in the tests")
    monkeypatch.setattr(CatalysisHub, "post", offline)
    monkeypatch.setattr(CMRCatApp, "database", offline)
    monkeypatch.setenv("FRAGPLACE_ROOT", str(tmp_path))
    monkeypatch.setenv("FRAGPLACE_HUMAN", "tester")
    yield tmp_path
    set_run(None)


@pytest.fixture
def chosen(root):
    """The example study with its settings approved and EMT chosen at 1*."""
    build_example(root, C)
    calls.structure_retrieval(C)
    assert "blocked" in calls.compute_plan(C)                                   # gated on approve settings
    calls.calculation_protocol(C, "mlip", "the example runs no DFT; EMT computes every energy")
    record_choice(root, C, "approve settings", [], "the example's settings", "tester")
    assert calls.compute_plan(C)["run_first"] == ["mlip_selection"]             # after the potential is chosen
    assert calls.mlip_selection(C, "EMT is the example's test potential")["using"] == "emt"
    return root


def test_the_docstring_mirrors_the_registry():
    assert inspect.getdoc(compute_plan).startswith(docstring_head(BY_NAME["compute_plan"]))


def test_the_estimate_measures_once_and_recommends_a_lane(chosen):
    out = calls.compute_plan(C)
    c = Study(chosen, C)
    slab = len(artifacts.read(StructureRef.model_validate(c.data["retrieval"]["structures"][0])))
    adsorbate = len(artifacts.read(StructureRef.model_validate(c.data["inputs"]["adsorbate_vacuum"])))
    timing = c.data["compute_timing"]
    assert set(timing) == {"calculator", "atoms", "s_per_force_call", "force_calls_per_item"}
    assert timing["calculator"] == "emt" and timing["atoms"] == slab + adsorbate and timing["s_per_force_call"] > 0
    assert out["timing"] == timing and set(out["estimates"]) == set(HEAVY_TOOLS)
    relax = out["estimates"]["relaxation"]
    assert relax["items"] is None and relax["total_minutes"] is None and relax["lane"] == "auto"
    assert relax["minutes_per_item"] == pytest.approx(150 * timing["s_per_force_call"] / 60, abs=1e-3)
    sites = out["estimates"]["site_enumeration"]
    assert sites["items"] == 1 and sites["total_minutes"] == 0 and sites["lane"] == "worker"
    assert "compute_plan" not in c.data and out["checkpoint_due"] == "approve the plan"
    assert "Compute plan" in out["summary"] and "No rule proposed yet" in out["summary"]
    assert calls.compute_plan(C)["timing"] == timing                            # measured once: the cached timing is used

    box = human.checkpoint_box(Study(chosen, C), "approve the plan")["questions"][0]["options"][0]["preview"]
    assert "| Compute plan | none proposed: the heavy tools run in the default lane |" in box and "| Force call |" in box


def test_a_proposal_is_checked_and_recorded(chosen):
    out = calls.compute_plan(C, RULES, "relaxations may pass an hour once the pairs are known; the screen is short")
    assert out["proposed"]["relaxation"] == {"lane": "auto", "batch_above_min": 70.0, "cpus": 8, "mem_GB": 16.0, "time": "04:00:00", "workers": 8}
    assert out["proposed"]["pull_force_screen"]["workers"] == 1
    c = Study(chosen, C)
    plan = c.data["compute_plan"]
    assert set(plan) == {"rules", "reason", "estimates"} and plan["rules"] == out["proposed"] and plan["reason"].startswith("relaxations")
    assert c.data["notes"][-1]["author"] == "hpc-specialist" and "relaxation auto, batch above 70 min" in c.data["notes"][-1]["text"]
    assert "proposed 2 rules" in out["summary"]

    preview = human.checkpoint_box(c, "approve the plan")["questions"][0]["options"][0]["preview"]
    assert "| relaxation | auto, batch above 70 min; 8 CPUs, 16 GB, 04:00:00, 8 workers |" in preview
    assert "| pull_force_screen | worker; 2 CPUs, 4 GB, 00:30:00, 1 worker |" in preview and "default lane" not in preview
    text = briefing(chosen, C, "approve the plan")
    assert "Compute plan:" in text and "relaxation: auto, batch above 70 min" in text and "Force call:" in text
    assert calls.compute_plan(C)["proposed"] == plan["rules"]                   # an estimate afterwards still shows the proposal


def test_an_invalid_rule_is_refused_with_every_reason(chosen):
    bad = {"relaxation": {"lane": "local", "cpus": 4, "mem_GB": 8, "workers": 6},
           "uncertainty_estimation": {"lane": "auto", "cpus": 200, "mem_GB": 8, "time": "01:00:00"},
           "pull_force_screen": {"lane": "batch", "cpus": 2, "mem_GB": 4, "time": "1:00", "partition": "gpu-debug"},
           "report": {"lane": "worker", "cpus": 1, "mem_GB": 1, "time": "00:10:00"}}
    out = calls.compute_plan(C, bad, "a bad plan")
    assert out["error"] == "ValueError"
    for words in ("lane 'local'", "set time", "6 workers on 4 CPUs", "needs batch_above_min", "200 CPUs", "write HH:MM:SS",
                  "CPU only", "report: not a heavy step"):
        assert words in out["message"], words
    assert "error" in calls.compute_plan(C, RULES, "  ")                        # a proposal needs a reason
    assert "compute_plan" not in Study(chosen, C).data


def test_rules_against_the_partition_limits():
    est = {"relaxation": {"total_minutes": 600.0}}
    checked, problems, warnings = check_rules({"relaxation": {"lane": "batch", "cpus": 16, "mem_GB": 300, "time": "2-00:00:00", "partition": "interactive"}}, est)
    assert any("191 GB" in p for p in problems) and any("at most 1-00:00:00" in p for p in problems) and not checked
    checked, problems, warnings = check_rules({"relaxation": {"lane": "batch", "cpus": 16, "mem_GB": 32, "time": "01:00:00", "workers": 4}}, est)
    assert not problems and checked["relaxation"]["time"] == "01:00:00" and "shorter than the estimate, 150 min" in warnings[0]


def test_the_plan_is_fixed_once_the_human_approved_it(chosen):
    calls.compute_plan(C, RULES, "as proposed")
    record_choice(chosen, C, "approve the plan", [], "the plan holds", "tester")
    out = calls.compute_plan(C, {"relaxation": dict(RULES["relaxation"], cpus=16, workers=16)}, "more cores")
    assert "blocked" in out and "approve the plan" in out["blocked"]
    assert Study(chosen, C).data["compute_plan"]["rules"]["relaxation"]["cpus"] == 8
    assert "estimates" in calls.compute_plan(C)                                 # the estimate itself is still answered
