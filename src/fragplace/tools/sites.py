"""Symmetry-inequivalent sites and the A–B pairs inside the window. Tools: site_enumeration, pair_enumeration. Defined in fragplace.registry."""
from __future__ import annotations

import warnings
from typing import Any, Dict, Hashable, List, Optional, Sequence, Tuple

import numpy as np

from ..runtime import artifacts, geometry, project
from ..runtime.journal import log, traced
from ..schemas.records import Pair, Role, Site, SiteEnumeration, StructureRef, SymmetryOperation

SYMPREC_A = 0.05      # spglib's tolerance on a relaxed slab
MATCH_A = 0.3         # an operation maps a site onto another when they lie this close in the plane; sites sit >= 0.8 Å apart
LABELS = {"ontop": "top", "bridge": "bridge", "fcc": "fcc", "hcp": "hcp", "4fold": "4fold"}
LAYER_GAP_A = 0.5     # the second layer: the subsurface atoms within this of the highest one, as tag_slab_layers draws the top layer


@traced(step="2", tool="site_enumeration")
def site_enumeration(slab: StructureRef, cell_repeat: Tuple[int, int]) -> SiteEnumeration:
    """Every symmetry-inequivalent site of the slab, fcc and hcp hollows apart, with the site graph and a Burnside-checked count; pymatgen's finder as the baseline.

    Board steps: 2. Status: core. Lane: laptop. Allowed roles: solution-planner.

    Inputs:
        slab: StructureRef
        cell_repeat: tuple[int, int]
    Outputs:
        sites: SiteEnumeration
    Checks:
        - Burnside count equals the explicit list
        - C4v square cell with two identical adsorbates gives 2
    Thresholds:
        none
    Wraps:
        - spglib.get_symmetry_dataset
        - acat.adsorption_sites.SlabAdsorptionSites
        - acat.adsorption_sites.SlabAdsorptionSites.get_graph
        - pymatgen.core.adsorption.AdsorbateSiteFinder as baseline
    Logs: symmetry group; every site; count and check.

    On a slab of one element ACAT labels the sites of the supplied cell. A slab of several elements, an ionic or
    oxide surface such as NaCl(100), has no ACAT surface type, so its sites come from the Delaunay triangulation
    of the top layer, named by the species they sit on: top Na, top Cl, bridge Na-Cl, hollow. Either way the sites
    are tiled over the repeat by its lattice translations, since ACAT's cost grows steeply with the cell. Edges
    join each site to its first neighbour shell of sites, ACAT's get_neighbor_site_list rule: top to bridge and
    bridge to hollow on a close-packed facet. spglib gives the operations of the slab that keep the top surface
    on top; orbits of sites under them are the inequivalent sites, and the site group of each is its stabiliser,
    so a bridge of an ABC-stacked (111) slab is Cs, not the C2v of the top layer alone. A count that differs from
    pymatgen's baseline is flagged in the trace.
    """
    settings = project.current_settings()
    supplied = artifacts.read(slab)
    tags = set(supplied.get_tags())
    if artifacts.TAG_SURFACE not in tags or not tags <= {artifacts.TAG_SUBSURFACE, artifacts.TAG_SURFACE}:
        artifacts.tag_slab_layers(supplied)          # a builder's layer numbers would read as fragment tags
    n1, n2 = (int(k) for k in cell_repeat)
    atoms = supplied.repeat((n1, n2, 1))
    ref = artifacts.write(atoms, f"slab-{n1}x{n2}", Role.slab, settings_hash=slab.settings_hash,
                          energy_eV=slab.energy_eV * n1 * n2 if slab.energy_eV is not None else None)
    if len(set(supplied.get_chemical_symbols())) > 1:
        surface = f"the top layer of {supplied.get_chemical_formula(mode='metal', empirical=True)}, by Delaunay triangulation"
        found = _top_layer_sites(supplied)
    else:
        surface = acat_surface(settings.metal, settings.facet)
        found = _acat(supplied, surface).get_sites()
    sites = _tile(found, supplied, atoms, (n1, n2))
    edges = neighbour_shell_edges([s.position for s in sites], atoms.cell.array)
    ops, group = surface_operations(atoms)
    enum = SiteEnumeration(sites=sites, count=0, burnside_count=0, symmetry_group=group, edges=edges, slab=ref,
                           operations=ops, total_sites=len(sites))
    table = image_table(enum, atoms.cell.array)
    orbit = _orbits(table, range(len(sites)))
    for s in sites:
        s.orbit = orbit[s.index]
    for rep in sorted(set(orbit.values())):
        pg = geometry.point_group(op for g, op in enumerate(ops) if table[g, rep] == rep)
        for s in sites:
            if s.orbit == rep:
                s.point_group = pg
    perms = [list(row) for row in table]
    enum.count = len(set(orbit.values()))
    burnside_count = burnside(perms, [(i,) for i in range(len(sites))])
    if abs(burnside_count - round(burnside_count)) > 1e-9 or round(burnside_count) != enum.count:
        raise ValueError(f"Burnside count {burnside_count} differs from the {enum.count} orbits listed")
    enum.burnside_count = int(round(burnside_count))
    enum.baseline_count = _baseline(supplied)
    log("site_enumeration", f"symmetry {group}, {len(ops)} surface-preserving operations; surface {surface}; "
                            f"{len(sites)} sites in the {n1}x{n2} cell, {enum.count} inequivalent, Burnside {enum.burnside_count}; "
                            f"pymatgen baseline {enum.baseline_count}")
    if enum.baseline_count is not None and enum.baseline_count != enum.count:
        log("site_enumeration", f"flag: {enum.count} inequivalent sites against {enum.baseline_count} from pymatgen's baseline; "
                                f"the list below is the one used, and the difference is for the human to read")
    for rep in sorted(set(orbit.values())):
        s = sites[rep]
        log("site_enumeration", f"site {rep}: {s.label}, {s.point_group}, coordination {s.coordination}, "
                                f"atom beneath {s.atom_beneath}, {sum(1 for t in sites if t.orbit == rep)} in the cell")
    return enum


