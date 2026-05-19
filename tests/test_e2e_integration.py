"""
End-to-end integration test for the Night Fall dream pipeline.

Uses real bucket YAML files on disk and real DreamStorage / surfacing logic.
Only the LLM layer is replaced with a fake so no API key is required.

Run with:
    pytest tests/test_e2e_integration.py -v
"""
from __future__ import annotations

import asyncio
import json
from datetime import timedelta
from pathlib import Path

import yaml

from night_fall.config import NightFallConfig
from night_fall.metadata import now_utc
from night_fall.storage import DreamStorage
from night_fall.tool import night_fall_tool


# ─── Fake LLM infrastructure ──────────────────────────────────────────────────


class _Message:
    def __init__(self, content):
        self.content = content


class _Choice:
    def __init__(self, content):
        self.message = _Message(content)


class _Response:
    def __init__(self, content):
        self.choices = [_Choice(content)]


class _FakeCompletions:
    def __init__(self, responses):
        self.responses = list(responses)

    async def create(self, **kwargs):
        return _Response(self.responses.pop(0))


class _FakeChat:
    def __init__(self, responses):
        self.completions = _FakeCompletions(responses)


class _FakeClient:
    def __init__(self, responses):
        self.chat = _FakeChat(responses)


class _FakeDehydrator:
    def __init__(self, responses):
        self.api_available = True
        self.model = "fake-model"
        self.client = _FakeClient(responses)


class _FakeMCP:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return decorator


# ─── Local bucket reader (reads real .md files from disk) ─────────────────────


class LocalBucketReader:
    """Read Ombre-format bucket .md files from a directory tree.

    Parses YAML frontmatter (--- delimiters) with pyyaml.
    No Ombre installation required.
    """

    def __init__(self, buckets_dir: Path):
        self.buckets_dir = buckets_dir

    async def list_all(self, include_archive: bool = False) -> list[dict]:
        results = []
        for md_file in self.buckets_dir.rglob("*.md"):
            text = md_file.read_text(encoding="utf-8")
            if not text.startswith("---\n"):
                continue
            try:
                _, rest = text.split("---\n", 1)
                raw_meta, body = rest.split("---\n", 1)
                meta = yaml.safe_load(raw_meta) or {}
            except (ValueError, yaml.YAMLError):
                continue
            if not isinstance(meta, dict) or not meta.get("id"):
                continue
            results.append({
                "id": meta["id"],
                "content": body.strip(),
                "metadata": meta,
            })
        return results


# ─── Integration server factory ───────────────────────────────────────────────


def _make_server(buckets_dir: Path, llm_responses: list[str]):
    class _IntegrationServer:
        def __init__(self):
            self.mcp = _FakeMCP()
            self.bucket_mgr = LocalBucketReader(buckets_dir)
            self.dehydrator = _FakeDehydrator(llm_responses)
            self.config = {"transport": "stdio"}

    return _IntegrationServer()


# ─── Bucket seeding helpers ────────────────────────────────────────────────────


def _write_bucket(path: Path, bucket_id: str, name: str, content: str, **meta) -> None:
    now_iso = now_utc().isoformat()
    metadata = {
        "id": bucket_id,
        "name": name,
        "tags": [],
        "domain": ["default"],
        "type": "dynamic",
        "valence": meta.get("valence", 0.3),
        "arousal": meta.get("arousal", 0.6),
        "importance": meta.get("importance", 7),
        "created": meta.get("created", now_iso),
        "last_active": now_iso,
        "activation_count": 1,
        "resolved": meta.get("resolved", False),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    frontmatter = yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False)
    path.write_text(f"---\n{frontmatter}---\n{content}\n", encoding="utf-8")


def _seed_buckets(buckets_dir: Path) -> None:
    """Write 3 test bucket files (recent, older, very old) to disk."""
    dyn = buckets_dir / "dynamic" / "default"
    _write_bucket(
        dyn / "rain_hallway_test_bucket_01.md",
        "test_bucket_01",
        "rain_hallway",
        "The hallway was full of rain and a red door would not open.",
        valence=0.3,
        arousal=0.7,
    )
    _write_bucket(
        dyn / "cold_light_test_bucket_02.md",
        "test_bucket_02",
        "cold_light",
        "Her voice came through the window like cold light.",
        valence=0.32,
        arousal=0.58,
    )
    _write_bucket(
        dyn / "station_clock_test_bucket_03.md",
        "test_bucket_03",
        "station_clock",
        "A station clock kept stopping under a blue sign.",
        valence=0.4,
        arousal=0.55,
        # Created 20 days ago so it enters the remote-echo selection phase.
        created=(now_utc() - timedelta(days=20)).isoformat(),
    )


