"""Optional OpenAI helpers with graceful fallback when no API key is present."""
from __future__ import annotations

import json
from functools import lru_cache

from .config import settings


@lru_cache(maxsize=1)
def _client():
    if not settings.ai_enabled:
        return None
    try:
        from openai import OpenAI

        return OpenAI(api_key=settings.openai_api_key)
    except Exception:
        return None


def chat_json(system: str, user: str) -> dict | None:
    """Return a JSON object from the chat model, or None if unavailable."""
    client = _client()
    if client is None:
        return None
    try:
        resp = client.chat.completions.create(
            model=settings.openai_chat_model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return json.loads(resp.choices[0].message.content or "{}")
    except Exception:
        return None


def chat_text(system: str, user: str) -> str | None:
    client = _client()
    if client is None:
        return None
    try:
        resp = client.chat.completions.create(
            model=settings.openai_chat_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return resp.choices[0].message.content
    except Exception:
        return None


def embed(text: str) -> list[float] | None:
    client = _client()
    if client is None:
        return None
    try:
        resp = client.embeddings.create(
            model=settings.openai_embed_model, input=text[:8000]
        )
        return resp.data[0].embedding
    except Exception:
        return None