@traced(step="3.2", tool="pair_enumeration")
def pair_enumeration(sites: SiteEnumeration, d_bond_A: float, window: Tuple[float, float], site_A: Optional[int] = None) -> Dict[str, Any]:
    """Every symmetry-distinct (A site, B site) pair inside the window [1.5 d, 5] Å, ordered by site-graph distance with in-plane distance as tiebreaker, nearest first, counted.

    Board steps: 3.2. Status: core. Lane: laptop. Allowed roles: solution-planner.

    Inputs:
        sites: SiteEnumeration
        d_bond_A: float, from literature_lookup or the adsorbate structure
        window: tuple[float, float] in units of d and Å
        site_A: int | None, the site fragment A holds; every symmetry-distinct A site when None
    Outputs:
        pairs: list[Pair], nearest first
        count: int
    Checks:
        - no pair outside the window
        - symmetry duplicates removed and counted
    Thresholds:
        d_definition: open: team decision: vacuum or adsorbed bond length
        upper_bound_A: open: team decision: 5 or NEBscape's 4.5
    Wraps:
        - acat.adsorption_sites.SlabAdsorptionSites.get_neighbor_site_list
        - acat.build.adlayer.SystematicPatternGenerator
    Logs: every pair with both distances; the count.

    window is (lower in units of d, upper in Å); the upper bound must equal the locked decision. With A at a
    given site, two B sites are one pair when an operation of A's site group maps one onto the other; with
    site_A None, A runs over one site per orbit. The candidate id of a pair is A<site>-B<site>, the id
    adsorbate_placement gives the structure it builds for the pair.
    """
    settings = project.current_settings()
    upper = float(project.decision("pair_enumeration", "upper_bound_A", settings))
    d_definition = project.decision("pair_enumeration", "d_definition", settings)
    if abs(float(window[1]) - upper) > 1e-9:
        raise ValueError(f"window upper bound {window[1]} Å differs from the locked decision pair_enumeration.upper_bound_A = {upper}")
    lower = float(window[0]) * float(d_bond_A)
    cell = artifacts.read(sites.slab).cell.array
    table = image_table(sites, cell)
    a_sites = [int(site_A)] if site_A is not None else sorted({s.orbit for s in sites.sites})
    xyz = np.array([s.position for s in sites.sites])
    pairs, removed = [], 0
    for a in a_sites:
        stab = [g for g in range(len(table)) if table[g, a] == a]
        d_ip = np.hypot(*geometry.mic(xyz - xyz[a], cell)[:, :2].T)
        inside = [b for b in range(len(xyz)) if b != a and lower <= d_ip[b] <= upper]
        orbit = _orbits(table[stab], inside)
        reps = sorted(set(orbit.values()))
        expected = burnside([list(table[g]) for g in stab], [(b,) for b in inside])
        if round(expected) != len(reps):
            raise ValueError(f"A at site {a}: Burnside count {expected} differs from the {len(reps)} B orbits listed")
        removed += len(inside) - len(reps)
        hops = geometry.site_graph_distances(sites, a)
        for b in reps:
            pairs.append(Pair(candidate_id=f"A{a:03d}-B{b:03d}", site_A=a, site_B=b, site_graph_distance=hops.get(b, -1),
                              in_plane_distance_A=float(d_ip[b]), within_window=True, window_A=(lower, upper), d_bond_A=float(d_bond_A)))
    pairs.sort(key=lambda p: (p.site_graph_distance < 0, p.site_graph_distance, round(p.in_plane_distance_A, 3), p.site_A, p.site_B))
    assert all(lower <= p.in_plane_distance_A <= upper for p in pairs), "a pair outside the window"
    log("pair_enumeration", f"window [{window[0]} d, {upper}] Å = [{lower:.2f}, {upper:.2f}] Å, d = {d_bond_A:.3f} Å ({d_definition}); "
                            f"{len(pairs)} symmetry-distinct pairs, {removed} symmetry duplicates removed")
    for p in pairs:
        log("pair_enumeration", f"{p.candidate_id}: {sites.sites[p.site_A].label} to {sites.sites[p.site_B].label}, "
                                f"site-graph {p.site_graph_distance}, in-plane {p.in_plane_distance_A:.2f} Å")
    return {"pairs": pairs, "count": len(pairs)}


