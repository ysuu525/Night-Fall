from __future__ import annotations

from datetime import timedelta

import pytest

from night_fall.metadata import now_utc, new_dream_id
from night_fall.storage import DreamStorage


def _metadata(generated_at: str) -> dict:
    return {
        "dream_id": new_dream_id(),
        "generated_at": generated_at,
        "dream_mode": "integrative",
        "core_affect": {"valence": 0.31, "arousal": 0.58},
        "source_bucket_ids": ["bucket_a"],
        "imagery_fragments": [
            {"source_bucket_id": "bucket_a", "excerpt": "water entered the sponge"}
        ],
        "surfaced": False,
        "surfaced_at": None,
        "spontaneous": None,
        "surface_attempts": 0,
    }


def test_storage_preserves_schema_and_excerpt(tmp_path):
    storage = DreamStorage(tmp_path / "dreams", tmp_path / "logs")
    record = storage.write(_metadata(now_utc().isoformat()), "I dreamed.")

    loaded = storage.read(record.path)

    assert {
        "dream_id",
        "generated_at",
        "dream_mode",
        "core_affect",
        "source_bucket_ids",
        "imagery_fragments",
        "surfaced",
        "surfaced_at",
        "spontaneous",
        "surface_attempts",
    }.issubset(loaded.metadata)
    assert "deletion_scheduled_at" not in loaded.metadata
    assert "surface_score" not in loaded.metadata
    assert "dream_charge" not in loaded.metadata
    assert loaded.metadata["imagery_fragments"][0] == {
        "source_bucket_id": "bucket_a",
        "excerpt": "water entered the sponge",
    }
    assert loaded.metadata["surface_attempts"] == 0
    assert loaded.body == "I dreamed."


def test_forbidden_metadata_is_rejected(tmp_path):
    storage = DreamStorage(tmp_path / "dreams", tmp_path / "logs")
    metadata = _metadata(now_utc().isoformat())
    metadata["deletion_scheduled_at"] = "never"

    with pytest.raises(ValueError):
        storage.write(metadata, "I dreamed.")


def test_cleanup_exhausted_deletes_after_4_attempts(tmp_path):
    storage = DreamStorage(tmp_path / "dreams", tmp_path / "logs")
    now = now_utc()
    meta = _metadata(now.isoformat())
    meta["surface_attempts"] = 4
    storage.write(meta, "I dreamed.")

    deleted = storage.cleanup_exhausted()

    assert deleted == 1
    assert storage.list() == []
    assert storage.status(now)["deleted"] == 1


def test_cleanup_exhausted_spares_dreams_below_threshold(tmp_path):
    storage = DreamStorage(tmp_path / "dreams", tmp_path / "logs")
    now = now_utc()
    meta = _metadata(now.isoformat())
    meta["surface_attempts"] = 3
    storage.write(meta, "I dreamed.")

    deleted = storage.cleanup_exhausted()

    assert deleted == 0
    assert len(storage.list()) == 1
