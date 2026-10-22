"""What the human sees: geometry files and pictures of a step's structures, written by code under
runs/<study>/geometries/<step>/ after each step that makes structures, and on request by show_structures, which
the orchestrator calls and opens before it asks the human anything about a structure.

Every structure goes out as extended XYZ with its energy when one is known, which ASE, OVITO, VESTA and Jmol read,
and as a PNG with a top view over a side view. A slab with an adsorbate on a cell wider than the window is drawn in
a window around the adsorbate, made whole across the cell boundary with the slab atoms of the neighbouring cells,
so A and B stay visible on a 6x6 slab; a clean slab, a narrow cell and the selected cell are drawn whole with the
cell outline; a molecule or a fragment is drawn on its own. A relaxed candidate shows its start and its end side by
side, and both frames go in its .xyz. A contact sheet puts the step's structures on pages of 24, each with its id
and one line. The sites of step 2 are drawn as a map over the two top layers, one marker per kind of site. A step
drawn again replaces its pictures. Pictures are for the human; an agent reads cards.
"""
from __future__ import annotations

import os
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from ..runtime import artifacts, geometry
from ..schemas.records import Candidate, SiteEnumeration, StructureRef

WINDOW_A = 6.5                            # half-width of the window around an adsorbate
MOLECULE_A = 2.5                          # least half-width of the window around a molecule or a fragment
SHEET_COLUMNS, SHEET_PAGE = 4, 24
DPI = 120
TEXT, GREY, EDGE = "#222222", "#8c8c8c", "#3a3a3a"
STYLE = {"font.family": "DejaVu Sans", "font.size": 8, "text.color": TEXT, "figure.facecolor": "white",
         "savefig.facecolor": "white", "legend.frameon": False}
SITE_STYLE = {"top": ("o", "#7c3aed"), "bridge": ("D", "#059669"), "fcc": ("^", "#2563eb"), "hcp": ("v", "#dc2626"),
              "4fold": ("s", "#d97706"), "hollow": ("h", "#0891b2")}     # keyed on a label's first word: "top Na" draws as top
FOLDERS = {"structure_retrieval": "1-structures", "site_enumeration": "2-sites", "adsorbate_placement": "3.2-placed",
           "anomaly_filter_before": "5-gate-before", "relaxation": "4-relaxed", "anomaly_filter": "5-gate",
           "soap_clustering": "6-kept", "ranking": "8-ranked", "reference_energies": "solution-final-states"}
STAGES = ("inputs", "placed", "relaxed", "kept", "ranked", "final")

Scene = Tuple[Any, Tuple[float, float, float, float], Tuple[float, float, float, float], Optional[np.ndarray]]


# ---- drawing
def _figure(width: float, height: float):
    """A figure with no pyplot state behind it, so a server process draws without a display and leaks nothing."""
    from matplotlib.figure import Figure
    return Figure(figsize=(width, height), dpi=DPI, layout="constrained")


def _save(fig, path: Path) -> str:
    fig.savefig(path, dpi=DPI, facecolor="white")
    return str(path)


def _radii(atoms) -> np.ndarray:
    from ase.data import covalent_radii
    return covalent_radii[atoms.numbers]


def _box(points: np.ndarray, radii: np.ndarray, pad: float = 0.4) -> Tuple[float, float, float, float]:
    """The bounding box of discs in the plane of a view: xlo, ylo, xhi, yhi."""
    lo, hi = (points - radii[:, None]).min(axis=0) - pad, (points + radii[:, None]).max(axis=0) + pad
    return float(lo[0]), float(lo[1]), float(hi[0]), float(hi[1])