# ---- symmetry and counting, shared by the two tools
def acat_surface(metal: str, facet: str) -> str:
    """ACAT's surface name, the metal's bulk lattice and the facet: Pt and 111 give fcc111."""
    from ase.data import atomic_numbers, reference_states
    if metal not in atomic_numbers:
        raise ValueError(f"settings.metal is {metal!r}: ACAT's surface type needs one element; an alloy needs its surface named by hand")
    return f"{reference_states[atomic_numbers[metal]]['symmetry']}{facet}"


def _acat(atoms, surface: str):
    if not hasattr(np, "in1d"):       # ACAT 2.0.3 calls np.in1d, which NumPy 2.4 removed; np.isin is the same on its 1-D input
        np.in1d = np.isin
    from acat.adsorption_sites import SlabAdsorptionSites
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return SlabAdsorptionSites(atoms.copy(), surface=surface)


def _top_layer_sites(atoms) -> List[dict]:
    """The sites of a slab of several elements, in the form of ACAT's get_sites: a top site on every atom of the top
    layer, a bridge at the middle of every edge of the layer's Delaunay triangulation, and a hollow at the centre of
    every Delaunay cell. Triangles on one circle make one cell, so the four ions of a square give one fourfold
    hollow and its diagonal no bridge. Labels name the anchor species, metals first: top Na, bridge Na-Cl; a hollow
    names the atom of the second layer beneath it when there is one, hollow over Cl."""
    from ase.formula import non_metals
    from scipy.spatial import Delaunay
    cell = atoms.cell.array
    plane = cell[:2, :2]
    top = artifacts.surface_indices(atoms)
    sub = [k for k in range(len(atoms)) if k not in set(top)]
    second = [k for k in sub if atoms.positions[k, 2] >= atoms.positions[sub, 2].max() - LAYER_GAP_A] if sub else []
    rank = {el: (el in non_metals, el) for el in set(atoms.get_chemical_symbols())}
    base = (np.linalg.solve(plane.T, atoms.positions[top, :2].T).T % 1.0) @ plane      # the top layer wrapped into the cell
    shifts = [i * plane[0] + j * plane[1] for i in range(-2, 3) for j in range(-2, 3)]
    xy = np.concatenate([base + s for s in shifts])
    owner = [k for _ in shifts for k in top]
    tri = Delaunay(xy)
    centres = np.array([_circumcentre(*xy[t]) for t in tri.simplices])
    parent = list(range(len(tri.simplices)))

    def find(t: int) -> int:
        while parent[t] != t:
            parent[t] = parent[parent[t]]
            t = parent[t]
        return t

    for t, row in enumerate(tri.neighbors):
        for u in row:
            if u >= 0 and np.linalg.norm(centres[t] - centres[u]) < MATCH_A:     # one circle; a NaN centre never joins
                rt, ru = find(t), find(int(u))
                if rt != ru:
                    parent[max(rt, ru)] = min(rt, ru)
    cells: Dict[int, List[int]] = {}
    edges: Dict[Tuple[int, int], List[int]] = {}
    for t, (a, b, c) in enumerate(tri.simplices):
        cells.setdefault(find(t), []).append(t)
        for p, q in ((a, b), (b, c), (a, c)):
            edges.setdefault((min(p, q), max(p, q)), []).append(find(t))

    def inside(point) -> bool:
        f = np.linalg.solve(plane.T, point)
        return bool(np.all((f >= -1e-6) & (f < 1 - 1e-6)))

    def height(ks) -> float:
        return float(np.mean(atoms.positions[ks, 2]))

    found = [{"site": f"top {atoms[k].symbol}", "position": np.array([*base[n], atoms.positions[k, 2]]), "indices": [k], "subsurf_index": None}
             for n, k in enumerate(top)]
    for (p, q), owners in edges.items():
        mid = (xy[p] + xy[q]) / 2
        if (len(owners) == 2 and owners[0] == owners[1]) or not inside(mid):      # the diagonal of a cell of four or more atoms
            continue
        ks = sorted((owner[p], owner[q]), key=lambda k: rank[atoms[k].symbol])
        found.append({"site": "bridge " + "-".join(atoms[k].symbol for k in ks), "position": np.array([*mid, height(ks)]), "indices": ks,
                      "subsurf_index": None})
    for root, members in cells.items():
        corners = sorted({int(v) for t in members for v in tri.simplices[t]})
        centre = xy[corners].mean(axis=0)
        if np.isnan(centres[root]).any() or not inside(centre):
            continue
        ks = [owner[v] for v in corners]
        under = None
        if second:
            d = np.hypot(*geometry.mic(atoms.positions[second] - np.array([*centre, 0.0]), cell)[:, :2].T)
            under = second[int(np.argmin(d))] if d.min() <= MATCH_A else None
        found.append({"site": "hollow" + (f" over {atoms[under].symbol}" if under is not None else ""), "position": np.array([*centre, height(ks)]),
                      "indices": ks, "subsurf_index": under})
    return found


