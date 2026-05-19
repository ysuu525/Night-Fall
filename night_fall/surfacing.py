from __future__ import annotations

from datetime import datetime
import logging
import math
from typing import Any

from .metadata import clamp01

logger = logging.getLogger("night_fall.surfacing")


def age_hours(record, now: datetime) -> float:
    return (now - record.generated_at).total_seconds() / 3600


def affect_score(record, current_valence: float, current_arousal: float) -> float:
    """Normalized affect resonance in [0, 1]. Returns 0.0 when affect is not provided."""
    if not (0 <= current_valence <= 1 and 0 <= current_arousal <= 1):
        return 0.0
    affect = record.metadata.get("core_affect", {})
    dv = clamp01(affect.get("valence", 0.5)) - current_valence
    da = clamp01(affect.get("arousal", 0.3), 0.3) - current_arousal
    return max(0.0, 1.0 - math.sqrt((dv * dv + da * da) / 2))


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


async def cue_score(record, query_embedding: list[float] | None, adapter) -> float:
    """Cosine similarity between query embedding and the dream's recall_cues embedding.
    Returns 0.0 when either side is missing. Negative values are clipped to 0."""
    if not query_embedding:
        return 0.0
    engine = getattr(adapter, "embedding_engine", None)
    if engine is None:
        return 0.0
    stored = await engine.get_embedding(record.dream_id)
    if not stored:
        return 0.0
    sim = _cosine_similarity(query_embedding, stored)
    return max(0.0, sim)


def compute_surface_score(a: float, c: float, alpha: float) -> float:
    """Two-channel surface score: max(a, c) + alpha * min(a, c).

    The max + weak-bonus shape (instead of linear weighting) honors the spec:
    affect and cue are two independent recall paths; either being strong should
    suffice to trigger surfacing, with a small bonus when both align. Do not
    convert this to a linear combination. See spec section 2 DESIGN INTENT.
    """
    return max(a, c) + alpha * min(a, c)


def is_eligible_breath(
    query: str,
    valence: float,
    arousal: float,
    is_session_start: bool,
) -> bool:
    """Spec section 5: only contextual breaths participate in dream surfacing.

    A pure no-arg status check (no query, no affect, not session_start) does not
    consume a dream's chance to be remembered.
    """
    has_query = bool(query and query.strip())
    has_affect = 0 <= valence <= 1 and 0 <= arousal <= 1
    return bool(is_session_start or has_query or has_affect)


async def evaluate_pending(
    pending: list,
    cfg,
    query_embedding: list[float] | None,
    current_valence: float,
    current_arousal: float,
    adapter: Any,
) -> list[dict]:
    """Score every pending dream once. Returns a list of dicts:
        {"record": record, "a": float, "c": float, "score": float, "top": float}
    The caller is responsible for: incrementing surface_attempts (only when top
    >= attempt_threshold), picking the best candidate above surface_threshold,
    and the spontaneous fallback.
    """
    evaluated = []
    for record in pending:
        a = affect_score(record, current_valence, current_arousal)
        c = await cue_score(record, query_embedding, adapter)
        score = compute_surface_score(a, c, cfg.alpha_subordinate)
        evaluated.append(
            {
                "record": record,
                "a": a,
                "c": c,
                "score": score,
                "top": max(a, c),
            }
        )
    return evaluated