def _llm_responses() -> list[str]:
    """Two fake LLM responses: imagery extraction + dream writing."""
    return [
        json.dumps({
            "imagery_fragments": [
                {"source_bucket_id": "test_bucket_01", "excerpt": "hallway was full of rain"},
                {"source_bucket_id": "test_bucket_02", "excerpt": "cold light"},
                {"source_bucket_id": "test_bucket_03", "excerpt": "station clock kept stopping"},
            ]
        }),
        json.dumps({
            "dream_text": "水漫过走廊，红门纹丝不动。停止的钟表下，她的声音像冷光透进来。",
            "core_affect": {"valence": 0.28, "arousal": 0.72},
            "recall_cues": [
                "独自归家的迟疑",
                "熟悉空间忽然陌生",
                "湿润季节的傍晚",
            ],
        }),
    ]


def _cfg(tmp_path: Path) -> NightFallConfig:
    return NightFallConfig(repo_root=tmp_path, ombre_home=None, data_dir=tmp_path)


# ─── Tests ────────────────────────────────────────────────────────────────────


def test_full_dream_pipeline(tmp_path, monkeypatch):
    """generate → status → surface: full happy path using real file I/O."""
    buckets_dir = tmp_path / "buckets"
    _seed_buckets(buckets_dir)
    server = _make_server(buckets_dir, _llm_responses())
    cfg = _cfg(tmp_path)
    monkeypatch.setattr("night_fall.tool.choose_dream_mode", lambda: "fragmentary")

    # 1. generate
    result = asyncio.run(night_fall_tool(server, cfg, action="generate"))
    assert "latent dream formed" in result

    # 2. dream file written to disk with correct schema
    dream_files = list((tmp_path / "dreams").glob("dream_*.md"))
    assert len(dream_files) == 1
    file_text = dream_files[0].read_text(encoding="utf-8")
    assert "surfaced: false" in file_text
    assert "dream_mode: fragmentary" in file_text
    assert "valence: 0.28" in file_text

    # 3. status shows 1 pending
    status = asyncio.run(night_fall_tool(server, cfg, action="status"))
    assert "pending dreams: 1" in status

    # 4. bypass the 3-hour minimum by rewriting generated_at
    storage = DreamStorage(tmp_path / "dreams", tmp_path / "logs")
    record = storage.read(dream_files[0])
    four_hours_ago = (now_utc() - timedelta(hours=4)).isoformat()
    storage.update(record, generated_at=four_hours_ago)

    # 5. surface with affect matching the dream's core_affect (valence 0.28, arousal 0.72)
    surface_result = asyncio.run(
        night_fall_tool(server, cfg, action="surface", current_valence=0.3, current_arousal=0.7)
    )
    assert "=== 浮上来的梦 ===" in surface_result
    assert "水漫过走廊" in surface_result
    assert "spontaneous: false" in surface_result
    assert "source_bucket_ids" not in surface_result

    # 6. v2 lifecycle: surfaced dream is physically destroyed (one-shot).
    # The .md file must be gone and the event log must record the surfacing.
    assert list((tmp_path / "dreams").glob("dream_*.md")) == []
    events_file = (tmp_path / "logs" / "events.jsonl").read_text(encoding="utf-8")
    assert "surfaced_one_shot" in events_file
    assert '"event": "surfaced"' in events_file


def test_surface_blocked_before_three_hours(tmp_path, monkeypatch):
    """A freshly generated dream must not surface before 3 hours have passed."""
    buckets_dir = tmp_path / "buckets"
    _seed_buckets(buckets_dir)
    server = _make_server(buckets_dir, _llm_responses())
    cfg = _cfg(tmp_path)
    monkeypatch.setattr("night_fall.tool.choose_dream_mode", lambda: "integrative")

    asyncio.run(night_fall_tool(server, cfg, action="generate"))

    # surface immediately — dream is seconds old, well within the 3-hour lock
    result = asyncio.run(
        night_fall_tool(server, cfg, action="surface", current_valence=0.3, current_arousal=0.7)
    )
    assert result == "No latent dream surfaced."


def test_exhausted_dream_cleanup(tmp_path, monkeypatch):
    """A dream with surface_attempts >= 4 is deleted by the cleanup action."""
    buckets_dir = tmp_path / "buckets"
    _seed_buckets(buckets_dir)
    server = _make_server(buckets_dir, _llm_responses())
    cfg = _cfg(tmp_path)
    monkeypatch.setattr("night_fall.tool.choose_dream_mode", lambda: "residual")

    asyncio.run(night_fall_tool(server, cfg, action="generate"))

    # force exhaustion by setting surface_attempts to 4
    storage = DreamStorage(tmp_path / "dreams", tmp_path / "logs")
    dream_files = list((tmp_path / "dreams").glob("dream_*.md"))
    record = storage.read(dream_files[0])
    storage.update(record, surface_attempts=4)

    # cleanup deletes the exhausted dream
    cleanup_result = asyncio.run(night_fall_tool(server, cfg, action="cleanup"))
    assert "cleanup complete" in cleanup_result

    # dreams directory is now empty
    assert list((tmp_path / "dreams").glob("dream_*.md")) == []
