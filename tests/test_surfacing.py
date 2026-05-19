from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import timedelta

from night_fall.config import NightFallConfig
from night_fall.metadata import now_utc, new_dream_id
from night_fall.storage import DreamStorage
from night_fall.tool import night_fall_tool


def _cfg(tmp_path, **kwargs) -> NightFallConfig:
    base = NightFallConfig(repo_root=tmp_path, ombre_home=None, data_dir=tmp_path)
    return replace(base, **kwargs)


def _metadata(generated_at: str, **overrides) -> dict:
    meta = {
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
        "recall_cues": ["独自归家的迟疑", "湿润季节的傍晚"],
    }
    meta.update(overrides)
    return meta


class _Server:
    """Bare server stub — no embedding engine, no LLM. Surface flows that only
    exercise the affect channel work fine without these."""

    def __init__(self):
        self.embedding_engine = None


def _surface(tmp_path, **kwargs) -> str:
    cfg = _cfg(tmp_path)
    return asyncio.run(night_fall_tool(_Server(), cfg, action="surface", **kwargs))


def test_dream_cannot_surface_before_min_surface_age(tmp_path):
    storage = DreamStorage(tmp_path / "dreams", tmp_path / "logs")
    now = now_utc()
    storage.write(_metadata((now - timedelta(hours=2, minutes=59)).isoformat()), "dream")

    response = _surface(tmp_path, current_valence=0.30, current_arousal=0.60)

    # The dream is still under the latency floor — nothing should surface and
    # the dream must still exist on disk.
    assert response == "No latent dream surfaced."
    assert len(list((tmp_path / "dreams").glob("dream_*.md"))) == 1


def test_affect_channel_alone_can_surface(tmp_path):
    storage = DreamStorage(tmp_path / "dreams", tmp_path / "logs")
    now = now_utc()
    storage.write(_metadata((now - timedelta(hours=4)).isoformat()), "dream")

    response = _surface(tmp_path, current_valence=0.31, current_arousal=0.61)

    # Single-channel affect resonance is enough under the max+α*min rule.
    assert "=== 浮上来的梦 ===" in response
    assert "spontaneous: false" in response


def test_ineligible_breath_does_nothing(tmp_path):
    storage = DreamStorage(tmp_path / "dreams", tmp_path / "logs")
    now = now_utc()
    record = storage.write(_metadata((now - timedelta(hours=6)).isoformat()), "dream")

    response = _surface(tmp_path)  # no query, no affect, not session_start

    assert response.startswith("Breath not contextual")
    refreshed = storage.read(record.path)
    assert refreshed.metadata["surface_attempts"] == 0


def test_session_start_eligible_even_without_query_or_affect(tmp_path):
    """is_session_start=true makes a no-arg breath eligible; without resonance
    the dream still does not surface, but eligibility was passed."""
    storage = DreamStorage(tmp_path / "dreams", tmp_path / "logs")
    now = now_utc()
    storage.write(_metadata((now - timedelta(hours=4)).isoformat()), "dream")

    response = _surface(tmp_path, is_session_start=True)

    assert response != "Breath not contextual — no dream surfacing this turn."


def test_spontaneous_surface_under_low_random(tmp_path, monkeypatch):
    storage = DreamStorage(tmp_path / "dreams", tmp_path / "logs")
    now = now_utc()
    storage.write(_metadata((now - timedelta(hours=10)).isoformat()), "dream")
    # Force spontaneous to fire and force affect to miss the surface threshold.
    monkeypatch.setattr("night_fall.tool.random.random", lambda: 0.0)

    response = _surface(tmp_path, is_session_start=True)

    assert "=== 浮上来的梦 ===" in response
    assert "spontaneous: true" in response


def test_already_surfaced_dreams_filtered_out(tmp_path):
    """If a dream metadata says surfaced=true (shouldn't normally happen after
    v2 destruction, but possible during migration), it must not resurface."""
    storage = DreamStorage(tmp_path / "dreams", tmp_path / "logs")
    now = now_utc()
    meta = _metadata((now - timedelta(hours=4)).isoformat())
    meta["surfaced"] = True
    meta["surfaced_at"] = now.isoformat()
    storage.write(meta, "Already surfaced.")

    response = _surface(tmp_path, current_valence=0.30, current_arousal=0.60)

    assert response == "No latent dream surfaced."


def test_surface_with_no_dreams_returns_nothing(tmp_path):
    response = _surface(tmp_path, current_valence=0.30, current_arousal=0.60)
    assert response == "No latent dream surfaced."
