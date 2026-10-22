"""Write the generated blocks of README.md and AGENTS.md from _board.py and fragplace.registry, or check them.

Usage: python board_tables.py --write | --check
Blocks sit between HTML-comment markers, <!-- name --> ... <!-- /name -->:
  README.md:  board:evolution, board:who, registry:modules, registry:layout
  AGENTS.md:   board:pipeline, registry:tools, records:models, registry:layout
The layout block is built from the files on disk, so a module without a description here, or a described module
that is missing, fails the write; the tree is the repository as it is.
"""
import inspect, re, sys
from pathlib import Path
SRC = Path(__file__).resolve().parent
ROOT = SRC.parents[2]
sys.path.insert(0, str(SRC)); sys.path.insert(0, str(ROOT / "src"))
from _board import STEPS, OWNER_NAMES, PHASES  # noqa: E402
from fragplace.registry.tools import CATEGORY, REGISTRY, BY_NAME  # noqa: E402
from fragplace.registry.agents import AGENTS, HPC_ONLY, SKILLS_OURS  # noqa: E402
from fragplace.schemas import records  # noqa: E402

def md(s):
    return str(s).replace("*", "\\*").replace("|", "\\|")

def row(step, cells):
    """One table row; every cell of a deferred step is struck through, so the row reads as commented out."""
    if step.deferred:
        cells = [f"~~{c}~~" if c.strip() else c for c in cells]
    return "| " + " | ".join(cells) + " |"

def evolution_table():
    rows = ["| Board step | What the board says | Refined by the literature | What we added or decided | Open, or an extension |", "|---|---|---|---|---|"]
    for s in STEPS:
        tail = f"Open: {s.open}" if s.open else (f"Extension: {s.ext}" if s.ext else "none")
        if s.deferred:
            tail = f"Deferred: {s.deferred}" + (f". Open: {s.open}" if s.open else "")
        rows.append(row(s, [md(s.title), md(s.board), f"{md(s.lit_source)}: {md(s.lit)}", md(s.ours), md(tail)]))
    return "\n".join(rows)

def agents_cell(s):
    parts = [f"{n}: {r}" for n, r in s.agents] + ([f"extension: {s.agent_ext}"] if s.agent_ext else [])
    return "; ".join(parts)

def who_table():
    rows = ["| Step | Human | LLM agent | Skill | Tool | Checkpoint |", "|---|---|---|---|---|---|"]
    for s in STEPS:
        tool = (f"deferred, {s.deferred}; " if s.deferred else "") + (s.action if s.tools else "")
        rows.append(row(s, [md(s.title), md(s.human or ''), md(agents_cell(s)), md(s.skill or ''), md(tool), md(s.checkpoint or '')]))
    rows += ["", "The actor that does the work in each step, in order: " + ", ".join(f"{s.title} {OWNER_NAMES[s.owners[0]].lower()}" for s in STEPS) + "."]
    return "\n".join(rows)

def modules_table():
    rows = ["| Phase | Board step | Tool | Takes | Returns | Status |", "|---|---|---|---|---|---|"]
    for s in STEPS:
        for name in s.tools + s.ext_tools:
            t = BY_NAME[name]
            rows.append(row(s, [PHASES[s.phase], md(s.title), f"`{t.name}`", md(', '.join(t.inputs)), md(', '.join(t.outputs)), "deferred at this step" if s.deferred else t.status]))
    return "\n".join(rows)

def pipeline_table():
    rows = ["| Step | Owner | What it does | Tools | Checkpoint |", "|---|---|---|---|---|"]
    for s in STEPS:
        owner = {"T": "Tool", "L": "LLM", "H": "Human", "S": "Skill"}[s.owners[0]]
        tools = ", ".join(f"`{t}`" for t in s.tools) + (" ; extension: " + ", ".join(f"`{t}`" for t in s.ext_tools) if s.ext_tools else "")
        detail = (f"Deferred, {s.deferred}. " if s.deferred else "") + s.detail
        rows.append(row(s, [md(s.title), owner, md(detail), tools, md(s.checkpoint or '')]))
    return "\n".join(rows)

