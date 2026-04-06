from __future__ import annotations

EMPTY_PROVIDER_VALUES = {"", "disabled", "none", "off"}


def normalize_ai_provider(provider: str | None) -> str:
    return (provider or "").strip().lower()


def provider_requires_api_key(provider: str | None) -> bool:
    return normalize_ai_provider(provider) not in {"ollama", "codex2gpt", *EMPTY_PROVIDER_VALUES}


def is_ai_configured(
    *,
    provider: str | None,
    base_url: str | None,
    model: str | None,
    api_key: str | None,
) -> bool:
    normalized_provider = normalize_ai_provider(provider)
    if normalized_provider in EMPTY_PROVIDER_VALUES:
        return False
    if not (base_url or "").strip():
        return False
    if not (model or "").strip():
        return False
    if provider_requires_api_key(normalized_provider):
        return bool((api_key or "").strip())
    return True
