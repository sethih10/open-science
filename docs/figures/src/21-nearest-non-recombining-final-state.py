"""Figure 21: the final-state problem for a dissociation step. The product fragments must sit as
close as possible without bonding back; a far final state folds diffusion into the band."""
import sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
from _style import *
from matplotlib.patches import Circle

A_COL, B_COL, RED = "#1e3a8a", "#d97706", "#b91c1c"
fig = plt.figure(figsize=(13, 7.6))
title(fig, "Final state of a dissociation step: the fragments as close as possible without bonding back",
      "top: the initial state and three product candidates · bottom left: why the far one is wrong · bottom right: the recipe · schematic, not to scale")

# ---------- top row: four mini lattices
def lattice(ax, nx=6, ny=4):
    dy = math.sqrt(3) / 2
    pts = []
    for j in range(ny):
        for i in range(nx):
            x = i + (0.5 if j % 2 else 0.0); y = j * dy
            pts.append((x, y))
            ax.add_patch(Circle((x, y), 0.30, fc="#e5e5e5", ec="#b5b5b5", lw=0.8, zorder=1))
    ax.set_xlim(-0.6, nx + 0.1); ax.set_ylim(-0.6, (ny - 1) * dy + 0.6); ax.set_aspect("equal"); ax.axis("off")
    return pts

def hollow(i, j, up=True):
    """centre of the triangle above (up) or below the atom (i, j) in the row-offset hex grid"""
    dy = math.sqrt(3) / 2
    x = i + (0.5 if j % 2 else 0.0)
    return (x + 0.5, j * dy + dy / 3) if up else (x + 0.5, j * dy - dy / 3)

def frag(ax, p, col, r, label):
    ax.add_patch(Circle(p, r, fc=col, ec="white", lw=1.0, zorder=3))
    ax.text(p[0], p[1], label, ha="center", va="center", fontsize=7.5, color="white", fontweight="bold", zorder=4)

panels = [("Initial state: AB*", "A bound at a hollow, B on A", None),
          ("Candidate 1: adjacent hollow", "B relaxes back onto A:\nrejected, the bond re-forms", "exists"),
          ("Candidate 2: next hollow, one lattice spacing", "no A–B bond after relaxation:\nchosen, the nearest that stays apart", "ours"),
          ("Candidate 3: far hollow", "valid, but the band from AB* to here\nincludes one or more diffusion steps", None)]
xs = [0.03, 0.27, 0.51, 0.75]
for k, (t, sub, kind) in enumerate(panels):
    ax = fig.add_axes([xs[k], 0.50, 0.22, 0.33])
    pts = lattice(ax)
    A = hollow(2, 1, up=True)
    if k == 0:
        frag(ax, A, A_COL, 0.26, "A"); frag(ax, (A[0] + 0.22, A[1] + 0.30), B_COL, 0.19, "B")
        ax.plot([A[0], A[0] + 0.22], [A[1], A[1] + 0.30], color="#333333", lw=2.2, zorder=2)
    elif k == 1:
        B = hollow(2, 1, up=False); B = (B[0] + 0.5, B[1] + math.sqrt(3) / 2 * 0 + 0.0)  # adjacent hcp-type hollow
        B = (A[0] + 0.5, A[1] - math.sqrt(3) / 6 * 0 - 0.29)
        frag(ax, A, A_COL, 0.26, "A"); frag(ax, B, B_COL, 0.19, "B")
        ax.plot([A[0], B[0]], [A[1], B[1]], color=RED, lw=3.0, zorder=2)
        ax.text(A[0] + 0.25, A[1] + 0.62, "bond re-forms", color=RED, fontsize=7.2, ha="center")
    elif k == 2:
        B = hollow(3, 1, up=True)
        frag(ax, A, A_COL, 0.26, "A"); frag(ax, B, B_COL, 0.19, "B")
        ax.annotate("", xy=(B[0], B[1] + 0.50), xytext=(A[0], A[1] + 0.50),
                    arrowprops=dict(arrowstyle="<->", color=HI_EDGE, lw=1.3, shrinkA=0, shrinkB=0))
        ax.text((A[0] + B[0]) / 2, A[1] + 0.66, "one spacing", color=HI_EDGE, fontsize=7.2, ha="center")
    else:
        B = hollow(5, 2, up=True); B = (B[0] - 0.5, B[1])
        frag(ax, A, A_COL, 0.26, "A"); frag(ax, B, B_COL, 0.19, "B")
        ax.annotate("", xy=(B[0] - 0.25, B[1] - 0.10), xytext=(A[0] + 0.28, A[1] + 0.10),
                    arrowprops=dict(arrowstyle="-|>", color=GREY, lw=1.2, linestyle="--"))
        ax.text((A[0] + B[0]) / 2, (A[1] + B[1]) / 2 - 0.45, "diffusion", color="#555555", fontsize=7.2, ha="center")
    if kind == "ours":
        for s in ax.spines.values(): s.set_visible(True); s.set_edgecolor(HI_EDGE); s.set_linewidth(1.6)
        ax.axis("on"); ax.set_xticks([]); ax.set_yticks([]); ax.set_facecolor(HI_FACE)
    elif kind == "exists":
        for s in ax.spines.values(): s.set_visible(True); s.set_edgecolor(RED); s.set_linewidth(1.2)
        ax.axis("on"); ax.set_xticks([]); ax.set_yticks([]); ax.set_facecolor("#fff5f5")
    fig.text(xs[k] + 0.11, 0.855, t, ha="center", va="bottom", fontsize=8.8, fontweight="bold",
             color=HI_EDGE if kind == "ours" else (RED if kind == "exists" else TEXT))
    fig.text(xs[k] + 0.11, 0.485, sub, ha="center", va="top", fontsize=7.4, color="#444444", linespacing=1.2)

