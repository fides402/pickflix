"""OpenRouter integration: live free-model catalog + chat completions with fallback.

The free-model list is never hardcoded: it is derived on every refresh from the
official /models endpoint by checking pricing.prompt == 0 and pricing.completion == 0,
so it tracks whatever OpenRouter currently offers for free instead of going stale.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

from app.config import get_settings

PREFERRED_DEFAULT = "openai/gpt-oss-120b:free"


@dataclass
class FreeModel:
    id: str
    name: str
    context_length: int | None


class ModelsUnavailableError(RuntimeError):
    pass


class OpenRouterClient:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._cache: list[FreeModel] = []
        self._cache_at: float = 0.0

    async def free_models(self, force_refresh: bool = False) -> list[FreeModel]:
        stale = (time.time() - self._cache_at) > self._settings.free_models_cache_ttl_seconds
        if force_refresh or stale or not self._cache:
            self._cache = await self._fetch_free_models()
            self._cache_at = time.time()
        return self._cache

    async def default_model_id(self) -> str:
        models = await self.free_models()
        ids = {m.id for m in models}
        if PREFERRED_DEFAULT in ids:
            return PREFERRED_DEFAULT
        return next(iter(ids), PREFERRED_DEFAULT)

    async def _fetch_free_models(self) -> list[FreeModel]:
        url = f"{self._settings.openrouter_base_url}/models"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        free: list[FreeModel] = []
        for m in data:
            pricing = m.get("pricing", {})
            try:
                is_free = float(pricing.get("prompt", "1")) == 0.0 and float(pricing.get("completion", "1")) == 0.0
            except (TypeError, ValueError):
                is_free = False
            if is_free:
                free.append(FreeModel(id=m["id"], name=m.get("name", m["id"]), context_length=m.get("context_length")))
        return free

    async def chat_json(self, messages: list[dict], model: str | None = None, max_tokens: int = 1200) -> tuple[str, str]:
        """Returns (content, model_used). Falls back through free models on 429/5xx."""
        candidates = [model] if model else []
        free = await self.free_models()
        candidates += [m.id for m in free if m.id != model]
        if not candidates:
            candidates = [self._settings.default_model]

        last_error: Exception | None = None
        async with httpx.AsyncClient(timeout=60) as client:
            for candidate in candidates:
                try:
                    resp = await client.post(
                        f"{self._settings.openrouter_base_url}/chat/completions",
                        headers={"Authorization": f"Bearer {self._settings.openrouter_api_key}"},
                        json={"model": candidate, "messages": messages, "max_tokens": max_tokens},
                    )
                    if resp.status_code == 429:
                        last_error = RuntimeError(f"{candidate} rate-limited")
                        continue
                    resp.raise_for_status()
                    content = resp.json()["choices"][0]["message"]["content"]
                    if not content:
                        # reasoning models can exhaust max_tokens on internal
                        # chain-of-thought before ever writing `content`,
                        # leaving it null -- treat that as a failed candidate
                        last_error = RuntimeError(f"{candidate} returned empty content (reasoning budget exhausted)")
                        continue
                    return content, candidate
                except httpx.HTTPStatusError as exc:
                    last_error = exc
                    continue
        raise ModelsUnavailableError(f"All free-model candidates failed: {last_error}")
