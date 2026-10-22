"""The batch lane and the relaxation pool: one sbatch job per heavy call, found again by its hash and never
submitted twice; TIMEOUT and OUT_OF_MEMORY submitted again with twice the time or memory, NODE_FAIL and PREEMPTED as
they were, three attempts in all; the scheduler polled no more often than every 15 s; the job script's lines; the
lane each heavy call takes once the human has approved a compute plan; and the pool's relaxations equal to the
serial path's. Stand-ins for sbatch, squeue and sacct on PATH play the scheduler, so nothing is ever submitted."""
import json
import os
import sys
from pathlib import Path

import pytest

from fragplace.execution import batch, pool, srun
from fragplace.mcp import server
from fragplace.runtime.journal import set_run
from fragplace.study import calls

SRC = Path(__file__).resolve().parents[1] / "src"
FAKE_SLURM = """#!@PYTHON@
# Stands in for sbatch, squeue and sacct, by the name it is called with. sbatch gives each job the next id, copies
# its script, takes the job's final state from the first line of finals, COMPLETED when none is left, and its queue
# states from queue; with FAKE_SBATCH_RUN set it runs a job that is to complete, as the job would.
import os, re, subprocess, sys
from pathlib import Path
here = Path(__file__).resolve().parent
me, args = Path(sys.argv[0]).name, sys.argv[1:]
with open(here / "calls.log", "a") as f:
    f.write(me + " " + " ".join(args) + "\\n")
def take(path):
    lines = path.read_text().splitlines() if path.exists() else []
    path.write_text("".join(x + "\\n" for x in lines[1:]))
    return lines[0] if lines else ""
if me == "sbatch":
    counter = here / "counter"
    job = int(counter.read_text()) + 1 if counter.exists() else 101
    counter.write_text(str(job))
    text = Path(args[-1]).read_text()
    (here / f"script-{job}.sh").write_text(text)
    final = take(here / "finals") or "COMPLETED"
    (here / f"final-{job}").write_text(final)
    (here / f"states-{job}").write_text((here / "queue").read_text() if (here / "queue").exists() else "")
    log = re.search(r"--output=(\\S+)", text).group(1).replace("%j", str(job))
    cpus = re.search(r"--cpus-per-task=(\\d+)", text).group(1)
    if final == "COMPLETED" and os.environ.get("FAKE_SBATCH_RUN"):
        with open(log, "w") as out:
            subprocess.run(["bash", args[-1]], stdout=out, stderr=subprocess.STDOUT,
                           env={**os.environ, "SLURM_JOB_ID": str(job), "SLURM_CPUS_PER_TASK": cpus})
    else:
        Path(log).write_text(f"step {job} started\\nslurmstepd: error: *** JOB {job} ENDED {final} ***\\n")
    print(f"{job};triton")
elif me == "squeue":
    print(take(here / f"states-{args[args.index('-j') + 1]}"))
elif me == "sacct":
    path = here / f"final-{args[args.index('-j') + 1]}"
    print(path.read_text() if path.exists() else "")
"""


class Clock:
    """A clock that moves only when the lane sleeps, so the 15 s floor is checked without waiting."""

    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def sleep(self, s):
        assert s > 0
        self.now += s


