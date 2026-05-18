from __future__ import annotations

import asyncio
import json
from pathlib import Path

from night_fall.config import NightFallConfig
from night_fall.extension import register_night_fall
from night_fall.metadata import now_utc
from night_fall.tool import night_fall_tool


class FakeMCP:
    def __init__(self):
        self.tools = {
            "breath": object(),
            "hold": object(),
            "grow": object(),
            "trace": object(),
            "pulse": object(),
            "dream": object(),
        }

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return decorator


class FakeBucketManager:
    async def list_all(self, include_archive=False):
        return [
            {
                "id": "bucket_a",
                "content": "The hallway was full of rain and a red door would not open.",
                "metadata": {
                    "id": "bucket_a",
                    "created": now_utc().isoformat(),
                    "importance": 8,
                    "valence": 0.3,
                    "arousal": 0.6,
                    "type": "dynamic",
                    "resolved": False,
                },
            },
            {
                "id": "bucket_b",
                "content": "Her voice came through the window like cold light.",
                "metadata": {
                    "id": "bucket_b",
                    "created": "2026-04-20T00:00:00+00:00",
                    "importance": 7,
                    "valence": 0.32,
                    "arousal": 0.58,
                    "type": "dynamic",
                },
            },
            {
                "id": "bucket_c",
                "content": "A station clock kept stopping under a blue sign.",
                "metadata": {
                    "id": "bucket_c",
                    "created": "2026-05-10T00:00:00+00:00",
                    "importance": 6,
                    "valence": 0.4,
                    "arousal": 0.55,
                    "type": "dynamic",
                },
            },
        ]


class Message:
    def __init__(self, content):
        self.content = content


class Choice:
    def __init__(self, content):
        self.message = Message(content)


class Response:
    def __init__(self, content):
        self.choices = [Choice(content)]


class FakeCompletions:
    def __init__(self, responses, calls):
        self.responses = responses
        self.calls = calls

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return Response(self.responses.pop(0))


class FakeChat:
    def __init__(self, responses, calls):
        self.completions = FakeCompletions(responses, calls)


class FakeClient:
    def __init__(self, responses, calls):
        self.chat = FakeChat(responses, calls)


class FakeDehydrator:
    def __init__(self, responses, calls):
        self.api_available = True
        self.model = "fake-model"
        self.client = FakeClient(responses, calls)


class FakeServer:
    def __init__(self):
        self.mcp = FakeMCP()
        self.bucket_mgr = FakeBucketManager()
        self.llm_calls = []
        self.dehydrator = FakeDehydrator(
            [
                json.dumps(
                    {
                        "imagery_fragments": [
                            {"source_bucket_id": "bucket_a", "excerpt": "hallway was full of rain"},
                            {"source_bucket_id": "bucket_b", "excerpt": "cold light"},
                            {"source_bucket_id": "bucket_c", "excerpt": "station clock kept stopping"},
                        ]
                    }
                ),
                json.dumps(
                    {
                        "dream_text": "I stood in a hallway while cold light gathered around a stopped clock.",
                        "core_affect": {"valence": 0.21, "arousal": 0.77},
                    }
                ),
            ],
            self.llm_calls,
        )
        self.config = {"transport": "stdio"}


def _cfg(tmp_path: Path) -> NightFallConfig:
    return NightFallConfig(repo_root=tmp_path, ombre_home=None, data_dir=tmp_path)


def test_registers_only_night_fall_without_removing_existing_tools(tmp_path):
    server = FakeServer()

    register_night_fall(server, _cfg(tmp_path))

    assert set(server.mcp.tools) == {
        "breath",
        "hold",
        "grow",
        "trace",
        "pulse",
        "dream",
        "night_fall",
    }


def test_generate_stores_latent_dream_without_returning_body(tmp_path, monkeypatch):
    server = FakeServer()
    cfg = _cfg(tmp_path)
    order = []

    def choose_mode():
        assert len(server.llm_calls) == 1
        order.append("mode")
        return "residual"

    monkeypatch.setattr("night_fall.tool.choose_dream_mode", choose_mode)

    response = asyncio.run(night_fall_tool(server, cfg, action="generate"))

    assert "latent dream formed" in response
    assert "red door would not open" not in response
    assert order == ["mode"]
    assert len(server.llm_calls) == 2
    assert "imagery_fragments" in server.llm_calls[0]["messages"][0]["content"]
    assert "dream_mode" in server.llm_calls[1]["messages"][1]["content"]
    records = list((tmp_path / "dreams").glob("dream_*.md"))
    assert len(records) == 1
    text = records[0].read_text(encoding="utf-8")
    assert "surfaced: false" in text
    assert "dream_mode: residual" in text
    assert "valence: 0.21" in text
    assert "deletion_scheduled_at" not in text
    assert "dream_charge" not in text


def test_generate_does_not_write_when_imagery_has_too_few_valid_fragments(tmp_path):
    server = FakeServer()
    server.dehydrator = FakeDehydrator(
        [
            json.dumps(
                {
                    "imagery_fragments": [
                        {"source_bucket_id": "bucket_a", "excerpt": "invented silver moon"},
                    ]
                }
            )
        ],
        server.llm_calls,
    )
    cfg = _cfg(tmp_path)

    response = asyncio.run(night_fall_tool(server, cfg, action="generate"))

    assert "imagery extraction failed" in response
    assert list((tmp_path / "dreams").glob("dream_*.md")) == []


def test_status_returns_empty_state(tmp_path):
    response = asyncio.run(night_fall_tool(object(), _cfg(tmp_path), action="status"))

    assert response.startswith("Night Fall status:")
    assert "pending dreams: 0" in response
    assert "surfaced dreams: 0" in response


def test_cleanup_action_returns_completion_message(tmp_path):
    response = asyncio.run(night_fall_tool(object(), _cfg(tmp_path), action="cleanup"))

    assert "cleanup complete" in response


def test_unknown_action_returns_error_hint(tmp_path):
    response = asyncio.run(night_fall_tool(object(), _cfg(tmp_path), action="invalid"))

    assert "Unknown Night Fall action" in response


def test_generate_debug_mode_exposes_dream_id_and_fragment_count(tmp_path, monkeypatch):
    server = FakeServer()
    cfg = _cfg(tmp_path)
    monkeypatch.setattr("night_fall.tool.choose_dream_mode", lambda: "integrative")

    response = asyncio.run(night_fall_tool(server, cfg, action="generate", debug=True))

    assert "debug dream_id" in response
    assert "debug fragments" in response