def _circumcentre(a, b, c) -> np.ndarray:
    """The centre of the circle through three points of the plane; NaN for three points on a line."""
    d = 2.0 * (a[0] * (b[1] - c[1]) + b[0] * (c[1] - a[1]) + c[0] * (a[1] - b[1]))
    if abs(d) < 1e-9:
        return np.full(2, np.nan)
    sa, sb, sc = a @ a, b @ b, c @ c
    return np.array([sa * (b[1] - c[1]) + sb * (c[1] - a[1]) + sc * (a[1] - b[1]),
                     sa * (c[0] - b[0]) + sb * (a[0] - c[0]) + sc * (b[0] - a[0])]) / d


def _tile(found: List[dict], supplied, atoms, repeat: Tuple[int, int]) -> List[Site]:
    """ACAT's sites of the supplied cell copied into every image of the repeat; anchor atoms and the atom beneath
    are the copies nearest the copied site, since a site on the cell edge is anchored on atoms of the next image.
    ACAT expands a small cell by repetition and may report an index of the expansion; modulo n it is the atom."""
    n = len(supplied)
    cell = supplied.cell.array
    big = atoms.cell.array
    images = [(m0, m1) for m0 in range(repeat[0]) for m1 in range(repeat[1])]   # Atoms.repeat's order

    def copy_near(i: int, point) -> int:
        copies = [i % n + k * n for k in range(len(images))]
        d = np.linalg.norm(geometry.mic(atoms.positions[copies] - point, big)[:, :2], axis=1)
        return copies[int(np.argmin(d))]

    sites: List[Site] = []
    for m0, m1 in images:
        shift = m0 * cell[0] + m1 * cell[1]
        for s in found:
            pos = np.asarray(s["position"], dtype=float) + shift
            frac = np.linalg.solve(big[:2, :2].T, pos[:2]) % 1.0
            pos[:2] = frac @ big[:2, :2]
            beneath = s.get("subsurf_index")
            sites.append(Site(index=len(sites), label=LABELS.get(s["site"], s["site"]), point_group="", coordination=len(s["indices"]),
                              atom_beneath=supplied[int(beneath) % n].symbol if beneath is not None else None,
                              position=tuple(float(x) for x in pos), anchor_atoms=[copy_near(int(i), pos) for i in s["indices"]]))
    return sites


