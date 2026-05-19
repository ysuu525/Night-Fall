from __future__ import annotations

import asyncio
import json
from datetime import timedelta

from night_fall.config import NightFallConfig
from night_fall.metadata import now_utc, new_dream_id
from night_fall.storage import DreamStorage
from night_fall.tool import night_fall_tool


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
        "recall_cues": ["独自归家的迟疑", "湿润季节的傍晚"],
    }


class _Server:
    embedding_engine = None


def test_surfaced_dream_is_physically_destroyed(tmp_path):
    storage = DreamStorage(tmp_path / "dreams", tmp_path / "logs")
    four_hours_ago = (now_utc() - timedelta(hours=4)).isoformat()
    record = storage.write(_meta(four_hours_ago), "I walked into the rain.")

    cfg = NightFallConfig(repo_root=tmp_path, ombre_home=None, data_dir=tmp_path)
    response = asyncio.run(
        night_fall_tool(
            _Server(), cfg, action="surface",
            current_valence=0.40, current_arousal=0.50,
        )
    )

    # Response carries the dream content through the dedicated channel
    assert "=== 浮上来的梦 ===" in response
    assert "I walked into the rain." in response

    # File is gone
    assert not record.path.exists()
    assert list((tmp_path / "dreams").glob("dream_*.md")) == []

    # Event log records the lifecycle
    log_lines = (tmp_path / "logs" / "events.jsonl").read_text(encoding="utf-8").splitlines()
    events = [json.loads(line) for line in log_lines]
    surfaced_events = [e for e in events if e["event"] == "surfaced"]
    deleted_events = [e for e in events if e["event"] == "deleted"]
    assert len(surfaced_events) == 1
    assert surfaced_events[0]["dream_id"] == record.dream_id
    assert surfaced_events[0]["spontaneous"] is False
    assert any(e["deletion_reason"] == "surfaced_one_shot" for e in deleted_events)


def test_surfaced_dream_cannot_resurface(tmp_path):
    """After one surface, subsequent surface calls find no pending dream."""
    storage = DreamStorage(tmp_path / "dreams", tmp_path / "logs")
    four_hours_ago = (now_utc() - timedelta(hours=4)).isoformat()
    storage.write(_meta(four_hours_ago), "The hallway echoed.")

    cfg = NightFallConfig(repo_root=tmp_path, ombre_home=None, data_dir=tmp_path)

    first = asyncio.run(
        night_fall_tool(
            _Server(), cfg, action="surface",
            current_valence=0.40, current_arousal=0.50,
        )
    )
    second = asyncio.run(
        night_fall_tool(
            _Server(), cfg, action="surface",
            current_valence=0.40, current_arousal=0.50,
        )
    )

    assert "=== 浮上来的梦 ===" in first
    assert second == "No latent dream surfaced."


def test_status_counts_surfaced_from_event_log(tmp_path):
    storage = DreamStorage(tmp_path / "dreams", tmp_path / "logs")
    four_hours_ago = (now_utc() - timedelta(hours=4)).isoformat()
    storage.write(_meta(four_hours_ago), "One.")
    storage.write(_meta(four_hours_ago), "Two.")

    cfg = NightFallConfig(repo_root=tmp_path, ombre_home=None, data_dir=tmp_path)

    # Surface twice. Each call destroys its picked dream so the on-disk count
    # would lose the historical signal — status() must read the event log.
    asyncio.run(night_fall_tool(_Server(), cfg, action="surface", current_valence=0.40, current_arousal=0.50))
    asyncio.run(night_fall_tool(_Server(), cfg, action="surface", current_valence=0.40, current_arousal=0.50))

    status = asyncio.run(night_fall_tool(_Server(), cfg, action="status"))
    assert "surfaced dreams: 2" in status
    assert "pending dreams: 0" in status
