"""Write the generated blocks of README.md and AGENTS.md from _board.py and fragplace.registry, or check them.

Usage: python board_tables.py --write | --check
Blocks sit between HTML-comment markers, <!-- name --> ... <!-- /name -->:
  README.md:  board:evolution, board:who, registry:modules
  AGENTS.md:   board:pipeline, registry:tools, records:models
"""
import inspect, re, sys
from pathlib import Path
SRC = Path(__file__).resolve().parent
ROOT = SRC.parents[2]
sys.path.insert(0, str(SRC)); sys.path.insert(0, str(ROOT / "src"))
from _board import STEPS, OWNER_NAMES, PHASES  # noqa: E402
from fragplace.registry.tools import CATEGORY, REGISTRY, BY_NAME  # noqa: E402
from fragplace.schemas import records  # noqa: E402

def md(s):
    return str(s).replace("*", "\\*").replace("|", "\\|")

def evolution_table():
    rows = ["| Board step | What the board says | Refined by the literature | What we added or decided | Open, or an extension |", "|---|---|---|---|---|"]
    for s in STEPS:
        tail = f"Open: {s.open}" if s.open else (f"Extension: {s.ext}" if s.ext else "none")
        rows.append(f"| {md(s.title)} | {md(s.board)} | {md(s.lit_source)}: {md(s.lit)} | {md(s.ours)} | {md(tail)} |")
    return "\n".join(rows)

def agents_cell(s):
    parts = [f"{n}: {r}" for n, r in s.agents] + ([f"extension: {s.agent_ext}"] if s.agent_ext else [])
    return "; ".join(parts)

def who_table():
    rows = ["| Step | Human | LLM agent | Skill | Tool | Checkpoint |", "|---|---|---|---|---|---|"]
    for s in STEPS:
        rows.append(f"| {md(s.title)} | {md(s.human or '')} | {md(agents_cell(s))} | {md(s.skill or '')} | {md(s.action if s.tools else '')} | {md(s.checkpoint or '')} |")
    rows += ["", "The actor that does the work in each step, in order: " + ", ".join(f"{s.title} {OWNER_NAMES[s.owners[0]].lower()}" for s in STEPS) + "."]
    return "\n".join(rows)

def modules_table():
    rows = ["| Phase | Board step | Tool | Takes | Returns | Status |", "|---|---|---|---|---|---|"]
    for s in STEPS:
        for name in s.tools + s.ext_tools:
            t = BY_NAME[name]
            rows.append(f"| {PHASES[s.phase]} | {md(s.title)} | `{t.name}` | {md(', '.join(t.inputs))} | {md(', '.join(t.outputs))} | {t.status} |")
    return "\n".join(rows)

def pipeline_table():
    rows = ["| Step | Owner | What it does | Tools | Checkpoint |", "|---|---|---|---|---|"]
    for s in STEPS:
        owner = {"T": "Tool", "L": "LLM", "H": "Human", "S": "Skill"}[s.owners[0]]
        tools = ", ".join(f"`{t}`" for t in s.tools) + (" ; extension: " + ", ".join(f"`{t}`" for t in s.ext_tools) if s.ext_tools else "")
        rows.append(f"| {md(s.title)} | {owner} | {md(s.detail)} | {tools} | {md(s.checkpoint or '')} |")
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

TARGETS = {ROOT / "README.md": {"board:evolution": evolution_table, "board:who": who_table, "registry:modules": modules_table},
           ROOT / "AGENTS.md": {"board:pipeline": pipeline_table, "registry:tools": tools_section, "records:models": models_table}}

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
