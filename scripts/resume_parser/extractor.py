from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from io import BytesIO
import logging
from pathlib import Path
import shutil
from typing import Any


class ResumeExtractionError(RuntimeError):
    """Raised when input text cannot be extracted."""


@dataclass(slots=True)
class ExtractResult:
    raw_text: str
    source_file: Path
    extraction_method: str
    ocr_used: bool = False
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class _PageExtraction:
    text: str
    used_ocr: bool = False
    warnings: list[str] = field(default_factory=list)


def extract_text_from_path(path: str | Path) -> ExtractResult:
    file_path = Path(path).expanduser().resolve()
    if not file_path.exists():
        raise ResumeExtractionError(f"Input file does not exist: {file_path}")

    suffix = file_path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return ExtractResult(
            raw_text=file_path.read_text(encoding="utf-8"),
            source_file=file_path,
            extraction_method="text",
        )

    if suffix != ".pdf":
        raise ResumeExtractionError(
            f"Unsupported file type `{suffix or '<none>'}`. Only PDF and text files are supported."
        )

    return _extract_pdf_text(file_path)


def _extract_pdf_text(path: Path) -> ExtractResult:
    warnings: list[str] = []
    fitz_module = _import_optional_module("fitz")

    if fitz_module is not None:
        try:
            result = _extract_pdf_text_with_pymupdf(path, fitz_module)
            result.warnings.extend(warnings)
            return result
        except ResumeExtractionError:
            raise
        except Exception as exc:  # pragma: no cover - defensive fallback
            warnings.append(f"PyMuPDF extraction failed: {exc}")
    else:
        warnings.append("PyMuPDF is not installed; falling back to pypdf.")

    result = _extract_pdf_text_with_pypdf(path)
    result.warnings = [*warnings, *result.warnings]
    return result


def _extract_pdf_text_with_pymupdf(path: Path, fitz_module: Any) -> ExtractResult:
    doc = fitz_module.open(str(path))
    try:
        page_texts: list[str] = []
        warnings: list[str] = []
        ocr_used = False

        for page in doc:
            page_extraction = _extract_text_from_fitz_page(page, fitz_module)
            page_texts.append(page_extraction.text)
            warnings.extend(page_extraction.warnings)
            ocr_used = ocr_used or page_extraction.used_ocr

        raw_text = "\n\n".join(text for text in page_texts if text.strip()).strip()
        if not raw_text:
            raise ResumeExtractionError(
                "No extractable text found in PDF. OCR is unavailable or did not return readable text."
            )

        return ExtractResult(
            raw_text=raw_text,
            source_file=path,
            extraction_method="pymupdf+ocr" if ocr_used else "pymupdf",
            ocr_used=ocr_used,
            warnings=warnings,
        )
    finally:
        doc.close()


def _extract_text_from_fitz_page(page: Any, fitz_module: Any) -> _PageExtraction:
    warnings: list[str] = []

    initial_text = _extract_page_text_from_textpage(page)
    if not _page_needs_ocr(initial_text):
        return _PageExtraction(text=initial_text)

    ocr_text = _extract_page_text_with_fitz_ocr(page)
    if ocr_text:
        warnings.append("Used PyMuPDF OCR fallback for at least one page.")
        return _PageExtraction(text=ocr_text, used_ocr=True, warnings=warnings)

    pytesseract_text = _extract_page_text_with_pytesseract(page, fitz_module)
    if pytesseract_text:
        warnings.append("Used pytesseract OCR fallback for at least one page.")
        return _PageExtraction(text=pytesseract_text, used_ocr=True, warnings=warnings)

    return _PageExtraction(text=initial_text, warnings=warnings)


def _extract_page_text_from_textpage(page: Any, textpage: Any | None = None) -> str:
    blocks = page.get_text("blocks", sort=True, textpage=textpage)
    words = page.get_text("words", sort=True, textpage=textpage)
    return _compose_page_text(blocks, words, float(page.rect.width))


def _compose_page_text(blocks: list[tuple[Any, ...]], words: list[tuple[Any, ...]], page_width: float) -> str:
    text_blocks = [block for block in blocks if len(block) >= 7 and block[6] == 0 and str(block[4]).strip()]
    if not text_blocks and words:
        return _compose_text_from_words(words)

    ordered_blocks = _order_blocks(text_blocks, words, page_width)
    block_lines = _build_block_lines_from_words(words)

    rendered_blocks: list[str] = []
    for block in ordered_blocks:
        block_no = int(block[5])
        text = "\n".join(block_lines.get(block_no, [])) or str(block[4]).strip()
        text = text.strip()
        if text:
            rendered_blocks.append(text)

    return "\n".join(rendered_blocks).strip()


def _order_blocks(
    blocks: list[tuple[Any, ...]], words: list[tuple[Any, ...]], page_width: float
) -> list[tuple[Any, ...]]:
    if _looks_like_two_column_page(words, page_width):
        split_x = page_width / 2
        left = [block for block in blocks if _block_center_x(block) <= split_x]
        right = [block for block in blocks if _block_center_x(block) > split_x]
        return [
            *sorted(left, key=lambda item: (round(float(item[1]), 2), round(float(item[0]), 2))),
            *sorted(right, key=lambda item: (round(float(item[1]), 2), round(float(item[0]), 2))),
        ]

    return sorted(blocks, key=lambda item: (round(float(item[1]), 2), round(float(item[0]), 2)))