# ---------- bottom left: energy profile
ax = fig.add_axes([0.05, 0.08, 0.40, 0.31]); ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(-0.2, 3.2)
import numpy as np
x = np.linspace(0, 4, 200); y = 0.4 + 2.0 * np.exp(-((x - 1.9) / 0.7) ** 2)
ax.plot(x, y, color=HI_EDGE, lw=2.0)
ax.plot([0, 0.4], [0.4, 0.4], color=TEXT, lw=2.4); ax.plot([3.6, 4.0], [0.4, 0.4], color=HI_EDGE, lw=2.4)
x2 = np.linspace(4, 9, 300); y2 = 0.4 + 0.5 * np.exp(-((x2 - 5.2) / 0.45) ** 2) + 0.5 * np.exp(-((x2 - 7.4) / 0.45) ** 2) - 0.08 * (x2 > 6.3)
ax.plot(x2, y2, color=GREY, lw=1.6, ls="--")
ax.plot([8.8, 9.3], [0.32, 0.32], color=GREY, lw=2.4)
ax.text(0.2, 0.15, "IS: AB*", ha="center", fontsize=8); ax.text(1.9, 2.55, "TS: the barrier we want", ha="center", fontsize=8, color=HI_EDGE)
ax.text(3.8, 0.15, "FS near", ha="center", fontsize=8, color=HI_EDGE); ax.text(9.05, 0.06, "FS far", ha="center", fontsize=8, color="#555555")
ax.text(6.3, 1.25, "diffusion saddles that a far final state\npulls into the same band: more images,\nmore iterations, and the band may not\nconverge or may sample the wrong maximum", ha="center", fontsize=7.0, color="#555555", linespacing=1.2)
ax.annotate("", xy=(0.4, 2.4), xytext=(0.4, 0.4), arrowprops=dict(arrowstyle="<->", color=TEXT, lw=1.0))
ax.text(0.55, 1.4, "E_a", fontsize=8.5)
fig.text(0.25, 0.41, "Nearest valid state: one saddle, a short band, fewer failed DFT bands", ha="center", fontsize=8.8, fontweight="bold")

# ---------- bottom right: recipe
ax = fig.add_axes([0.50, 0.05, 0.48, 0.37]); ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
fig.text(0.74, 0.41, "The recipe: CatTSunami's AutoFrameDissociation, and what we add (blue)", ha="center", fontsize=8.8, fontweight="bold")
steps = [("1  Place A, the fragment that keeps the binding atom", "CatTSunami: 5 lowest-energy placements within 2 Å of the old binding site",
          "ours: all symmetry-distinct placements, counted"),
         ("2  Place B in a shell around A", "CatTSunami: 5 placements in a 1 to 3 Å shell, 25 pairs in all",
          "ours: all symmetry-distinct pairs by site-graph distance"),
         ("3  Relax each pair with the MLIP, then gate", "CatTSunami: discard frames 'where the products react' or show an anomaly",
          "ours: same gate as the initial state; bond re-formed, desorbed, moved, surface changed"),
         ("4  Choose", "CatTSunami: one surviving frame picked at random",
          "ours: nearest surviving pair first, then energy; keep several; report rejected pairs and E(FS near) − E(FS ∞)")]
y = 0.93; h = 0.19
for t, cat, ours in steps:
    box(ax, 0.01, y - h, 0.98, h, t, fs=7.9)
    ax.texts[-1].set_position((0.5, y - 0.012)); ax.texts[-1].set_va("top")
    ax.text(0.5, y - h + 0.062, cat, ha="center", va="bottom", fontsize=6.9, zorder=3)
    ax.text(0.5, y - h + 0.018, ours, ha="center", va="bottom", fontsize=6.9, color=HI_EDGE, zorder=3)
    y -= h + 0.03
ax.text(0.5, 0.0, "E(FS ∞) = E(A*) + E(B*) − E(slab) from separate cells; the difference to E(FS near) is the lateral interaction",
        ha="center", va="bottom", fontsize=6.9, style="italic", color="#444444")
finish(fig, os.path.join(os.path.dirname(__file__), "..", "21-nearest-non-recombining-final-state.png"))
