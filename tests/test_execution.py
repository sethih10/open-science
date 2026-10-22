"""Heavy calls go to a compute node: the lane chosen and the srun command made for it, which tools count as heavy,
the worker's protocol, one worker per session that is started again when it has gone, failures answered as errors,
and the server publishing every tool with its schema unchanged; and the command line's fixes: --chosen, the root,
the human's name, the bond, a study run from the chat. A stand-in for srun on PATH runs the command where it is,
so every test runs offline and without Slurm."""
import asyncio
import dataclasses
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from fragplace.cli.main import main, parser
from fragplace.execution import srun
from fragplace.execution.local import BLAS_THREADS_MAX
from fragplace.mcp import server
from fragplace.registry.tools import OPERATIONS, ORCHESTRATOR_OPERATIONS, REGISTRY
from fragplace.runtime.journal import set_run

SRC = Path(__file__).resolve().parents[1] / "src"
OPTIONS = "--partition=interactive --cpus-per-task=4 --mem=8G --time=02:00:00"
LIGHT = {"study_status", "note", "show_structures", "literature_lookup", "structure_retrieval", "calculation_protocol", "pair_enumeration",
         "adsorbate_placement", "descriptor_card", "ranking", "report"}
FAKE_SRUN = """#!/bin/sh
# Stands in for srun: notes each call on one line, then runs the command here, inside a job as srun's command is.
printf '%s|%s|%s\\n' "OMP_NUM_THREADS=$OMP_NUM_THREADS" "FRAGPLACE_ROOT=$FRAGPLACE_ROOT" "$*" >> "$(dirname "$0")/srun.log"
case "$FAKE_SRUN" in
  fail) echo "srun: error: Unable to allocate resources: Invalid partition name specified" >&2; exit 1 ;;
  silent) printf '%s{"ready": "fake"}\\n' "@LINE@"; exec sleep 600 ;;
esac
while [ "$#" -gt 0 ] && [ "$1" != "--quiet" ]; do shift; done
shift
export SLURM_JOB_ID=fake
exec "$@"
""".replace("@LINE@", srun.LINE)


@pytest.fixture
def root(tmp_path, monkeypatch):
    """A root of the test's own, which FRAGPLACE_ROOT names; this checkout's sources for every child process; no lane
    asked for; the server's lanes closed afterwards, its worker among them."""
    r = tmp_path / "root"
    r.mkdir()
    monkeypatch.setenv("FRAGPLACE_ROOT", str(r))
    monkeypatch.setenv("FRAGPLACE_HUMAN", "Ada Tester")
    monkeypatch.setenv("PYTHONPATH", f"{SRC}{os.pathsep}{os.environ.get('PYTHONPATH', '')}")
    for name in (srun.ENV, srun.JOB_ENV, srun.LANE_ENV, srun.IDLE_ENV, "FAKE_SRUN"):
        monkeypatch.delenv(name, raising=False)
    yield r
    server.close_lanes()
    set_run(None)


