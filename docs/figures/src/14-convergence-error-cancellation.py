"""Figure 14: errors cancel in E_ads, so the difference converges long before the total energy."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _style import *
import numpy as np

fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.9))
fig.subplots_adjust(top=0.78, bottom=0.17, left=0.08, right=0.98, wspace=0.3)
title(fig, "Converge the difference, not the total: errors cancel in E_ads",
      "Left: cutoff. Right: k-point mesh and smearing on a metal. Schematic, not to scale.")

# (a) cutoff
E = np.linspace(250, 700, 200)
etot = 1.2 * np.exp(-(E - 250) / 90)          # error in E(slab+A), eV
eads = 0.09 * np.exp(-(E - 250) / 60)         # error in E_ads, eV
a.axhspan(-0.01, 0.01, color="#dbeafe", zorder=0)
a.plot(E, etot, color=GREY, lw=2, label="error in E(slab + A)")
a.plot(E, eads, color=HI_EDGE, lw=2.4, label="error in E_ads")
a.axvline(380, color=HI_EDGE, ls="--", lw=1)
a.axvline(640, color=GREY, ls="--", lw=1)
a.text(385, 0.9, "E_ads converged\n(≈ 1.3 × ENMAX)", color=HI_EDGE, fontsize=8, va="top")
a.text(560, 0.5, "E_total converged\n(much later)", color="#555555", fontsize=8, va="top")
a.text(430, 0.03, "±10 meV target band", color=HI_EDGE, fontsize=7.5)
a.set_xlabel("plane-wave cutoff (eV)"); a.set_ylabel("error against converged value (eV)")
a.set_ylim(-0.05, 1.3); a.legend(frameon=False, fontsize=8, loc="upper right")
a.set_title("(1) cutoff: the same basis-set error sits in slab and slab+A", fontsize=9, loc="left")
for s in ("top", "right"): a.spines[s].set_visible(False)

# (b) k-points
n = np.arange(2, 13)
rng = np.random.default_rng(3)
noisy = 0.25 * np.cos(n * 1.9) * np.exp(-(n - 2) / 2.2)   # small sigma, more oscillation
smooth = 0.10 * np.cos(n * 1.9) * np.exp(-(n - 2) / 1.8)   # larger sigma
b.axhspan(-0.01, 0.01, color="#dbeafe", zorder=0)
b.plot(n, noisy, "o-", color=GREY, lw=1.6, ms=4, label="σ = 0.05 eV (sharp Fermi edge)")
b.plot(n, smooth, "s-", color=HI_EDGE, lw=2, ms=4, label="σ = 0.2 eV (Methfessel–Paxton)")
b.axvline(7, color=HI_EDGE, ls="--", lw=1)
b.text(7.2, 0.22, "converged for E_ads\n(≈ 0.25 Å⁻¹ spacing on a 2×2 cell)", color=HI_EDGE, fontsize=8, va="top")
b.set_xlabel("in-plane k-points per direction (n × n × 1)"); b.set_ylabel("E_ads error (eV)")
b.set_ylim(-0.3, 0.3); b.legend(frameon=False, fontsize=8, loc="lower right")
b.set_title("(2) k-points on a metal: smearing damps the oscillation", fontsize=9, loc="left")
for s in ("top", "right"): b.spines[s].set_visible(False)
fig.text(0.5, 0.03, "Rule of thumb: converge E_ads to ±10 meV with identical settings on both sides; a tool can run this sweep unattended.",
         ha="center", fontsize=8, style="italic", color="#444444")
finish(fig, os.path.join(os.path.dirname(__file__), "..", "14-convergence-error-cancellation.png"))
