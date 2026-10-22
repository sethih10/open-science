"""The three relaxed inputs, the cleaved fragments, the cell and the settings lock. Tools: structure_retrieval, calculation_protocol. Defined in fragplace.registry."""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from ..errors import FragPlaceError, OpenDecision, SettingsMismatch
from ..registry.tools import NO_DFT, WITHOUT_DFT, runs_dft
from ..runtime import artifacts, geometry, project
from ..runtime.journal import current_run, log, traced
from ..schemas.records import Role, Settings, StructureRef

# The protocol table: only the values AGENTS.md section 3 states. A protocol fills what the inputs leave unset and
# never overrides them; a value neither gives stays unset and is reported, never filled from memory.
PROTOCOLS: Dict[str, Dict[str, Any]] = {
    NO_DFT: {},             # no DFT runs: the lock holds no DFT setting, and the potential computes every energy
    "oc20": {"functional": "RPBE", "pseudopotential_family": "PAW", "cutoff_eV": 350.0},
    "aiida_common_workflows": {},
    "sssp": {},
}
MUST_MATCH = {"oc20": ("functional", "pseudopotential_family")}   # OC20NEB as ground truth: the lock matches OC20
# The k-mesh rule of the table: k-points along each in-plane cell vector times its length in Å, rounded up;
# Γ-centred, one k-point along the vacuum, the same mesh for slab and slab+A. Only OC20 states a rule.
KMESH_RULE_A = {"oc20": 40.0}
FOUND = "PROJECT.md before the lock"    # the origin of a value the settings already held
REPORTED = ("functional", "dispersion", "spin_polarised", "initial_moments", "hubbard_u", "pseudopotential_family", "pseudopotential_version",
            "cutoff_eV", "kmesh", "smearing", "sigma_eV", "layers", "fixed_layers", "vacuum_A", "dipole_correction", "cell_repeat", "cell_A",
            "min_image_distance_A", "force_threshold_eV_per_A", "scf_threshold_eV", "convergence_target_meV", "gas_references")
# What a study without DFT uses, and so all its lock reports; every other setting is DFT's and stays unset.
RUN_SETTINGS = ("cell_repeat", "cell_A", "min_image_distance_A", "force_threshold_eV_per_A", "gas_references")
DFT_SETTINGS = ("functional", "dispersion", "hubbard_u", "pseudopotential_family", "pseudopotential_version", "cutoff_eV", "kmesh", "smearing",
                "sigma_eV", "layers", "fixed_layers", "vacuum_A", "dipole_correction", "scf_threshold_eV", "convergence_target_meV")
NO_DFT_CHOICES = ("spin", "spin_polarised", "initial_moments")    # the physics choices a potential can use
MAX_SLAB_DRIFT_A = 1.0     # the initial state's slab atoms sit within this of the clean slab's, or the files disagree
SYMPREC_A = 0.05           # spglib's tolerance on a relaxed slab, as site_enumeration's
SAME_POSITION_A = 0.3      # an operation maps an adsorbate atom onto another when it lands this close to it


