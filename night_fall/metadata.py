from __future__ import annotations

from datetime import datetime, timezone
import random
import uuid

DREAM_MODES = ("integrative", "fragmentary", "residual")
MAX_SURFACE_ATTEMPTS = 4
REQUIRED_METADATA_FIELDS = {
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
}
FORBIDDEN_METADATA_FIELDS = {
    "deletion_scheduled_at",
    "surface_score",
    "surfacing_reason_detail",
    "recall_count",
}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def now_iso() -> str:
    return now_utc().isoformat(timespec="seconds")


def parse_dt(value: str) -> datetime:
    text = (value or "").strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def new_dream_id() -> str:
    return f"dream_{uuid.uuid4().hex[:12]}"


def clamp01(value: object, default: float = 0.5) -> float:
    try:
        num = float(value)
    except (TypeError, ValueError):
        num = default
    return max(0.0, min(1.0, num))


def choose_dream_mode() -> str:
    return random.choices(
        population=["integrative", "fragmentary", "residual"],
        weights=[0.70, 0.20, 0.10],
        k=1,
    )[0]


def validate_metadata(metadata: dict) -> None:
    missing = REQUIRED_METADATA_FIELDS - set(metadata)
    if missing:
        raise ValueError(f"Dream metadata missing fields: {sorted(missing)}")
    forbidden = FORBIDDEN_METADATA_FIELDS & set(metadata)
    if forbidden:
        raise ValueError(f"Dream metadata contains forbidden fields: {sorted(forbidden)}")
    mode = metadata.get("dream_mode")
    if mode not in DREAM_MODES:
        raise ValueError(f"Unsupported dream mode: {mode}")
    affect = metadata.get("core_affect")
    if not isinstance(affect, dict):
        raise ValueError("core_affect must be a mapping")
    clamp01(affect.get("valence"))
    clamp01(affect.get("arousal"))
    for item in metadata.get("imagery_fragments") or []:
        if not isinstance(item, dict):
            raise ValueError("imagery_fragments items must be mappings")
        if not item.get("source_bucket_id") or not item.get("excerpt"):
            raise ValueError("imagery_fragments must include source_bucket_id and excerpt")
