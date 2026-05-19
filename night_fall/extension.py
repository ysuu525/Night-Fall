from __future__ import annotations

from .config import NightFallConfig
from .tool import get_surfaceable_dream, night_fall_tool


_NIGHT_FALL_DOC = """Night Fall latent dream lifecycle.

Actions:
- generate: Create a new latent dream from emotional Ombre memories. Typically
  called at session end or low-activity moments.
- surface: Manual / debugging entry point. Normal dream surfacing happens
  automatically inside breath (v1) — Claude does not need to call this in the
  regular flow. Returns at most one surfaced dream, in a dedicated section
  prefixed by "=== 浮上来的梦 ===".
- status: Report counts of pending / surfaced / deleted dreams.
- cleanup: Remove dreams that have been considered but not picked
  MAX_SURFACE_ATTEMPTS times.

When to call surface (the breath discipline):
- Right after breath, at the start of a new conversation
  (pass is_session_start=true).
- Right after breath, when the conversation has shifted to a register where
  past memories would genuinely inform your response — i.e., when you find
  yourself wanting to look back, not when checking status.
- Right after breath, when the current context carries emotional weight that
  may resonate with past experiences.

When NOT to call surface:
- On every turn as a status check.
- When the conversation is in a routine functional register that does not
  invite recall (e.g., debugging code, fetching factual information).
- Multiple times in quick succession without new context having developed.

surface without query/valence/arousal and without is_session_start does
nothing — dreams only resonate with contextual moments.

A surfaced dream is delivered once. If you want to keep it, call
hold(content=...) explicitly. Otherwise it disappears permanently after this
turn.

Args:
- action: generate | surface | status | cleanup
- query: contextual phrase or motif from the current conversation (surface only)
- current_valence / current_arousal: 0..1, -1 means unspecified (surface only)
- is_session_start: pass true on the first breath of a new conversation
- current_motifs: deprecated, retained for compatibility
- debug: include diagnostic info in the response
"""


def register_night_fall(ombre_server, cfg: NightFallConfig) -> None:
    if getattr(ombre_server, "_night_fall_registered", False):
        return

    @ombre_server.mcp.tool()
    async def night_fall(
        action: str = "generate",
        query: str = "",
        current_valence: float = -1,
        current_arousal: float = -1,
        current_motifs: str = "",
        is_session_start: bool = False,
        debug: bool = False,
    ) -> str:
        return await night_fall_tool(
            ombre_server,
            cfg,
            action=action,
            query=query,
            current_valence=current_valence,
            current_arousal=current_arousal,
            current_motifs=current_motifs,
            is_session_start=is_session_start,
            debug=debug,
        )

    night_fall.__doc__ = _NIGHT_FALL_DOC

    async def _auto_surface() -> str | None:
        return await get_surfaceable_dream(ombre_server, cfg)

    ombre_server._night_fall_auto_surface = _auto_surface
    ombre_server._night_fall_registered = True
