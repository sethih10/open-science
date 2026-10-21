"""Figure 31: who does what, one card per board step in three phase columns; inside each card, chips for the
human, the LLM agent, the skill and the tool, with the concrete name; the chip with the thick edge does the work.
All text from _board.py. Axes in inches."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _style import *
from _board import STEPS, BY_KEY, PHASES, BOARD_DATE
from matplotlib.patches import FancyBboxPatch

FW, FH = 16.0, 13.8
fig = plt.figure(figsize=(FW, FH))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, FW); ax.set_ylim(0, FH); ax.axis("off")
fig.text(0.5, 0.985, "Who does what, step by step: one card per board step; inside it, the human, the LLM agent, the skill and the tool that act, the thick edge does the work",
         ha="center", va="top", fontsize=12.5, fontweight="bold")
fig.text(0.5, 0.967, f"board of {BOARD_DATE} · three phases left to right, cards top to bottom · {PAUSE} a checkpoint where the agent waits · dashed: an extension · tool names are the files under mcp/tools/, skills the folders under skills/, agents the files under agents/",
         ha="center", va="top", fontsize=8.4, color="#555555")

COLS = {"setup": 0.4, "step3": 5.6, "select": 10.8}; CW = 4.8; CARD_W = 4.6
TOPY = 12.55; ROW, RGAP, HEAD, PADB, GAP = 0.30, 0.06, 0.36, 0.10, 0.24
CORAL_F, CORAL_E = FLOW["coral"]

def chip(x, y, w, lane, text, owner=False, ext=False, pause=False):
    name, ec, fc = LANE[lane]
    ax.add_patch(FancyBboxPatch((x, y), w, ROW, boxstyle="round,pad=0.01,rounding_size=0.06", fc=fc if not ext else "white", ec=ec,
                                lw=2.0 if owner else 0.8, ls="--" if ext else "-", zorder=3))
    ax.add_patch(FancyBboxPatch((x + 0.05, y + 0.03), 0.24, ROW - 0.06, boxstyle="round,pad=0.005,rounding_size=0.04", fc=ec, ec="none", zorder=4))
    ax.text(x + 0.17, y + ROW / 2, lane, ha="center", va="center", fontsize=7.4, fontweight="bold", color="white", zorder=5)
    body = wrap(text, 72)
    ax.text(x + 0.38, y + ROW / 2, body, ha="left", va="center", fontsize=6.9, color="#555555" if ext else "#111111", zorder=5, linespacing=1.12)
    if pause:
        ax.text(x + w - 0.08, y + ROW / 2, PAUSE, ha="right", va="center", fontsize=7, color=ec, fontweight="bold", zorder=5)

def chips_of(s):
    rows = []
    if s.human: rows.append(("H", s.human, s.owners[0] == "H", False, bool(s.checkpoint)))
    if s.agent: rows.append(("L", f"{s.agent[0]}: {s.agent[1]}", s.owners[0] == "L", False, False))
    if s.agent_ext: rows.append(("L", "extension: " + s.agent_ext, False, True, False))
    if s.skill: rows.append(("S", s.skill, s.owners[0] == "S", False, False))
    if s.tools: rows.append(("T", s.action, s.owners[0] == "T", False, False))
    return rows

def card(x, ytop_, s):
    rows = chips_of(s)
    h = HEAD + len(rows) * (ROW + RGAP) + PADB
    y = ytop_ - h
    ax.add_patch(FancyBboxPatch((x, y), CARD_W, h, boxstyle="round,pad=0.02,rounding_size=0.12", fc="white", ec="#9a9a9a", lw=1.1, zorder=2))
    ax.text(x + 0.16, y + h - 0.19, s.title, ha="left", va="center", fontsize=9.0, fontweight="bold", zorder=4)
    if s.checkpoint:
        ax.text(x + CARD_W - 0.14, y + h - 0.19, f"{PAUSE} {s.checkpoint}", ha="right", va="center", fontsize=6.8, color=LANE["H"][1], fontweight="bold", zorder=4)
    yy = y + h - HEAD - ROW
    for lane, text, owner, ext, pause in rows:
        chip(x + 0.14, yy, CARD_W - 0.28, lane, text, owner=owner, ext=ext, pause=pause)
        yy -= ROW + RGAP
    return y

def down(x, y0, y1, label=None):
    arrow(ax, (x, y0), (x, y1), lw=1.2, ms=10)
    if label: ax.text(x + 0.12, (y0 + y1) / 2, label, ha="left", va="center", fontsize=7.2, color="#555555", style="italic")

# phase headers and bands
for ph, x in COLS.items():
    ax.text(x + CARD_W / 2 + 0.1, TOPY + 0.32, PHASES[ph], ha="center", va="center", fontsize=9.6, fontweight="bold", color=CORAL_E if ph == "step3" else "#333333")
arrow(ax, (COLS["setup"] + CARD_W + 0.12, TOPY + 0.32), (COLS["step3"] - 0.02, TOPY + 0.32), lw=1.4, ms=11)
arrow(ax, (COLS["step3"] + CARD_W + 0.18, TOPY + 0.32), (COLS["select"] - 0.02, TOPY + 0.32), lw=1.4, ms=11)

band_bottom = {}
for ph, x in COLS.items():
    steps = [s for s in STEPS if s.phase == ph]
    x0 = x + 0.1 if ph != "step3" else x + 0.1
    yt = TOPY
    for i, s in enumerate(steps):
        yb = card(x0, yt, s)
        if i < len(steps) - 1:
            label = "or" if s.key == "3.5" else None
            down(x0 + CARD_W / 2, yb - 0.02, yb - GAP + 0.02, label=label)
            yt = yb - GAP
    band_bottom[ph] = yb
x = COLS["step3"]; ax.add_patch(FancyBboxPatch((x - 0.05, band_bottom["step3"] - 0.25), CW, TOPY + 0.5 - (band_bottom["step3"] - 0.25), boxstyle="round,pad=0.02,rounding_size=0.15", fc=CORAL_F, ec=CORAL_E, lw=1.4, zorder=1))
ax.text(FW / 2, 0.22, "Legend: H human · L LLM agent · S skill, a written procedure the LLM follows · T tool, deterministic code · thick edge does the work · dashed, an extension · "
                      f"{PAUSE} a checkpoint where the agent waits for the human.\nfinal-state-planner runs every card: it calls each tool by name, reads cards, never writes coordinates.",
        ha="center", va="bottom", fontsize=7.4, style="italic", color="#444444", linespacing=1.4)
finish(fig, os.path.join(os.path.dirname(__file__), "..", "31-who-does-what.png"), copy_to="who-does-what")
