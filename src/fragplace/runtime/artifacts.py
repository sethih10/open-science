"""Structures on disk and the conventions every tool shares for them.

A StructureRef points at an extxyz file under runs/<study>/structures/; the LLM never sees coordinates, only
the card. Atom roles travel as ASE tags, the fairchem convention extended by one value for the second fragment:
0 subsurface, 1 the top slab layer, 2 fragment A, the one that keeps the binding atom, 3 fragment B, the one
that was broken off. Constraints travel with the file. Every heavy import is local so the package imports
without ASE.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable, List, Optional

import numpy as np

from ..schemas.records import Role, StructureRef
from .journal import current_run

TAG_SUBSURFACE, TAG_SURFACE, TAG_A, TAG_B = 0, 1, 2, 3
FRAGMENT_TAGS = {"A": TAG_A, "B": TAG_B}


def resolve(path: str) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    run = current_run()
    if run and (run.dir / p).exists():
        return run.dir / p
    return p


def read(ref: StructureRef):
    from ase.io import read as ase_read
    return ase_read(resolve(ref.path), format=ref.format)


def structure_hash(atoms) -> str:
    """Hash of species, positions to 1e-4 Å, cell and tags: the identity of a structure for the cache."""
    h = hashlib.sha256()
    h.update(np.asarray(atoms.get_atomic_numbers()).tobytes())
    h.update(np.round(atoms.get_positions(), 4).tobytes())
    h.update(np.round(atoms.get_cell().array, 4).tobytes())
    h.update(np.asarray(atoms.get_tags()).tobytes())
    return h.hexdigest()[:16]


def write(atoms, name: str, role: Role, energy_eV: Optional[float] = None, settings_hash: Optional[str] = None,
          calculator: Optional[str] = None, directory: Optional[Path] = None) -> StructureRef:
    """Write atoms as extxyz under the run's structures/ (or `directory`) and return the ref."""
    from ase.io import write as ase_write
    run = current_run()
    base = Path(directory) if directory else (run.dir / "structures" if run else Path("structures"))
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"{name}.extxyz"
    out = atoms.copy()
    out.calc = None
    out.info = {k: v for k, v in out.info.items() if isinstance(v, (str, bool, int, float, np.integer, np.floating))}  # extxyz keeps scalars only
    ase_write(path, out, format="extxyz")
    rel = str(path.relative_to(run.dir)) if run and path.is_relative_to(run.dir) else str(path)
    return StructureRef(path=rel, format="extxyz", role=role, energy_eV=energy_eV, settings_hash=settings_hash, calculator=calculator)


def fragment_indices(atoms, fragment: str) -> List[int]:
    tag = FRAGMENT_TAGS[fragment]
    return [i for i, t in enumerate(atoms.get_tags()) if t == tag]


def fragment_atoms(ref: StructureRef, fragment: str):
    """The atoms of one fragment from a file: those tagged as the fragment when the file holds more, such as a whole
    candidate; every atom otherwise. Positions stay where they are, in the file's cell."""
    atoms = read(ref)
    idx = fragment_indices(atoms, fragment)
    frag = atoms[idx] if idx and len(idx) < len(atoms) else atoms.copy()
    frag.set_constraint()
    frag.set_tags([FRAGMENT_TAGS[fragment]] * len(frag))
    return frag


def binding_atom(atoms) -> int:
    """The binding atom of a fragment file: info["binding_atom"] as structure_retrieval writes it, else the lowest atom."""
    if "binding_atom" in atoms.info:
        return int(atoms.info["binding_atom"])
    return int(np.argmin(atoms.positions[:, 2]))


def binding_index(atoms, fragment: str) -> int:
    """The index of a fragment's binding atom in a whole structure: info["binding_A"] or info["binding_B"], as
    structure_retrieval and adsorbate_placement write them from the bond the human named, else the fragment's
    lowest atom."""
    key = f"binding_{fragment}"
    if key in atoms.info:
        return int(atoms.info[key])
    idx = fragment_indices(atoms, fragment)
    return min(idx, key=lambda i: atoms.positions[i, 2])


def adsorbate_indices(atoms) -> List[int]:
    return [i for i, t in enumerate(atoms.get_tags()) if t in (TAG_A, TAG_B)]


def slab_indices(atoms) -> List[int]:
    return [i for i, t in enumerate(atoms.get_tags()) if t in (TAG_SUBSURFACE, TAG_SURFACE)]


def surface_indices(atoms) -> List[int]:
    return [i for i, t in enumerate(atoms.get_tags()) if t == TAG_SURFACE]


def surface_plane_z(atoms) -> float:
    """The surface plane: the mean z of the atoms tagged as the top layer; of the highest slab layer if none is tagged."""
    top = surface_indices(atoms)
    if top:
        return float(np.mean(atoms.get_positions()[top, 2]))
    slab = slab_indices(atoms) or list(range(len(atoms)))
    z = atoms.get_positions()[slab, 2]
    return float(np.mean(z[z >= z.max() - 0.5]))


def tag_slab_layers(atoms, top_tolerance_A: float = 0.5):
    """Tag the top layer 1 and everything else 0; returns the same atoms."""
    z = atoms.get_positions()[:, 2]
    tags = np.where(z >= z.max() - top_tolerance_A, TAG_SURFACE, TAG_SUBSURFACE)
    atoms.set_tags(tags)
    return atoms


def centre(atoms, indices: Iterable[int]) -> np.ndarray:
    idx = list(indices)
    return atoms.get_positions()[idx].mean(axis=0)


def in_plane_distance(atoms, i: int, j: int) -> float:
    """Minimum-image distance in the surface plane between atoms i and j."""
    d = atoms.get_distance(i, j, mic=True, vector=True)
    return float(np.hypot(d[0], d[1]))
