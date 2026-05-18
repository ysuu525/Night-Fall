from __future__ import annotations

from .config import NightFallConfig
from .tool import night_fall_tool


def register_night_fall(ombre_server, cfg: NightFallConfig) -> None:
    if getattr(ombre_server, "_night_fall_registered", False):
        return

    @ombre_server.mcp.tool()
    async def night_fall(
        action: str = "generate",
        current_valence: float = -1,
        current_arousal: float = -1,
        current_motifs: str = "",
        debug: bool = False,
    ) -> str:
        """Night Fall latent dream lifecycle: generate, surface, status, or cleanup."""
        return await night_fall_tool(
            ombre_server,
            cfg,
            action=action,
            current_valence=current_valence,
            current_arousal=current_arousal,
            current_motifs=current_motifs,
            debug=debug,
        )

    ombre_server._night_fall_registered = True
