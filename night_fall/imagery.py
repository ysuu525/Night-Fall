from __future__ import annotations

import logging
from pathlib import Path
import re


logger = logging.getLogger("night_fall.imagery")


class ImageryExtractionError(RuntimeError):
    pass


def _prompt() -> str:
    path = Path(__file__).resolve().parent / "prompts" / "imagery_extraction.md"
    return path.read_text(encoding="utf-8")


def _compact(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _validate_excerpt(excerpt: str, content: str) -> str | None:
    trimmed = excerpt.strip()
    if not trimmed:
        return None
    if trimmed in content:
        return trimmed
    compact_excerpt = _compact(trimmed)
    compact_content = _compact(content)
    if compact_excerpt and compact_excerpt in compact_content:
        return compact_excerpt
    return None


def _validate_fragments(raw, buckets: list[dict]) -> list[dict]:
    by_id = {
        str(bucket.get("id") or bucket.get("metadata", {}).get("id")): bucket.get("content", "")
        for bucket in buckets
    }
    fragments = []
    if not isinstance(raw, dict) or not isinstance(raw.get("imagery_fragments"), list):
        raise ImageryExtractionError("Imagery extraction response did not match the JSON schema.")
    per_bucket: dict[str, int] = {}
    seen: set[tuple[str, str]] = set()
    for item in raw["imagery_fragments"]:
        if not isinstance(item, dict):
            continue
        source_id = str(item.get("source_bucket_id", "")).strip()
        excerpt = str(item.get("excerpt", "")).strip()
        if not source_id or not excerpt:
            continue
        valid_excerpt = _validate_excerpt(excerpt, by_id.get(source_id, ""))
        if not valid_excerpt:
            logger.warning("Dropping unverified imagery excerpt from %s: %s", source_id, excerpt[:80])
            continue
        if per_bucket.get(source_id, 0) >= 2:
            continue
        key = (source_id, valid_excerpt)
        if key in seen:
            continue
        fragments.append({"source_bucket_id": source_id, "excerpt": valid_excerpt})
        per_bucket[source_id] = per_bucket.get(source_id, 0) + 1
        seen.add(key)
        if len(fragments) >= 6:
            break
    return fragments


async def extract_imagery(adapter, buckets: list[dict]) -> list[dict]:
    payload = {
        "buckets": [
            {
                "source_bucket_id": b.get("id") or b.get("metadata", {}).get("id"),
                "metadata": b.get("metadata", {}),
                "content": b.get("content", "")[:1600],
            }
            for b in buckets
        ]
    }
    raw = await adapter.call_json_model(_prompt(), payload, max_tokens=700, temperature=0.3)
    fragments = _validate_fragments(raw, buckets)
    if len(fragments) < 2:
        raise ImageryExtractionError("Imagery extraction produced fewer than 2 verified fragments.")
    if len(fragments) < 3:
        logger.warning("Imagery extraction produced only %s verified fragments.", len(fragments))
    return fragments
