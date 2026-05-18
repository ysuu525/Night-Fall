from __future__ import annotations

from .config import NightFallConfig
from .imagery import ImageryExtractionError
from .imagery import extract_imagery
from .metadata import choose_dream_mode, new_dream_id, now_iso, now_utc
from .ombre_adapter import JsonModelError
from .ombre_adapter import OmbreAdapter
from .selection import select_buckets
from .storage import DreamStorage
from .surfacing import choose_surface_candidate
from .writer import DreamWriterError
from .writer import write_dream


def _storage(cfg: NightFallConfig) -> DreamStorage:
    return DreamStorage(cfg.dreams_dir, cfg.logs_dir)


async def night_fall_tool(
    ombre_server,
    cfg: NightFallConfig,
    action: str = "generate",
    current_valence: float = -1,
    current_arousal: float = -1,
    current_motifs: str = "",
    debug: bool = False,
) -> str:
    action_name = (action or "generate").strip().lower()
    store = _storage(cfg)
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
        eligible, candidate, spontaneous = choose_surface_candidate(
            store.list(),
            cfg,
            now,
            current_valence,
            current_arousal,
            current_motifs,
        )
        surfaced_record = None
        for record in eligible:
            new_attempts = int(record.metadata.get("surface_attempts", 0)) + 1
            if candidate is not None and record.dream_id == candidate.dream_id:
                surfaced_record = store.update(
                    record,
                    surface_attempts=new_attempts,
                    surfaced=True,
                    surfaced_at=now_iso(),
                    spontaneous=bool(spontaneous),
                )
            else:
                store.update(record, surface_attempts=new_attempts)
        store.cleanup_exhausted()
        if surfaced_record is None:
            return "No latent dream surfaced."
        affect = surfaced_record.metadata.get("core_affect", {})
        return (
            "A dream surfaced.\n\n"
            f"mode: {surfaced_record.metadata.get('dream_mode')}\n"
            f"spontaneous: {str(bool(spontaneous)).lower()}\n"
            f"core affect: valence={float(affect.get('valence', 0.5)):.2f}, "
            f"arousal={float(affect.get('arousal', 0.3)):.2f}\n\n"
            f"{surfaced_record.body}"
        )

    if action_name != "generate":
        return "Unknown Night Fall action. Use generate, surface, status, or cleanup."

    adapter = OmbreAdapter(ombre_server)
    buckets = await select_buckets(adapter, cfg.selection_limit, current_valence, current_arousal)
    if len(buckets) < 2:
        return "Night Fall skipped: not enough memory material to form a dream."

    try:
        fragments = await extract_imagery(adapter, buckets)
    except (ImageryExtractionError, JsonModelError) as exc:
        return f"Night Fall skipped: imagery extraction failed ({exc})."

    mode = choose_dream_mode()
    try:
        dream_text, core_affect = await write_dream(adapter, buckets, fragments, mode)
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
    }
    record = store.write(metadata, dream_text)
    if debug:
        return (
            "Night Fall complete: 1 latent dream formed.\n"
            "It has not surfaced.\n"
            f"debug dream_id: {record.dream_id}\n"
            f"debug fragments: {len(fragments)}"
        )
    return "Night Fall complete: 1 latent dream formed.\nIt has not surfaced."