def _build_block_lines_from_words(words: list[tuple[Any, ...]]) -> dict[int, list[str]]:
    lines_by_block: dict[int, dict[int, list[tuple[int, str]]]] = {}
    for word in words:
        if len(word) < 8:
            continue
        token = str(word[4]).strip()
        if not token:
            continue
        block_no = int(word[5])
        line_no = int(word[6])
        word_no = int(word[7])
        lines_by_block.setdefault(block_no, {}).setdefault(line_no, []).append((word_no, token))

    rendered: dict[int, list[str]] = {}
    for block_no, lines in lines_by_block.items():
        rendered[block_no] = [
            " ".join(token for _, token in sorted(tokens, key=lambda item: item[0])).strip()
            for _, tokens in sorted(lines.items(), key=lambda item: item[0])
        ]
    return rendered


def _compose_text_from_words(words: list[tuple[Any, ...]]) -> str:
    by_line: dict[tuple[int, int], list[tuple[int, str]]] = {}
    for word in words:
        if len(word) < 8:
            continue
        token = str(word[4]).strip()
        if not token:
            continue
        key = (int(word[5]), int(word[6]))
        by_line.setdefault(key, []).append((int(word[7]), token))

    lines: list[str] = []
    for _, tokens in sorted(by_line.items(), key=lambda item: item[0]):
        line = " ".join(token for _, token in sorted(tokens, key=lambda item: item[0])).strip()
        if line:
            lines.append(line)
    return "\n".join(lines).strip()


def _looks_like_two_column_page(words: list[tuple[Any, ...]], page_width: float) -> bool:
    if len(words) < 40 or page_width <= 0:
        return False

    centers = [((float(word[0]) + float(word[2])) / 2) for word in words if len(word) >= 8]
    if not centers:
        return False

    left = sum(center < page_width * 0.42 for center in centers)
    right = sum(center > page_width * 0.58 for center in centers)
    middle = len(centers) - left - right
    return left >= 15 and right >= 15 and middle <= max(6, len(centers) * 0.18)


def _block_center_x(block: tuple[Any, ...]) -> float:
    return (float(block[0]) + float(block[2])) / 2


def _page_needs_ocr(text: str) -> bool:
    visible_chars = sum(1 for char in text if char.isalnum() or "\u4e00" <= char <= "\u9fff")
    return visible_chars < 40


def _extract_page_text_with_fitz_ocr(page: Any) -> str:
    try:
        textpage = page.get_textpage_ocr(language="eng+chi_sim", dpi=300, full=True)
    except Exception:
        return ""
    return _extract_page_text_from_textpage(page, textpage=textpage)


def _extract_page_text_with_pytesseract(page: Any, fitz_module: Any) -> str:
    pytesseract = _import_optional_module("pytesseract")
    pillow_image = _import_pillow_image()

    if pytesseract is None or pillow_image is None or shutil.which("tesseract") is None:
        return ""

    matrix = fitz_module.Matrix(2, 2)
    pixmap = page.get_pixmap(matrix=matrix, alpha=False)
    image = pillow_image.open(BytesIO(pixmap.tobytes("png")))
    try:
        return str(pytesseract.image_to_string(image, lang="eng+chi_sim", config="--psm 6")).strip()
    except Exception:
        return ""


def _extract_pdf_text_with_pypdf(path: Path) -> ExtractResult:
    warnings: list[str] = []
    try:
        pypdf_module = import_module("pypdf")
        PdfReader = getattr(pypdf_module, "PdfReader")
    except ImportError as exc:
        raise ResumeExtractionError(
            "PDF parsing requires `pypdf`. Run this script via the repo uv environment."
        ) from exc

    logging.getLogger("pypdf").setLevel(logging.ERROR)
    logging.getLogger("pypdf._reader").setLevel(logging.ERROR)

    try:
        reader = PdfReader(str(path), strict=False)
    except Exception as exc:  # pragma: no cover - depends on parser internals
        raise ResumeExtractionError(f"Failed to read PDF file: {path}") from exc

    pages: list[str] = []
    for page in reader.pages:
        extracted = page.extract_text() or ""
        if extracted.strip():
            pages.append(extracted)

    raw_text = "\n\n".join(pages).strip()
    if not raw_text:
        raise ResumeExtractionError(
            "No extractable text found in PDF. Install PyMuPDF and Tesseract to enable OCR fallback."
        )

    warnings.append("Fell back to pypdf text extraction.")
    return ExtractResult(
        raw_text=raw_text,
        source_file=path,
        extraction_method="pypdf",
        warnings=warnings,
    )


def _import_optional_module(name: str) -> Any | None:
    try:
        return import_module(name)
    except ImportError:
        return None


def _import_pillow_image() -> Any | None:
    try:
        pil_image_module = import_module("PIL.Image")
    except ImportError:
        return None
    return pil_image_module
