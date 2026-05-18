from __future__ import annotations

from datetime import datetime
import math
import random

from .metadata import clamp01


def age_hours(record, now: datetime) -> float:
    return (now - record.generated_at).total_seconds() / 3600


def affect_resonance(record, current_valence: float, current_arousal: float) -> float | None:
    if not (0 <= current_valence <= 1 and 0 <= current_arousal <= 1):
        return None
    affect = record.metadata.get("core_affect", {})
    dv = clamp01(affect.get("valence", 0.5)) - current_valence
    da = clamp01(affect.get("arousal", 0.3), 0.3) - current_arousal
    return max(0.0, 1.0 - math.sqrt((dv * dv + da * da) / 2))


def choose_surface_candidate(records, cfg, now: datetime, current_valence: float, current_arousal: float, current_motifs: str):
    eligible = [
        r for r in records
        if not r.surfaced and cfg.min_surface_age_hours <= age_hours(r, now)
    ]
    if not eligible:
        return eligible, None, False

    resonant = []
    for record in eligible:
        resonance = affect_resonance(record, current_valence, current_arousal)
        if resonance is not None and resonance >= cfg.surface_threshold:
            resonant.append((resonance, record.generated_at, record))
    if resonant:
        resonant.sort(key=lambda item: (-item[0], item[1]))
        return eligible, resonant[0][2], False

    spontaneous_pool = [record for record in eligible if age_hours(record, now) >= cfg.spontaneous_after_hours]
    spontaneous_pool.sort(key=lambda record: record.generated_at)
    for record in spontaneous_pool:
        if random.random() < cfg.spontaneous_chance:
            return eligible, record, True
    return eligible, None, False
