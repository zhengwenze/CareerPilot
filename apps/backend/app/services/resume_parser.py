from __future__ import annotations
import re
import subprocess
import tempfile
import unicodedata
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree
from pypdf import PdfReader
from app.core.errors import ApiException, ErrorCode
from app.schemas.resume import ResumeParseArtifactsData, ResumeStructuredData

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_PATTERN = re.compile(r"(?:\+?\d[\d\s-]{7,}\d)")
CJK_SPACING_PATTERN = re.compile(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])")
SECTION_BREAK_PATTERN = re.compile(r"\s{2,}|[|｜]")
URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)
BULLET_PREFIX = re.compile(r"^(?:[-*•·●▪■◆]|[0-9]+[.)、])\s*")
DATE_SPAN_PATTERN = re.compile(
    r"(?:20\d{2}|19\d{2})\s*[./-]\s*(?:20\d{2}|19\d{2}|至今|present)",
    re.IGNORECASE,
)
DATE_RANGE_PATTERN = re.compile(
    r"((?:19|20)\d{2}\s*[./-]\s*\d{1,2})\s*[–—-]\s*((?:19|20)\d{2}\s*[./-]\s*\d{1,2}|至今|present)",
    re.IGNORECASE,
)
GPA_PATTERN = re.compile(r"GPA\s*([0-9]+(?:\.[0-9]+)?)", re.IGNORECASE)

SECTION_PATTERNS = {
    "education": [
        "教育",
        "教育经历",
        "教育背景",
        "education",
    ],
    "work_experience": [
        "工作经历",
        "实习经历",
        "experience",
        "professional experience",
    ],
    "projects": [
        "项目经历",
        "项目经验",
        "项目背景",
        "projects",
        "project experience",
    ],
    "skills": [
        "技能",
        "专业技能",
        "skills",
        "skill",
        "tech stack",
    ],
    "certifications": [
        "证书",
        "证书奖项",
        "竞赛获奖",
        "科研成果",
        "软件著作权",
        "certifications",
        "awards",
    ],
    "summary": [
        "个人优势",
        "个人评价",
        "自我评价",
        "个人总结",
        "个人简介",
    ],
}
INLINE_SECTION_HEADINGS = (
    "教育背景",
    "教育经历",
    "工作经历",
    "实习经历",
    "项目经历",
    "项目经验",
    "项目背景",
    "专业技能",
    "技术栈",
    "项目成果",
    "证书奖项",
    "竞赛获奖",
    "科研成果",
    "软件著作权",
)

TECHNICAL_KEYWORDS = [
    "A/B Testing",
    "Airflow",
    "C++",
    "Django",
    "Docker",
    "Excel",
    "FastAPI",
    "Flask",
    "Git",
    "Hadoop",
    "Java",
    "Python",
    "JavaScript",
    "Kubernetes",
    "Looker",
    "Machine Learning",
    "MySQL",
    "Next.js",
    "NextJS",
    "NumPy",
    "Pandas",
    "Power BI",
    "PostgreSQL",
    "PyTorch",
    "React",
    "Redis",
    "MinIO",
    "RocketMQ",
    "SQLAlchemy",
    "Spring Boot",
    "RESTful API",
    "Prompt Engineering",
    "scikit-learn",
    "Spark",
    "SQL",
    "Tableau",
    "TensorFlow",
    "TypeScript",
    "Vue",
    "数据分析",
    "数据建模",
    "实验分析",
    "指标体系",
    "用户增长",
]
TOOL_KEYWORDS = [
    "Docker",
    "Figma",
    "Git",
    "Jira",
    "Linux",
    "MATLAB",
    "Notion",
    "Photoshop",
    "Postman",
    "PRD",
    "SPSS",
    "Visio",
    "Xmind",
]
LANGUAGE_KEYWORDS = [
    "英语",
    "英文",
    "法语",
    "日语",
    "韩语",
    "粤语",
    "普通话",
    "English",
    "French",
    "Japanese",
    "Korean",
]
LOCATION_KEYWORDS = [
    "北京",
    "上海",
    "广州",
    "深圳",
    "杭州",
    "成都",
    "武汉",
    "苏州",
    "南京",
    "remote",
]
EDUCATION_HINTS = (
    "大学",
    "学院",
    "university",
    "college",
    "school",
    "本科",
    "硕士",
    "博士",
    "学历",
    "专业",
    "gpa",
)
WORK_HINTS = (
    "有限公司",
    "公司",
    "实习",
    "工程师",
    "经理",
    "分析师",
    "产品",
    "运营",
    "研发",
    "intern",
)
PROJECT_HINTS = (
    "项目",
    "平台",
    "系统",
    "课题",
    "project",
    "负责开发",
    "上线",
    "搭建",
    "重构",
)
SKILL_HINTS = (
    "技能",
    "熟悉",
    "掌握",
    "技术栈",
    "skill",
    "stack",
    "tool",
    "工具",
)
CERTIFICATION_HINTS = (
    "证书",
    "证照",
    "certification",
    "award",
    "奖学金",
    "cfa",
    "pmp",
    "cpa",
    "cet",
)
PROJECT_ACTION_PREFIXES = (
    "负责",
    "基于",
    "使用",
    "接入",
    "扩展",
    "完成",
    "设计",
    "搭建",
    "开发",
    "主导",
    "优化",
    "实现",
    "参与",
    "推动",
    "支持",
    "维护",
    "协助",
)