@traced(step="1", tool="structure_retrieval")
def structure_retrieval(slab: StructureRef, adsorbate_vacuum: StructureRef, initial_state: StructureRef, bond_to_break: Tuple[int, int]) -> Dict[str, Any]:
    """Take the three supplied relaxed structures with their energies, cleave the named bond to make A and B, and select the surface cell so periodic images stay apart.

    Board steps: 1. Status: core. Lane: laptop. Allowed roles: computational-chemist, solution-planner.

    Inputs:
        slab: StructureRef
        adsorbate_vacuum: StructureRef
        initial_state: StructureRef
        bond_to_break: tuple[int, int], atom indices in AB
    Outputs:
        fragment_A: StructureRef
        fragment_B: StructureRef
        cell_repeat: tuple[int, int]
        structures: list[StructureRef]
    Checks:
        - the three inputs share one settings set, check 8
        - images at least min_image_distance_A apart
    Thresholds:
        min_image_distance_A: 10
        image_measure: open: team decision: own_image, each atom to its own image, or pair_to_image, the pair to its nearest image
    Wraps:
        - ase.io
        - pymatgen.core
    Logs: input hashes; the cell and why.

    The initial state is the slab's atoms in the slab's order followed by AB's in AB's order; bond_to_break indexes
    AB, A's side first, as the human names it. A is the side of bond_to_break[0], its binding atom, and B the side
    of bond_to_break[1], its binding atom, whatever their heights: the H of water on NaCl may sit lower than its O.
    PROJECT.md's metal, adsorbate and product must have the compositions of the slab, of AB and of A and B, or the
    call stops. Both fragments are written where they sit in the initial state, in the selected cell, with the
    binding atom's index in info["binding_atom"]. structures holds the repeated slab and the slab with A alone at
    its initial-state site, A's binding atom in info["binding_A"], the base B is placed on while step 3.5 is
    deferred. The trace says whether a surface operation of the slab maps each other bond between the same two
    elements, the other O–H of water, onto the named one; when none does, breaking it is another cleavage.
    """
    hashes = {r.settings_hash for r in (slab, adsorbate_vacuum, initial_state)}
    methods = {r.calculator for r in (slab, adsorbate_vacuum, initial_state)}
    if len(hashes) > 1 or len(methods) > 1:
        raise SettingsMismatch(f"check 8: the three inputs were relaxed with different settings, hashes {sorted(map(str, hashes))}, "
                               f"methods {sorted(map(str, methods))}")
    recorded = [f"settings hash {h}" for h in hashes if h] + [f"method {m}" for m in methods if m]
    settings = project.current_settings(require_lock=False)
    s_atoms, ab, is_atoms = artifacts.read(slab), artifacts.read(adsorbate_vacuum), artifacts.read(initial_state)
    n = len(s_atoms)
    if (len(is_atoms) != n + len(ab) or list(is_atoms.numbers[:n]) != list(s_atoms.numbers)
            or list(is_atoms.numbers[n:]) != list(ab.numbers)):
        raise ValueError("the initial state must be the slab's atoms in the slab's order followed by the adsorbate's in its order")
    if not np.allclose(is_atoms.cell.array, s_atoms.cell.array, atol=1e-3):
        raise ValueError("the initial state and the slab have different cells")
    drift = float(np.linalg.norm(geometry.mic(is_atoms.positions[:n] - s_atoms.positions, s_atoms.cell.array), axis=1).max())
    if drift > MAX_SLAB_DRIFT_A:
        raise ValueError(f"the initial state's slab atoms sit up to {drift:.2f} Å from the clean slab's: not the same slab")

    i, j = (int(k) for k in bond_to_break)
    ads = list(range(n, len(is_atoms)))
    if not (0 <= i < len(ab) and 0 <= j < len(ab)) or i == j:
        raise ValueError(f"bond_to_break {bond_to_break} does not name two atoms of {ab.get_chemical_formula()}")
    graph = geometry.bonds(ab, range(len(ab)))            # the molecule's bonds, read in vacuum where nothing stretches them
    if (min(i, j), max(i, j)) not in graph:
        raise ValueError(f"atoms {i} and {j} of the adsorbate are not bonded in the relaxed adsorbate in vacuum")
    kept = [(n + p, n + q) for p, q in graph if {p, q} != {i, j}]
    parts = geometry.components(ads, kept)
    side = {k: p for p in parts for k in p}
    if side[n + i] is side[n + j]:
        raise ValueError(f"breaking {bond_to_break} leaves the adsorbate in one piece; the bond is in a ring")
    a_idx, b_idx = side[n + i], side[n + j]              # the human's order: A holds bond_to_break[0], B bond_to_break[1]
    a_binding, b_binding = n + i, n + j
    name_a = species_name(is_atoms[a_idx], a_idx.index(a_binding))
    name_b = species_name(is_atoms[b_idx], b_idx.index(b_binding))
    _check_system(settings, s_atoms, ab, name_a, name_b)
    lowest = geometry.lowest(is_atoms, ads)

    n1, n2, why = _cell_repeat(s_atoms, is_atoms, a_idx, b_idx, settings)
    rep = s_atoms.repeat((n1, n2, 1))
    energy = slab.energy_eV * n1 * n2 if slab.energy_eV is not None else None
    sh = slab.settings_hash

    def fragment(indices, tag, binding_atom, name, role):
        frag = is_atoms[list(indices)]
        frag.set_cell(rep.cell)
        frag.set_pbc(rep.pbc)
        frag.set_tags([tag] * len(frag))
        frag.set_constraint()
        frag.info = {"binding_atom": list(indices).index(binding_atom)}
        return frag, artifacts.write(frag, name, role, settings_hash=sh)

    frag_a, ref_a = fragment(a_idx, artifacts.TAG_A, a_binding, "fragment-A", Role.fragment_A)
    _, ref_b = fragment(b_idx, artifacts.TAG_B, b_binding, "fragment-B", Role.fragment_B)
    base = rep + frag_a
    base.set_constraint(rep.constraints)
    base.info = {"binding_A": len(rep) + a_idx.index(a_binding)}
    refs = [artifacts.write(rep, "slab-cell", Role.slab, energy_eV=energy, settings_hash=sh),
            artifacts.write(base, "A-at-initial-site", Role.candidate, settings_hash=sh)]
    log("structure_retrieval", "inputs " + ", ".join(f"{r.role.value} {artifacts.structure_hash(a)}" for r, a in
                                                       ((slab, s_atoms), (adsorbate_vacuum, ab), (initial_state, is_atoms))))
    log("structure_retrieval", "check 8 on the inputs: " + (", ".join(recorded) + ", the same for all three" if recorded
                               else "not checked, the inputs record neither a settings hash nor a method"))
    log("structure_retrieval", f"A = {name_a}, binding atom {is_atoms[a_binding].symbol}, atom {i} of the adsorbate; B = {name_b}, binding atom "
                               f"{is_atoms[b_binding].symbol}, atom {j}: named by the bond order, A's side first; cell {n1}x{n2}: {why}")
    if lowest != a_binding:
        log("structure_retrieval", f"the lowest adsorbate atom is {is_atoms[lowest].symbol}, atom {lowest - n}, "
                                   f"{is_atoms.positions[a_binding, 2] - is_atoms.positions[lowest, 2]:.2f} Å below A's binding atom; "
                                   f"A follows the bond order, not the height")
    log("structure_retrieval", _same_bonds(s_atoms, is_atoms, n, graph, i, j))
    return {"fragment_A": ref_a, "fragment_B": ref_b, "cell_repeat": (n1, n2), "structures": refs}