def tools_section():
    out = []
    for i, t in enumerate(REGISTRY, 1):
        out.append(f"### 3.{i} `{t.name}`, board step{'s' if len(t.board_steps) > 1 else ''} {', '.join(t.board_steps)}, {t.status}\n")
        out.append(t.purpose + "\n")
        out.append("| Field | Content |\n|---|---|")
        out.append("| Inputs | " + md("; ".join(f"{k}: {v}" for k, v in t.inputs.items())) + " |")
        out.append("| Outputs | " + md("; ".join(f"{k}: {v}" for k, v in t.outputs.items())) + " |")
        if t.checks: out.append("| Checks | " + md("; ".join(t.checks)) + " |")
        if t.thresholds: out.append("| Thresholds | " + md("; ".join(f"{k}: {v}" for k, v in t.thresholds.items())) + " |")
        if t.wraps: out.append("| Wraps | " + md("; ".join(t.wraps)) + " |")
        if t.logs: out.append("| Logs | " + md("; ".join(t.logs)) + " |")
        out.append(f"| Module | `src/fragplace/tools/{CATEGORY[t.name]}.py`, function `{t.name}({', '.join(t.inputs)})` |")
        out.append("")
    return "\n".join(out).rstrip()

def models_table():
    rows = ["| Record | Fields |", "|---|---|"]
    for name, cls in inspect.getmembers(records, inspect.isclass):
        if cls.__module__ != records.__name__ or not hasattr(cls, "model_fields"): continue
        fields = ", ".join(f"{f}: {md(str(info.annotation).replace('typing.', '').replace('<class ', '').replace('>', '').replace(chr(39), ''))}" for f, info in cls.model_fields.items())
        rows.append(f"| `{name}` | {fields} |")
    return "\n".join(rows)

