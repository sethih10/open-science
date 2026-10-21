"""Write the README tables from _board.py, or check that they are current.

Usage: python board_tables.py --write | --check
The README holds two blocks between HTML-comment markers:
  <!-- board:evolution --> ... <!-- /board:evolution -->
  <!-- board:who -->       ... <!-- /board:who -->
"""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _board import STEPS, OWNER_NAMES

README = Path(__file__).resolve().parents[4] / "README.md"

def md(s):
    return s.replace("*", "\\*").replace("|", "\\|")

def evolution_table():
    rows = ["| Board step | What the board says | Refined by the literature | What we added or decided | Open, or an extension |",
            "|---|---|---|---|---|"]
    for s in STEPS:
        tail = f"Open: {s.open}" if s.open else (f"Extension: {s.ext}" if s.ext else "none")
        rows.append(f"| {md(s.title)} | {md(s.board)} | {md(s.lit_source)}: {md(s.lit)} | {md(s.ours)} | {md(tail)} |")
    return "\n".join(rows)

def who_table():
    rows = ["| Step | Human | LLM agent | Skill | Tool | Checkpoint |", "|---|---|---|---|---|---|"]
    for s in STEPS:
        owner = OWNER_NAMES[s.owners[0]].lower()
        llm = "; ".join(x for x in [f"{s.agent[0]}: {s.agent[1]}" if s.agent else "", f"extension: {s.agent_ext}" if s.agent_ext else ""] if x)
        tool = s.action if s.tools else ""
        rows.append(f"| {md(s.title)} | {md(s.human or '')} | {md(llm)} | {md(s.skill or '')} | {md(tool)} | {md(s.checkpoint or '')} |")
    rows.append("")
    rows.append("The actor that does the work in each step, in order: " + ", ".join(f"{s.title} {OWNER_NAMES[s.owners[0]].lower()}" for s in STEPS) + ".")
    return "\n".join(rows)

BLOCKS = {"board:evolution": evolution_table, "board:who": who_table}

def render(text):
    for name, fn in BLOCKS.items():
        pat = re.compile(rf"(<!-- {re.escape(name)} -->\n).*?(\n<!-- /{re.escape(name)} -->)", re.S)
        if not pat.search(text):
            raise SystemExit(f"README is missing the markers for {name}")
        text = pat.sub(lambda m: m.group(1) + fn() + m.group(2), text)
    return text

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "--check"
    old = README.read_text()
    new = render(old)
    if mode == "--write":
        README.write_text(new); print("README tables written")
    else:
        if old != new:
            print("README tables are stale; run board_tables.py --write"); sys.exit(1)
        print("README tables are current")
