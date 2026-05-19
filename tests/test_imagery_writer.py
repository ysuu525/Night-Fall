from __future__ import annotations

import asyncio

import pytest

from night_fall.imagery import ImageryExtractionError, extract_imagery
from night_fall.writer import write_dream


class Adapter:
    def __init__(self, response):
        self.response = response

    async def call_json_model(self, *args, **kwargs):
        return self.response


def _buckets():
    return [
        {
            "id": "bucket_a",
            "content": "The hallway was full of rain. A red door would not open.",
            "metadata": {"id": "bucket_a"},
        },
        {
            "id": "bucket_b",
            "content": "Her voice came through the window like cold light.",
            "metadata": {"id": "bucket_b"},
        },
    ]


def test_imagery_extraction_validates_excerpts_against_sources():
    response = {
        "imagery_fragments": [
            {"source_bucket_id": "bucket_a", "excerpt": "hallway was full of rain"},
            {"source_bucket_id": "bucket_b", "excerpt": "cold light"},
            {"source_bucket_id": "bucket_b", "excerpt": "invented silver animal"},
        ]
    }

    fragments = asyncio.run(extract_imagery(Adapter(response), _buckets()))

    assert fragments == [
        {"source_bucket_id": "bucket_a", "excerpt": "hallway was full of rain"},
        {"source_bucket_id": "bucket_b", "excerpt": "cold light"},
    ]


def test_imagery_extraction_fails_with_fewer_than_two_valid_fragments():
    response = {
        "imagery_fragments": [
            {"source_bucket_id": "bucket_a", "excerpt": "invented silver animal"},
        ]
    }

    with pytest.raises(ImageryExtractionError):
        asyncio.run(extract_imagery(Adapter(response), _buckets()))


def test_writer_parses_final_core_affect_and_cues():
    response = {
        "dream_text": "I stood in the hallway while rain came through the lock.",
        "core_affect": {"valence": 0.22, "arousal": 0.74},
        "recall_cues": ["独自归家的迟疑", "熟悉空间忽然陌生", "湿润季节的傍晚"],
    }

    dream_text, affect, cues = asyncio.run(write_dream(
        Adapter(response),
        _buckets(),
        [{"source_bucket_id": "bucket_a", "excerpt": "hallway was full of rain"}],
        "fragmentary",
    ))

    assert dream_text.startswith("I stood")
    assert affect == {"valence": 0.22, "arousal": 0.74}
    assert cues == ["独自归家的迟疑", "熟悉空间忽然陌生", "湿润季节的傍晚"]


def test_residual_prompt_is_distinct_from_integrative():
    prompt = (
        __import__("pathlib")
        .Path(__file__)
        .resolve()
        .parents[1]
        .joinpath("night_fall/prompts/dream_writer.md")
        .read_text(encoding="utf-8")
    )

    assert "residual" in prompt
    assert "fragmentary" in prompt
    assert "integrative" in prompt
    assert "trivial" not in prompt
    assert "core_affect" in prompt
    assert "recall_cues" in prompt