@dataclass(slots=True)
class ResumeTextExtractionResult:
    raw_text: str
    source_type: str
    ocr_used: bool = False
    ocr_engine: str = "none"
    ocr_avg_confidence: float | None = None


def extract_text_from_resume_bytes(
    *,
    data: bytes,
    file_name: str,
) -> ResumeTextExtractionResult:
    source_type = _detect_source_type(file_name)
    if source_type == "pdf":
        return extract_text_from_pdf_or_ocr_bytes(data)
    if source_type == "docx":
        return ResumeTextExtractionResult(
            raw_text=extract_text_from_docx_bytes(data),
            source_type="docx",
        )
    if source_type == "image":
        return ResumeTextExtractionResult(
            raw_text=extract_text_from_image_bytes(data),
            source_type="image",
            ocr_used=True,
            ocr_engine="tesseract",
        )
    raise ApiException(
        status_code=400,
        code=ErrorCode.BAD_REQUEST,
        message="Unsupported resume file type",
    )


def extract_text_from_pdf_bytes(data: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(data))
    except Exception as exc:
        raise ApiException(
            status_code=400,
            code=ErrorCode.BAD_REQUEST,
            message="Failed to read PDF file",
            details={"reason": str(exc)},
        ) from exc

    pages: list[str] = []
    for index, page in enumerate(reader.pages):
        extracted = page.extract_text() or ""
        cleaned = _normalize_text(extracted)
        if cleaned:
            pages.append(cleaned)

    raw_text = "\n\n".join(pages).strip()
    if not raw_text:
        raise ApiException(
            status_code=400,
            code=ErrorCode.BAD_REQUEST,
            message="No extractable text found in PDF. Scanned PDFs are not supported yet.",
        )
    return raw_text


def extract_text_from_pdf_or_ocr_bytes(data: bytes) -> ResumeTextExtractionResult:
    try:
        raw_text = extract_text_from_pdf_bytes(data)
        return ResumeTextExtractionResult(
            raw_text=raw_text,
            source_type="pdf",
            ocr_used=False,
            ocr_engine="none",
        )
    except ApiException as exc:
        if "No extractable text found in PDF" not in exc.message:
            raise

    ocr_text = extract_text_from_scanned_pdf_bytes(data)
    return ResumeTextExtractionResult(
        raw_text=ocr_text,
        source_type="pdf",
        ocr_used=True,
        ocr_engine="tesseract",
    )