def _cell_repeat(slab, initial, a_idx, b_idx, settings: Settings) -> Tuple[int, int, str]:
    """The smallest repeat of the supplied cell whose images stay min_image_distance_A apart under the team's measure."""
    measure = project.decision("structure_retrieval", "image_measure", settings)
    need = settings.min_image_distance_A
    if measure == "pair_to_image":
        upper = float(project.decision("pair_enumeration", "upper_bound_A", settings))
        extent = sum(max((geometry.distance(initial, p, q) for p in idx for q in idx), default=0.0) for idx in (a_idx, b_idx))
        need = need + upper + extent
    elif measure != "own_image":
        raise OpenDecision(f"structure_retrieval.image_measure is {measure!r}; it must be own_image or pair_to_image")
    cell = slab.cell.array
    options = sorted(((n1, n2) for n1 in range(1, 13) for n2 in range(1, 13)), key=lambda m: (m[0] * m[1], abs(m[0] - m[1]), m))
    for n1, n2 in options:
        length = geometry.shortest_translation(np.array([n1 * cell[0], n2 * cell[1], cell[2]]))
        if length >= need:
            return n1, n2, (f"shortest in-plane translation {length:.2f} Å >= {need:.2f} Å, measure {measure}, "
                            f"min_image_distance_A {settings.min_image_distance_A}")
    raise ValueError(f"no repeat up to 12x12 of the supplied cell reaches {need:.1f} Å")


def species_name(atoms, first: Optional[int] = None) -> str:
    """The formula a study writes for a species: Hill order, H2O; with a binding atom, its element first and the rest
    in Hill order, OH, as an adsorbate is written."""
    from ase.formula import Formula
    if first is None:
        return atoms.get_chemical_formula()
    count = Formula(atoms.get_chemical_formula()).count()
    lead = atoms[first].symbol
    rest = {el: k for el, k in count.items() if el != lead}
    return lead + (str(count[lead]) if count[lead] > 1 else "") + (Formula.from_dict(rest).format("hill") if rest else "")


def initial_state_in_cell(slab_cell: StructureRef, slab: StructureRef, initial_state: StructureRef) -> StructureRef:
    """The initial state in the selected cell, by code: the selected slab with the adsorbate of the supplied initial
    state where it sits there, so E(IS) and every final state share one cell. The supplied initial state is the
    supplied slab's atoms followed by AB's; the selected cell repeats the supplied one from the same origin, so AB's
    positions hold in it. The slab's constraints are kept, and no energy, since the potential relaxes it next."""
    host, is_atoms = artifacts.read(slab_cell), artifacts.read(initial_state)
    n = len(artifacts.read(slab))
    system = host + is_atoms[n:]
    system.set_constraint(host.constraints)
    system.info = {}
    return artifacts.write(system, "initial-state-cell", Role.initial_state, settings_hash=initial_state.settings_hash)


