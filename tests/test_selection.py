from __future__ import annotations

import asyncio
from datetime import timedelta

from night_fall.metadata import now_utc
from night_fall.selection import select_buckets


def _bucket(bucket_id: str, age_days: int, **metadata):
    meta = {
        "id": bucket_id,
        "created": (now_utc() - timedelta(days=age_days)).isoformat(),
        "type": "dynamic",
    }
    meta.update(metadata)
    return {"id": bucket_id, "content": f"content for {bucket_id}", "metadata": meta}


class Adapter:
    def __init__(self, buckets):
        self.buckets = buckets

    async def list_candidate_buckets(self):
        return self.buckets


def test_selection_returns_three_to_five_unique_buckets():
    buckets = [
        _bucket("recent_hot", 1, valence=0.25, arousal=0.9, importance=7, resolved=False, digested=False),
        _bucket("recent_second", 2, valence=0.35, arousal=0.7, importance=6, resolved=False),
        _bucket("affect_old", 8, valence=0.28, arousal=0.82, importance=8),
        _bucket("remote_echo", 30, valence=0.30, arousal=0.75, importance=9),
        _bucket("other", 12, valence=0.9, arousal=0.1, importance=3),
    ]

    selected = asyncio.run(select_buckets(Adapter(buckets), limit=5, current_valence=-1, current_arousal=-1))

    selected_ids = [bucket["id"] for bucket in selected]
    assert 3 <= len(selected_ids) <= 5
    assert len(selected_ids) == len(set(selected_ids))
    assert "recent_hot" in selected_ids
    assert "affect_old" in selected_ids
    assert "remote_echo" in selected_ids


def test_selection_handles_missing_metadata_without_crashing():
    buckets = [
        {"id": "a", "content": "alpha", "metadata": {"id": "a"}},
        {"id": "b", "content": "beta", "metadata": {"id": "b", "created": now_utc().isoformat()}},
        _bucket("c", 20, importance=8),
    ]

    selected = asyncio.run(select_buckets(Adapter(buckets), limit=5, current_valence=-1, current_arousal=-1))

    assert len(selected) == 3
    assert {bucket["id"] for bucket in selected} == {"a", "b", "c"}


def test_selection_skips_when_fewer_than_two_candidates():
    selected = asyncio.run(select_buckets(Adapter([_bucket("only", 1)]), limit=5, current_valence=-1, current_arousal=-1))

    assert selected == []
