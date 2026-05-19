from __future__ import annotations

import asyncio
from datetime import timedelta

from night_fall.config import NightFallConfig
from night_fall.metadata import now_utc, new_dream_id
from night_fall.storage import DreamStorage
from night_fall.tool import night_fall_tool


def _meta(generated_at: str, valence: float, arousal: float) -> dict:
    return {
        "dream_id": new_dream_id(),
        "generated_at": generated_at,
        "dream_mode": "fragmentary",
        "core_affect": {"valence": valence, "arousal": arousal},
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


def test_attempts_only_increment_when_top_signal_passes_threshold(tmp_path, monkeypatch):
    """Affect-only setup with three dreams. Current affect at (0.1, 0.1):

    - Dream A core_affect=(0.55, 0.55) → score ≈ 0.55:
        ≥ attempt_threshold 0.45 → attempts +1
        < surface_threshold 0.62 → does not surface
    - Dream B core_affect=(0.9, 0.9) → score ≈ 0.2: below attempt floor
    - Dream C core_affect=(0.95, 0.05) → score ≈ 0.4: below attempt floor

    Spec section 3 DESIGN INTENT: low-signal breaths must not consume B and C's
    chance to be remembered."""
    storage = DreamStorage(tmp_path / "dreams", tmp_path / "logs")
    four_hours_ago = (now_utc() - timedelta(hours=4)).isoformat()

    record_a = storage.write(_meta(four_hours_ago, valence=0.55, arousal=0.55), "Dream A")
    record_b = storage.write(_meta(four_hours_ago, valence=0.9, arousal=0.9), "Dream B")
    record_c = storage.write(_meta(four_hours_ago, valence=0.95, arousal=0.05), "Dream C")

    # Prevent any spontaneous fire from confusing the count.
    monkeypatch.setattr("night_fall.tool.random.random", lambda: 1.0)

    cfg = NightFallConfig(repo_root=tmp_path, ombre_home=None, data_dir=tmp_path)

    response = asyncio.run(
        night_fall_tool(
            _Server(), cfg, action="surface",
            current_valence=0.1, current_arousal=0.1,
        )
    )
    # Sanity check — no dream should have surfaced (and thus no .md was destroyed)
    assert response == "No latent dream surfaced."

    a = storage.read(record_a.path)
    b = storage.read(record_b.path)
    c = storage.read(record_c.path)

    assert a.metadata["surface_attempts"] == 1, "moderate-signal dream should attempt"
    assert b.metadata["surface_attempts"] == 0, "low-signal dream should not attempt"
    assert c.metadata["surface_attempts"] == 0, "low-signal dream should not attempt"
