from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math

from .metadata import clamp01, parse_dt


@dataclass(frozen=True)
class NormalizedBucket:
    bucket: dict
    bucket_id: str
    age_days: float
    normalized_valence: float
    normalized_arousal: float
    recent_score: float
    unresolved_score: float
    undigested_like_score: float
    importance_score: float

    @property
    def emotional_intensity(self) -> float:
        return self.normalized_arousal


def bucket_id(bucket: dict) -> str:
    return str(bucket.get("id") or bucket.get("metadata", {}).get("id") or "")


def _age_days(meta: dict, now: datetime) -> float:
    created = meta.get("created") or meta.get("generated_at")
    if not created:
        return 3650.0
    try:
        return max(0.0, (now - parse_dt(str(created))).total_seconds() / 86400)
    except Exception:
        return 3650.0


def _has_field(meta: dict, name: str) -> bool:
    return name in meta and meta.get(name) is not None


def normalize_bucket(bucket: dict, now: datetime) -> NormalizedBucket:
    meta = bucket.get("metadata", {}) or {}
    age = _age_days(meta, now)
    resolved = bool(meta.get("resolved", False)) if _has_field(meta, "resolved") else False
    digested = bool(meta.get("digested", False)) if _has_field(meta, "digested") else True
    return NormalizedBucket(
        bucket=bucket,
        bucket_id=bucket_id(bucket),
        age_days=age,
        normalized_valence=clamp01(meta.get("valence", 0.5)),
        normalized_arousal=clamp01(meta.get("arousal", 0.3), 0.3),
        recent_score=math.exp(-age / 3.0),
        unresolved_score=0.0 if resolved else 1.0,
        undigested_like_score=1.0 if _has_field(meta, "digested") and not digested else 0.0,
        importance_score=clamp01(float(meta.get("importance", 5)) / 10.0, 0.5),
    )


def affect_similarity(bucket: NormalizedBucket, seed_valence: float, seed_arousal: float) -> float:
    distance = math.sqrt(
        (bucket.normalized_valence - seed_valence) ** 2
        + (bucket.normalized_arousal - seed_arousal) ** 2
    ) / math.sqrt(2)
    return max(0.0, 1.0 - distance)


def day_residue_score(bucket: NormalizedBucket) -> float:
    return (
        0.45 * bucket.recent_score
        + 0.30 * bucket.emotional_intensity
        + 0.15 * bucket.unresolved_score
        + 0.10 * bucket.undigested_like_score
    )


def affect_echo_score(bucket: NormalizedBucket, seed_valence: float, seed_arousal: float) -> float:
    return (
        0.75 * affect_similarity(bucket, seed_valence, seed_arousal)
        + 0.15 * bucket.importance_score
        + 0.10 * bucket.emotional_intensity
    )


def remote_echo_score(bucket: NormalizedBucket, seed_valence: float, seed_arousal: float) -> float:
    return (
        0.60 * affect_similarity(bucket, seed_valence, seed_arousal)
        + 0.25 * bucket.importance_score
        + 0.15 * bucket.emotional_intensity
    )


def _append_unique(selected: list[NormalizedBucket], candidates: list[NormalizedBucket], count: int) -> None:
    seen = {item.bucket_id for item in selected}
    for candidate in candidates:
        if not candidate.bucket_id or candidate.bucket_id in seen:
            continue
        selected.append(candidate)
        seen.add(candidate.bucket_id)
        if len([c for c in selected if c in candidates]) >= count:
            break


def _top_unique(candidates: list[NormalizedBucket], score_fn, count: int) -> list[NormalizedBucket]:
    ordered = sorted(candidates, key=score_fn, reverse=True)
    result: list[NormalizedBucket] = []
    seen: set[str] = set()
    for candidate in ordered:
        if not candidate.bucket_id or candidate.bucket_id in seen:
            continue
        result.append(candidate)
        seen.add(candidate.bucket_id)
        if len(result) >= count:
            break
    return result


async def select_buckets(adapter, limit: int, current_valence: float, current_arousal: float) -> list[dict]:
    now = datetime.now(timezone.utc)
    buckets = [b for b in await adapter.list_candidate_buckets() if bucket_id(b)]
    normalized = [normalize_bucket(bucket, now) for bucket in buckets]
    if len(normalized) < 2:
        return []

    target = max(3, min(limit, 5, len(normalized)))
    selected: list[NormalizedBucket] = []

    day_residue = _top_unique(normalized, day_residue_score, min(2, target))
    _append_unique(selected, day_residue, len(day_residue))
    if not selected:
        return []

    seed_valence = sum(item.normalized_valence for item in selected) / len(selected)
    seed_arousal = sum(item.normalized_arousal for item in selected) / len(selected)
    selected_ids = {item.bucket_id for item in selected}
    remaining = [item for item in normalized if item.bucket_id not in selected_ids]

    older = [item for item in remaining if item.age_days >= 3]
    affect_pool = older if older else remaining
    affect_echo = _top_unique(
        affect_pool,
        lambda item: affect_echo_score(item, seed_valence, seed_arousal),
        min(2, target - len(selected)),
    )
    _append_unique(selected, affect_echo, len(affect_echo))

    selected_ids = {item.bucket_id for item in selected}
    remaining = [item for item in normalized if item.bucket_id not in selected_ids]
    remote_pool = [item for item in remaining if item.age_days >= 14]
    if remote_pool and len(selected) < target:
        remote_echo = _top_unique(
            remote_pool,
            lambda item: remote_echo_score(item, seed_valence, seed_arousal),
            1,
        )
        _append_unique(selected, remote_echo, len(remote_echo))

    if len(selected) < target:
        selected_ids = {item.bucket_id for item in selected}
        remaining = [item for item in normalized if item.bucket_id not in selected_ids]
        fallback = _top_unique(
            remaining,
            lambda item: (
                0.45 * day_residue_score(item)
                + 0.35 * item.importance_score
                + 0.20 * item.emotional_intensity
            ),
            target - len(selected),
        )
        _append_unique(selected, fallback, len(fallback))

    return [item.bucket for item in selected[:target]]
