from __future__ import annotations

from pathlib import Path

from .extractor import extract_text_from_path
from .parser import parse_resume_text as _parse_resume_text


def parse_resume_text(raw_text: str):
    return _parse_resume_text(raw_text)


def parse_resume_file(path: str | Path):
    extracted = extract_text_from_path(path)
    result = _parse_resume_text(extracted.raw_text)
    result.source_file = extracted.source_file
    result.debug.extraction_method = extracted.extraction_method
    result.debug.ocr_used = extracted.ocr_used
    result.debug.extractor_warnings = extracted.warnings
    return result
