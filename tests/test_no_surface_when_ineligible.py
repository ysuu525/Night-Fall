from __future__ import annotations

import asyncio
from datetime import timedelta

from night_fall.config import NightFallConfig
from night_fall.metadata import now_utc, new_dream_id
from night_fall.storage import DreamStorage
from night_fall.tool import night_fall_tool


def _meta(generated_at: str) -> dict:
    return {
        "dream_id": new_dream_id(),
        "generated_at": generated_at,
        "dream_mode": "fragmentary",
        "core_affect": {"valence": 0.40, "arousal": 0.50},
        "source_bucket_ids": ["bucket_a"],
        "imagery_fragments": [{"source_bucket_id": "bucket_a", "excerpt": "..."}],
        "surfaced": False,
        "surfaced_at": None,
        "spontaneous": None,
        "surface_attempts": 0,
        "recall_cues": ["语境一", "语境二"],
    }


class _Server:
    embedding_engine = None


def test_ineligible_breath_does_not_consume_attempts(tmp_path):
    """A pure no-arg breath must not consume any dream's chance to be remembered.
    Spec section 5 DESIGN INTENT."""
    storage = DreamStorage(tmp_path / "dreams", tmp_path / "logs")
    four_hours_ago = (now_utc() - timedelta(hours=4)).isoformat()
    record = storage.write(_meta(four_hours_ago), "dream")

    cfg = NightFallConfig(repo_root=tmp_path, ombre_home=None, data_dir=tmp_path)
    response = asyncio.run(
        night_fall_tool(_Server(), cfg, action="surface")
    )

    assert response.startswith("Breath not contextual")

    refreshed = storage.read(record.path)
    assert refreshed.metadata["surface_attempts"] == 0
    assert refreshed.metadata["surfaced"] is False


def test_ineligible_breath_with_many_dreams_leaves_all_untouched(tmp_path):
    storage = DreamStorage(tmp_path / "dreams", tmp_path / "logs")
    four_hours_ago = (now_utc() - timedelta(hours=4)).isoformat()
    records = [storage.write(_meta(four_hours_ago), f"dream {i}") for i in range(5)]

    cfg = NightFallConfig(repo_root=tmp_path, ombre_home=None, data_dir=tmp_path)
    asyncio.run(night_fall_tool(_Server(), cfg, action="surface"))

    for record in records:
        refreshed = storage.read(record.path)
        assert refreshed.metadata["surface_attempts"] == 0