def extract_text_from_docx_bytes(data: bytes) -> str:
    try:
        with zipfile.ZipFile(BytesIO(data)) as archive:
            document_xml = archive.read("word/document.xml")
    except Exception as exc:
        raise ApiException(
            status_code=400,
            code=ErrorCode.BAD_REQUEST,
            message="Failed to read DOCX file",
            details={"reason": str(exc)},
        ) from exc

    try:
        root = ElementTree.fromstring(document_xml)
    except ElementTree.ParseError as exc:
        raise ApiException(
            status_code=400,
            code=ErrorCode.BAD_REQUEST,
            message="Failed to parse DOCX document XML",
            details={"reason": str(exc)},
        ) from exc

    namespaces = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", namespaces):
        texts = [
            node.text or ""
            for node in paragraph.findall(".//w:t", namespaces)
            if (node.text or "").strip()
        ]
        joined = _normalize_text("".join(texts))
        if joined:
            paragraphs.append(joined)

    raw_text = "\n".join(paragraphs).strip()
    if not raw_text:
        raise ApiException(
            status_code=400,
            code=ErrorCode.BAD_REQUEST,
            message="No extractable text found in DOCX file",
        )
    return raw_text


def extract_text_from_image_bytes(data: bytes) -> str:
    try:
        image_module = _load_pillow_image_module()
        image = image_module.open(BytesIO(data))
        image.load()
    except Exception as exc:
        raise ApiException(
            status_code=400,
            code=ErrorCode.BAD_REQUEST,
            message="Failed to read image resume",
            details={"reason": str(exc)},
        ) from exc

    return _ocr_pil_image(image)


def extract_text_from_scanned_pdf_bytes(data: bytes) -> str:
    image_module = _load_pillow_image_module()
    try:
        reader = PdfReader(BytesIO(data))
    except Exception as exc:
        raise ApiException(
            status_code=400,
            code=ErrorCode.BAD_REQUEST,
            message="Failed to read PDF file",
            details={"reason": str(exc)},
        ) from exc

    page_texts: list[str] = []
    for page in reader.pages:
        page_images = getattr(page, "images", []) or []
        for page_image in page_images:
            image_bytes = getattr(page_image, "data", None)
            if not image_bytes:
                continue
            try:
                image = image_module.open(BytesIO(image_bytes))
                image.load()
            except Exception:
                continue
            ocr_text = _ocr_pil_image(image)
            if ocr_text:
                page_texts.append(ocr_text)

    raw_text = "\n\n".join(page_texts).strip()
    if not raw_text:
        raise ApiException(
            status_code=400,
            code=ErrorCode.BAD_REQUEST,
            message="No extractable text found in scanned PDF after OCR",
        )
    return raw_text


def _ocr_pil_image(image) -> str:
    prepared = image.convert("L")
    with tempfile.NamedTemporaryFile(suffix=".png") as temp_input:
        prepared.save(temp_input.name, format="PNG")
        raw_text = _run_tesseract(temp_input.name)
    normalized = _normalize_text(raw_text)
    if not normalized:
        raise ApiException(
            status_code=400,
            code=ErrorCode.BAD_REQUEST,
            message="OCR could not extract text from resume image",
        )
    return normalized


def _run_tesseract(image_path: str) -> str:
    candidate_commands = [
        ["tesseract", image_path, "stdout", "-l", "chi_sim+eng"],
        ["tesseract", image_path, "stdout", "-l", "eng"],
        ["tesseract", image_path, "stdout"],
    ]
    for command in candidate_commands:
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            raise ApiException(
                status_code=500,
                code=ErrorCode.INTERNAL_ERROR,
                message="Tesseract OCR is not installed on the server",
            ) from exc
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
    raise ApiException(
        status_code=400,
        code=ErrorCode.BAD_REQUEST,
        message="OCR failed to extract text from resume file",
    )


def _load_pillow_image_module():
    try:
        from PIL import Image  # type: ignore
    except ModuleNotFoundError as exc:
        raise ApiException(
            status_code=500,
            code=ErrorCode.INTERNAL_ERROR,
            message="Pillow is required for image OCR support",
        ) from exc
    return Image


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    normalized = normalized.replace("\u3000", " ").replace("\r", "\n")
    normalized = CJK_SPACING_PATTERN.sub("", normalized)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    return normalized.strip()


def _inject_inline_section_breaks(value: str) -> str:
    result = value
    for heading in INLINE_SECTION_HEADINGS:
        result = re.sub(rf"([^\s\n|｜])({re.escape(heading)})", r"\1\n\2", result)
    return result


def _normalize_lines(raw_text: str) -> list[str]:
    prepared_text = _inject_inline_section_breaks(_normalize_text(raw_text))
    lines: list[str] = []
    for block in prepared_text.splitlines():
        normalized = _normalize_text(block)
        if not normalized:
            continue
        parts = [item.strip() for item in SECTION_BREAK_PATTERN.split(normalized) if item.strip()]
        lines.extend(parts or [normalized])
    return lines