def _scene(atoms, whole: bool = False, centre: Optional[np.ndarray] = None) -> Scene:
    """One structure as it is drawn: the atoms, the top and side windows, and the cell outline when the cell shows.

    A structure with no surface layer, a molecule or a fragment, is made whole about its first atom and drawn
    without its cell. A slab with an adsorbate on a cell wide enough is drawn around the adsorbate, made whole about
    A's binding atom, with every slab atom of the cell and its neighbours that falls in the window; centre puts the
    window where another frame of the same candidate has it, so start and end compare. Otherwise the cell is drawn
    as it is, with its outline."""
    from ase import Atoms
    from ase.geometry import find_mic
    tags = atoms.get_tags()
    cell = atoms.cell.array
    pos = atoms.positions.copy()
    if artifacts.TAG_SURFACE not in set(tags):
        if atoms.cell.rank == 3 and atoms.pbc.any() and len(atoms) > 1:
            pos = pos[0] + find_mic(pos - pos[0], cell, atoms.pbc)[0]
        mol = Atoms(numbers=atoms.numbers, positions=pos, tags=tags)
        r = _radii(mol)
        mid = (pos.min(axis=0) + pos.max(axis=0)) / 2
        half = max(MOLECULE_A, float((pos.max(axis=0) - pos.min(axis=0)).max()) / 2 + float(r.max()) + 0.5)
        return mol, (mid[0] - half, mid[1] - half, mid[0] + half, mid[1] + half), (mid[0] - half, mid[2] - half, mid[0] + half, mid[2] + half), None
    ads = artifacts.adsorbate_indices(atoms)
    half = WINDOW_A
    if ads:
        anchor = geometry.lowest(atoms, artifacts.fragment_indices(atoms, "A") or ads)
        pos[ads] = pos[anchor] + geometry.mic(pos[ads] - pos[anchor], cell)
        half = max(WINDOW_A, float(np.ptp(pos[ads][:, :2], axis=0).max()) / 2 + 3.0)
    if whole or not ads or geometry.shortest_translation(cell) < 2 * half + 2.0:
        flat = Atoms(numbers=atoms.numbers, positions=atoms.positions, tags=tags, cell=cell)
        r = _radii(flat)
        corners = np.array([[0.0, 0.0], cell[0][:2], cell[0][:2] + cell[1][:2], cell[1][:2], [0.0, 0.0]])
        xy = np.vstack([atoms.positions[:, :2], corners])
        top = _box(xy, np.concatenate([r, np.zeros(len(corners))]))
        return flat, top, _box(atoms.positions[:, [0, 2]], r), corners
    mid = pos[ads].mean(axis=0)
    a, b = cell[0], cell[1]
    frac = np.linalg.solve(np.array([a[:2], b[:2]]).T, mid[:2])
    shift = -np.floor(frac[0]) * a - np.floor(frac[1]) * b       # the adsorbate's centre into the cell
    if centre is not None:                                        # then to its image nearest the given centre
        d = np.asarray(centre, dtype=float) - (mid + shift)
        shift += d - geometry.mic(d, cell)[0]
    shift[2] = 0.0
    pos[ads] += shift
    mid = np.asarray(centre, dtype=float) if centre is not None else mid + shift
    slab = [i for i in range(len(atoms)) if i not in set(ads)]
    reach = half + 1.6
    numbers, points, labels = [], [], []
    for i in (-1, 0, 1):
        for j in (-1, 0, 1):
            p = pos[slab] + i * a + j * b
            inside = (np.abs(p[:, 0] - mid[0]) <= reach) & (np.abs(p[:, 1] - mid[1]) <= reach)
            numbers += list(atoms.numbers[slab][inside])
            points += list(p[inside])
            labels += list(tags[slab][inside])
    numbers += list(atoms.numbers[ads])
    points += list(pos[ads])
    labels += list(tags[ads])
    scene = Atoms(numbers=numbers, positions=np.array(points), tags=labels)
    r = _radii(scene)
    side = _box(scene.positions[:, [0, 2]], r)
    return scene, (mid[0] - half, mid[1] - half, mid[0] + half, mid[1] + half), (mid[0] - half, side[1], mid[0] + half, side[3]), None


def _window_centre(scene: Scene) -> np.ndarray:
    top = scene[1]
    return np.array([(top[0] + top[2]) / 2, (top[1] + top[3]) / 2, 0.0])


def _discs(ax, xy: np.ndarray, radii: np.ndarray, faces, depth: np.ndarray, edges=EDGE, width: float = 0.5) -> None:
    """Atoms as discs in data units, the farther first so the nearer cover them, in one collection: a sheet of
    two thousand atoms draws in a fraction of a second, where a patch per atom takes seconds."""
    from matplotlib.collections import EllipseCollection
    order = np.argsort(depth, kind="stable")
    d = 2 * np.asarray(radii)[order]
    ax.add_collection(EllipseCollection(d, d, np.zeros(len(d)), units="xy", offsets=np.asarray(xy)[order], offset_transform=ax.transData,
                                        facecolors=np.asarray(faces)[order], edgecolors=edges if isinstance(edges, str) else np.asarray(edges)[order],
                                        linewidths=width))