def neighbour_shell_edges(positions, cell, dx_A: float = 0.1) -> List[Tuple[int, int]]:
    """Each site joined to the sites of its first neighbour shell, the nearest within dx_A of the nearest distance;
    ACAT's get_neighbor_site_list with its defaults, made symmetric."""
    from ase.geometry import get_distances
    _, d = get_distances(np.asarray(positions), cell=cell, pbc=geometry.PLANE)
    edges = set()
    for i, row in enumerate(d):
        others = np.delete(np.arange(len(row)), i)
        nearest = row[others].min()
        for j in others[row[others] <= nearest + dx_A]:
            edges.add((min(i, int(j)), max(i, int(j))))
    return sorted(edges)


def surface_operations(atoms) -> Tuple[List[SymmetryOperation], str]:
    """The operations of the slab's space group that keep the surface normal and the slab in place, Cartesian, with
    the lattice translations of the cell among them; and the space-group symbol."""
    import spglib
    cell = (atoms.cell.array, atoms.get_scaled_positions(), atoms.numbers)
    data = spglib.get_symmetry_dataset(cell, symprec=SYMPREC_A)
    lat = atoms.cell.array
    ops = []
    for r, t in zip(data.rotations, data.translations):
        rc = lat.T @ r @ np.linalg.inv(lat.T)
        if abs(rc[2, 2] - 1) > 1e-6 or not np.allclose(rc[2, :2], 0, atol=1e-6) or not np.allclose(rc[:2, 2], 0, atol=1e-6):
            continue
        if abs((t[2] + 0.5) % 1 - 0.5) > 1e-6:
            continue
        tc = lat.T @ t
        tc[2] = 0.0
        ops.append(SymmetryOperation(rotation=np.round(rc, 10).tolist(), translation=np.round(tc, 10).tolist()))
    return ops, str(data.international)


def image_table(sites: SiteEnumeration, cell) -> np.ndarray:
    """table[g, i] is the site operation g maps site i onto, up to a lattice translation, matched by label."""
    xyz = np.array([s.position for s in sites.sites])
    labels = np.array([s.label for s in sites.sites])
    inv = np.linalg.inv(np.asarray(cell)[:2, :2])
    frac = xyz[:, :2] @ inv
    table = np.full((len(sites.operations), len(xyz)), -1, dtype=int)
    for g, op in enumerate(sites.operations):
        img = geometry.apply(op, xyz)[:, :2] @ inv
        diff = img[:, None, :] - frac[None, :, :]
        diff -= np.round(diff)
        dist = np.linalg.norm(diff @ np.asarray(cell)[:2, :2], axis=-1)
        dist[labels[:, None] != labels[None, :]] = np.inf
        j = dist.argmin(axis=1)
        if (dist[np.arange(len(xyz)), j] > MATCH_A).any():
            raise ValueError(f"operation {g} maps a site onto no site of its label: the site list is not symmetric")
        table[g] = j
    return table


def _orbits(table: np.ndarray, items: Sequence[int]) -> Dict[int, int]:
    """Each item's orbit under the operations of `table`, named by its smallest member."""
    members = set(items)
    parent = {i: i for i in members}

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for row in table:
        for i in members:
            j = int(row[i])
            if j in members:
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[max(ri, rj)] = min(ri, rj)
    return {i: find(i) for i in members}


def burnside(perms: Sequence[Sequence[int]], configurations: Sequence[Any]) -> float:
    """The number of orbits of a group acting on configurations, by Burnside's lemma: the mean number of
    configurations an operation fixes. perms[g][i] is where operation g sends point i; a tuple configuration is
    ordered, a frozenset one is not, as for two identical adsorbates."""
    def act(p, c) -> Hashable:
        return frozenset(p[i] for i in c) if isinstance(c, frozenset) else tuple(p[i] for i in c)
    configs = list(configurations)
    return sum(sum(1 for c in configs if act(p, c) == c) for p in perms) / len(perms)


def _baseline(atoms) -> Optional[int]:
    """pymatgen's count of inequivalent sites on the supplied cell; it labels fcc and hcp both hollow."""
    try:
        try:
            from pymatgen.core.adsorption import AdsorbateSiteFinder
        except ImportError:
            from pymatgen.analysis.adsorption import AdsorbateSiteFinder
        from pymatgen.io.ase import AseAtomsAdaptor
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            found = AdsorbateSiteFinder(AseAtomsAdaptor.get_structure(atoms), mi_vec=[0, 0, 1]).find_adsorption_sites(symm_reduce=0.01)
        return len(found["all"])
    except Exception as e:  # noqa: BLE001 - the baseline is a comparison, never a blocker
        log("site_enumeration", f"pymatgen baseline unavailable: {type(e).__name__}: {e}")
        return None
