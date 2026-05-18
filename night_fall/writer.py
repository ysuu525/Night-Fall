from __future__ import annotations

from pathlib import Path

from .metadata import clamp01


class DreamWriterError(RuntimeError):
    pass


def _prompt() -> str:
    path = Path(__file__).resolve().parent / "prompts" / "dream_writer.md"
    return path.read_text(encoding="utf-8")


def _validate(raw) -> tuple[str, dict] | None:
    if not isinstance(raw, dict):
        return None
    dream_text = str(raw.get("dream_text", "")).strip()
    affect = raw.get("core_affect")
    if not dream_text or not isinstance(affect, dict):
        return None
    return (
        dream_text,
        {
            "valence": round(clamp01(affect.get("valence", 0.5)), 2),
            "arousal": round(clamp01(affect.get("arousal", 0.3), 0.3), 2),
        },
    )


async def write_dream(adapter, buckets: list[dict], fragments: list[dict], mode: str) -> tuple[str, dict]:
    payload = {
        "dream_mode": mode,
        "imagery_fragments": fragments,
        "source_context": [
            {
                "source_bucket_id": b.get("id") or b.get("metadata", {}).get("id"),
                "metadata": {
                    "valence": b.get("metadata", {}).get("valence"),
                    "arousal": b.get("metadata", {}).get("arousal"),
                    "importance": b.get("metadata", {}).get("importance"),
                    "created": b.get("metadata", {}).get("created"),
                },
                "content_excerpt": b.get("content", "")[:700],
            }
            for b in buckets
        ],
    }
    raw = await adapter.call_json_model(_prompt(), payload, max_tokens=900, temperature=0.8)
    result = _validate(raw)
    if not result:
        raise DreamWriterError("Dream writer response did not match the JSON schema.")
    return result
