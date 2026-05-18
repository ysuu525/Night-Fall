# Night Fall

Night Fall is a runtime extension for [Ombre Brain](https://github.com/P0luz/Ombre-Brain). It adds one MCP tool, `night_fall`, to the same Ombre MCP server instance.

Night Fall does not fork, vendor, bundle, or redistribute Ombre. It extends a user-provided Ombre installation at runtime. Existing Ombre tools remain unchanged:

```text
breath / hold / grow / trace / pulse / dream
```

`dream` remains Ombre's original feature. `night_fall` is separate.

## What It Does

`night_fall` creates latent dreams that fade only after repeated failed surfacing:

1. `night_fall(action="generate")` selects emotionally charged Ombre memories, extracts imagery, writes a dream, and stores it privately.
2. The generated dream is not returned immediately. Its `dream_mode` is one of `integrative`, `fragmentary`, or `residual`.
3. For the first 3 hours, it cannot surface.
4. After 3 hours, `night_fall(action="surface")` may return it if the current affect resonates with the dream's `core_affect`.
5. After 24 hours, a very small spontaneous surfacing chance is also allowed.
6. Each surfacing evaluation that does not pick the dream increments `surface_attempts`. A dream is not removed by wall-clock time — it is deleted only after it has been evaluated `MAX_SURFACE_ATTEMPTS` (4) times and still not surfaced.
7. Surfaced dreams are returned through a dedicated channel and do not automatically enter long-term memory. A surfaced dream is preserved only if the user or Claude explicitly performs a hold-like action on it.

## Local Python Setup

Install Ombre Brain first. Then download or clone Night Fall anywhere you like. It is convenient during development to place the folders beside each other:

```text
somewhere/
  Ombre-Brain/
  Night-Fall/
```

That sibling layout is only a development convenience. End users do not need to place `Ombre-Brain/` inside or beside `Night-Fall/`.

From the Night Fall folder:

```bash
python scripts/install_local.py
python -m night_fall.launcher
```

The installer asks for your Ombre folder, validates `server.py`, and writes `.nightfall.yaml`.

You can also skip the installer:

```bash
OMBRE_HOME=/absolute/path/to/Ombre-Brain python -m night_fall.launcher
```

Keep using the same Claude MCP server entry you used for Ombre. You should see the original tools plus `night_fall`.

## Docker Setup

Night Fall does not provide a second Ombre image. It reuses Ombre's existing `ombre-brain` service from `docker-compose.user.yml`, bind-mounts this Night Fall folder, and changes the command to start Night Fall's launcher.

If your folders are arranged like this:

```text
somewhere/
  Ombre-Brain/
    docker-compose.user.yml
  Night-Fall/
```

run from `Ombre-Brain/`:

```bash
docker compose -f docker-compose.user.yml -f ../Night-Fall/docker/docker-compose.nightfall.override.yml up -d
```

This keeps the same Ombre container, same data mount, same port, and same Claude MCP config. Night Fall stores extension state in `/data/night_fall` inside the existing Ombre data volume.

If your Night Fall folder is elsewhere, edit only the override file's bind mount path.

## Tool Actions

```text
night_fall(action="generate")
night_fall(action="surface")
night_fall(action="status")
night_fall(action="cleanup")
```

Optional inputs:

```text
current_valence: 0.0-1.0, or -1 when unknown
current_arousal: 0.0-1.0, or -1 when unknown
current_motifs: accepted for interface compatibility; V1 surfacing is affect-led
debug: true/false
```

## Prompt Snippet

Night Fall does not edit Ombre's `CLAUDE_PROMPT.md`. If you want surfaced dreams to appear naturally after startup breath, add the contents of `NIGHT_FALL_PROMPT_APPEND.md` to your own Claude instructions.

## Development Notes

For this workspace, `Night-Fall-dev/Ombre-Brain/` is a read-only Ombre reference copy for source reading and integration tests. Do not edit it. All Night Fall source code lives in `Night-Fall-dev/Night-Fall/`.