def _draw(ax, scene: Scene, view: str) -> None:
    """One view of a scene on ax, as ASE's plot_atoms draws it: discs of the covalent radius in Jmol colours, seen
    from above or along y with z up, the nearer over the farther; thin outlines, no axes, the cell outline on a top
    view of a whole cell."""
    from ase.data.colors import jmol_colors
    atoms, top, side, outline = scene
    box = top if view == "top" else side
    pos = atoms.positions
    xy, depth = (pos[:, :2], pos[:, 2]) if view == "top" else (pos[:, [0, 2]], -pos[:, 1])
    _discs(ax, xy, _radii(atoms), jmol_colors[atoms.numbers], depth)
    if view == "top" and outline is not None:
        ax.plot(outline[:, 0], outline[:, 1], color=GREY, lw=0.7, ls=(0, (4, 3)))
    ax.set_xlim(box[0], box[2])
    ax.set_ylim(box[1], box[3])
    ax.set_aspect("equal")
    ax.set_axis_off()


def _resize(box: Tuple[float, float, float, float], width: float, height: float) -> Tuple[float, float, float, float]:
    """box grown to width by height about its centre, so the panels of one figure share one scale."""
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    return cx - width / 2, cy - height / 2, cx + width / 2, cy + height / 2


def _wrap(text: str, width: int = 34) -> str:
    return "\n".join(textwrap.wrap(text, width=width, break_long_words=False)) or text


def write_xyz(path: Path, frames: Sequence, names: Optional[Sequence[str]] = None, energies: Optional[Sequence[Optional[float]]] = None) -> str:
    """Frames as extended XYZ, each with its name and, when known, its energy, as ASE writes a calculator's."""
    from ase.calculators.singlepoint import SinglePointCalculator
    from ase.io import write
    out = []
    for k, atoms in enumerate(frames):
        a = atoms.copy()
        a.info = {"name": names[k]} if names else {}
        energy = energies[k] if energies else None
        if energy is not None:
            a.calc = SinglePointCalculator(a, energy=float(energy))
        out.append(a)
    write(str(path), out, format="extxyz")
    return str(path)


def picture(path: Path, frames: Sequence[Tuple[str, object]], title: str, whole: bool = False, share: bool = False) -> str:
    """One PNG: the top view over the side view of each (label, atoms), side by side. With share, the frames are
    one candidate's and every frame looks through the window of the first, so a move shows as a move."""
    import matplotlib
    scenes: List[Scene] = []
    for k, (_, atoms) in enumerate(frames):
        scenes.append(_scene(atoms, whole, _window_centre(scenes[0]) if share and k > 0 else None))
    span = max(max(s[1][2] - s[1][0], s[2][2] - s[2][0]) for s in scenes)
    tall = max(s[1][3] - s[1][1] for s in scenes), max(s[2][3] - s[2][1] for s in scenes)
    scenes = [(s[0], _resize(s[1], span, tall[0]), _resize(s[2], span, tall[1]), s[3]) for s in scenes]
    top, side = tall[0] / span, tall[1] / span
    width = min(5.0, max(1.8, 0.2 * span))        # about 0.2 inch per Å, so a whole 6x6 cell is not shrunk to a stamp
    across = width * len(frames)
    zoomed = any(s[3] is None and artifacts.TAG_SURFACE in set(s[0].get_tags()) for s in scenes)
    note = "Top view above, side view below" + (f"; a window {2 * WINDOW_A:.0f} Å wide around the adsorbate" if zoomed else "") + "."
    title, note = _wrap(title, int(across * 12)), _wrap(note, int(across * 17))
    labels = [_wrap(label, int(width * 13)) for label, _ in frames]
    lines = title.count("\n") + note.count("\n") + max(x.count("\n") for x in labels)
    with matplotlib.rc_context(STYLE):
        fig = _figure(across, width * (top + side) + 0.9 + 0.16 * lines)
        axes = fig.subplots(2, len(frames), squeeze=False, gridspec_kw={"height_ratios": [top, side]})
        for k, (label, scene) in enumerate(zip(labels, scenes)):
            _draw(axes[0][k], scene, "top")
            _draw(axes[1][k], scene, "side")
            axes[0][k].set_title(label, fontsize=9)
        fig.suptitle(title, fontsize=10, fontweight="bold")
        fig.supxlabel(note, fontsize=7, color=GREY)
        return _save(fig, path)