# ---- the repository layout: every folder of the package nested the same way, every tool, skill and agent named
PKG = {  # one line per module of src/fragplace/, in reading order; folders end with /
    "registry/": "every tool and every agent defined once",
    "registry/tools.py": "ToolSpec and REGISTRY, the tools of section 3; CATEGORY maps each tool to its module",
    "registry/agents.py": "the roster, the checkpoints, the skill names; the figures import it",
    "registry/steps.py": "the steps in execution order, each with its agents, its tools and its checkpoint; 3.5 commented out",
    "tools/": "one module per category, as ChemCrow and Biomni group theirs; a function per tool, parameters as in the registry",
    "schemas/": "the records of section 4",
    "schemas/records.py": "the Pydantic records every tool takes and returns",
    "runtime/": "what every tool runs under; the names are ChemGraph's",
    "runtime/project.py": "PROJECT.md: read, write, lock, require_locked, settings_hash; decision() for every open threshold",
    "runtime/journal.py": "Run, trace.jsonl, the @traced decorator",
    "runtime/cache.py": "content-addressed results of relaxations and force calls",
    "runtime/checkpoints.py": "the five checkpoints of registry/agents.py: require, record",
    "runtime/state.py": "the position in the pipeline, persisted in state.json",
    "runtime/policy.py": "the PreToolUse hooks of hooks/hooks.json: no coordinate or record edits, no approval by the model, the checkpoint before a gated tool, no answer filled in by the model",
    "runtime/artifacts.py": "structures on disk as StructureRef; tags 0 subsurface, 1 surface, 2 fragment A, 3 fragment B; each fragment's binding atom; the structure hash",
    "runtime/geometry.py": "the geometry the tools share: minimum images, bonds, heights, the nearest site, the site graph, symmetry operations",
    "memory/": "what a study learns",
    "memory/casebank.py": "lessons.md as records; retrieve by system and failure",
    "calculators/": "one ASE adapter base and a Committee; potentials imported lazily",
    "calculators/emt.py": "ASE EMT, the test potential: Pt-group metals and H, C, N, O",
    "calculators/uma.py": "UMA through fairchem; needs HF_TOKEN",
    "calculators/mace.py": "MACE: MACE-MP by name, or a model or committee from files",
    "calculators/chgnet.py": "CHGNet",
    "execution/": "Job and Backend",
    "execution/local.py": "the laptop and GPU lanes; the CPU budget every entry point sets the thread counts to",
    "execution/srun.py": "the lanes of the heavy tools: here, or the worker, one per session on a compute node under srun or a step of FRAGPLACE_SLURM_JOB",
    "execution/batch.py": "the batch lane: one sbatch job per heavy call, recorded in runs/<study>/jobs.json, found again by its hash, polled no more often than every 15 s, resubmitted on TIMEOUT, OUT_OF_MEMORY, NODE_FAIL and PREEMPTED, three attempts in all",
    "execution/pool.py": "the relaxation pool inside a job: workers sized to its cores, the potential loaded once per worker",
    "execution/slurm.py": "the HPC lane, custodian inside the job script",
    "execution/tracker.py": "job attempts, diagnoses, the retry cap of three",
    "study/": "a study's records and the calls on them; no agent lives here, the agents are agents/*.md",
    "study/calls.py": "the tools as the agents call them, by study name, each answering with a summary, the step's files and the question box when the human is owed an answer; what the MCP server publishes",
    "study/store.py": "Study: binds each tool's inputs from the run's artifacts; records the human's decisions, interview answers and checkpoint choices",
    "study/human.py": "the question boxes the orchestrator asks, built from the records, and the hook that records the human's answers under the human's name",
    "study/summary.py": "summary.md: one short block per step from the tool's own numbers, shown after the step and again at the end",
    "study/views.py": "the geometry files and pictures under geometries/<step>/, and show_structures for the human",
    "study/example.py": "the example study, OH on Pt(111) with a named potential and test values; init from the supplied structures",
    "study/rollout.py": "the test harness: the deterministic rollout over registry/steps.py without an LLM; stops at every checkpoint, resumes from state.json",
    "mcp/": "the MCP side",
    "mcp/server.py": "one MCP tool per registry entry and the three study operations; heavy tools sent to a compute node; the fragplace-server command",
    "eval/": "the agent-level benchmark",
    "eval/harness.py": "the study with and without each skill and agent, on the OC20NEB subset",
    "cli/": "the command line",
    "cli/main.py": "fragplace registry | check | init | run | approve | decide | status | decisions",
    "errors.py": "SettingsNotLocked, SettingsMismatch, Rejected, Escalate, CheckpointPending, OpenDecision",
}
ROOT_ENTRIES = [  # (name, description, children) for the plugin side and the data; the package is inserted at src/fragplace/
    ("README.md, CLAUDE.md, AGENTS.md", "the entry points; CLAUDE.md points a coding agent to AGENTS.md", []),
    ("PROJECT.md, lessons.md", "the settings template; the case bank", []),
    ("pyproject.toml", "package fragplace, commands fragplace and fragplace-server, one extra per lane", []),
    (".claude-plugin/plugin.json", "declares skills/, hooks/hooks.json and .mcp.json; Claude Code finds agents/ and commands/ by their names", []),
    (".claude-plugin/marketplace.json", "a local marketplace, so Claude Code loads the plugin for this repository without --plugin-dir", []),
    (".mcp.json", "the MCP server fragplace-server from the plugin's .venv; its tools are called as mcp__plugin_fragplace_fragplace__<tool>", []),
    ("commands/study.md", "/fragplace:study <name>: the session becomes the orchestrator of agents/solution-planner.md", []),
    ("hooks/hooks.json", "PreToolUse: block coordinate and record edits, the model passing a checkpoint, a gated tool before its checkpoint, an answer the model filled in; PostToolUse: record the human's answers", []),
    ("agents/", "the eight agents of section 6, one page each, allowed tools in the frontmatter; solution-planner is the orchestrator, the others its subagents", "agents"),
    ("skills/", "the six skills of section 6; five more are reused from AtomisticSkills", "skills"),
    ("src/fragplace/", "the package; the folder names are ChemGraph's, the tools by category ChemCrow's and Biomni's", "package"),
    ("tests/", "registry, tool modules, agent files and the figures' data module agree; records; operations; hooks; state and jobs; one golden example per tool; the example study end to end, scripted and as an agent drives it", []),
    ("ci/github-workflow.yml", "ruff, pytest, the figures rendered, the generated blocks checked; move to .github/workflows/ with a token that has the workflow scope", []),
    ("runs/<study>/", "PROJECT.md copy, trace.jsonl, checkpoints.json, summary.md, geometries/, cards/, structures/, cache/, report.md; state.json under the test harness", []),
    ("figures/", "the README figures, PNG and SVG", []),
    ("docs/", "README.md indexes it", [
        ("design/", "the design history and the three reviews", []),
        ("figures/src/_board.py", "the data module figures 29 to 32 and the generated blocks come from", []),
        ("benchmark/", "the OC20NEB subset, baselines, scoring: planned", [])]),
]

