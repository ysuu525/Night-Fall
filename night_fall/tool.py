from __future__ import annotations

import logging
import random

from .config import NightFallConfig
from .imagery import ImageryExtractionError
from .imagery import extract_imagery
from .metadata import choose_dream_mode, new_dream_id, now_iso, now_utc
from .ombre_adapter import JsonModelError
from .ombre_adapter import OmbreAdapter
from .selection import select_buckets
from .storage import DreamStorage
from .surfacing import (
    age_hours,
    evaluate_pending,
    is_eligible_breath,
)
from .writer import DreamWriterError
from .writer import write_dream

logger = logging.getLogger("night_fall.tool")


def _storage(cfg: NightFallConfig) -> DreamStorage:
    return DreamStorage(cfg.dreams_dir, cfg.logs_dir)


def _format_surface_response(record, spontaneous: bool) -> str:
    affect = record.metadata.get("core_affect", {})
    cues = record.metadata.get("recall_cues") or []
    cues_text = "｜".join(cues) if cues else "(none)"
    return (
        "=== 浮上来的梦 ===\n"
        f"dream_id: {record.dream_id}\n"
        f"mode: {record.metadata.get('dream_mode')}\n"
        f"spontaneous: {str(bool(spontaneous)).lower()}\n"
        f"core_affect: valence={float(affect.get('valence', 0.5)):.2f}, "
        f"arousal={float(affect.get('arousal', 0.3)):.2f}\n"
        f"recall_cues: {cues_text}\n\n"
        f"{record.body}"
    )


def _emit_and_destroy(store: DreamStorage, adapter: OmbreAdapter, record, spontaneous: bool):
    """Mark the dream as surfaced, write the lifecycle event, then physically
    destroy the dream so it cannot resurface or quietly persist. Spec section 6:
    'unheld surfaced dream does not enter any persistent layer'.
    """
    surfaced_record = store.update(
        record,
        surfaced=True,
        surfaced_at=now_iso(),
        spontaneous=bool(spontaneous),
    )
    store.log_event(
        "surfaced",
        {
            "dream_id": surfaced_record.dream_id,
            "generated_at": surfaced_record.metadata.get("generated_at"),
            "surfaced_at": surfaced_record.metadata.get("surfaced_at"),
            "spontaneous": bool(spontaneous),
        },
    )
    store.delete(surfaced_record, reason="surfaced_one_shot")
    engine = getattr(adapter, "embedding_engine", None)
    if engine is not None:
        try:
            engine.delete_embedding(surfaced_record.dream_id)
        except Exception as exc:
            logger.warning(f"Failed to delete embedding for {surfaced_record.dream_id}: {exc}")
    return _format_surface_response(surfaced_record, spontaneous)


async def _query_embedding(adapter: OmbreAdapter, query: str) -> list[float] | None:
    if not query or not query.strip():
        return None
    engine = getattr(adapter, "embedding_engine", None)
    if engine is None or not getattr(engine, "enabled", False):
        return None
    try:
        emb = await engine._generate_embedding(query)
        return emb or None
    except Exception as exc:
        logger.warning(f"Query embedding failed: {exc}")
        return None