@pytest.fixture
def fake_srun(root, tmp_path, monkeypatch):
    """The stand-in first on PATH, FRAGPLACE_SRUN set, no Slurm job around the test; the log the stand-in writes. The
    stand-in runs on this node, so the test's root under /tmp is the one its command sees."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "srun").write_text(FAKE_SRUN)
    (bin_dir / "srun").chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv(srun.ENV, "--partition=nowhere --cpus-per-task=2")
    monkeypatch.delenv("SLURM_JOB_ID", raising=False)
    monkeypatch.setattr(srun, "NODE_LOCAL", ())
    return bin_dir / "srun.log"


def test_the_srun_command_comes_from_the_environment(tmp_path):
    opts = srun.options({srun.ENV: OPTIONS})
    assert opts == ["--partition=interactive", "--cpus-per-task=4", "--mem=8G", "--time=02:00:00"]
    assert srun.options({srun.ENV: "-c 3 --mem=10G", srun.JOB_ENV: "21140845"}) == ["--jobid=21140845", "--overlap", "-n1", "-c", "3",
                                                                                     "--mem=10G"]
    for named in ("-n 2", "-n2", "--ntasks 2", "--ntasks=2"):
        assert "-n1" not in srun.options({srun.ENV: named, srun.JOB_ENV: "1"})
    assert "-n1" in srun.options({srun.ENV: "--ntasks-per-node=2", srun.JOB_ENV: "1"}) and "-n1" not in srun.options({srun.ENV: "-c 3"})
    assert srun.argv(server.WORKER_COMMAND, opts) == ["srun", *opts, "--quiet", sys.executable, "-m", "fragplace.mcp.server", "--worker"]
    assert srun.node_local(Path("/tmp")) and srun.node_local(Path("/tmp/x/root")) and srun.node_local(Path("/dev/shm/root"))
    assert not srun.node_local(Path("/scratch/x/root")) and not srun.node_local(Path("/tmpfs/root"))
    for spelled in (["-c", "6"], ["-c6"], ["--cpus-per-task", "6"], ["--cpus-per-task=2", "-c", "6"]):
        assert srun.cpus_per_task(spelled) == 6
    assert srun.cpus_per_task(["--mem=8G"]) is None
    env = srun.environment(opts, tmp_path, {"OMP_NUM_THREADS": "2", "PATH": "/bin"})
    assert env["FRAGPLACE_ROOT"] == str(tmp_path) and env["PATH"] == "/bin"
    assert (env["OMP_NUM_THREADS"], env["MKL_NUM_THREADS"], env["OPENBLAS_NUM_THREADS"]) == ("4", "4", str(min(4, BLAS_THREADS_MAX)))
    assert srun.environment(["-c", "16"], tmp_path, {})["OPENBLAS_NUM_THREADS"] == str(BLAS_THREADS_MAX)
    left = srun.environment(["--mem=8G"], tmp_path, {name: "2" for name in srun.THREAD_VARS})
    assert not set(srun.THREAD_VARS) & set(left)                    # without -c, the compute node's limit_threads counts the step's CPUs
    assert srun.idle_seconds({}) == 60 * srun.IDLE_MIN and srun.idle_seconds({srun.IDLE_ENV: "0.5"}) == 30


def test_the_lane_is_the_study_s_else_the_environment_s_and_local_inside_a_job():
    assert srun.choose(env={}) == "local"
    assert srun.choose(env={srun.ENV: OPTIONS}) == srun.choose(env={srun.JOB_ENV: "21140845"}) == "worker"
    assert srun.choose(env={srun.ENV: ""}) == "local"          # what ${FRAGPLACE_SRUN:-} in .mcp.json gives when it is unset
    assert srun.choose(env={srun.ENV: OPTIONS, "SLURM_JOB_ID": "123"}) == "local"
    assert srun.choose(env={srun.ENV: OPTIONS, srun.LANE_ENV: "local"}) == "local"
    assert srun.choose("local", env={srun.ENV: OPTIONS, srun.LANE_ENV: "worker"}) == "local"
    assert srun.choose("worker", env={}) == "worker"
    assert srun.choose(env={srun.LANE_ENV: "batch"}) == "batch" and srun.choose("batch", env={"SLURM_JOB_ID": "1"}) == "local"
    with pytest.raises(ValueError, match="auto is a lane of a compute plan's rule only"):
        srun.choose(env={srun.LANE_ENV: "auto"})
    assert srun.recommend(5)[0] == srun.recommend(60)[0] == "worker" and srun.recommend(71)[0] == "batch" and srun.recommend(None)[0] == "auto"


def test_the_heavy_tools_are_the_ones_that_compute():
    assert srun.HEAVY == {t.name for t in REGISTRY if t.lane != "laptop"} | {"anomaly_filter", "site_enumeration", "soap_clustering"}
    published = {t.name for t in REGISTRY} | set(OPERATIONS) | set(ORCHESTRATOR_OPERATIONS)
    assert published - srun.HEAVY == LIGHT


def test_the_worker_answers_each_request_on_one_line_and_leaves_when_stdin_closes(root):
    requests = [{"name": "study_status", "kwargs": {"study": "nothing-here"}}, {"name": "no_such_tool", "kwargs": {}},
                {"name": "study_status", "kwargs": {"study": "nothing-here"}}]
    p = subprocess.run(server.WORKER_COMMAND, input="".join(json.dumps(r) + "\n" for r in requests), capture_output=True, text=True,
                       timeout=600)
    assert p.returncode == 0, p.stderr
    lines = p.stdout.splitlines()
    assert all(x.startswith(srun.LINE) for x in lines)              # whatever else is printed goes to stderr
    said = [json.loads(x[len(srun.LINE):]) for x in lines]
    assert set(said[0]) == {"ready"} and len(said) == 5
    assert said[1]["answer"]["inputs"] is False and "fragplace init nothing-here" in said[1]["answer"]["next"]
    assert said[2]["answer"]["error"] == "ComputeNodeError" and "KeyError: 'no_such_tool'" in said[2]["answer"]["message"]
    assert said[3]["answer"]["inputs"] is False                     # a failed request does not end the worker
    assert said[4] == {"bye": "stdin closed"}
    assert (root / "runs" / "nothing-here").is_dir()                # the root came from FRAGPLACE_ROOT


def test_the_worker_leaves_by_itself_when_idle(root, monkeypatch):
    monkeypatch.setenv(srun.IDLE_ENV, "0.02")
    p = subprocess.Popen(server.WORKER_COMMAND, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    assert p.wait(timeout=600) == 0                                 # its stdin still open: it left because no request came
    said = [json.loads(x[len(srun.LINE):]) for x in p.stdout.read().splitlines()]
    p.stdin.close()
    assert set(said[0]) == {"ready"} and said[1:] == [{"bye": "no request for 0.02 min"}]


def test_heavy_calls_share_one_worker_and_light_calls_stay_here(root, fake_srun):
    pytest.importorskip("mcp")
    app = server.build(root)

    def call(name):
        return str(asyncio.run(app.call_tool(name, {"study": "nothing-here"})))
    assert "fragplace init nothing-here" in call("study_status")
    assert not fake_srun.exists()                                   # a session that never computes never allocates
    assert "has no inputs" in call("site_enumeration") and "has no inputs" in call("soap_clustering")
    assert fake_srun.read_text().splitlines() == [f"OMP_NUM_THREADS=2|FRAGPLACE_ROOT={root}|--partition=nowhere --cpus-per-task=2 --quiet "
                                                  + " ".join(server.WORKER_COMMAND)]
    worker = server.lane("worker")
    worker.proc.kill()
    worker.proc.wait()                                              # the worker died between two calls
    assert "has no inputs" in call("anomaly_filter")
    assert len(fake_srun.read_text().splitlines()) == 2             # so the next heavy call started another


def test_a_worker_that_cannot_start_or_answer_comes_back_as_an_error(root, fake_srun, monkeypatch, tmp_path):
    lane = srun.WorkerLane(server.WORKER_COMMAND)
    monkeypatch.setenv("FAKE_SRUN", "fail")
    out = lane.run("relaxation", {"study": "nothing-here"})
    assert out["error"] == "ComputeNodeError" and out["message"].startswith("the worker did not start")
    assert "Invalid partition name specified" in out["message"]
    monkeypatch.setenv("FAKE_SRUN", "silent")
    monkeypatch.setattr(srun, "STOP_S", 1)
    monkeypatch.setitem(srun.BY_NAME, "relaxation", dataclasses.replace(srun.BY_NAME["relaxation"], timeout_s=1))
    out = lane.run("relaxation", {"study": "nothing-here"})
    assert out["error"] == "ComputeNodeError" and out["message"].startswith("relaxation gave no answer within")
    assert "the worker was stopped and the job srun made for it ended" in out["message"] and lane.proc is None
    monkeypatch.setenv("PATH", str(tmp_path / "no-srun-here"))
    out = lane.run("relaxation", {"study": "nothing-here"})
    assert out["error"] == "ComputeNodeError" and out["message"].startswith("srun did not start")
    monkeypatch.setattr(srun, "NODE_LOCAL", ("/tmp",))
    monkeypatch.setenv("FRAGPLACE_ROOT", "/tmp/fragplace-root")
    out = lane.run("relaxation", {"study": "nothing-here"})
    assert out["error"] == "ComputeNodeError" and "/tmp/fragplace-root is on this node's own disk" in out["message"]


def test_the_server_publishes_the_registry_and_the_operations_with_their_schemas(root):
    pytest.importorskip("mcp")
    from mcp.server.fastmcp import FastMCP
    from fragplace.study import calls
    tools = {t.name: t for t in asyncio.run(server.build(root).list_tools())}
    assert set(tools) == {t.name for t in REGISTRY} | set(OPERATIONS) | set(ORCHESTRATOR_OPERATIONS)
    assert "For the orchestrator alone." in tools["show_structures"].description
    plain = FastMCP("plain")
    for name in srun.HEAVY:
        plain.tool(name=name)(calls.FUNCTIONS[name])
    for t in asyncio.run(plain.list_tools()):
        assert tools[t.name].inputSchema == t.inputSchema and tools[t.name].outputSchema == t.outputSchema


def test_chosen_keeps_every_id_whether_repeated_or_listed():
    base = ["approve", "s", "pick up to five final states", "--reason", "nearest first"]
    assert parser().parse_args(base + ["--chosen", "a", "--chosen", "b", "c"]).chosen == ["a", "b", "c"]
    assert parser().parse_args(base + ["--chosen", "a", "b", "--chosen", "c"]).chosen == ["a", "b", "c"]
    assert parser().parse_args(base).chosen is None and parser().parse_args(base).who is None


def test_a_root_that_is_runs_or_inside_it_is_refused(root, monkeypatch):
    for bad in (root / "runs", root / "runs" / "_demo"):
        with pytest.raises(SystemExit) as e:
            main(["--root", str(bad), "status", "s"])
        assert "the folder that holds runs/" in str(e.value) and f"--root {root} " in str(e.value)
    monkeypatch.setenv("FRAGPLACE_ROOT", str(root / "runs" / "_demo"))
    with pytest.raises(SystemExit, match="holds runs/"):
        main(["init", "s"])
    assert not (root / "runs").exists()
    monkeypatch.setenv(srun.ENV, "--partition=nowhere")           # the worker lane: the root crosses to a compute node
    monkeypatch.delenv("SLURM_JOB_ID", raising=False)
    with pytest.raises(SystemExit, match="own disk"):
        main(["--root", "/tmp/fragplace-root", "status", "s"])


def test_decide_names_the_human_and_the_real_path(root, capsys):
    (root / "PROJECT.md").write_text((SRC.parent / "PROJECT.md").read_text())
    main(["init", "s"])
    assert f"made at {root / 'runs' / 's'}" in capsys.readouterr().out
    main(["decide", "s", "pull_force_screen.threshold_eV_per_A", "0.5", "--reason", "the test value"])
    assert f"in {root / 'runs' / 's' / 'PROJECT.md'}, set by Ada Tester" in capsys.readouterr().out
    with pytest.raises(SystemExit, match="no study nothing-here"):
        main(["decide", "nothing-here", "pull_force_screen.threshold_eV_per_A", "0.5", "--reason", "r"])


def test_init_without_a_bond_lists_the_atoms_of_the_adsorbate(root, tmp_path):
    pytest.importorskip("ase")
    from ase import Atoms
    path = tmp_path / "H2O.xyz"
    Atoms("OH2", positions=[[0, 0, 0], [0.76, 0.59, 0], [-0.76, 0.59, 0]]).write(path)
    with pytest.raises(SystemExit) as e:
        main(["init", "water", "--slab", str(path), "--adsorbate", str(path), "--initial-state", str(path)])
    assert "--bond i,j" in str(e.value) and "  0 O\n  1 H\n  2 H" in str(e.value) and "0.76" not in str(e.value)
    with pytest.raises(SystemExit, match="only with --slab"):
        main(["init", "water", "--facet", "100"])


def test_the_example_is_made_under_srun_and_a_study_run_from_the_chat_is_read_as_such(root, fake_srun, monkeypatch, capsys):
    pytest.importorskip("ase")
    pytest.importorskip("mcp")
    ran = {}

    def exec_here(file, command, env):                              # os.execvpe as a child: the command runs, then this command ends
        ran["p"] = subprocess.run(command, env=env, capture_output=True, text=True, timeout=900)
        raise SystemExit(ran["p"].returncode)
    monkeypatch.setattr(os, "execvpe", exec_here)
    with pytest.raises(SystemExit) as e:
        main(["init", "chat", "--example"])
    assert e.value.code == 0, ran["p"].stderr
    assert "on a compute node: srun --partition=nowhere --cpus-per-task=2" in capsys.readouterr().err
    assert f"made at {root / 'runs' / 'chat'}" in ran["p"].stdout
    assert fake_srun.read_text().splitlines() == [f"OMP_NUM_THREADS=2|FRAGPLACE_ROOT={root}|--partition=nowhere --cpus-per-task=2 --quiet "
                                                  f"{sys.executable} -m fragplace.cli.main init chat --example"]
    from fragplace.study.store import Study
    c = Study(root, "chat")
    c.put("options", {**c.options, "lane": "local"})
    assert "approve the plan" in str(asyncio.run(server.build(root).call_tool("relaxation", {"study": "chat"})))
    assert len(fake_srun.read_text().splitlines()) == 1             # the study's own lane, local, wins over FRAGPLACE_SRUN
    monkeypatch.delenv(srun.ENV)                                    # from here on in this process, where srun would replace the test run
    from fragplace.study import calls
    assert calls.structure_retrieval("chat")["fragment_A"] == "O"
    main(["status", "chat"])
    out = capsys.readouterr().out
    assert "run from the chat" in out and "done structure_retrieval" in out
    with pytest.raises(SystemExit, match="ran from the chat, structure_retrieval, and has no state.json"):
        main(["run", "chat"])
