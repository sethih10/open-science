"""Figure 13: physics choices need judgement; numerical choices are convergence tests."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _style import *

fig = plt.figure(figsize=(11, 7.4))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
title(fig, "Two kinds of DFT setting: physics choices need judgement, numerical choices are convergence tests",
      "What a practitioner decides before the first adsorption calculation, and how · schematic")

# column headers
box(ax, 0.04, 0.815, 0.42, 0.055, "Physics setup  ·  owner: Human, informed by literature", fs=9.5)
box(ax, 0.54, 0.815, 0.42, 0.055, "Numerical setup  ·  owner: Tool, by convergence test", fs=9.5)

left = [
 ("Exchange–correlation functional", "PBE, RPBE, BEEF-vdW · CE27 benchmark; system literature\nPBE over-binds CO; RPBE corrects part of it"),
 ("Dispersion correction", "D3, vdW-DF · needed for large or flat-lying adsorbates"),
 ("Spin and magnetism", "Fe, Co, Ni: spin-polarised with initial moments, or SCF fails"),
 ("Hubbard U (oxides)", "Literature U per element; same U for every intermediate"),
 ("Gas-phase references and corrections", "½E(H₂) for H; O₂, CO₂, N₂ carry known GGA errors"),
 ("Slab model", "Facet, layers (≥ 4), fixed bottom layers, surface cell for coverage"),
]
right = [
 ("Pseudopotential family", "VASP: recommended PAW set (_pv/_sv when semicore matters)\nQE: SSSP efficiency or precision · all Δ-test verified · never mixed"),
 ("Plane-wave cutoff", "Start at ≥ 1.3 × largest ENMAX; then converge E_ads, not E_total"),
 ("k-point mesh", "Γ-centred, spacing ≈ 0.2–0.3 Å⁻¹ in-plane, 1 point along vacuum;\nconverge E_ads with the same mesh for slab and slab+A"),
 ("Smearing (metals)", "Methfessel–Paxton or Marzari–Vanderbilt, σ = 0.1–0.2 eV;\nfree-energy extrapolation to σ → 0"),
 ("Vacuum and dipole correction", "≥ 12–15 Å vacuum; dipole correction for asymmetric slabs"),
 ("Force and SCF thresholds", "Forces < 0.02–0.03 eV Å⁻¹; SCF 10⁻⁵–10⁻⁶ eV"),
]
y0, dh = 0.712, 0.098
for i, (t, b) in enumerate(left):
    box(ax, 0.04, y0 - i * dh, 0.42, 0.080, t, b, fs=8.8, bfs=7.4)
for i, (t, b) in enumerate(right):
    box(ax, 0.54, y0 - i * dh, 0.42, 0.080, t, b, fs=8.8, bfs=7.4)

# bottom boxes
box(ax, 0.04, 0.065, 0.42, 0.075, "Locked in PROJECT.md at the Approve-settings checkpoint",
    "Changed only by a human; every intermediate and transition state uses the same set", fs=8.8, bfs=7.4)
box(ax, 0.54, 0.065, 0.42, 0.075, "Convergence tool (ours)",
    "Sweeps cutoff, k-mesh, smearing and layers on E_ads of one test adsorbate;\nreports the cheapest setting inside ±10 meV and writes it to PROJECT.md",
    hi=True, fs=8.8, bfs=7.4)
for x in (0.25, 0.75):
    arrow(ax, (x, y0 - 5 * dh - 0.004), (x, 0.145))
arrow(ax, (0.538, 0.1025), (0.462, 0.1025))
ax.text(0.50, 0.112, "settings", ha="center", fontsize=7.5, color="#555555")
ax.text(0.50, 0.025, "Rule: converge the quantity you report (E_ads), with the same settings on both sides of the difference.",
        ha="center", fontsize=8, style="italic", color="#444444")
finish(fig, os.path.join(os.path.dirname(__file__), "..", "13-dft-setup-two-kinds-of-choice.png"))