def package_nodes():
    pkg = ROOT / "src" / "fragplace"
    on_disk = sorted(str(p.relative_to(pkg)) + ("/" if p.is_dir() else "") for p in pkg.rglob("*")
                     if "__pycache__" not in p.parts and p.name != "__init__.py" and not p.name.endswith(".pyc"))
    described = set(PKG) | {f"tools/{c}.py" for c in CATEGORY.values()}
    missing = [d for d in described if d not in on_disk]; undescribed = [d for d in on_disk if d not in described]
    if missing or undescribed:
        raise SystemExit(f"layout: described but missing {missing}; on disk but undescribed {undescribed}")
    tools = {}
    for t in REGISTRY: tools.setdefault(CATEGORY[t.name], []).append(t.name)
    nodes, folders = [], {}
    for path, desc in PKG.items():
        if path.endswith("/"):
            folders[path] = (path, desc, []); nodes.append(folders[path])
            if path == "tools/":
                folders[path][2].extend((f"{c}.py", ", ".join(names), []) for c, names in tools.items())
        else:
            folder = path.rsplit("/", 1)[0] + "/" if "/" in path else None
            (folders[folder][2] if folder else nodes).append((path.split("/")[-1], desc, []))
    return nodes

def agent_nodes():
    out = []
    for name, decides in AGENTS.items():
        assert (ROOT / "agents" / f"{name}.md").exists(), f"agents/{name}.md is missing"
        out.append((f"{name}.md", decides.split(";")[0].split(",")[0] + ("; only with HPC" if name in HPC_ONLY else ""), []))
    return out

def skill_nodes():
    out = []
    for name in SKILLS_OURS:
        assert (ROOT / "skills" / name / "SKILL.md").exists(), f"skills/{name}/SKILL.md is missing"
        out.append((f"{name}/SKILL.md", "", []))
    return out

def layout_tree():
    def expand(entries):
        out = []
        for name, desc, kids in entries:
            kids = {"agents": agent_nodes, "skills": skill_nodes, "package": package_nodes}[kids]() if isinstance(kids, str) else expand(kids)
            out.append((name, desc, kids))
        return out
    lines = []
    def walk(entries, prefix):
        for i, (name, desc, kids) in enumerate(entries):
            last = i == len(entries) - 1
            lines.append((prefix + ("└── " if last else "├── ") + name, desc))
            walk(kids, prefix + ("    " if last else "│   "))
    lines.append(("open-science-hackathon/", "the FragPlace plugin, laid out as Claude Code lays out a plugin"))
    walk(expand(ROOT_ENTRIES), "")
    width = max(len(left) for left, _ in lines) + 2
    return "```\n" + "\n".join(f"{left:{width}s}{desc}".rstrip() for left, desc in lines) + "\n```"

TARGETS = {ROOT / "README.md": {"board:evolution": evolution_table, "board:who": who_table, "registry:modules": modules_table, "registry:layout": layout_tree},
           ROOT / "AGENTS.md": {"board:pipeline": pipeline_table, "registry:tools": tools_section, "records:models": models_table, "registry:layout": layout_tree}}

def render(text, blocks):
    for name, fn in blocks.items():
        pat = re.compile(rf"(<!-- {re.escape(name)} -->\n).*?(\n<!-- /{re.escape(name)} -->)", re.S)
        if not pat.search(text):
            raise SystemExit(f"missing markers for {name}")
        text = pat.sub(lambda m: m.group(1) + fn() + m.group(2), text)
    return text

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "--check"
    stale = []
    for path, blocks in TARGETS.items():
        old = path.read_text(); new = render(old, blocks)
        if mode == "--write":
            path.write_text(new); print(f"{path.name}: blocks written")
        elif old != new:
            stale.append(path.name)
    if mode != "--write":
        if stale:
            print("stale generated blocks in " + ", ".join(stale) + "; run board_tables.py --write"); sys.exit(1)
        print("README.md and AGENTS.md generated blocks are current")