def sheet(path: Path, items: Sequence[Tuple[str, str, object]], title: str) -> List[str]:
    """A contact sheet: the top view of every structure, each with its id and one line under it, on pages of
    SHEET_PAGE; the first page is path, the next path-2, path-3. Empty when there is nothing to draw."""
    import matplotlib
    pages = [items[k:k + SHEET_PAGE] for k in range(0, len(items), SHEET_PAGE)]
    out = []
    for n, page in enumerate(pages, start=1):
        scenes = [_scene(atoms) for _, _, atoms in page]
        span, tall = max(s[1][2] - s[1][0] for s in scenes), max(s[1][3] - s[1][1] for s in scenes)
        scenes = [(s[0], _resize(s[1], span, tall), s[2], s[3]) for s in scenes]      # one scale for the page
        cols = min(SHEET_COLUMNS, len(page))
        rows = (len(page) + cols - 1) // cols
        width = 2.4
        heading = _wrap(title + (f", page {n} of {len(pages)}" if len(pages) > 1 else ""), int(width * cols * 12))
        captions = [f"{label}\n{_wrap(line)}" for label, line, _ in page]
        per_row = 0.16 * max(x.count("\n") + 1 for x in captions)
        with matplotlib.rc_context(STYLE):
            fig = _figure(width * cols, rows * (width * tall / span + per_row) + 0.15 + 0.18 * (heading.count("\n") + 1))
            axes = fig.subplots(rows, cols, squeeze=False)
            for ax in axes.flat:
                ax.set_axis_off()
            for ax, caption, scene in zip(axes.flat, captions, scenes):
                _draw(ax, scene, "top")
                ax.set_title(caption, fontsize=8)
            fig.suptitle(heading, fontsize=10, fontweight="bold")
            target = path if n == 1 else path.with_name(f"{path.stem}-{n}{path.suffix}")
            out.append(_save(fig, target))
    return out


def sites_map(path: Path, slab, sites: SiteEnumeration, title: str) -> str:
    """The two top layers seen from above with every site marked, one marker and colour per inequivalent site;
    the representative of each, the site the cards and the summary name, is ringed and named in the legend. An atom
    of the second layer shows through each hcp hollow, none through an fcc one."""
    import matplotlib
    from ase.data.colors import jmol_colors
    from matplotlib.colors import to_rgba
    from matplotlib.lines import Line2D
    r = _radii(slab)
    surface = artifacts.surface_indices(slab) or list(range(len(slab)))
    z_top = float(np.mean(slab.positions[surface, 2]))
    below = [i for i in range(len(slab)) if i not in set(surface) and z_top - 3.5 < slab.positions[i, 2] < z_top - 0.5]
    second = [i for i in below if slab.positions[i, 2] >= max(slab.positions[below, 2]) - 0.5] if below else []
    cell = slab.cell.array
    corners = np.array([[0.0, 0.0], cell[0][:2], cell[0][:2] + cell[1][:2], cell[1][:2], [0.0, 0.0]])
    with matplotlib.rc_context(STYLE):
        lo, hi = corners.min(axis=0) - 1.8, corners.max(axis=0) + 1.8
        width = 6.4
        fig = _figure(width, width * (hi[1] - lo[1]) / (hi[0] - lo[0]) + 1.0)
        ax = fig.subplots()
        for layer, scale, z in ((second, 0.55, 1), (surface, 0.75, 2)):
            xy, radii, faces, edges = [], [], [], []
            for i in (-1, 0, 1):                 # the neighbouring cells too, faded, so the edges read as a surface
                for j in (-1, 0, 1):
                    fade = 1.0 if (i, j) == (0, 0) else 0.35
                    for a in layer:
                        p = slab.positions[a][:2] + i * cell[0][:2] + j * cell[1][:2]
                        if np.all(p > lo - 2.0) and np.all(p < hi + 2.0):
                            xy.append(p)
                            radii.append(scale * r[a])
                            faces.append(to_rgba(jmol_colors[slab.numbers[a]] if z == 2 else "#e4e4ea", fade))
                            edges.append(to_rgba(EDGE if z == 2 else GREY, fade))
            if xy:
                _discs(ax, np.array(xy), np.array(radii), faces, np.zeros(len(xy)), edges=edges, width=0.5 if z == 2 else 0.4)
                ax.collections[-1].set_zorder(z)
        ax.plot(corners[:, 0], corners[:, 1], color=GREY, lw=0.7, ls=(0, (4, 3)), zorder=3)
        handles = []
        seen: Dict[str, int] = {}
        for rep in sorted({s.orbit for s in sites.sites}):
            members = [s for s in sites.sites if s.orbit == rep]
            label = sites.sites[rep].label
            kind = label.split()[0] if label else label
            marker, colour = SITE_STYLE.get(kind, ("P", "#6b7280"))
            hollow = seen.get(kind, 0) > 0         # a second orbit of the same kind, top Cl after top Na, draws open
            seen[kind] = seen.get(kind, 0) + 1
            xy = np.array([s.position[:2] for s in members])
            face = "white" if hollow else colour
            ax.plot(xy[:, 0], xy[:, 1], ls="none", marker=marker, ms=5.5, mfc=face, mec=colour, mew=0.8, zorder=4)
            ax.plot(*sites.sites[rep].position[:2], ls="none", marker="o", ms=13, mfc="none", mec=TEXT, mew=0.9, zorder=5)
            handles.append(Line2D([], [], ls="none", marker=marker, ms=6, mfc=face, mec=colour, mew=0.8,
                                  label=f"{label}: {len(members)} in the cell, site {rep} ringed"))
        ax.set_xlim(lo[0], hi[0])
        ax.set_ylim(lo[1], hi[1])
        ax.set_aspect("equal")
        ax.set_axis_off()
        ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 0.0), ncol=2, fontsize=8, handletextpad=0.3,
                  columnspacing=1.5)
        ax.set_title(title, fontsize=10, fontweight="bold")
        return _save(fig, path)


