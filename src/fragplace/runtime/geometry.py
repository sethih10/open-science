"""Geometry every tool shares: in-plane minimum images, bonds and fragments, heights, the site nearest a point, the
site graph and the symmetry operations of a site enumeration applied to points.

Numbers from atoms and records; nothing here writes a structure. The surface is periodic along the first two cell
vectors and the normal is z, as in ASE's slab builders. Bonds are ASE's natural cutoffs: two atoms are bonded when
closer than the sum of their covalent radii times `mult`, BOND_MULT unless a check names its own threshold.
"""
from __future__ import annotations

from collections import deque
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from ..schemas.records import Site, SiteEnumeration, SymmetryOperation
from .artifacts import surface_plane_z

PLANE = (True, True, False)
BOND_MULT = 1.2        # the usual tolerance on covalent radii; O–H at 0.97 Å sits right at the bare sum, 0.97 Å


def mic(vectors, cell) -> np.ndarray:
    """Minimum-image displacement vectors, periodic in the surface plane only."""
    from ase.geometry import find_mic
    out, _ = find_mic(np.atleast_2d(np.asarray(vectors, dtype=float)), cell, pbc=PLANE)
    return out


def in_plane_norm(vector) -> float:
    return float(np.hypot(vector[0], vector[1]))


def in_plane_distance(a, b, cell) -> float:
    """Minimum-image distance in the surface plane between two points."""
    return in_plane_norm(mic(np.asarray(b, dtype=float) - np.asarray(a, dtype=float), cell)[0])


def distance(atoms, i: int, j: int) -> float:
    return float(atoms.get_distance(i, j, mic=True))


def min_distance(atoms, group_a: Sequence[int], group_b: Sequence[int]) -> float:
    """Shortest minimum-image distance between any atom of one group and any atom of the other."""
    return min(distance(atoms, i, j) for i in group_a for j in group_b)


def cutoffs(atoms, mult: float = 1.0) -> List[float]:
    from ase.neighborlist import natural_cutoffs
    return natural_cutoffs(atoms, mult=mult)


def bonds(atoms, indices: Iterable[int], mult: float = BOND_MULT) -> List[Tuple[int, int]]:
    """Bonded pairs among `indices`, minimum image."""
    idx = list(indices)
    r = cutoffs(atoms, mult)
    return [(i, j) for k, i in enumerate(idx) for j in idx[k + 1:] if distance(atoms, i, j) < r[i] + r[j]]


def components(nodes: Iterable[int], edges: Iterable[Tuple[int, int]]) -> List[List[int]]:
    """Connected components of a graph, each sorted, ordered by their smallest node."""
    adj: Dict[int, set] = {n: set() for n in nodes}
    for i, j in edges:
        adj[i].add(j)
        adj[j].add(i)
    seen, out = set(), []
    for n in sorted(adj):
        if n in seen:
            continue
        comp, queue = [], deque([n])
        seen.add(n)
        while queue:
            k = queue.popleft()
            comp.append(k)
            for m in adj[k] - seen:
                seen.add(m)
                queue.append(m)
        out.append(sorted(comp))
    return out


def height(atoms, i: int) -> float:
    """Height of atom i above the surface plane."""
    return float(atoms.positions[i, 2] - surface_plane_z(atoms))


def lowest(atoms, indices: Sequence[int]) -> int:
    """The atom of a group nearest the surface plane: the binding atom of an adsorbed fragment."""
    return min(indices, key=lambda i: atoms.positions[i, 2])


def shortest_translation(cell) -> float:
    """Length of the shortest nonzero in-plane lattice translation: the distance from any atom to its own image."""
    a, b = np.asarray(cell)[0], np.asarray(cell)[1]
    return float(min(np.linalg.norm(i * a + j * b) for i in range(-3, 4) for j in range(-3, 4) if (i, j) != (0, 0)))


def image_distance(atoms, indices: Sequence[int]) -> float:
    """Shortest distance from any atom of a group to a periodic image of any atom of the group, the images of the
    surface plane only: how close a pair of fragments comes to its own copies."""
    cell = atoms.cell.array
    pos = atoms.positions[list(indices)]
    best = np.inf
    for i in range(-3, 4):
        for j in range(-3, 4):
            if (i, j) == (0, 0):
                continue
            shift = i * cell[0] + j * cell[1]
            d = np.linalg.norm(pos[:, None, :] - (pos[None, :, :] + shift), axis=-1)
            best = min(best, float(d.min()))
    return best


# ---- sites
def nearest_site(sites: SiteEnumeration, point, cell) -> Tuple[Site, float]:
    """The enumerated site nearest a point in the surface plane, and its in-plane distance."""
    xy = np.array([s.position for s in sites.sites])
    d = np.hypot(*mic(xy - np.asarray(point, dtype=float), cell)[:, :2].T)
    k = int(np.argmin(d))
    return sites.sites[k], float(d[k])


def site_graph(sites: SiteEnumeration) -> Dict[int, List[int]]:
    adj: Dict[int, List[int]] = {s.index: [] for s in sites.sites}
    for i, j in sites.edges:
        adj[i].append(j)
        adj[j].append(i)
    return adj


def site_graph_distances(sites: SiteEnumeration, source: int) -> Dict[int, int]:
    """Breadth-first hops from one site to every site it reaches on the site graph."""
    adj = site_graph(sites)
    dist, queue = {source: 0}, deque([source])
    while queue:
        k = queue.popleft()
        for m in adj[k]:
            if m not in dist:
                dist[m] = dist[k] + 1
                queue.append(m)
    return dist


def apply(op: SymmetryOperation, points) -> np.ndarray:
    """x' = R x + t for each row of points."""
    return np.atleast_2d(np.asarray(points, dtype=float)) @ np.asarray(op.rotation).T + np.asarray(op.translation)


def site_image(sites: SiteEnumeration, op: SymmetryOperation, index: int, cell, tol_A: float) -> Optional[int]:
    """The site an operation maps a site onto, up to a lattice translation; None when no site of the same label lies
    within tol_A, which means the site list or the operation is not a symmetry of the slab."""
    target = apply(op, sites.sites[index].position)[0]
    site, d = nearest_site(sites, target, cell)
    return site.index if d <= tol_A and site.label == sites.sites[index].label else None


def stabiliser(sites: SiteEnumeration, index: int, cell, tol_A: float) -> List[SymmetryOperation]:
    """The operations that map a site onto itself: its site group, as operations of the slab."""
    return [op for op in sites.operations if site_image(sites, op, index, cell, tol_A) == index]


def point_group(ops: Iterable[SymmetryOperation]) -> str:
    """Schoenflies symbol of a two-dimensional site group, from the in-plane parts of its operations."""
    rotations, mirrors = 0, 0
    seen = set()
    for op in ops:
        r = np.round(np.asarray(op.rotation)[:2, :2], 6)
        key = tuple(r.ravel())
        if key in seen:
            continue
        seen.add(key)
        if np.linalg.det(r) > 0:
            rotations += 1
        else:
            mirrors += 1
    if rotations == 1:
        return "Cs" if mirrors else "C1"
    return f"C{rotations}v" if mirrors else f"C{rotations}"
