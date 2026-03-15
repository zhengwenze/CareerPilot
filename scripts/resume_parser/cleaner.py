from __future__ import annotations

import re
import unicodedata

SECTION_BREAK_PATTERN = re.compile(r"\s{2,}|[|｜]")
BULLET_PREFIX = re.compile(r"^(?:[-*•·●▪■◆]|[0-9]+[.)、])\s*")


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    normalized = normalized.replace("\u3000", " ").replace("\r", "\n")
    normalized = re.sub(r"[ \t]+", " ", normalized)
    return normalized.strip()


def normalize_lines(raw_text: str) -> list[str]:
    lines: list[str] = []
    for block in raw_text.splitlines():
        normalized = normalize_text(block)
        if not normalized:
            continue
        parts = [item.strip() for item in SECTION_BREAK_PATTERN.split(normalized) if item.strip()]
        lines.extend(parts or [normalized])
    return lines


def clean_list_line(line: str) -> str:
    return BULLET_PREFIX.sub("", normalize_text(line)).strip()


def dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = normalize_text(item)
        if not normalized:
            continue
        lowered = normalized.casefold()
        if lowered in seen:
            continue
        seen.add(lowered)
        result.append(normalized)
    return result
