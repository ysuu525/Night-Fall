from __future__ import annotations

import json
import os
from typing import Any


class JsonModelError(RuntimeError):
    pass


class OmbreAdapter:
    """Narrow boundary around Ombre internals used by Night Fall."""

    def __init__(self, ombre_server: Any):
        self.ombre_server = ombre_server

    @property
    def config(self) -> dict:
        return getattr(self.ombre_server, "config", {}) or {}

    @property
    def dehydrator(self) -> Any:
        return getattr(self.ombre_server, "dehydrator", None)

    async def list_candidate_buckets(self) -> list[dict]:
        bucket_mgr = getattr(self.ombre_server, "bucket_mgr", None)
        if bucket_mgr is None:
            return []
        buckets = await bucket_mgr.list_all(include_archive=False)
        candidates = []
        for bucket in buckets:
            meta = bucket.get("metadata", {})
            if meta.get("type") in ("permanent", "feel", "archived"):
                continue
            if meta.get("pinned") or meta.get("protected"):
                continue
            if not bucket.get("content"):
                continue
            candidates.append(bucket)
        return candidates

    async def call_json_model(
        self,
        system_prompt: str,
        payload: dict,
        *,
        max_tokens: int = 700,
        temperature: float = 0.7,
    ) -> dict | list | None:
        raw_errors = []
        for _ in range(2):
            raw = await self._call_raw_model(
                system_prompt,
                payload,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError as exc:
                raw_errors.append(str(exc))
                continue
        raise JsonModelError(f"LLM returned invalid JSON after retry: {'; '.join(raw_errors)}")

    async def _call_raw_model(
        self,
        system_prompt: str,
        payload: dict,
        *,
        max_tokens: int,
        temperature: float,
    ) -> str:
        dehydrator = self.dehydrator
        client = getattr(dehydrator, "client", None)
        model = getattr(dehydrator, "model", "deepseek-chat")

        if not client or not getattr(dehydrator, "api_available", False):
            env_key = os.environ.get("DEEPSEEK_API_KEY", "")
            if not env_key:
                raise JsonModelError(
                    "No LLM provider available. Configure Ombre's dehydration API or set DEEPSEEK_API_KEY."
                )
            try:
                from openai import AsyncOpenAI
            except ImportError as exc:
                raise JsonModelError("The openai package is required for DEEPSEEK_API_KEY provider.") from exc
            client = AsyncOpenAI(
                api_key=env_key,
                base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
                timeout=60.0,
            )
            model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        if not response.choices:
            raise JsonModelError("LLM provider returned no choices.")
        raw = response.choices[0].message.content or ""
        if not raw.strip():
            raise JsonModelError("LLM provider returned an empty response.")
        return raw
