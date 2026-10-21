"""Assert that the four board figures, README.md and agent.md carry the same steps, names, tools and decisions as
_board.py. Run after rendering 29 to 32. Exit code 1 on any failure."""
import hashlib, re, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _board import STEPS, CHECKPOINTS, OWNER_NAMES

SRC = Path(__file__).resolve().parent; FIG = SRC.parent; ROOT = SRC.parents[3]
DUMPS = {29: "29-board-evolution", 30: "30-board-flowchart", 31: "31-who-does-what", 32: "32-architecture"}
COPIES = {29: "board-evolution", 30: "pipeline", 31: "who-does-what", 32: "architecture"}
fails = []

def dump(n):
    return (FIG / f"{DUMPS[n]}.txt").read_text()

def need(cond, msg):
    if not cond: fails.append(msg)

for n in DUMPS:
    need((FIG / f"{DUMPS[n]}.txt").exists(), f"figure {n}: no text dump; render it first")
if fails:
    print("\n".join(fails)); sys.exit(1)

texts = {n: dump(n) for n in DUMPS}
flat = {n: re.sub(r"\s+", " ", t) for n, t in texts.items()}
for s in STEPS:
    for n in (29, 30, 31):
        need(s.title in flat[n], f"figure {n}: step title missing: {s.title}")
    if s.open:
        for n in (29, 30):
            need(s.open in flat[n], f"figure {n}: open decision missing at {s.key}: {s.open}")
    if s.ext:
        need(s.ext in flat[29], f"figure 29: extension missing at {s.key}")
    for t in s.tools:
        for n in (30, 31, 32):
            need(t in flat[n], f"figure {n}: tool missing: {t} (step {s.key})")
    if s.agent:
        for n in (30, 31, 32):
            need(s.agent[0] in flat[n], f"figure {n}: agent missing: {s.agent[0]} (step {s.key})")
    if s.skill:
        need(s.skill.split(";")[0].split(",")[0].strip() in flat[31], f"figure 31: skill missing at {s.key}: {s.skill}")
for c in CHECKPOINTS:
    for n in (30, 31, 32):
        need(c in flat[n], f"figure {n}: checkpoint missing: {c}")
keys = {s.key for s in STEPS} | {"3"}   # "(3)" is the group header of the six points
for n, t in texts.items():
    for m in re.finditer(r"\((\d\.\d|\d\*?)\)", t):
        need(m.group(1) in keys, f"figure {n}: step number {m.group(1)} is not a board key")

# README tables current
r = subprocess.run([sys.executable, str(SRC / "board_tables.py"), "--check"], capture_output=True, text=True)
need(r.returncode == 0, "README: " + r.stdout.strip())

# agent.md section 2: owner and tools per step
agent = (ROOT / "agent.md").read_text()
sec = agent[agent.index("## 2. The exact pipeline"):agent.index("## 3. The tools")]
rows = [l for l in sec.splitlines() if l.startswith("| ") and not l.startswith("| Step") and not l.startswith("|--")]
by_first = {}
for l in rows:
    cells = [c.strip() for c in l.strip("|").split("|")]
    by_first[cells[0]] = cells
for s in STEPS:
    if s.key == "prompt": continue
    head = s.title.replace("(", "").replace(")", "").replace("\\", "")
    match = next((c for k, c in by_first.items() if k.replace("\\", "").startswith(head.split(" ")[0] + " ") or k.replace("\\", "") == head), None)
    if not match:
        fails.append(f"agent.md section 2: no row for {s.title}"); continue
    owner_word = {"T": "Tool", "L": "LLM", "H": "Human", "S": "Skill"}[s.owners[0]]
    need(match[1].startswith(owner_word), f"agent.md section 2: owner of {s.title} is '{match[1]}', _board says {owner_word}")
    for t in s.tools:
        need(t in match[3], f"agent.md section 2: tool {t} missing in the row of {s.title}")

# root copies identical to archive PNGs
for n, name in COPIES.items():
    a, b = FIG / f"{DUMPS[n]}.png", ROOT / "figures" / f"{name}.png"
    need(b.exists() and hashlib.md5(a.read_bytes()).hexdigest() == hashlib.md5(b.read_bytes()).hexdigest(), f"figures/{name}.png differs from the archive PNG")

if fails:
    print("\n".join(fails)); print(f"{len(fails)} problems"); sys.exit(1)
print("all four figures, README tables and agent.md section 2 agree with _board.py")
