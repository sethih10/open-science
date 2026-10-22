"""The anomaly filter, eleven checks, and the descriptor card the agents read. Tools: anomaly_filter, descriptor_card. Defined in fragplace.registry."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from .. import calculators
from ..registry.tools import fixed_threshold
from ..runtime import artifacts, geometry, project
from ..runtime.journal import current_run, log, traced
from ..schemas.records import Candidate, CheckVerdict, DescriptorCard, GateResult, Settings, SiteEnumeration, StructureRef

MAGNETIC = {"Fe", "Co", "Ni"}


@traced(step="5", tool="anomaly_filter")
def anomaly_filter(candidate: Candidate, start: Candidate, slab: StructureRef, settings: Settings, prior_E_ads_eV: Optional[float] = None, frequencies_cm: Optional[List[float]] = None) -> GateResult:
    """The nine checks of the gate per fragment, before and after relaxation, plus the two final-state checks: the A–B bond re-formed, and the periodic image; verdict into the card; a failing candidate is never kept.

    Board steps: 5, 3.1. Status: core. Lane: laptop. Allowed roles: solution-planner.

    Inputs:
        candidate: Candidate
        start: Candidate
        slab: StructureRef
        settings: Settings
        prior_E_ads_eV: float | None
        frequencies_cm: list[float] | None
    Outputs:
        gate: GateResult
    Checks:
        - 1 desorbed per fragment
        - 2 migrated
        - 3 dissociated within a fragment
        - 4 reconstructed
        - 5 not a minimum
        - 6 magnetism collapsed
        - 7 outside expected range
        - 8 settings mismatch
        - 9 intercalated
        - 10 A–B bond re-formed
        - 11 periodic image
    Thresholds:
        desorbed_A: 3
        AB_bond_reformed_A: open: team decision
        migrated: open: team decision
        dissociated: open: team decision
        reconstructed: open: team decision
        imaginary_noise_cm: open: team decision
        expected_range_width_eV: open: team decision
        magnetism_collapsed: open: team decision
        intercalated: open: team decision
        frequencies_source: open: team decision: mlip or dft
    Wraps:
        - fairchem.data.oc.utils.DetectTrajAnomaly
        - ase.vibrations.Vibrations
        - acat.adsorbate_coverage.SlabAdsorbateCoverage
        - CatBench anomaly classes as names
    Logs: every verdict with its measured value; every rejection with its reason.

    candidate is the relaxed structure and start the one relaxation began from; slab is the clean slab relaxed
    with the same potential. Heights are above the surface plane, the mean height of the top layer. Check 2
    measures the in-plane move of each fragment's binding atom; 3, each bond of a fragment's start as a multiple
    of the two covalent radii; 4, the top layer against the clean slab. Check 5 computes the adsorbate atoms'
    frequencies with the candidate's own potential when none are given and the team chose mlip; imaginary modes
    are negative numbers. Check 7 runs only against a human-verified prior, E_ads taken against the gas
    references of PROJECT.md, which must be on the potential's energy scale. Check 11 measures as the team's
    structure_retrieval.image_measure says. A check that cannot run passes with the reason "not checked".
    """
    s = project.require_locked(settings)

    def th(name: str) -> float:
        return float(project.decision("anomaly_filter", name, s))

    atoms, begin, clean = artifacts.read(candidate.structure), artifacts.read(start.structure), artifacts.read(slab)
    cell = atoms.cell.array
    stage = "before_relaxation" if candidate.structure.path == start.structure.path else "after_relaxation"
    frags = {k: v for k, v in (("A", artifacts.fragment_indices(atoms, "A")), ("B", artifacts.fragment_indices(atoms, "B"))) if v}
    ads = artifacts.adsorbate_indices(atoms)
    plane = artifacts.surface_plane_z(atoms)
    v: List[CheckVerdict] = []

    limit = fixed_threshold("anomaly_filter", "desorbed_A")
    for name, idx in frags.items():
        h = float(artifacts.centre(atoms, idx)[2] - plane)
        v.append(CheckVerdict(check_id=1, name="desorbed", passed=h <= limit, measured=h, threshold=f"> {limit} Å", fragment=name,
                              reason=f"{name} centre {h:.2f} Å above the surface plane"))
    limit = th("migrated")
    for name, idx in frags.items():
        b = geometry.lowest(begin, idx)
        d = geometry.in_plane_distance(begin.positions[b], atoms.positions[b], cell)
        v.append(CheckVerdict(check_id=2, name="migrated", passed=d <= limit, measured=d, threshold=f"> {limit} Å", fragment=name,
                              reason=f"{name} binding atom moved {d:.2f} Å in the plane"))
    limit = th("dissociated")
    radii = geometry.cutoffs(atoms, 1.0)
    for name, idx in frags.items():
        stretch = [geometry.distance(atoms, i, j) / (radii[i] + radii[j]) for i, j in geometry.bonds(begin, idx)]
        worst = max(stretch) if stretch else None
        v.append(CheckVerdict(check_id=3, name="dissociated", passed=worst is None or worst <= limit, measured=worst, threshold=f"> {limit} × covalent sum",
                              fragment=name, reason=f"{name} longest bond {worst:.2f} × the covalent sum" if stretch else f"{name} has no bond, not checked"))
    limit = th("reconstructed")
    top = [i for i in artifacts.surface_indices(clean) if i < len(atoms)]
    if len(atoms) < len(clean) or list(atoms.numbers[:len(clean)]) != list(clean.numbers):
        raise ValueError(f"{candidate.id} does not start with the clean slab's atoms in the clean slab's order")
    moved = float(np.linalg.norm(geometry.mic(atoms.positions[top] - clean.positions[top], cell), axis=1).max()) if top else 0.0
    v.append(CheckVerdict(check_id=4, name="reconstructed", passed=moved <= limit, measured=moved, threshold=f"> {limit} Å",
                          reason=f"top-layer atoms moved up to {moved:.2f} Å from the clean slab"))
    v.append(_minimum(candidate, atoms, ads, s, frequencies_cm, stage, th("imaginary_noise_cm")))
    v.append(_magnetism(candidate, atoms, clean, s, th("magnetism_collapsed")))
    v.append(_expected_range(candidate, atoms, ads, slab, s, prior_E_ads_eV, th("expected_range_width_eV")))
    hashes = {candidate.structure.settings_hash, slab.settings_hash, project.settings_hash(s)}
    calcs = {c for c in (candidate.structure.calculator, slab.calculator) if c}
    v.append(CheckVerdict(check_id=8, name="settings mismatch", passed=len(hashes) == 1 and len(calcs) <= 1, threshold="exact equality",
                          reason=f"settings hashes {sorted(map(str, hashes))}, potentials {sorted(calcs) or ['none recorded']}"))
    limit = th("intercalated")
    depth = float(min(atoms.positions[i, 2] - plane for i in ads)) if ads else 0.0
    v.append(CheckVerdict(check_id=9, name="intercalated", passed=depth >= -limit, measured=depth, threshold=f"< -{limit} Å",
                          reason=f"lowest adsorbate atom {depth:.2f} Å above the surface plane"))
    if len(frags) == 2:
        limit = th("AB_bond_reformed_A")
        d = geometry.min_distance(atoms, frags["A"], frags["B"])
        v.append(CheckVerdict(check_id=10, name="A–B bond re-formed", passed=d >= limit, measured=d, threshold=f"< {limit} Å",
                              reason=f"A–B distance {d:.2f} Å"))
        measure = project.decision("structure_retrieval", "image_measure", s)
        d = geometry.shortest_translation(cell) if measure == "own_image" else geometry.image_distance(atoms, frags["A"] + frags["B"])
        v.append(CheckVerdict(check_id=11, name="periodic image", passed=d >= s.min_image_distance_A, measured=d,
                              threshold=f"< {s.min_image_distance_A} Å", reason=f"images {d:.2f} Å apart, measure {measure}"))
    gate = GateResult(candidate_id=candidate.id, verdicts=v, passed=all(x.passed for x in v), stage=stage)
    failed = [x for x in v if not x.passed]
    log("anomaly_filter", f"{candidate.id} {stage}: " + ("pass" if gate.passed else "REJECTED, " + "; ".join(
        f"check {x.check_id} {x.name}: {x.reason}" for x in failed)))
    for x in v:
        log("anomaly_filter", f"{candidate.id} check {x.check_id} {x.name}{' ' + x.fragment if x.fragment else ''}: "
                              f"{'pass' if x.passed else 'FAIL'}, measured {x.measured}, fails {x.threshold}")
    return gate


def _minimum(candidate: Candidate, atoms, ads: List[int], s: Settings, given, stage: str, noise: float) -> CheckVerdict:
    source = project.decision("anomaly_filter", "frequencies_source", s)
    freqs = list(given) if given is not None else None
    if freqs is None and source == "mlip" and stage == "after_relaxation" and ads:
        freqs = frequencies(atoms, candidate.structure.calculator or s.mlip, ads)
    if not freqs:
        why = "before relaxation" if stage == "before_relaxation" else f"no frequencies, source {source}"
        return CheckVerdict(check_id=5, name="not a minimum", passed=True, threshold=f"imaginary below -{noise} cm⁻¹", reason=f"not checked: {why}")
    imaginary = [f for f in freqs if f < -noise]
    return CheckVerdict(check_id=5, name="not a minimum", passed=not imaginary, measured=float(min(freqs)), threshold=f"imaginary below -{noise} cm⁻¹",
                        reason=(f"{len(imaginary)} imaginary mode(s), " + ", ".join(f"{-f:.0f}i" for f in imaginary) + " cm⁻¹") if imaginary
                        else f"no imaginary mode beyond {noise} cm⁻¹, {len(freqs)} modes")


def frequencies(atoms, calculator: str, indices: List[int]) -> List[float]:
    """Harmonic frequencies in cm⁻¹ of the given atoms, the rest held still; imaginary modes as negative numbers."""
    from ase.vibrations import Vibrations
    work = atoms.copy()
    work.calc = calculators.get(calculator)._calc
    with tempfile.TemporaryDirectory() as tmp:
        vib = Vibrations(work, indices=indices, name=str(Path(tmp) / "vib"))
        vib.run()
        raw = vib.get_frequencies()
    return [float(f.real) if abs(f.imag) < 1e-9 else -float(abs(f.imag)) for f in raw]


def _magnetism(candidate: Candidate, atoms, clean, s: Settings, limit: float) -> CheckVerdict:
    name, th = "magnetism collapsed", f"moment below {limit} μB on a magnetic slab"
    if not (s.spin_polarised or MAGNETIC & set(clean.get_chemical_symbols())):
        return CheckVerdict(check_id=6, name=name, passed=True, threshold=th, reason="non-magnetic slab, not checked")
    adapter = calculators.get(candidate.structure.calculator or s.mlip)
    m_slab, m_cand = adapter.magnetic_moments(clean), adapter.magnetic_moments(atoms)
    if m_slab is None or m_cand is None:
        return CheckVerdict(check_id=6, name=name, passed=True, threshold=th, reason=f"not checked: {adapter.name} gives no moments")
    total_slab, total = abs(float(np.sum(m_slab))), abs(float(np.sum(m_cand)))
    collapsed = total_slab >= limit and total < limit
    return CheckVerdict(check_id=6, name=name, passed=not collapsed, measured=total, threshold=th,
                        reason=f"total moment {total:.2f} μB against {total_slab:.2f} μB on the clean slab")


def _expected_range(candidate: Candidate, atoms, ads: List[int], slab: StructureRef, s: Settings, prior, width: float) -> CheckVerdict:
    name, th = "outside expected range", f"|E_ads − prior| > {width / 2:g} eV"
    reference = gas_reference(s, atoms[ads].get_chemical_symbols()) if ads else None
    missing = [w for w, x in (("no human-verified prior", prior), ("no candidate energy", candidate.structure.energy_eV),
                              ("no slab energy", slab.energy_eV), ("no gas reference for these atoms", reference)) if x is None]
    if missing:
        return CheckVerdict(check_id=7, name=name, passed=True, threshold=th, reason="not checked: " + ", ".join(missing))
    e_ads = candidate.structure.energy_eV - slab.energy_eV - reference
    return CheckVerdict(check_id=7, name=name, passed=abs(e_ads - prior) <= width / 2, measured=e_ads, threshold=th,
                        reason=f"E_ads {e_ads:.2f} eV against the prior {prior:.2f} eV")


def gas_reference(s: Settings, symbols: List[str]) -> Optional[float]:
    """The energy of these atoms from the locked gas references: the combination of reference species with the same
    composition; None when the references cannot make it."""
    from ase.formula import Formula
    refs = []
    for g in s.gas_references:
        try:
            refs.append((g, Formula(g.species).count()))
        except ValueError:
            continue
    want: Dict[str, int] = {}
    for el in symbols:
        want[el] = want.get(el, 0) + 1
    if not refs:
        return None
    elements = sorted(set(want) | {el for _, c in refs for el in c})
    m = np.array([[c.get(el, 0) for _, c in refs] for el in elements], dtype=float)
    b = np.array([want.get(el, 0) for el in elements], dtype=float)
    x = np.linalg.lstsq(m, b, rcond=None)[0]
    if not np.allclose(m @ x, b, atol=1e-8):
        return None
    return float(sum(k * (g.energy_eV + g.correction_eV) for k, (g, _) in zip(x, refs)))


@traced(step="3.4", tool="descriptor_card")
def descriptor_card(candidate: Candidate, gate: Optional[GateResult], sites: SiteEnumeration) -> DescriptorCard:
    """Render a structure as the text card the LLM reads, with site, distances, verdicts and the A–B distance; a PNG beside it as a second look.

    Board steps: 3.4, 5, 8. Status: core. Lane: laptop. Allowed roles: solution-planner, surface-chemist, scientific-critic.

    Inputs:
        candidate: Candidate
        gate: GateResult | None
        sites: SiteEnumeration
    Outputs:
        card: DescriptorCard
    Checks:
        - two configurations never share a card: distances and site labels always present
    Thresholds:
        none
    Wraps:
        - pymatgen
        - robocrystallographer pattern
        - ase.io.write png
    Logs: the card beside the structure.

    Each fragment is read at the site nearest its binding atom, the atom nearest the surface; the single-value
    fields describe B in a pair and A alone otherwise, and one line per fragment carries both. The card, its text
    and a top-view PNG go to cards/ under the structure's file name, so the start and the relaxed structure of one
    candidate keep two cards.
    """
    settings = project.current_settings(require_lock=False)
    atoms = artifacts.read(candidate.structure)
    cell = atoms.cell.array
    slab_idx = artifacts.slab_indices(atoms)
    frags = {k: v for k, v in (("A", artifacts.fragment_indices(atoms, "A")), ("B", artifacts.fragment_indices(atoms, "B"))) if v}
    if not frags:
        raise ValueError(f"{candidate.id} holds no fragment to describe")
    z = atoms.positions[slab_idx, 2]
    layer = _layers(z)
    layers = int(layer.max() + 1) if len(z) else 0
    fixed = {int(i) for c in atoms.constraints if type(c).__name__ == "FixAtoms" for i in c.get_indices()}
    fixed_layers = sum(1 for k in range(layers) if all(slab_idx[i] in fixed for i in np.flatnonzero(layer == k)))
    lines, info = [], {}
    for name, idx in frags.items():
        b = geometry.lowest(atoms, idx)
        site, off = geometry.nearest_site(sites, atoms.positions[b], cell)
        nn = sorted(geometry.distance(atoms, b, j) for j in slab_idx)[:3]
        tilt = None
        if len(idx) > 1:
            axis = geometry.mic(artifacts.centre(atoms, idx) - atoms.positions[b], cell)[0]
            tilt = float(np.degrees(np.arccos(np.clip(axis[2] / np.linalg.norm(axis), -1, 1))))
        info[name] = (site, geometry.height(atoms, b), nn, tilt)
        lines.append(f"{name} {atoms[idx].get_chemical_formula()}: {site.label} site {site.index}, {off:.2f} Å off it, {site.point_group}, "
                     f"coordination {site.coordination}; height {geometry.height(atoms, b):.2f} Å; nearest slab atoms "
                     + ", ".join(f"{d:.2f}" for d in nn) + " Å" + (f"; tilt {tilt:.0f}°" if tilt is not None else ""))
    main = info.get("B") or info["A"]
    pair = len(frags) == 2
    moved = [f"{x.fragment} {x.measured:.2f} Å" for x in (gate.verdicts if gate else []) if x.check_id == 2 and x.measured is not None]
    a_len, b_len = (float(np.linalg.norm(cell[k])) for k in (0, 1))
    gamma = float(np.degrees(np.arccos(np.dot(cell[0], cell[1]) / (a_len * b_len))))
    card = DescriptorCard(
        candidate_id=candidate.id, composition=atoms.get_chemical_formula(), cell=f"{a_len:.2f} × {b_len:.2f} Å, γ {gamma:.0f}°",
        facet=settings.facet, layers=layers, vacuum_A=float(cell[2, 2] - (z.max() - z.min())) if len(z) else float(cell[2, 2]), fixed_layers=fixed_layers,
        site_label=" · ".join(f"{k} {i[0].label}" for k, i in info.items()), point_group=" · ".join(i[0].point_group for i in info.values()),
        coordination=main[0].coordination, height_A=main[1], nn_distances_A=main[2], tilt_deg=main[3],
        displacement_from_start=("moved from the start: " + ", ".join(moved)) if moved else "",
        verdicts=gate.verdicts if gate else [], AB_distance_A=geometry.min_distance(atoms, frags["A"], frags["B"]) if pair else None,
        site_graph_distance=geometry.site_graph_distances(sites, info["A"][0].index).get(info["B"][0].index) if pair else None,
        energy_eV=candidate.structure.energy_eV, fragment_lines=lines)
    assert card.site_label and card.nn_distances_A, "a card without site labels or distances"
    run = current_run()
    if run:
        stem = Path(candidate.structure.path).stem
        card.image_path = _image(atoms, run.dir / "cards" / f"{stem}.png", run.dir)
        (run.dir / "cards" / f"{stem}.txt").write_text(card.text() + "\n")
        (run.dir / "cards" / f"{stem}.json").write_text(card.model_dump_json(indent=1))
    log("descriptor_card", f"{candidate.id}: {card.site_label}" + (f", A–B {card.AB_distance_A:.2f} Å, site-graph {card.site_graph_distance}" if pair else ""))
    return card


def _layers(z: np.ndarray, gap_A: float = 0.5) -> np.ndarray:
    """Layer index of each height, 0 at the bottom; a new layer starts where heights jump by more than gap_A."""
    order = np.argsort(z)
    layer = np.zeros(len(z), dtype=int)
    for n in range(1, len(order)):
        layer[order[n]] = layer[order[n - 1]] + (z[order[n]] - z[order[n - 1]] > gap_A)
    return layer


def _image(atoms, path: Path, root: Path) -> Optional[str]:
    """A top view as a second look; never the basis of a decision."""
    try:
        from ase.io import write
        write(str(path), atoms, format="png", rotation="0x", scale=20)
        return str(path.relative_to(root))
    except Exception as e:  # noqa: BLE001 - the picture is optional, the text card is not
        log("descriptor_card", f"no image: {type(e).__name__}: {e}")
        return None