# ---- the study's structures
def _ref(x) -> Optional[StructureRef]:
    return x if isinstance(x, StructureRef) else (StructureRef.model_validate(x) if x else None)


def _read(x):
    ref = _ref(x)
    return artifacts.read(ref) if ref is not None else None


def _starts(c) -> Dict[str, StructureRef]:
    """Every candidate's structure before relaxation: the placed ones and the minima of 3.6."""
    return {x["id"]: _ref(x["structure"]) for x in c.data.get("placed", []) + c.data.get("hopped", [])}


def _ends(c) -> Dict[str, Tuple[StructureRef, Dict[str, Any]]]:
    """Every relaxed candidate's structure after relaxation, with its result."""
    return {r["candidate_id"]: (_ref(r["structure"]), r) for r in c.data.get("relaxed", []) if r.get("structure")}


def _labels(c) -> Dict[int, str]:
    sites = c.data.get("sites", {}).get("sites", [])
    return {s["index"]: s["label"] for s in sites}


def _clear(folder: Path) -> None:
    """A step drawn again replaces its pictures: the folder's own .png and .xyz files go first."""
    for p in list(folder.glob("*.png")) + list(folder.glob("*.xyz")):
        p.unlink()


def after_step(c, tool_name: str) -> List[str]:
    """The geometry files of the step a tool just finished, under geometries/<step>/; none for a tool that makes
    no structure. Returns the paths relative to the run folder."""
    if tool_name not in FOLDERS:
        return []
    folder = c.run.dir / "geometries" / FOLDERS[tool_name]
    folder.mkdir(parents=True, exist_ok=True)
    _clear(folder)
    made = _WRITERS[tool_name](c, folder)
    return [os.path.relpath(p, c.run.dir) for p in made]


def _structures(c, folder: Path) -> List[str]:
    inp, r = c.data["inputs"], c.data.get("retrieval")
    supplied = [("slab", "slab", inp["slab"]), ("adsorbate in vacuum", "adsorbate-in-vacuum", inp["adsorbate_vacuum"]),
                ("initial state", "initial-state", inp["initial_state"])]
    groups = [(supplied, "inputs.png", "The supplied inputs")]
    if r:
        n1, n2 = r["cell_repeat"]
        groups += [([("fragment A, keeps the binding atom", "fragment-A", r["fragment_A"]), ("fragment B, broken off", "fragment-B", r["fragment_B"])],
                    "fragments.png", "The two fragments of the cleaved bond"),
                   ([(f"{n1} × {n2} of the supplied slab, A at its site", "selected-cell", r["structures"][1])], "selected-cell.png",
                    "The selected cell, wide enough that images stay apart")]
    out = []
    for group, name, title in groups:
        frames = [(label, _read(ref)) for label, _, ref in group]
        for (label, stem, ref), (_, atoms) in zip(group, frames):
            out.append(write_xyz(folder / f"{stem}.xyz", [atoms], [label], [_ref(ref).energy_eV]))
        out.append(picture(folder / name, frames, title, whole=True))
    return out