async def night_fall_tool(
    ombre_server,
    cfg: NightFallConfig,
    action: str = "generate",
    query: str = "",
    current_valence: float = -1,
    current_arousal: float = -1,
    current_motifs: str = "",
    is_session_start: bool = False,
    debug: bool = False,
) -> str:
    action_name = (action or "generate").strip().lower()
    store = _storage(cfg)
    adapter = OmbreAdapter(ombre_server)
    now = now_utc()

    if action_name == "status":
        status = store.status(now)
        oldest = status["oldest_pending_age_hours"]
        oldest_text = "none" if oldest is None else f"{oldest:.1f}h"
        return (
            "Night Fall status:\n"
            f"pending dreams: {status['pending']}\n"
            f"surfaced dreams: {status['surfaced']}\n"
            f"deleted dreams: {status['deleted']}\n"
            f"oldest pending age: {oldest_text}"
        )

    if action_name == "cleanup":
        deleted = store.cleanup_exhausted()
        return f"Night Fall cleanup complete: {deleted} exhausted unsurfaced dream(s) deleted."

    if action_name == "surface":
        if not is_eligible_breath(query, current_valence, current_arousal, is_session_start):
            return "Breath not contextual — no dream surfacing this turn."

        pending = [
            r for r in store.list()
            if not r.surfaced and age_hours(r, now) >= cfg.min_surface_age_hours
        ]
        if not pending:
            return "No latent dream surfaced."

        query_emb = await _query_embedding(adapter, query)
        evaluated = await evaluate_pending(
            pending, cfg, query_emb, current_valence, current_arousal, adapter
        )

        # Step 1: increment surface_attempts only for dreams whose top channel
        # passes the attempt_threshold. Low-signal breaths do not consume the
        # dream's chance (spec section 3 DESIGN INTENT).
        for item in evaluated:
            if item["top"] >= cfg.attempt_threshold:
                record = item["record"]
                new_attempts = int(record.metadata.get("surface_attempts", 0)) + 1
                item["record"] = store.update(record, surface_attempts=new_attempts)

        # Step 2: pick best candidate above surface_threshold.
        best = None  # (score, item)
        for item in evaluated:
            if item["score"] >= cfg.surface_threshold:
                if best is None or item["score"] > best[0]:
                    best = (item["score"], item)

        if best is not None:
            return _emit_and_destroy(store, adapter, best[1]["record"], spontaneous=False)

        # Step 3: spontaneous fallback — each pending dream independently has a
        # small chance to surface even without resonance.
        for item in evaluated:
            if random.random() < cfg.spontaneous_surface_prob:
                return _emit_and_destroy(store, adapter, item["record"], spontaneous=True)

        # Step 4: real deletion for dreams that have exhausted their attempts.
        store.cleanup_exhausted()
        return "No latent dream surfaced."

    if action_name != "generate":
        return "Unknown Night Fall action. Use generate, surface, status, or cleanup."

    buckets = await select_buckets(adapter, cfg.selection_limit, current_valence, current_arousal)
    if len(buckets) < 2:
        return "Night Fall skipped: not enough memory material to form a dream."

    try:
        fragments = await extract_imagery(adapter, buckets)
    except (ImageryExtractionError, JsonModelError) as exc:
        return f"Night Fall skipped: imagery extraction failed ({exc})."

    mode = choose_dream_mode()
    try:
        dream_text, core_affect, recall_cues = await write_dream(adapter, buckets, fragments, mode)
    except (DreamWriterError, JsonModelError) as exc:
        return f"Night Fall skipped: dream writing failed ({exc})."

    source_ids = []
    for bucket in buckets:
        source_id = str(bucket.get("id") or bucket.get("metadata", {}).get("id") or "").strip()
        if source_id not in source_ids:
            source_ids.append(source_id)

    metadata = {
        "dream_id": new_dream_id(),
        "generated_at": now_iso(),
        "dream_mode": mode,
        "core_affect": core_affect,
        "source_bucket_ids": source_ids,
        "imagery_fragments": fragments,
        "surfaced": False,
        "surfaced_at": None,
        "spontaneous": None,
        "surface_attempts": 0,
        "recall_cues": recall_cues,
    }
    record = store.write(metadata, dream_text)

    # Embed recall_cues so the cue-channel can fire later. Graceful degradation:
    # if embedding fails (no API key, timeout), the dream still lives but only
    # the affect channel will resonate.
    engine = getattr(adapter, "embedding_engine", None)
    if engine is not None and getattr(engine, "enabled", False) and recall_cues:
        cues_text = "；".join(recall_cues)
        try:
            ok = await engine.generate_and_store(record.dream_id, cues_text)
            if not ok:
                logger.warning(f"Embedding generation returned false for {record.dream_id}")
        except Exception as exc:
            logger.warning(f"Embedding generation failed for {record.dream_id}: {exc}")

    if debug:
        return (
            "Night Fall complete: 1 latent dream formed.\n"
            "It has not surfaced.\n"
            f"debug dream_id: {record.dream_id}\n"
            f"debug fragments: {len(fragments)}\n"
            f"debug recall_cues: {len(recall_cues)}"
        )
    return "Night Fall complete: 1 latent dream formed.\nIt has not surfaced."
