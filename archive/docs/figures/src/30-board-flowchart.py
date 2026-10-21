"""Figure 30: the pipeline we will implement. The board's steps top to bottom, each with its tool call; amber tags
for the open decisions; purple side boxes for our agents, dashed where they are extensions; a pink pause glyph at
every human checkpoint. All text from _board.py."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _style import *
from _board import STEPS, BY_KEY, BOARD_DATE, PLANNER, code_order_note
from matplotlib.patches import FancyBboxPatch

GREY_F, GREY_E = FLOW["grey"]; CORAL_F, CORAL_E = FLOW["coral"]
PUR_F, PUR_E, PUR_T = FLOW["purple"]; AMB_F, AMB_E, AMB_T = FLOW["amber"]; PINK = FLOW["pink"]
fig = plt.figure(figsize=(9.5, 18))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
fig.text(0.5, 0.982, "The pipeline we will implement: the board's steps, each with its tool call and its open decision", ha="center", va="top", fontsize=12, fontweight="bold")
fig.text(0.5, 0.966, f"board of {BOARD_DATE} · grey: computation · coral: step 3, the stated problem · purple: our agents, dashed is an extension\namber: open decision · pink {PAUSE}: a checkpoint where the agent waits",
         ha="center", va="top", fontsize=7.6, color="#555555", linespacing=1.3)
fig.text(0.5, 0.944, f"{PLANNER} calls every tool by name, reads cards, never writes coordinates, stops at every {PAUSE}",
         ha="center", va="top", fontsize=7.6, color=PUR_T, style="italic")

SX, SW = 0.02, 0.245          # side boxes
CX, W = 0.30, 0.46            # main column
TX, TW = 0.775, 0.215         # amber tags
H, G = 0.045, 0.010

def mono_split(action):
    """'tool: what it does' -> (tool, rest); agent lines keep the first word as the name."""
    if ":" in action:
        a, b = action.split(":", 1); return a.strip(), b.strip()
    return action, ""

def main_box(y, s, h=H, fc=GREY_F, ec=GREY_E, x=CX, w=W):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.003,rounding_size=0.012", fc=fc, ec=ec, lw=1.2, zorder=3))
    ax.text(x + 0.012, y + h - 0.006, s.title, ha="left", va="top", fontsize=8.6, fontweight="bold", zorder=4)
    tool, rest = mono_split(s.action)
    body = wrap(f"{tool}: {rest}" if rest else tool, int(w * 160))
    ax.text(x + w / 2, y + 0.005, body, ha="center", va="bottom", fontsize=6.6, color="#333333", zorder=4, linespacing=1.15)
    if s.checkpoint:
        ax.text(x + w - 0.006, y + h - 0.005, f"{PAUSE} {s.checkpoint}", ha="right", va="top", fontsize=5.9, color=PINK, fontweight="bold", zorder=5)
    if s.open:
        ty = y + h / 2
        ax.plot([x + w, TX], [ty, ty], color=AMB_E, lw=1.0, zorder=2)
        th = 0.030
        ax.add_patch(FancyBboxPatch((TX, ty - th / 2), TW, th, boxstyle="round,pad=0.002,rounding_size=0.008", fc=AMB_F, ec=AMB_E, lw=1.0, zorder=3))
        ax.text(TX + TW / 2, ty, wrap("open: " + s.open, 38), ha="center", va="center", fontsize=6.0, color=AMB_T, zorder=4, linespacing=1.15)

def side_box(y_center, name, note, dashed=False, board=None):
    h = 0.046; y = y_center - h / 2
    ax.add_patch(FancyBboxPatch((SX, y), SW, h, boxstyle="round,pad=0.003,rounding_size=0.012", fc=PUR_F, ec=PUR_E, lw=1.1, ls="--" if dashed else "-", zorder=3))
    ax.text(SX + SW / 2, y + h - 0.006, name, ha="center", va="top", fontsize=7.6, fontweight="bold", color=PUR_T, zorder=4)
    sub = wrap(note, 40) if note else ""
    if board: sub = (sub + "\n" if sub else "") + f"board: {board}"
    ax.text(SX + SW / 2, y + 0.005, sub, ha="center", va="bottom", fontsize=5.9, color="#555555", zorder=4, linespacing=1.15)
    arrow(ax, (SX + SW + 0.003, y_center), (CX - 0.004, y_center), color=PUR_E, lw=1.1, ms=9, ls="--" if dashed else "-")

def down(y0, y1, x=CX + W / 2):
    arrow(ax, (x, y0), (x, y1), color=GREY_E, lw=1.2, ms=10)

y = 0.922; centre = {}
for key in ("prompt", "1", "1*", "2"):
    s = BY_KEY[key]; main_box(y - H, s); centre[key] = y - H / 2
    down(y - H - 0.002, y - H - G + 0.002); y -= H + G

# ---- step 3 group
pts = [BY_KEY[k] for k in ("3.1", "3.2", "3.3", "3.4")]
ih, ig = 0.043, 0.007; fork_h = 0.062
g_h = 0.026 + 4 * (ih + ig) + fork_h + 0.030
g_top = y
ax.add_patch(FancyBboxPatch((CX, g_top - g_h), W, g_h, boxstyle="round,pad=0.003,rounding_size=0.02", fc=CORAL_F, ec=CORAL_E, lw=1.4, zorder=2))
ax.text(CX + W / 2, g_top - 0.014, "(3) Adsorbate placement, very important: the stated problem", ha="center", va="center", fontsize=8.8, fontweight="bold", zorder=4)
centre["3"] = g_top - 0.014
yy = g_top - 0.026; ix, iw = CX + 0.018, W - 0.036
for s in pts:
    purple = s.key == "3.4"
    main_box(yy - ih, s, h=ih, fc=PUR_F if purple else "white", ec=PUR_E if purple else GREY_E, x=ix, w=iw)
    centre[s.key] = yy - ih / 2
    yy -= ih; down(yy - 0.002, yy - ig + 0.002, x=ix + iw / 2); yy -= ig
half = (iw - 0.03) / 2; xl, xr = ix, ix + half + 0.03
ax.plot([xl + half / 2, xr + half / 2], [yy - 0.0, yy - 0.0], color=GREY_E, lw=1.2, zorder=4)
yy -= 0.004
for s, xx in ((BY_KEY["3.5"], xl), (BY_KEY["3.6"], xr)):
    ax.add_patch(FancyBboxPatch((xx, yy - fork_h), half, fork_h, boxstyle="round,pad=0.003,rounding_size=0.012", fc="white", ec=GREY_E, lw=1.2, zorder=3))
    ax.text(xx + half / 2, yy - 0.005, wrap(s.title, 24), ha="center", va="top", fontsize=7.2, fontweight="bold", zorder=4, linespacing=1.05)
    tool, rest = mono_split(s.action)
    ax.text(xx + half / 2, yy - fork_h + 0.005, wrap(f"{tool}: {rest}", 36), ha="center", va="bottom", fontsize=5.9, color="#333333", zorder=4, linespacing=1.12)
    centre[s.key] = yy - fork_h / 2
ax.text(CX + W / 2, yy - fork_h / 2, "or", ha="center", va="center", fontsize=8, color="#555555", zorder=5)
s35 = BY_KEY["3.5"]
if s35.open:
    ty = centre["3.5"]; th = 0.030
    ax.plot([CX + W, TX], [ty, ty], color=AMB_E, lw=1.0, zorder=2)
    ax.add_patch(FancyBboxPatch((TX, ty - th / 2), TW, th, boxstyle="round,pad=0.002,rounding_size=0.008", fc=AMB_F, ec=AMB_E, lw=1.0, zorder=3))
    ax.text(TX + TW / 2, ty, wrap("open: " + s35.open, 38), ha="center", va="center", fontsize=6.0, color=AMB_T, zorder=4, linespacing=1.15)
ax.text(CX + W / 2, g_top - g_h + 0.012, code_order_note(), ha="center", va="center", fontsize=6.4, style="italic", color=CORAL_E, zorder=4)
y = g_top - g_h
down(y - 0.002, y - G + 0.002); y -= G

for key in ("4", "5", "6", "7", "8", "solution"):
    s = BY_KEY[key]; main_box(y - H, s); centre[key] = y - H / 2
    if key != "solution": down(y - H - 0.002, y - H - G + 0.002)
    y -= H + G

# ---- side boxes: our agents at the steps where the board drew an input, dashed where they are extensions
side_box(centre["prompt"], " · ".join(n for n, _ in BY_KEY["prompt"].agents), "; ".join(r for _, r in BY_KEY["prompt"].agents), board=BY_KEY["prompt"].board_input)
side_box(centre["1*"], "active-learning loop", BY_KEY["1*"].ext, dashed=True)
side_box(centre["3.1"], BY_KEY["3.4"].agents[0][0], "point 3.4: " + BY_KEY["3.4"].agents[0][1], board="Critic, knowledge")
side_box(centre["3.3"], "vision model", BY_KEY["3.4"].ext, dashed=True, board="Vision model (?)")
side_box(centre["5"], BY_KEY["3.4"].agents[0][0], BY_KEY["5"].ext, dashed=True, board=BY_KEY["5"].board_input)
side_box(centre["7"], "agentic uncertainty, DFT", BY_KEY["7"].ext, dashed=True, board=BY_KEY["7"].board_input)
side_box(centre["8"], BY_KEY["8"].agents[0][0], BY_KEY["8"].agents[0][1], board=BY_KEY["8"].board_input)
ax.text(0.5, 0.012, "Side boxes: where the board drew an agent input, the agent that takes it; amber tags: the one open decision per step, agent.md section 11 has the full list.",
        ha="center", va="bottom", fontsize=6.8, style="italic", color="#444444")
finish(fig, os.path.join(os.path.dirname(__file__), "..", "30-board-flowchart.png"), copy_to="pipeline")