def _sites(c, folder: Path) -> List[str]:
    e = SiteEnumeration.model_validate(c.data["sites"])
    slab = artifacts.read(e.slab)
    title = f"{e.count} inequivalent sites of {e.total_sites} in the cell, group {e.symmetry_group}"
    return [sites_map(folder / "sites.png", slab, e, title), write_xyz(folder / "slab-cell.xyz", [slab], ["the slab the sites are on"])]


def _placed(c, folder: Path) -> List[str]:
    labels = _labels(c)
    items = []
    for x in (Candidate.model_validate(x) for x in c.data.get("placed", [])):
        where = f"B on {labels.get(x.site_B, 'site')} site {x.site_B}" + (f", orientation {x.orientation}" if x.orientation else "")
        items.append((x.id, where, artifacts.read(x.structure)))
    if not items:
        return []
    return [write_xyz(folder / "placed.xyz", [a for _, _, a in items], [k for k, _, _ in items]),
            *sheet(folder / "sheet.png", items, f"{len(items)} candidates placed, before relaxation")]


def _failed(verdicts: List[Dict[str, Any]]) -> str:
    return "fails " + "; ".join(f"check {v['check_id']}, {v['name']}" + (f" {v['fragment']}" if v.get("fragment") else "")
                                for v in verdicts if not v["passed"])


def _gate_before(c, folder: Path) -> List[str]:
    starts = _starts(c)
    items = [(g["candidate_id"], _failed(g["verdicts"]), artifacts.read(starts[g["candidate_id"]]))
             for g in c.data.get("gates_before", []) if not g["passed"] and g["candidate_id"] in starts]
    if not items:
        return []
    return [write_xyz(folder / "rejected.xyz", [a for _, _, a in items], [k for k, _, _ in items]),
            *sheet(folder / "rejected.png", items, f"{len(items)} placed structures fail the gate before relaxation; they are not relaxed")]


def _relaxed(c, folder: Path) -> List[str]:
    starts, ends = _starts(c), _ends(c)
    if not ends:
        return []
    lowest = min(r["energy_eV"] for _, r in ends.values())
    calc = c.data.get("mlip", {}).get("calculator") or "the chosen potential"
    out, items = [], []
    for cid, (ref, r) in ends.items():
        end = artifacts.read(ref)
        frames = [("end, relaxed", end)]
        if cid in starts:
            frames.insert(0, ("start, placed", artifacts.read(starts[cid])))
        state = f"{r['steps']} steps" + ("" if r.get("converged", True) else ", not converged")
        out.append(write_xyz(folder / f"{cid}.xyz", [a for _, a in frames], [f"{cid} {k.split(',')[0]}" for k, _ in frames],
                             [None] * (len(frames) - 1) + [r["energy_eV"]]))
        out.append(picture(folder / f"{cid}.png", frames, f"{cid}: E {r['energy_eV']:.3f} eV, {state}", share=True))
        items.append((cid, f"ΔE {r['energy_eV'] - lowest:+.3f} eV, {state}", end))
    return out + sheet(folder / "sheet.png", items, f"{len(items)} relaxed with {calc}; ΔE from the lowest")


def _gate(c, folder: Path) -> List[str]:
    ends = _ends(c)
    out = []
    gates = c.data.get("gates", [])
    for passed, name in ((True, "passed"), (False, "rejected")):
        items = [(g["candidate_id"], "passes every check" if passed else _failed(g["verdicts"]), artifacts.read(ends[g["candidate_id"]][0]))
                 for g in gates if g["passed"] == passed and g["candidate_id"] in ends]
        if items:
            what = "pass the gate after relaxation" if passed else "fail the gate after relaxation; never kept"
            out += sheet(folder / f"{name}.png", items, f"{len(items)} of {len(gates)} {what}")
    return out


