from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

from night_fall.config import NightFallConfig
from night_fall.metadata import now_utc, new_dream_id
from night_fall.storage import DreamStorage
from night_fall.surfacing import choose_surface_candidate
from night_fall.tool import night_fall_tool


def _cfg(tmp_path, **kwargs) -> NightFallConfig:
    base = NightFallConfig(repo_root=tmp_path, ombre_home=None, data_dir=tmp_path)
    return replace(base, **kwargs)


def _metadata(generated_at: str) -> dict:
    return {
        "dream_id": new_dream_id(),
        "generated_at": generated_at,
        "dream_mode": "fragmentary",
        "core_affect": {"valence": 0.30, "arousal": 0.60},
        "source_bucket_ids": ["bucket_a"],
        "imagery_fragments": [
            {"source_bucket_id": "bucket_a", "excerpt": "a red door under rain"}
        ],
        "surfaced": False,
        "surfaced_at": None,
        "spontaneous": None,
        "surface_attempts": 0,
    }


def test_dream_cannot_surface_before_three_hours(tmp_path):
    storage = DreamStorage(tmp_path / "dreams", tmp_path / "logs")
    now = now_utc()
    storage.write(_metadata((now - timedelta(hours=2, minutes=59)).isoformat()), "dream")

    eligible, candidate, spontaneous = choose_surface_candidate(
        storage.list(),
        _cfg(tmp_path),
        now,
        current_valence=0.30,
        current_arousal=0.60,
        current_motifs="red door rain",
    )

    assert candidate is None
    assert spontaneous is False
    assert eligible == []


def test_affect_resonance_can_surface_after_three_hours(tmp_path):
    storage = DreamStorage(tmp_path / "dreams", tmp_path / "logs")
    now = now_utc()
    storage.write(_metadata((now - timedelta(hours=4)).isoformat()), "dream")

    eligible, candidate, spontaneous = choose_surface_candidate(
        storage.list(),
        _cfg(tmp_path),
        now,
        current_valence=0.32,
        current_arousal=0.62,
        current_motifs="red door",
    )

    assert candidate is not None
    assert spontaneous is False
    assert len(eligible) == 1


def test_missing_current_affect_does_not_surface_before_spontaneous_window(tmp_path):
    storage = DreamStorage(tmp_path / "dreams", tmp_path / "logs")
    now = now_utc()
    storage.write(_metadata((now - timedelta(hours=6)).isoformat()), "dream")

    eligible, candidate, spontaneous = choose_surface_candidate(
        storage.list(),
        _cfg(tmp_path),
        now,
        current_valence=-1,
        current_arousal=-1,
        current_motifs="red door",
    )

    assert candidate is None
    assert spontaneous is False
    assert len(eligible) == 1


def test_spontaneous_surface_after_24h_is_testable(tmp_path, monkeypatch):
    storage = DreamStorage(tmp_path / "dreams", tmp_path / "logs")
    now = now_utc()
    storage.write(_metadata((now - timedelta(hours=25)).isoformat()), "dream")
    monkeypatch.setattr("night_fall.surfacing.random.random", lambda: 0.0)

    eligible, candidate, spontaneous = choose_surface_candidate(
        storage.list(),
        _cfg(tmp_path, spontaneous_chance=0.02),
        now,
        current_valence=-1,
        current_arousal=-1,
        current_motifs="",
    )

    assert candidate is not None
    assert spontaneous is True


def test_surface_action_updates_metadata(tmp_path):
    storage = DreamStorage(tmp_path / "dreams", tmp_path / "logs")
    now = now_utc()
    record = storage.write(_metadata((now - timedelta(hours=4)).isoformat()), "I saw the door.")

    response = __import__("asyncio").run(
        night_fall_tool(
            ombre_server=object(),
            cfg=_cfg(tmp_path),
            action="surface",
            current_valence=0.30,
            current_arousal=0.60,
        )
    )

    surfaced = storage.read(record.path)
    assert "A dream surfaced." in response
    assert "source_bucket_ids" not in response
    assert surfaced.metadata["surfaced"] is True
    assert surfaced.metadata["spontaneous"] is False
    assert surfaced.metadata["surfaced_at"]
    assert surfaced.metadata["surface_attempts"] >= 1


def test_surface_with_no_dreams_returns_nothing_surfaced(tmp_path):
    response = __import__("asyncio").run(
        night_fall_tool(
            ombre_server=object(),
            cfg=_cfg(tmp_path),
            action="surface",
            current_valence=0.30,
            current_arousal=0.60,
        )
    )

    assert response == "No latent dream surfaced."


def test_already_surfaced_dream_is_not_selected_again(tmp_path):
    storage = DreamStorage(tmp_path / "dreams", tmp_path / "logs")
    now = now_utc()
    meta = _metadata((now - timedelta(hours=4)).isoformat())
    meta["surfaced"] = True
    meta["surfaced_at"] = now.isoformat()
    storage.write(meta, "Already surfaced dream.")

    eligible, candidate, spontaneous = choose_surface_candidate(
        storage.list(),
        _cfg(tmp_path),
        now,
        current_valence=0.30,
        current_arousal=0.60,
        current_motifs="",
    )

    assert candidate is None
    assert eligible == []


def test_surface_attempts_incremented_for_all_evaluated_dreams(tmp_path):
    storage = DreamStorage(tmp_path / "dreams", tmp_path / "logs")
    now = now_utc()
    # Resonant dream (will be selected)
    meta_a = _metadata((now - timedelta(hours=4)).isoformat())
    record_a = storage.write(meta_a, "Dream A")
    # Non-resonant dream (evaluated but not selected)
    meta_b = _metadata((now - timedelta(hours=5)).isoformat())
    meta_b["core_affect"] = {"valence": 0.01, "arousal": 0.01}
    record_b = storage.write(meta_b, "Dream B")

    __import__("asyncio").run(
        night_fall_tool(
            ombre_server=object(),
            cfg=_cfg(tmp_path),
            action="surface",
            current_valence=0.30,
            current_arousal=0.60,
        )
    )

    a = storage.read(record_a.path)
    b = storage.read(record_b.path)
    assert a.metadata["surface_attempts"] == 1
    assert b.metadata["surface_attempts"] == 1