def composition(text: str, reduce: bool = False) -> Optional[Dict[str, int]]:
    """The element counts a formula names, reduced to the formula unit when asked; None when the text is no formula."""
    from ase.formula import Formula
    try:
        f = Formula(str(text).strip())
    except ValueError:
        return None
    return (f.reduce()[0] if reduce else f).count() if f.count() else None


def _check_system(settings: Settings, slab, ab, name_a: str, name_b: str) -> None:
    """PROJECT.md's metal, adsorbate and product name the compositions of the slab, of AB, and of A and B, or stop."""
    held = [("metal", settings.metal, slab.get_chemical_formula(mode="metal", empirical=True), True),
            ("adsorbate", settings.adsorbate, ab.get_chemical_formula(), False),
            ("product A", settings.product[0], name_a, False), ("product B", settings.product[1], name_b, False)]
    wrong = [f"{field} {named!r}, the inputs give {found}" for field, named, found, reduce in held
             if composition(named, reduce) is None or composition(named, reduce) != composition(found, reduce)]
    if wrong:
        raise SettingsMismatch("PROJECT.md and the inputs disagree: " + "; ".join(wrong) + ". Correct PROJECT.md, or the bond, A's side first")


def _same_bonds(slab, initial, n: int, graph, i: int, j: int) -> str:
    """Whether a surface operation of the slab maps each other bond of AB between the same two elements onto the
    named one, A's end onto A's end: breaking it then gives the same final states, else it is another cleavage."""
    sym = initial.get_chemical_symbols()
    named = (sym[n + i], sym[n + j])
    bonds = [(a, b) for a, b in graph if {a, b} != {i, j} and sorted((sym[n + a], sym[n + b])) == sorted(named)]
    if not bonds:
        return f"the named {named[0]}–{named[1]} bond is the only one of its kind in the adsorbate"
    perms = _adsorbate_symmetry(slab, initial, n)
    lines = []
    for a, b in bonds:
        ends = [(p, q) for p, q in ((a, b), (b, a)) if (sym[n + p], sym[n + q]) == named]
        mapped = any(perm[i] == p and perm[j] == q for perm in perms for p, q in ends)
        lines.append(f"the other {named[0]}–{named[1]}, atoms {a} and {b} of the adsorbate, maps onto the named one under "
                     + ("a surface operation of the slab: breaking it gives the same final states" if mapped
                        else "no surface operation of the slab: breaking it is another cleavage, not run in this study"))
    return "; ".join(lines)


def _adsorbate_symmetry(slab, initial, n: int) -> List[List[int]]:
    """The permutations of the adsorbate's atoms made by the operations of the slab that keep its surface on top and
    map the adsorbate of the initial state onto itself, species onto species, within SAME_POSITION_A."""
    import spglib
    lat = slab.cell.array
    data = spglib.get_symmetry_dataset((lat, slab.get_scaled_positions(), slab.numbers), symprec=SYMPREC_A)
    if data is None:
        return []
    pos, num = initial.positions[n:], initial.numbers[n:]
    out = []
    for r, t in zip(data.rotations, data.translations):
        rc = lat.T @ r @ np.linalg.inv(lat.T)
        if abs(rc[2, 2] - 1) > 1e-6 or not np.allclose([rc[2, 0], rc[2, 1], rc[0, 2], rc[1, 2]], 0, atol=1e-6) or abs((t[2] + 0.5) % 1 - 0.5) > 1e-6:
            continue                                     # the operation turns the slab over or moves it along the normal
        tc = lat.T @ t
        tc[2] = 0.0
        image = pos @ rc.T + tc
        d = np.linalg.norm(geometry.mic((image[:, None] - pos[None]).reshape(-1, 3), lat), axis=1).reshape(len(pos), len(pos))
        d[num[:, None] != num[None, :]] = np.inf
        perm = d.argmin(axis=1)
        if d[np.arange(len(pos)), perm].max() <= SAME_POSITION_A and len(set(perm.tolist())) == len(pos):
            out.append([int(k) for k in perm])
    return out


