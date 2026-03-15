from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.resume_parser import extractor


class FakePage:
    def __init__(
        self,
        *,
        width: float = 600.0,
        blocks: list[tuple] | None = None,
        words: list[tuple] | None = None,
        ocr_blocks: list[tuple] | None = None,
        ocr_words: list[tuple] | None = None,
    ) -> None:
        self.rect = SimpleNamespace(width=width)
        self._blocks = blocks or []
        self._words = words or []
        self._ocr_blocks = ocr_blocks or []
        self._ocr_words = ocr_words or []

    def get_text(self, mode: str, sort: bool = True, textpage=None):
        if textpage is None:
            if mode == "blocks":
                return self._blocks
            if mode == "words":
                return self._words
        else:
            if mode == "blocks":
                return self._ocr_blocks
            if mode == "words":
                return self._ocr_words
        raise AssertionError(f"Unexpected get_text call: mode={mode!r}, textpage={textpage!r}")

    def get_textpage_ocr(self, language: str, dpi: int, full: bool):
        if not self._ocr_blocks and not self._ocr_words:
            raise RuntimeError("ocr unavailable")
        return "ocr-textpage"


class FakeDocument:
    def __init__(self, pages: list[FakePage]) -> None:
        self._pages = pages

    def __iter__(self):
        return iter(self._pages)

    def close(self) -> None:
        return None


def test_extract_pdf_prefers_pymupdf_blocks_words(monkeypatch, tmp_path: Path) -> None:
    pdf_path = tmp_path / "resume.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    page = FakePage(
        blocks=[
            (40, 20, 200, 50, "ignored block text", 0, 0),
            (40, 80, 220, 110, "ignored block text", 1, 0),
        ],
        words=[
            (40, 20, 80, 30, "郑文泽", 0, 0, 0),
            (40, 80, 90, 90, "教育背景", 1, 0, 0),
            (40, 95, 120, 105, "新疆大学", 1, 1, 0),
        ],
    )
    fitz_module = SimpleNamespace(open=lambda _: FakeDocument([page]))

    monkeypatch.setattr(extractor, "_import_optional_module", lambda name: fitz_module if name == "fitz" else None)

    result = extractor.extract_text_from_path(pdf_path)

    assert result.extraction_method == "pymupdf"
    assert result.ocr_used is False
    assert "郑文泽" in result.raw_text
    assert "新疆大学" in result.raw_text


def test_extract_pdf_uses_pymupdf_ocr_when_page_text_missing(monkeypatch, tmp_path: Path) -> None:
    pdf_path = tmp_path / "resume.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    page = FakePage(
        blocks=[],
        words=[],
        ocr_blocks=[(40, 20, 220, 50, "ignored ocr text", 0, 0)],
        ocr_words=[
            (40, 20, 80, 30, "扫描简历", 0, 0, 0),
            (90, 20, 180, 30, "可识别文本", 0, 0, 1),
        ],
    )
    fitz_module = SimpleNamespace(open=lambda _: FakeDocument([page]))

    monkeypatch.setattr(extractor, "_import_optional_module", lambda name: fitz_module if name == "fitz" else None)

    result = extractor.extract_text_from_path(pdf_path)

    assert result.extraction_method == "pymupdf+ocr"
    assert result.ocr_used is True
    assert "扫描简历 可识别文本" in result.raw_text


def test_extract_pdf_falls_back_to_pypdf_when_pymupdf_missing(monkeypatch, tmp_path: Path) -> None:
    pdf_path = tmp_path / "resume.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    class FakePdfPage:
        def extract_text(self) -> str:
            return "来自 pypdf 的文本"

    class FakePdfReader:
        def __init__(self, path: str, strict: bool = False) -> None:
            self.pages = [FakePdfPage()]

    monkeypatch.setattr(extractor, "_import_optional_module", lambda name: None)
    monkeypatch.setattr(extractor, "import_module", lambda name: SimpleNamespace(PdfReader=FakePdfReader))

    result = extractor.extract_text_from_path(pdf_path)

    assert result.extraction_method == "pypdf"
    assert result.ocr_used is False
    assert "来自 pypdf 的文本" in result.raw_text
    assert any("pypdf" in warning for warning in result.warnings)
