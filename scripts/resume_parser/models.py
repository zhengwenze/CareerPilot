from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ResumeBasicInfo:
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    summary: str = ""


@dataclass(slots=True)
class ResumeSkills:
    technical: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ResumeStructuredData:
    basic_info: ResumeBasicInfo = field(default_factory=ResumeBasicInfo)
    education: list[str] = field(default_factory=list)
    work_experience: list[str] = field(default_factory=list)
    projects: list[str] = field(default_factory=list)
    skills: ResumeSkills = field(default_factory=ResumeSkills)
    certifications: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ParseDebugData:
    cleaned_lines: list[str] = field(default_factory=list)
    sections: dict[str, list[str]] = field(default_factory=dict)
    field_confidence: dict[str, float] = field(default_factory=dict)
    extraction_method: str = ""
    ocr_used: bool = False
    extractor_warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ParseResult:
    structured_data: ResumeStructuredData
    raw_text: str
    source_file: Path | None = None
    debug: ParseDebugData = field(default_factory=ParseDebugData)

    def to_dict(self, *, include_debug: bool = False) -> dict[str, Any]:
        payload = self.structured_data.to_dict()
        if not include_debug:
            return payload

        payload["_debug"] = {
            "source_file": str(self.source_file) if self.source_file is not None else None,
            "raw_text": self.raw_text,
            "cleaned_lines": self.debug.cleaned_lines,
            "sections": self.debug.sections,
            "field_confidence": self.debug.field_confidence,
            "extraction_method": self.debug.extraction_method,
            "ocr_used": self.debug.ocr_used,
            "extractor_warnings": self.debug.extractor_warnings,
        }
        return payload
