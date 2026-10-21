"""Records round-trip; the run directory, cache, checkpoints and case bank behave."""
import json
from pathlib import Path

import pytest

from fragplace.runtime import checkpoints, project as config
from fragplace.runtime.cache import Cache
from fragplace.memory.casebank import SEED, CaseBank
from fragplace.errors import CheckpointPending, SettingsNotLocked
from fragplace.runtime.journal import Run, content_hash, set_run, traced
from fragplace.schemas.records import CheckVerdict, DescriptorCard, HumanChoice, Settings


def settings():
    return Settings(metal="Pt", facet="111", adsorbate="OH", product=("O", "H"), functional="RPBE", cutoff_eV=350.0,
                    kmesh=(4, 4, 1), smearing="MP", sigma_eV=0.1, layers=4, fixed_layers=2, vacuum_A=15.0)


def test_descriptor_card_text_carries_site_distances_and_verdicts():
    card = DescriptorCard(candidate_id="c1", composition="Pt36OH", cell="3x3", facet="111", layers=4, vacuum_A=15, fixed_layers=2,
                          site_label="fcc", point_group="C3v", coordination=3, height_A=1.9, nn_distances_A=[2.1, 2.1, 2.1],
                          AB_distance_A=2.8, site_graph_distance=1,
                          verdicts=[CheckVerdict(check_id=10, name="bond re-formed", passed=True, reason="")])
    text = card.text()
    assert "fcc" in text and "2.80" in text and "check 10" in text


def test_project_lock_round_trip(tmp_path: Path):
    s = settings()
    with pytest.raises(SettingsNotLocked):
        config.require_locked(s)
    locked = config.lock(s, approved_by="team")
    config.write(tmp_path / "PROJECT.md", locked)
    back = config.read(tmp_path / "PROJECT.md")
    assert back.locked and back.approved_by == "team"
    assert config.settings_hash(back) == config.settings_hash(locked)


def test_run_trace_and_traced_decorator(tmp_path: Path):
    run = Run(tmp_path, "test")
    set_run(run)

    @traced(step="2", tool="site_enumeration")
    def fake(slab: str) -> dict:
        return {"count": 3}

    fake("slab.xyz")
    events = run.events()
    assert len(events) == 1 and events[0].tool == "site_enumeration" and events[0].outputs_ref.startswith("structures/")
    with pytest.raises(RuntimeError):
        @traced(step="2", tool="site_enumeration")
        def bad(slab: str):
            raise RuntimeError("boom")
        bad("x")
    assert run.events()[-1].message.startswith("error")
    set_run(None)


def test_cache_keys_change_with_settings(tmp_path: Path):
    c = Cache(tmp_path)
    k1 = c.key("s", "uma", "h1", "relax"); k2 = c.key("s", "uma", "h2", "relax")
    assert k1 != k2
    c.put(k1, {"energy": -1.0})
    assert c.get(k1) == {"energy": -1.0} and c.get(k2) is None


def test_checkpoints_block_until_recorded(tmp_path: Path):
    with pytest.raises(CheckpointPending):
        checkpoints.require(tmp_path, "approve settings")
    checkpoints.record(tmp_path, HumanChoice(checkpoint="approve settings", chosen=[], reason="ok", who="team"))
    assert checkpoints.require(tmp_path, "approve settings").who == "team"
    with pytest.raises(ValueError):
        checkpoints.require(tmp_path, "not a checkpoint")


def test_casebank_round_trip(tmp_path: Path):
    bank = CaseBank(tmp_path / "lessons.md")
    for c in SEED:
        bank.add(c)
    assert len(bank.all()) == 3
    assert bank.retrieve(system="Ni")[0].correction.startswith("set initial magnetic")
    assert bank.retrieve(failure="symmetry trap")


def test_content_hash_is_stable():
    assert content_hash({"a": 1, "b": [1, 2]}) == content_hash({"b": [1, 2], "a": 1})