@pytest.fixture
def slurm(tmp_path, monkeypatch):
    """The stand-ins first on PATH, a root of the test's own with a study s that has records, the clock patched;
    returns the folder the stand-ins keep their files in."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "fake_slurm").write_text(FAKE_SLURM.replace("@PYTHON@", sys.executable))
    (bin_dir / "fake_slurm").chmod(0o755)
    for name in ("sbatch", "squeue", "sacct"):
        (bin_dir / name).symlink_to(bin_dir / "fake_slurm")
    root = tmp_path / "root"
    (root / "runs" / "s").mkdir(parents=True)
    (root / "runs" / "s" / "artifacts.json").write_text("{}")
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("FRAGPLACE_ROOT", str(root))
    monkeypatch.setenv("PYTHONPATH", f"{SRC}{os.pathsep}{os.environ.get('PYTHONPATH', '')}")
    monkeypatch.delenv("FAKE_SBATCH_RUN", raising=False)
    for name in (srun.ENV, srun.JOB_ENV, srun.LANE_ENV, "SLURM_JOB_ID"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(batch, "NODE_LOCAL", (), raising=False)
    monkeypatch.setattr(batch, "node_local", lambda root: False)
    clock = Clock()
    monkeypatch.setattr(batch, "monotonic", clock)
    monkeypatch.setattr(batch, "sleep", clock.sleep)
    monkeypatch.setattr(batch, "_LAST_POLL", [float("-inf")])
    yield bin_dir
    server.close_lanes()
    set_run(None)


def calls_of(bin_dir, command):
    return [x for x in (bin_dir / "calls.log").read_text().splitlines() if x.startswith(command + " ")] if (bin_dir / "calls.log").exists() else []


def jobs(root):
    return json.loads((root / "runs" / "s" / "jobs.json").read_text())


def trace(root):
    return [json.loads(x)["message"] for x in (root / "runs" / "s" / "trace.jsonl").read_text().splitlines()]


RULE = {"cpus": 8, "mem_GB": 16, "time": "01:00:00", "workers": 4}


def test_the_job_script_sets_every_resource_and_passes_the_environment_on(tmp_path, monkeypatch):
    monkeypatch.setenv("FRAGPLACE_ROOT", str(tmp_path))
    monkeypatch.setenv("PYTHONPATH", "/shared/src")
    lines = batch.script("s", "relaxation", tmp_path / "jobs" / "h", RULE).splitlines()
    assert lines[0] == "#!/bin/bash -l"
    for line in ("#SBATCH --job-name=fragplace-s-relaxation", "#SBATCH --cpus-per-task=8", "#SBATCH --mem=16G", "#SBATCH --time=01:00:00",
                 f"#SBATCH --output={tmp_path / 'jobs' / 'h'}/slurm-%j.out", 'export OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK" MKL_NUM_THREADS="$SLURM_CPUS_PER_TASK"',
                 "export PYTHONPATH=/shared/src", f"export FRAGPLACE_ROOT={tmp_path}", "export FRAGPLACE_WORKERS=4"):
        assert line in lines, line
    assert not any("--partition" in x for x in lines)                    # Triton picks the partition from the time
    assert "#SBATCH --partition=batch-milan" in batch.script("s", "relaxation", tmp_path, {**RULE, "partition": "batch-milan"})
    assert lines[-1].startswith("exec ") and lines[-1].endswith(f"-m fragplace.execution.batch run {tmp_path / 'jobs' / 'h' / 'request.json'}")
    assert batch.hms(2 * batch.seconds("16:00:00")) == "1-08:00:00" and batch.seconds("1-08:00:00") == 32 * 3600


def test_a_call_runs_in_one_job_and_the_same_call_again_submits_nothing(slurm, monkeypatch):
    root = Path(os.environ["FRAGPLACE_ROOT"])
    monkeypatch.setenv("FAKE_SBATCH_RUN", "1")
    (slurm / "queue").write_text("PENDING\nRUNNING\n")
    lane = batch.BatchLane(calls.FUNCTIONS, RULE, records="r1")
    out = lane.run("study_status", {"study": "s"})
    assert out["inputs"] is False, out                                   # the call ran inside the job and wrote result.json
    assert len(calls_of(slurm, "sbatch")) == 1 and calls_of(slurm, "sbatch")[0].startswith("sbatch --parsable ")
    assert len(calls_of(slurm, "squeue")) == 3 and len(calls_of(slurm, "sacct")) == 1     # one squeue a poll, sacct once it left
    (key, rec), = jobs(root).items()
    assert rec["handle_id"] == "101" and rec["state"] == "done" and rec["slurm_state"] == "COMPLETED" and rec["attempts"] == 1
    assert rec["hash"] == key and rec["resources"]["cpus"] == 8 and rec["submitted"] and rec["finished"]
    folder = root / "runs" / "s" / "jobs" / key
    assert {"request.json", "result.json", "job.sh", "slurm-101.out"} <= {p.name for p in folder.iterdir()}
    said = trace(root)
    assert any("submitted job 101" in x for x in said) and any("PENDING to RUNNING" in x for x in said)
    assert batch.BatchLane(calls.FUNCTIONS, RULE, records="r1").run("study_status", {"study": "s"}) == out
    assert len(calls_of(slurm, "sbatch")) == 1 and any("stored result of job 101" in x for x in trace(root))
    batch.BatchLane(calls.FUNCTIONS, RULE, records="r2").run("study_status", {"study": "s"})
    assert len(calls_of(slurm, "sbatch")) == 2                           # changed records: a new request


def test_a_call_still_running_at_its_timeout_is_left_running_and_reattached(slurm):
    root = Path(os.environ["FRAGPLACE_ROOT"])
    (slurm / "queue").write_text("RUNNING\n" * 400)
    out = batch.BatchLane(calls.FUNCTIONS, RULE).run("study_status", {"study": "s"})
    assert out["job"] == "101" and out["state"] == "RUNNING" and "reattaches" in out["next"]
    (slurm / "states-101").write_text("")                                # the job ends while no call watches it
    key = next(iter(jobs(root)))
    (root / "runs" / "s" / "jobs" / key / "result.json").write_text(json.dumps({"answer": 42}))
    assert batch.BatchLane(calls.FUNCTIONS, RULE).run("study_status", {"study": "s"}) == {"answer": 42}
    assert len(calls_of(slurm, "sbatch")) == 1 and any("reattached to job 101" in x for x in trace(root))
    assert not calls_of(slurm, "scancel")


def test_time_and_memory_double_on_a_retry_and_three_attempts_are_all(slurm, monkeypatch):
    root = Path(os.environ["FRAGPLACE_ROOT"])
    monkeypatch.setenv("FAKE_SBATCH_RUN", "1")
    (slurm / "finals").write_text("TIMEOUT\nOUT_OF_MEMORY\nCOMPLETED\n")
    out = batch.BatchLane(calls.FUNCTIONS, RULE, records="a").run("study_status", {"study": "s"})
    assert out["inputs"] is False
    scripts = [(slurm / f"script-{j}.sh").read_text() for j in (101, 102, 103)]
    assert "--time=01:00:00" in scripts[0] and "--time=02:00:00" in scripts[1] and "--mem=16G" in scripts[1]
    assert "--time=02:00:00" in scripts[2] and "--mem=32G" in scripts[2]
    rec = next(iter(jobs(root).values()))
    assert rec["attempts"] == 3 and rec["handle_id"] == "103" and len(rec["diagnoses"]) == 2
    assert any("submitted again as job 102, attempt 2 of 3, time 01:00:00 to 02:00:00" in x for x in trace(root))

    (slurm / "finals").write_text("NODE_FAIL\nPREEMPTED\nTIMEOUT\nCOMPLETED\n")
    out = batch.BatchLane(calls.FUNCTIONS, RULE, records="b").run("study_status", {"study": "s"})
    assert out["error"] == "BatchJobError" and out["state"] == "TIMEOUT" and out["attempts"] == 3 and out["job"] == "106"
    assert "ENDED TIMEOUT" in out["log_tail"] and "ENDED TIMEOUT" in out["message"]
    assert "--time=01:00:00" in (slurm / "script-105.sh").read_text()     # NODE_FAIL and PREEMPTED go again as they were
    assert len(calls_of(slurm, "sbatch")) == 6
    again = batch.BatchLane(calls.FUNCTIONS, RULE, records="b").run("study_status", {"study": "s"})
    assert again["state"] == "TIMEOUT" and "submits nothing" in again["message"] and len(calls_of(slurm, "sbatch")) == 6

    (slurm / "finals").write_text("FAILED\n")
    out = batch.BatchLane(calls.FUNCTIONS, RULE, records="c").run("study_status", {"study": "s"})
    assert out["state"] == "FAILED" and out["attempts"] == 1 and len(calls_of(slurm, "sbatch")) == 7


def test_the_scheduler_is_polled_no_more_often_than_every_15_s(slurm, monkeypatch):
    asked = []
    real = batch.slurm_state
    monkeypatch.setattr(batch, "slurm_state", lambda job: asked.append(batch.monotonic()) or real(job))
    (slurm / "queue").write_text("PENDING\n" * 3 + "RUNNING\n" * 2)
    batch.BatchLane(calls.FUNCTIONS, RULE, records="x").run("study_status", {"study": "s"})
    batch.BatchLane(calls.FUNCTIONS, RULE, records="y").run("study_status", {"study": "s"})   # a second call keeps the floor too
    assert len(asked) >= 8 and all(b - a >= batch.POLL_S for a, b in zip(asked, asked[1:]))


def test_a_root_on_a_node_s_own_disk_and_a_study_without_records_submit_nothing(slurm, monkeypatch):
    out = batch.BatchLane(calls.FUNCTIONS, RULE).run("study_status", {"study": "nothing-here"})
    assert "blocked" in out
    monkeypatch.setattr(batch, "node_local", srun.node_local)
    monkeypatch.setenv("FRAGPLACE_ROOT", "/tmp/fragplace-root")
    out = batch.BatchLane(calls.FUNCTIONS, RULE).run("study_status", {"study": "s"})
    assert out["error"] == "ComputeNodeError" and "own disk" in out["message"]
    assert not calls_of(slurm, "sbatch")
    for module in ("batch.py", "slurm.py", "srun.py", "pool.py"):
        code = [x for x in (SRC / "fragplace" / "execution" / module).read_text().splitlines() if not x.strip().startswith("#")]
        assert not any('"scancel"' in x or "'scancel'" in x for x in code), module


# ---- the lane of each heavy call once the human has approved a compute plan
def planned_study(root, placed=20):
    from fragplace.study.store import Study
    c = Study(root, "s")
    c.put("mlip", {"calculator": "emt"})
    c.put("placed", [{"id": f"c{k}"} for k in range(placed)])
    c.put("compute_plan", {"rules": {"pull_force_screen": {"lane": "auto", "batch_above_min": 0.1, **RULE},
                                     "site_enumeration": {"lane": "batch", **RULE}, "relaxation": {"lane": "batch", **RULE},
                                     "uncertainty_estimation": {"lane": "worker", **RULE}}})
    c.put("compute_timing", {"calculator": "emt", "atoms": 146, "s_per_force_call": 1.5})
    return c


def approve(root):
    from fragplace.runtime import checkpoints
    from fragplace.schemas.records import HumanChoice
    checkpoints.record(root / "runs" / "s", HumanChoice(checkpoint="approve the plan", chosen=[], reason="test", who="tester"))


def test_each_heavy_call_takes_its_approved_rule_s_lane(slurm, monkeypatch):
    root = Path(os.environ["FRAGPLACE_ROOT"])
    c = planned_study(root)
    assert server.route("pull_force_screen", {"study": "s"}) == ("local", {})              # before the approval, the default lane
    approve(root)
    lane, rule = server.route("pull_force_screen", {"study": "s"})
    assert server.expected_minutes(c, "pull_force_screen", {}) == pytest.approx(0.5) and lane == "batch" and rule["workers"] == 4
    c.data["compute_plan"]["rules"]["pull_force_screen"]["batch_above_min"] = 1
    c.put("compute_plan", c.data["compute_plan"])
    assert server.route("pull_force_screen", {"study": "s"})[0] == "local"                 # auto within its threshold: the default lane
    c.data["compute_plan"]["estimates"] = {"pull_force_screen": {"force_calls_per_item": 4}}
    c.put("compute_plan", c.data["compute_plan"])
    assert server.expected_minutes(c, "pull_force_screen", {}) == pytest.approx(2.0)       # the plan's own estimate for the tool wins
    assert server.route("pull_force_screen", {"study": "s"})[0] == "batch"
    assert server.route("site_enumeration", {"study": "s"})[0] == "batch"
    assert server.route("relaxation", {"study": "s"})[0] == "local"                        # its items are not known: it cannot run yet
    assert server.route("uncertainty_estimation", {"study": "s"})[0] == "local"            # worker, but kept is not known yet
    assert server.route("anomaly_filter", {"study": "s"}) == ("local", {})                 # no rule: the default lane
    monkeypatch.setenv(srun.LANE_ENV, "worker")
    assert server.route("anomaly_filter", {"study": "s"})[0] == "worker"
    assert any("lane batch for site_enumeration: the approved rule" in x for x in trace(root))


def test_an_approved_batch_rule_sends_the_call_through_one_job_and_back(slurm, monkeypatch):
    pytest.importorskip("mcp")
    root = Path(os.environ["FRAGPLACE_ROOT"])
    planned_study(root)
    approve(root)
    monkeypatch.setenv("FAKE_SBATCH_RUN", "1")
    out = server.dispatched("site_enumeration", calls.FUNCTIONS["site_enumeration"])(study="s")
    assert "has no inputs" in out["blocked"]                            # the call itself ran inside the job, and answered
    assert "#SBATCH --job-name=fragplace-s-site_enumeration" in (slurm / "script-101.sh").read_text()
    server.dispatched("site_enumeration", calls.FUNCTIONS["site_enumeration"])(study="s")
    assert len(calls_of(slurm, "sbatch")) == 1                           # the same call with the same records: the stored result


def test_a_request_s_records_leave_out_what_the_call_itself_writes(slurm):
    root = Path(os.environ["FRAGPLACE_ROOT"])
    c = planned_study(root)
    before = server.records("s", "relaxation", {})
    c.put("order", ["c1"])
    c.put("relaxed", [{"candidate_id": "c1"}])
    c.put("notes", [{"author": "scientific-critic", "text": "fine"}])
    assert server.records("s", "relaxation", {}) == before
    c.put("placed", [{"id": "c1"}])
    assert server.records("s", "relaxation", {}) != before


# ---- the relaxation pool
def test_the_pool_relaxes_as_the_serial_path_does(run, pt111, monkeypatch):
    pytest.importorskip("acat")
    from fragplace.runtime import artifacts, geometry
    from fragplace.schemas.records import Candidate
    from fragplace.tools.placement import adsorbate_placement
    from fragplace.tools.relaxation import relaxation
    from fragplace.tools.sites import pair_enumeration, site_enumeration
    from fragplace.tools.structure import structure_retrieval
    refs = pt111["refs"]
    retrieval = structure_retrieval(refs["slab"], refs["adsorbate_vacuum"], refs["initial_state"], (0, 1))
    sites = site_enumeration(refs["slab"], retrieval["cell_repeat"])
    atoms = artifacts.read(retrieval["structures"][1])
    site, _ = geometry.nearest_site(sites, atoms.positions[artifacts.binding_index(atoms, "A")], atoms.cell.array)
    base = Candidate(id=f"A{site.index:03d}", structure=retrieval["structures"][1], site_A=site.index)
    pairs = pair_enumeration(sites, 0.97, (1.5, 5.0), site.index)["pairs"][:3]
    placed = [adsorbate_placement(sites, retrieval["fragment_B"], p.site_B, 0, 2.0, 0.1, base) for p in pairs]
    candidates = placed + placed[:1]                                     # the same structure twice: once relaxed, then a hit

    def relax_all():
        for p in (run.dir / "cache").iterdir():
            p.unlink()
        out = relaxation(candidates, "emt", 0.05, 200)
        return [(r.model_dump(exclude={"structure"}), artifacts.read(r.structure).get_positions().tolist()) for r in out]
    monkeypatch.delenv(pool.ENV, raising=False)
    serial = relax_all()
    monkeypatch.setenv(pool.ENV, "2")
    pooled = relax_all()
    # Equal record for record, in the same order; a float may differ in its last digits, since a worker's BLAS runs on
    # its share of the threads and this process on all of them.
    for k, ((r1, p1), (r2, p2)) in enumerate(zip(serial, pooled)):
        floats = {"energy_eV", "fmax_eV_per_A"}
        assert {f: v for f, v in r1.items() if f not in floats} == {f: v for f, v in r2.items() if f not in floats}, k
        assert all(r1[f] == pytest.approx(r2[f], rel=1e-10, abs=1e-12) for f in floats), (k, r1, r2)
        assert max(abs(a - b) for x, y in zip(p1, p2) for a, b in zip(x, y)) < 1e-9, k
    assert len(pooled) == len(serial) == 4 and [r["cache_hit"] for r, _ in pooled] == [False, False, False, True]
    with pool.using(1):
        assert relax_all() == serial                                     # the approved rule's workers win over the environment
    said = [e.message for e in run.events() if e.tool == "relaxation"]
    assert any("3 of 4 candidates relaxed in a pool of 2 processes" in x for x in said)
    assert pool.shape(3, 8, cpus=4) == (3, 1) and pool.shape(10, 2, cpus=6) == (2, 3) and pool.shape(5, 4, cpus=1) == (1, 1)