def _find_first_match(pattern: re.Pattern[str], lines: list[str], raw_text: str) -> str:
    for chunk in [*lines, raw_text]:
        match = pattern.search(chunk)
        if match:
            return match.group(0).strip().replace(" ", "")
    return ""


def _detect_location(lines: list[str]) -> str:
    joined = " ".join(lines).lower()
    for keyword in LOCATION_KEYWORDS:
        if keyword.lower() in joined:
            return keyword
    return ""


def _guess_name(lines: list[str]) -> str:
    if lines:
        match = re.match(
            r"^([\u4e00-\u9fffA-Za-z·\s]{2,30}?)(?=(?:电话|手机|邮箱|email|phone)\s*[:：])",
            lines[0],
            re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()

    for line in lines[:5]:
        lowered = line.lower()
        if EMAIL_PATTERN.search(line) or PHONE_PATTERN.search(line):
            continue
        if _match_section(line) is not None:
            continue
        if _looks_like_education_line(line) or _looks_like_work_line(line) or _looks_like_project_line(line):
            continue
        if any(keyword.lower() in lowered for keyword in LOCATION_KEYWORDS):
            continue
        if len(line) <= 24 and len(line.split()) <= 4:
            return line
    return ""


def _guess_summary(lines: list[str]) -> str:
    summary_lines: list[str] = []
    for line in lines[1:8]:
        if _match_section(line) is not None:
            break
        if EMAIL_PATTERN.search(line) or PHONE_PATTERN.search(line):
            continue
        if any(token in line for token in LOCATION_KEYWORDS):
            continue
        if any(token in line for token in ("到岗", "实习", "求职方向")):
            continue
        if _looks_like_education_line(line) or _looks_like_work_line(line) or _looks_like_project_line(line):
            continue
        summary_lines.append(line)
    return " ".join(summary_lines[:3]).strip()


def _match_section(line: str) -> str | None:
    normalized = BULLET_PREFIX.sub("", line.strip()).lower().rstrip(":：")
    for section, headings in SECTION_PATTERNS.items():
        for heading in sorted(headings, key=len, reverse=True):
            if normalized == heading:
                return section
            if normalized.startswith(f"{heading}:") or normalized.startswith(f"{heading}："):
                return section
            if normalized.startswith(f"{heading} "):
                return section
            if normalized.startswith(heading):
                return section
    return None


def _split_sections(lines: list[str]) -> dict[str, list[str]]:
    sections = {
        "education": [],
        "work_experience": [],
        "projects": [],
        "skills": [],
        "certifications": [],
        "summary": [],
    }
    current_section: str | None = None

    for line in lines:
        matched = _match_section(line)
        if matched is not None:
            current_section = matched
            remainder = _strip_section_heading(line, matched)
            if remainder:
                sections[current_section].append(remainder)
            continue
        if current_section is not None:
            sections[current_section].append(_clean_list_line(line))

    return sections


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = item.strip()
        if not normalized:
            continue
        lowered = normalized.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        result.append(normalized)
    return result


def _clean_list_line(line: str) -> str:
    return BULLET_PREFIX.sub("", line).strip()


def _strip_section_heading(line: str, section: str) -> str:
    normalized = _clean_list_line(line)
    for heading in sorted(SECTION_PATTERNS[section], key=len, reverse=True):
        pattern = re.compile(rf"^{re.escape(heading)}(?:\s*[:：]\s*|\s+)?", re.IGNORECASE)
        if pattern.match(normalized):
            return pattern.sub("", normalized, count=1).strip()
    return ""


def _extract_keyword_tags(lines: list[str], raw_text: str, keywords: list[str]) -> list[str]:
    joined = " ".join(lines).lower()
    haystack = f"{joined} {raw_text.lower()}"
    found: list[str] = []
    for keyword in keywords:
        if keyword.lower() in haystack:
            found.append(keyword)
    return _dedupe_preserve_order(found)


def _extract_keyword_tags_from_text(text: str, keywords: list[str]) -> list[str]:
    return _extract_keyword_tags([text], text, keywords)


def _extract_objective_lines(lines: list[str]) -> list[str]:
    objective_lines: list[str] = []
    for line in lines[:8]:
        if _match_section(line) is not None:
            break
        if "求职方向" in line:
            objective_lines.append(line)
    return objective_lines


def _normalize_date_value(value: str) -> str:
    compact = re.sub(r"\s+", "", value)
    return compact.replace("-", ".").replace("/", ".")


def _extract_date_range(line: str) -> tuple[str, str]:
    match = DATE_RANGE_PATTERN.search(line)
    if not match:
        return "", ""
    return _normalize_date_value(match.group(1)), _normalize_date_value(match.group(2))


def _merge_wrapped_lines(lines: list[str]) -> list[str]:
    merged: list[str] = []
    for line in lines:
        normalized = _clean_list_line(line)
        if not normalized:
            continue
        if (
            merged
            and _match_section(normalized) is None
            and not DATE_RANGE_PATTERN.search(normalized)
            and (
                normalized[:1] in {";", "；", "，", ",", "、", "）", ")"}
                or len(normalized) <= 12
                or normalized.startswith(("英", "软", "证"))
            )
        ):
            merged[-1] = f"{merged[-1]}{normalized}"
            continue
        merged.append(normalized)
    return merged


def _build_education_items(lines: list[str]) -> list[dict[str, object]]:
    merged_lines = _merge_wrapped_lines(lines)
    items: list[dict[str, object]] = []
    current: dict[str, object] | None = None

    for line in merged_lines:
        if (
            current is None
            or _extract_date_range(line) != ("", "")
            or any(token in line for token in ("大学", "学院", "University", "College"))
        ):
            if current is not None:
                items.append(current)
            start_date, end_date = _extract_date_range(line)
            school = ""
            school_match = re.match(r"^([^\s(（]+(?:大学|学院|University|College))", line, re.IGNORECASE)
            if school_match:
                school = school_match.group(1).strip()
            degree = ""
            for candidate in ("本科", "硕士", "博士", "大专", "MBA", "Master", "Bachelor", "PhD"):
                if candidate.lower() in line.lower():
                    degree = candidate
                    break
            major = ""
            major_match = re.search(
                r"(?:本科|硕士|博士|大专|MBA|Master|Bachelor|PhD)\s*/\s*([^\d()（）]+?)(?=\s+(?:19|20)\d{2})",
                line,
                re.IGNORECASE,
            )
            if major_match:
                major = major_match.group(1).strip(" /")
            current = {
                "id": f"edu_{len(items) + 1}",
                "school": school or line,
                "degree": degree,
                "major": major,
                "start_date": start_date,
                "end_date": end_date,
                "gpa": "",
                "honors": _extract_parenthetical_tokens(line),
                "source_refs": [],
            }
            continue

        if current is None:
            continue
        gpa_match = GPA_PATTERN.search(line)
        if gpa_match:
            current["gpa"] = gpa_match.group(1)
        current_honors = list(current["honors"])
        for fragment in re.split(r"[；;，,]", line):
            cleaned = fragment.strip(" 。")
            if cleaned and cleaned not in current_honors:
                current_honors.append(cleaned)
        current["honors"] = current_honors

    if current is not None:
        items.append(current)
    return items


def _extract_parenthetical_tokens(line: str) -> list[str]:
    honors: list[str] = []
    for token in re.findall(r"[（(]([^()（）]+)[)）]", line):
        for item in re.split(r"[/／]", token):
            cleaned = item.strip()
            if cleaned:
                honors.append(cleaned)
    return _dedupe_preserve_order(honors)


def _looks_like_project_action_line(line: str) -> bool:
    stripped = _clean_list_line(line)
    return stripped.startswith(PROJECT_ACTION_PREFIXES)


def _looks_like_project_header(line: str) -> bool:
    stripped = _clean_list_line(line)
    if not stripped:
        return False
    if _looks_like_project_action_line(stripped):
        return False
    if DATE_RANGE_PATTERN.search(stripped):
        return True
    if URL_PATTERN.search(stripped):
        return True
    if "项目" in stripped and len(stripped) <= 40:
        return True
    return len(stripped) <= 40 and all(token not in stripped for token in ("：", ";", "；", "。"))


def _project_name_from_header(line: str) -> str:
    return URL_PATTERN.sub("", line).strip(" -|")


def _build_project_items(lines: list[str]) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    current: dict[str, object] | None = None

    for raw_line in lines:
        line = _clean_list_line(raw_line)
        if not line:
            continue
        if _looks_like_project_header(line) and (
            current is None or current["bullets"] or current["summary"]
        ):
            if current is not None:
                current["skills_used"] = _extract_keyword_tags_from_text(
                    " ".join(
                        [
                            current["name"],
                            current["role"],
                            current["summary"],
                            *[bullet["text"] for bullet in current["bullets"]],
                        ]
                    ),
                    TECHNICAL_KEYWORDS + TOOL_KEYWORDS,
                )
                items.append(current)
            start_date, end_date = _extract_date_range(line)
            current = {
                "id": f"proj_{len(items) + 1}",
                "name": _project_name_from_header(line),
                "role": "",
                "start_date": start_date,
                "end_date": end_date,
                "summary": "",
                "bullets": [],
                "skills_used": [],
                "source_refs": [],
            }
            continue

        if current is None:
            continue

        if not current["summary"] and not _looks_like_project_action_line(line):
            current["summary"] = line
            continue

        current["bullets"].append(
            {
                "id": f"{current['id']}_b{len(current['bullets']) + 1}",
                "text": line,
                "kind": "responsibility",
                "metrics": [],
                "skills_used": _extract_keyword_tags_from_text(line, TECHNICAL_KEYWORDS + TOOL_KEYWORDS),
                "source_refs": [],
            }
        )

    if current is not None:
        current["skills_used"] = _extract_keyword_tags_from_text(
            " ".join(
                [
                    current["name"],
                    current["role"],
                    current["summary"],
                    *[bullet["text"] for bullet in current["bullets"]],
                ]
            ),
            TECHNICAL_KEYWORDS + TOOL_KEYWORDS,
        )
        items.append(current)
    return items


def _build_certification_items(lines: list[str]) -> list[dict[str, object]]:
    merged_lines = _merge_wrapped_lines(lines)
    items: list[dict[str, object]] = []
    for line in merged_lines:
        for fragment in re.split(r"[；;]", line):
            cleaned = fragment.strip(" 。")
            if not cleaned:
                continue
            items.append(
                {
                    "id": f"cert_{len(items) + 1}",
                    "name": cleaned,
                    "issuer": "",
                    "date": "",
                    "source_refs": [],
                }
            )
    return items


def _looks_like_education_line(line: str) -> bool:
    lowered = line.lower()
    return any(token in lowered for token in EDUCATION_HINTS)


def _looks_like_work_line(line: str) -> bool:
    lowered = line.lower()
    if lowered.startswith("实习时间") or lowered.startswith("到岗时间"):
        return False
    if any(token in lowered for token in ("可实习", "立即到岗", "求职方向")):
        return False
    if any(token in lowered for token in EDUCATION_HINTS) and not any(
        token in lowered for token in ("有限公司", "公司", "intern", "工程师", "经理", "分析师", "产品", "运营", "研发")
    ):
        return False
    return bool(DATE_SPAN_PATTERN.search(lowered)) or any(token in lowered for token in WORK_HINTS)


def _looks_like_project_line(line: str) -> bool:
    lowered = line.lower()
    return any(token in lowered for token in PROJECT_HINTS)


def _looks_like_skill_line(line: str) -> bool:
    lowered = line.lower()
    return any(token in lowered for token in SKILL_HINTS)


def _looks_like_certification_line(line: str) -> bool:
    lowered = line.lower()
    return any(token in lowered for token in CERTIFICATION_HINTS)


def _fallback_section_lines(
    *,
    lines: list[str],
    predicate,
    limit: int,
) -> list[str]:
    matches = [
        _clean_list_line(line)
        for line in lines
        if line and _match_section(line) is None and predicate(line)
    ]
    return _dedupe_preserve_order(matches[:limit])


def _has_meaningful_content(structured: ResumeStructuredData) -> bool:
    basic = structured.basic_info
    return any(
        [
            basic.name,
            basic.email,
            basic.phone,
            basic.location,
            basic.summary,
            structured.education,
            structured.work_experience,
            structured.projects,
            structured.skills.technical,
            structured.skills.tools,
            structured.skills.languages,
            structured.certifications,
        ]
    )


def build_structured_resume(raw_text: str) -> ResumeStructuredData:
    lines = _normalize_lines(raw_text)
    sections = _split_sections(lines)
    education_items = _build_education_items(sections["education"])
    education = _dedupe_preserve_order(
        [item["school"] if not item["major"] else f"{item['school']} {item['major']} {item['degree']} {item['start_date']} {item['end_date']}".strip() for item in education_items]
        or sections["education"]
    )
    work_experience = _dedupe_preserve_order(sections["work_experience"])
    project_items = _build_project_items(sections["projects"])
    projects = _dedupe_preserve_order(
        [
            " ".join(
                part
                for part in [
                    item["name"],
                    item["summary"],
                    *[bullet["text"] for bullet in item["bullets"]],
                ]
                if part
            ).strip()
            for item in project_items
        ]
        or sections["projects"]
    )
    certification_items = _build_certification_items(sections["certifications"])
    certifications = _dedupe_preserve_order(
        [item["name"] for item in certification_items] or sections["certifications"]
    )

    if not education:
        education = _fallback_section_lines(
            lines=lines,
            predicate=_looks_like_education_line,
            limit=4,
        )

    if not work_experience:
        work_experience = _fallback_section_lines(
            lines=lines,
            predicate=_looks_like_work_line,
            limit=6,
        )

    if not projects:
        projects = _fallback_section_lines(
            lines=lines,
            predicate=_looks_like_project_line,
            limit=6,
        )

    skill_lines = _dedupe_preserve_order(
        [
            *sections["skills"],
            *_fallback_section_lines(
                lines=lines,
                predicate=_looks_like_skill_line,
                limit=6,
            ),
        ]
    )

    if not certifications:
        certifications = _fallback_section_lines(
            lines=lines,
            predicate=_looks_like_certification_line,
            limit=4,
        )

    structured = ResumeStructuredData(
        basic_info={
            "name": _guess_name(lines),
            "email": _find_first_match(EMAIL_PATTERN, lines, raw_text),
            "phone": _find_first_match(PHONE_PATTERN, lines, raw_text),
            "location": _detect_location(lines),
            "summary": " ".join(
                _dedupe_preserve_order(
                    [*_extract_objective_lines(lines), *sections["summary"]]
                )
            ).strip()
            or _guess_summary(lines),
        },
        education=education,
        education_items=education_items,
        work_experience=work_experience,
        projects=projects,
        project_items=project_items,
        skills={
            "technical": _extract_keyword_tags(
                skill_lines,
                raw_text,
                TECHNICAL_KEYWORDS,
            ),
            "tools": _extract_keyword_tags(
                skill_lines,
                raw_text,
                TOOL_KEYWORDS,
            ),
            "languages": _extract_keyword_tags(
                skill_lines,
                raw_text,
                LANGUAGE_KEYWORDS,
            ),
        },
        certifications=certifications,
        certification_items=certification_items,
    )
    if not _has_meaningful_content(structured):
        raise ApiException(
            status_code=400,
            code=ErrorCode.BAD_REQUEST,
            message="Failed to extract structured resume fields from PDF text",
        )
    return structured


def build_initial_resume_parse_artifacts(
    *,
    file_name: str,
) -> ResumeParseArtifactsData:
    return ResumeParseArtifactsData(
        pipeline={
            "current_stage": "uploaded",
            "history": [
                {
                    "stage": "uploaded",
                    "status": "success",
                    "message": "文件已上传，等待解析",
                }
            ],
        },
        document_blocks=[],
        ocr={"used": False, "engine": "none", "avg_confidence": None},
        quality={
            "text_extractable": False,
            "layout_complexity": "unknown",
            "parser_confidence": 0.0,
        },
        meta={
            "source_type": _detect_source_type(file_name),
            "parser_version": "resume-parser-v2",
            "ai_correction_applied": False,
        },
    )


def build_resume_parse_artifacts(
    *,
    file_name: str,
    raw_text: str | None,
    structured: ResumeStructuredData | None,
    ai_status: str | None,
    parse_status: str,
    parse_error: str | None = None,
    source_type: str | None = None,
    ocr_used: bool = False,
    ocr_engine: str = "none",
) -> ResumeParseArtifactsData:
    document_blocks = _build_document_blocks(raw_text)
    history: list[dict[str, object]] = [
        {
            "stage": "uploaded",
            "status": "success",
            "message": "文件已上传",
        }
    ]

    if raw_text:
        history.append(
            {
                "stage": "extracting_text",
                "status": "success",
                "message": "文本提取成功",
            }
        )
    else:
        history.append(
            {
                "stage": "extracting_text",
                "status": "failed",
                "message": parse_error or "文本提取失败",
            }
        )

    if structured is not None:
        history.append(
            {
                "stage": "rule_parse",
                "status": "success",
                "message": "规则解析成功",
            }
        )
    elif raw_text:
        history.append(
            {
                "stage": "rule_parse",
                "status": "failed",
                "message": parse_error or "规则解析失败",
            }
        )

    if ai_status == "applied":
        history.append(
            {
                "stage": "ai_correction",
                "status": "success",
                "message": "AI 校准已应用",
            }
        )
    elif ai_status == "fallback_rule":
        history.append(
            {
                "stage": "ai_correction",
                "status": "fallback",
                "message": "AI 校准失败，已回退规则结果",
            }
        )
    elif ai_status == "skipped":
        history.append(
            {
                "stage": "ai_correction",
                "status": "skipped",
                "message": "AI 校准未启用",
            }
        )

    if parse_status == "success":
        history.append(
            {
                "stage": "validated",
                "status": "success",
                "message": "结构化结果校验通过",
            }
        )
        history.append(
            {
                "stage": "completed",
                "status": "success",
                "message": "解析完成",
            }
        )
        current_stage = "completed"
    else:
        history.append(
            {
                "stage": "failed",
                "status": "failed",
                "message": parse_error or "解析失败",
            }
        )
        current_stage = "failed"

    return ResumeParseArtifactsData(
        pipeline={
            "current_stage": current_stage,
            "history": history,
        },
        document_blocks=document_blocks,
        ocr={"used": ocr_used, "engine": ocr_engine, "avg_confidence": None},
        quality={
            "text_extractable": bool(raw_text),
            "layout_complexity": _estimate_layout_complexity(document_blocks),
            "parser_confidence": _estimate_parser_confidence(structured),
        },
        meta={
            "source_type": source_type or _detect_source_type(file_name),
            "parser_version": "resume-parser-v2",
            "ai_correction_applied": ai_status == "applied",
        },
    )


def _detect_source_type(file_name: str) -> str:
    suffix = Path(file_name).suffix.lower()
    if suffix == ".pdf":
        return "pdf"
    if suffix == ".docx":
        return "docx"
    if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        return "image"
    return "unknown"


def _build_document_blocks(raw_text: str | None) -> list[dict[str, object]]:
    if not raw_text:
        return []

    blocks: list[dict[str, object]] = []
    for index, line in enumerate(_normalize_lines(raw_text), start=1):
        block_type = "paragraph"
        if _match_section(line) is not None:
            block_type = "heading"
        blocks.append(
            {
                "id": f"blk_{index}",
                "page": 1,
                "type": block_type,
                "text": line,
                "bbox": [],
            }
        )
    return blocks


def _estimate_layout_complexity(document_blocks: list[dict[str, object]]) -> str:
    block_count = len(document_blocks)
    if block_count >= 80:
        return "high"
    if block_count >= 30:
        return "medium"
    return "low"


def _estimate_parser_confidence(structured: ResumeStructuredData | None) -> float:
    if structured is None or not _has_meaningful_content(structured):
        return 0.0

    signals = [
        bool(
            structured.basic_info.name
            or structured.basic_info.email
            or structured.basic_info.phone
        ),
        bool(structured.education),
        bool(structured.work_experience),
        bool(structured.projects),
        bool(
            structured.skills.technical
            or structured.skills.tools
            or structured.skills.languages
        ),
        bool(structured.certifications),
    ]
    score = 0.35 + (sum(1 for signal in signals if signal) / len(signals)) * 0.6
    return round(min(score, 0.98), 2)
