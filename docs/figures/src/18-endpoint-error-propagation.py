"""Figure 18: an error in the adsorption endpoint moves the barrier one-to-one and the rate exponentially."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _style import *
import numpy as np

fig = plt.figure(figsize=(11, 5.6))
title(fig, "An endpoint error moves the barrier one-to-one and the rate exponentially",
      "Why the trust layer is worth ten times more when adsorption energies feed transition states · schematic, not to scale")

# left: reaction profile with a wrong initial state
a = fig.add_axes([0.07, 0.16, 0.50, 0.62])
x = np.linspace(0, 1, 300)
prof = 0.0 + 0.9 * np.exp(-((x - 0.5) / 0.16) ** 2) - 0.3 * (x > 0.5) * (1 - np.exp(-((x - 0.5) / 0.16) ** 2))
a.plot(x, prof, color=GREY, lw=2.2)
a.axhline(0.0, xmin=0.02, xmax=0.22, color=HI_EDGE, lw=2.2)
a.axhline(0.15, xmin=0.02, xmax=0.22, color="#b91c1c", lw=2.2, ls="--")
a.text(0.02, 0.19, "IS wrong by δ (wrong site, unrelaxed, on a saddle)", color="#b91c1c", fontsize=8)
a.text(0.02, -0.07, "IS correct", color=HI_EDGE, fontsize=8)
a.annotate("", xy=(0.5, 0.9), xytext=(0.5, 0.0), arrowprops=dict(arrowstyle="<->", color=HI_EDGE, lw=1.4))
a.text(0.52, 0.45, "E_a", color=HI_EDGE, fontsize=9, fontweight="bold")
a.annotate("", xy=(0.62, 0.9), xytext=(0.62, 0.15), arrowprops=dict(arrowstyle="<->", color="#b91c1c", lw=1.4, ls="--"))
a.text(0.64, 0.5, "E_a − δ", color="#b91c1c", fontsize=9, fontweight="bold")
a.text(0.5, 0.95, "TS", ha="center", fontsize=9)
a.text(0.93, -0.25, "FS", ha="center", fontsize=9)
a.set_xlim(0, 1); a.set_ylim(-0.45, 1.1); a.set_xticks([]); a.set_yticks([])
a.set_xlabel("reaction coordinate"); a.set_ylabel("energy")
a.set_title("(1)  E_a = E(TS) − E(IS): the endpoint error enters the barrier in full", fontsize=9, loc="left")
for s_ in ("top", "right"): a.spines[s_].set_visible(False)

# right: rate factor vs error
b = fig.add_axes([0.66, 0.16, 0.31, 0.62])
d = np.linspace(0, 0.3, 200)
for T, c, lab in ((300, GREY, "300 K"), (500, HI_EDGE, "500 K")):
    b.plot(d, np.exp(d / (8.617e-5 * T)), color=c, lw=2.2, label=lab)
b.axhspan(1, 2, color="#dbeafe", zorder=0)
for dd, txt in ((0.05, "×3"), (0.10, "×10"), (0.20, "×100")):
    v = np.exp(dd / (8.617e-5 * 500))
    b.plot([dd], [v], "o", color=HI_EDGE, ms=4)
    b.text(dd + 0.008, v, txt + " at 500 K", fontsize=7.5, color=HI_EDGE, va="center")
b.set_yscale("log"); b.set_xlabel("barrier error δ (eV)"); b.set_ylabel("factor in rate, exp(δ / k_B T)")
b.set_ylim(1, 3e4); b.legend(frameon=False, fontsize=8, loc="upper left")
b.set_title("(2)  the same error in the rate", fontsize=9, loc="left")
b.text(0.01, 1.4, "tolerable band", fontsize=7.5, color=HI_EDGE)
for s_ in ("top", "right"): b.spines[s_].set_visible(False)
fig.text(0.5, 0.03, "Site ranking tolerates 0.1 eV; a rate does not. A validated endpoint is the cheapest accuracy in the whole chain.",
         ha="center", fontsize=8, style="italic", color="#444444")
finish(fig, os.path.join(os.path.dirname(__file__), "..", "18-endpoint-error-propagation.png"))