def _kept(c, folder: Path) -> List[str]:
    ends = _ends(c)
    role: Dict[str, str] = {}
    for k in c.data.get("clusters", []):
        for cid in {k["nearest"], k["lowest"]}:
            which = " and the ".join(w for w, x in (("nearest", k["nearest"]), ("lowest", k["lowest"])) if x == cid)
            role[cid] = f"cluster {k['id']}, " + ("its only member" if len(k["members"]) == 1 else f"the {which} of {len(k['members'])}")
    items = [(k, role.get(k, "kept"), artifacts.read(ends[k][0])) for k in c.data.get("kept", []) if k in ends]
    return sheet(folder / "sheet.png", items, f"{len(items)} kept after SOAP clustering") if items else []


def _ranked(c, folder: Path) -> List[str]:
    ends = _ends(c)
    cards = {x["candidate_id"]: x for x in c.data.get("cards_kept", [])}
    items = []
    for r in c.data.get("ranked", []):
        if r["candidate_id"] not in ends:
            continue
        ab = cards.get(r["candidate_id"], {}).get("AB_distance_A")
        line = f"rank {r['rank']}, shell {r['site_graph_distance']}" + (f", A–B {ab:.2f} Å" if ab is not None else "")
        items.append((r["candidate_id"], line, artifacts.read(ends[r["candidate_id"]][0])))
    return sheet(folder / "sheet.png", items, "Ranked: nearest first, then by energy") if items else []


def _final(c, folder: Path) -> List[str]:
    ends = _ends(c)
    states = [f for f in c.data.get("final_states", []) if f["candidate_id"] in ends]
    if not states:
        return []
    items = [(f["candidate_id"], f"lateral {f['lateral_interaction_eV']:+.3f} eV, A–B {f['AB_distance_A']:.2f} Å", artifacts.read(ends[f["candidate_id"]][0]))
             for f in states]
    return [write_xyz(folder / "final-states.xyz", [a for _, _, a in items], [k for k, _, _ in items], [f["E_near_eV"] for f in states]),
            *sheet(folder / "sheet.png", items, f"The {len(items)} final states the human picked")]


_WRITERS = {"structure_retrieval": _structures, "site_enumeration": _sites, "adsorbate_placement": _placed,
            "anomaly_filter_before": _gate_before, "relaxation": _relaxed, "anomaly_filter": _gate, "soap_clustering": _kept,
            "ranking": _ranked, "reference_energies": _final}


def show(c, ids: Optional[List[str]], stage: str) -> Dict[str, object]:
    """Pictures and files of the named candidates at one stage, for the human, in geometries/views/<stage>/; every
    candidate of the stage when ids is empty. A stage with nothing in it yet, an unknown stage or an unknown id is a
    ValueError that says what is known."""
    if stage not in STAGES:
        raise ValueError(f"stage {stage!r}; known: {', '.join(STAGES)}")
    if stage == "inputs":
        if ids:
            raise ValueError("stage inputs shows the supplied structures and takes no candidate ids")
        files = after_step(c, "structure_retrieval")
        return {"files": files, "open": next(f for f in files if f.endswith(".png"))}
    if stage == "placed":
        pool = _starts(c)
    else:
        ends = _ends(c)
        keep = {"relaxed": list(ends), "kept": c.data.get("kept", []), "ranked": [x["candidate_id"] for x in c.data.get("ranked", [])],
                "final": [x["candidate_id"] for x in c.data.get("final_states", [])]}[stage]
        pool = {k: ends[k][0] for k in keep if k in ends}
    if not pool:
        raise ValueError(f"nothing at stage {stage} yet: the step that makes it has not run")
    chosen = list(ids) if ids else list(pool)
    unknown = [k for k in chosen if k not in pool]
    if unknown:
        raise ValueError(f"unknown at stage {stage}: {unknown}; known: {list(pool)}")
    folder = c.run.dir / "geometries" / "views" / stage
    folder.mkdir(parents=True, exist_ok=True)
    _clear(folder)
    atoms = {k: artifacts.read(pool[k]) for k in chosen}
    out = [write_xyz(folder / f"{k}.xyz", [atoms[k]], [k], [pool[k].energy_eV]) for k in chosen]
    out += sheet(folder / "sheet.png", [(k, stage, atoms[k]) for k in chosen], f"{len(chosen)} at stage {stage}")
    if len(chosen) <= 2:
        out.append(picture(folder / "views.png", [(k, atoms[k]) for k in chosen], f"{' and '.join(chosen)} at stage {stage}"))
    files = [os.path.relpath(p, c.run.dir) for p in out]
    return {"files": files, "open": files[-1]}
