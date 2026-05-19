from __future__ import annotations

import asyncio
from datetime import timedelta

from night_fall.config import NightFallConfig
from night_fall.metadata import now_utc, new_dream_id
from night_fall.storage import DreamStorage
from night_fall.tool import get_surfaceable_dream


def _meta(generated_at: str) -> dict:
    return {
        "dream_id": new_dream_id(),
        "generated_at": generated_at,
        "dream_mode": "integrative",
        "core_affect": {"valence": 0.40, "arousal": 0.50},
        "source_bucket_ids": ["bucket_a"],
        "imagery_fragments": [{"source_bucket_id": "bucket_a", "excerpt": "..."}],
        "surfaced": False,
        "surfaced_at": None,
        "spontaneous": None,
        "surface_attempts": 0,
        "recall_cues": ["一个 cue"],
    }


class _Server:
    embedding_engine = None


def _cfg(tmp_path) -> NightFallConfig:
    return NightFallConfig(repo_root=tmp_path, ombre_home=None, data_dir=tmp_path)


def test_returns_none_when_pool_empty(tmp_path):
    cfg = _cfg(tmp_path)
    DreamStorage(cfg.dreams_dir, cfg.logs_dir)  # create dirs
    result = asyncio.run(get_surfaceable_dream(_Server(), cfg))
    assert result is None


def test_skips_dreams_inside_latency_window(tmp_path):
    cfg = _cfg(tmp_path)
    storage = DreamStorage(cfg.dreams_dir, cfg.logs_dir)
    one_hour_ago = (now_utc() - timedelta(hours=1)).isoformat()
    storage.write(_meta(one_hour_ago), "Too young to surface.")

    result = asyncio.run(get_surfaceable_dream(_Server(), cfg))
    assert result is None
    # Dream is still on disk untouched.
    assert len(list(cfg.dreams_dir.glob("dream_*.md"))) == 1


def test_picks_newest_pending_past_latency(tmp_path):
    cfg = _cfg(tmp_path)
    storage = DreamStorage(cfg.dreams_dir, cfg.logs_dir)
    older = (now_utc() - timedelta(hours=10)).isoformat()
    newer = (now_utc() - timedelta(hours=4)).isoformat()

    meta_old = _meta(older)
    meta_old["dream_id"] = "dream_old"
    storage.write(meta_old, "Older dream body.")

    meta_new = _meta(newer)
    meta_new["dream_id"] = "dream_new"
    storage.write(meta_new, "Newer dream body.")

    result = asyncio.run(get_surfaceable_dream(_Server(), cfg))
    assert result is not None
    assert "=== 浮上来的梦 ===" in result
    assert "dream_new" in result
    assert "Newer dream body." in result
    # Older one is still pending on disk; only the picked one is destroyed.
    remaining = list(cfg.dreams_dir.glob("dream_*.md"))
    assert len(remaining) == 1
    assert remaining[0].stem == "dream_old"


def test_surfaced_dream_does_not_resurface(tmp_path):
    cfg = _cfg(tmp_path)
    storage = DreamStorage(cfg.dreams_dir, cfg.logs_dir)
    four_hours_ago = (now_utc() - timedelta(hours=4)).isoformat()
    storage.write(_meta(four_hours_ago), "A single dream.")

    first = asyncio.run(get_surfaceable_dream(_Server(), cfg))
    second = asyncio.run(get_surfaceable_dream(_Server(), cfg))

    assert first is not None and "=== 浮上来的梦 ===" in first
    assert second is None