@traced(step="1", tool="calculation_protocol")
def calculation_protocol(settings_from_inputs: Settings, physics_choices: Dict[str, Any], protocol: str, protocol_reason: str) -> Settings:
    """Lock the numerical and physical settings in PROJECT.md from the inputs' settings, the human's physics choices and a verified protocol; never from the model's memory.

    Board steps: 1. Status: core. Lane: laptop. Allowed roles: computational-chemist.

    Inputs:
        settings_from_inputs: Settings, as read from the relaxed inputs
        physics_choices: dict from the human: functional, dispersion, spin, U, and a k-mesh when the human gives one
        protocol: mlip, no DFT runs | aiida_common_workflows | sssp | oc20
        protocol_reason: str, stated by the computational chemist
    Outputs:
        settings: Settings with locked False until the human approves
    Checks:
        - protocol mlip: no DFT setting is set or asked; the lock holds the selected cell, the force threshold, the gas references and the open decisions
        - a DFT protocol: cutoff, k-mesh, smearing, layers from the protocol table of AGENTS.md section 3, the k-mesh by the protocol's rule on the selected cell
        - if OC20NEB is the benchmark, RPBE and PAW as OC20
    Thresholds:
        convergence_target_meV: open: team decision: DFT only, asked when the study runs DFT
        gas_references: open: team decision
    Wraps:
        - aiida_common_workflows.workflows.relax.CommonRelaxWorkChain protocols
        - SSSP
        - pymatgen.io.vasp.sets.MPRelaxSet
    Logs: protocol and reason; every setting and its origin.

    Protocol mlip is the lock of a study that runs no DFT, every study until dft_single_points is built: the
    potential chosen at 1* computes every energy, so every DFT setting is cleared, none is reported, a physics
    choice other than spin is refused, and no DFT-only decision is asked. The lock holds the gas-reference
    species and no energy: the potential computes them after 1*. Each open decision with a single
    answer without DFT, frequencies from the potential, takes it. A DFT protocol locks as follows.

    The inputs' own settings win: the protocol fills only what they leave unset, and a physics choice that
    contradicts them stops the lock, since new physics needs new inputs. The k-mesh is the human's when
    physics_choices gives kmesh, three positive integers; else the protocol's rule on cell_A, the in-plane lengths
    of the selected cell: for oc20, 40 / length along each in-plane vector, rounded up, and one k-point along the
    vacuum. Without cell_A the k-mesh stays unset and the trace says why. Every setting reported gets its origin
    in origins: physics choice, the protocol, a decision, PROJECT.md before the lock, or unset; the human confirms
    each at approve settings. Every open threshold of the
    registry must be set before the lock, so no tool meets an open decision after it. Writes the run's
    PROJECT.md, unlocked.
    """
    if protocol not in PROTOCOLS:
        raise ValueError(f"protocol {protocol!r}; known: {', '.join(PROTOCOLS)}")
    if not (protocol_reason or "").strip():
        raise ValueError("the computational chemist states why this protocol, in one sentence")
    dft = runs_dft(protocol)
    s = settings_from_inputs.model_copy(deep=True)
    origin: Dict[str, str] = {}
    choices = {"spin": "spin_polarised", "U": "hubbard_u",
               **{k: k for k in ("functional", "dispersion", "spin_polarised", "initial_moments", "hubbard_u", "kmesh")}}
    for key, value in (physics_choices or {}).items():
        field = choices.get(key)
        if field is None:
            raise ValueError(f"physics choice {key!r}; known: functional, dispersion, spin, initial_moments, U, kmesh")
        if not dft and key not in NO_DFT_CHOICES:
            raise ValueError(f"physics choice {key!r} is a DFT setting and protocol {NO_DFT} runs no DFT; "
                             "a study that runs DFT names oc20, sssp or aiida_common_workflows")
        if field == "kmesh":
            value = _kmesh(value)
        held = getattr(s, field)
        if held not in (None, {}, False) and held != value:
            raise SettingsMismatch(f"check 8: the inputs were computed with {field} = {held!r}, the choice is {value!r}; new physics needs new inputs")
        setattr(s, field, value)
        origin[field] = "physics choice"
    for field, value in PROTOCOLS[protocol].items():
        held = getattr(s, field)
        if held is None:
            setattr(s, field, value)
            origin[field] = f"protocol {protocol}"
        elif held != value:
            if field in MUST_MATCH.get(protocol, ()):
                raise SettingsMismatch(f"check 8: protocol {protocol} needs {field} = {value!r} to match the benchmark; the inputs have {held!r}")
            origin[field] = f"{FOUND}; protocol {protocol} says {value!r}"
    rule, kmesh_unset = KMESH_RULE_A.get(protocol), ""
    if rule is not None and s.cell_A:
        mesh = tuple(max(1, math.ceil(rule / float(length) - 1e-9)) for length in s.cell_A) + (1,)   # 1e-9 absorbs float noise
        if s.kmesh is None:
            s.kmesh = mesh
            origin["kmesh"] = f"protocol {protocol}: {rule:g} / in-plane length, Γ-centred, one along the vacuum"
        elif "kmesh" not in origin and tuple(s.kmesh) != mesh:
            origin["kmesh"] = f"{FOUND}; protocol {protocol} says {mesh}"
    elif rule is not None and s.kmesh is None:
        kmesh_unset = (f"kmesh unset: cell_A, the in-plane lengths of the selected cell, is not known, so the protocol {protocol} "
                       f"rule of {rule:g} / in-plane length cannot apply")
    cleared: List[str] = []
    if dft:
        s.convergence_target_meV = float(project.decision("calculation_protocol", "convergence_target_meV", s))
        origin["convergence_target_meV"] = "decision calculation_protocol.convergence_target_meV"
    else:
        cleared = [f for f in DFT_SETTINGS if getattr(s, f) not in (None, {})]
        for f in DFT_SETTINGS:
            setattr(s, f, {} if f == "hubbard_u" else None)
        for key, answer in WITHOUT_DFT.items():
            given = s.decisions.get(key)
            if given not in (None, answer):
                raise SettingsMismatch(f"{key} = {given!r} needs DFT; protocol {NO_DFT} runs none, so it is {answer!r}")
            s.decisions[key] = answer
    wanted = list(project.decision("calculation_protocol", "gas_references", s))
    if dft:
        held = [composition(g.species) or g.species for g in s.gas_references]
        absent = [sp for sp in wanted if (composition(sp) or sp) not in held]       # OH is held by a reference named HO
        if absent:
            raise OpenDecision(f"gas reference energies missing in PROJECT.md for {', '.join(absent)}")
    else:       # the lock holds the species; the potential chosen at 1* computes their energies, and no file's energy is used
        cleared += ["gas_references"] if s.gas_references else []
        s.gas_references = []
        origin["gas_references"] = f"decision calculation_protocol.gas_references, {', '.join(wanted) or 'none'}: computed with the potential chosen at 1*"
    missing = project.missing_decisions(s, dft=dft)
    if missing:
        raise OpenDecision("set before the lock, under decisions in PROJECT.md: " + ", ".join(missing))
    reported = REPORTED if dft else RUN_SETTINGS + tuple(f for f in ("spin_polarised", "initial_moments") if f in origin)
    s.origins = {f: origin.get(f) or (FOUND if getattr(s, f) not in (None, {}, []) else "unset") for f in reported}
    s.protocol, s.protocol_reason = protocol, protocol_reason
    s.locked, s.approved_by, s.approved_at = False, None, None

    run = current_run()
    if run:
        path = run.dir / "PROJECT.md"
        if path.exists() and project.read(path).locked:
            raise FragPlaceError(f"{path} is locked; a new value means a new study")
        project.write(path, s)
    log("calculation_protocol", f"protocol {protocol}: {protocol_reason}")
    log("calculation_protocol", "origins: " + "; ".join(f"{k} {v}" for k, v in s.origins.items()))
    if not dft:
        log("calculation_protocol", "no DFT runs: the potential chosen at 1* computes every energy, and the lock holds no DFT setting"
            + (f"; cleared {', '.join(cleared)}" if cleared else ""))
        return s
    if kmesh_unset:
        log("calculation_protocol", kmesh_unset)
    unset: List[str] = [f for f in ("cutoff_eV", "kmesh", "smearing", "sigma_eV", "layers", "pseudopotential_family") if getattr(s, f) is None]
    if unset:
        log("calculation_protocol", "unset, needed only by DFT single points: " + ", ".join(unset))
    return s


def _kmesh(value) -> Tuple[int, int, int]:
    """A k-mesh as the human gives it: three positive integers."""
    if isinstance(value, (list, tuple)) and len(value) == 3 and all(isinstance(k, int) and not isinstance(k, bool) and k > 0 for k in value):
        return (int(value[0]), int(value[1]), int(value[2]))
    raise ValueError(f"kmesh {value!r}: give three positive integers, such as [3, 3, 1]")
