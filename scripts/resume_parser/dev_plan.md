可以。你现在要做的不是接口，而是一条**可独立运行、可调试、可扩展**的解析流水线：

**PDF 文件 → 文本提取 → 版面归一化 → 分段(section)识别 → 条目(item)组装 → 字段抽取 → 置信度/回退 → 标准 JSON 输出**

这和你那份开发清单的核心方向是一致的：**第一版先做规则引擎、可解释、可保存的结构化结果，不先上 AI 黑盒。** 

我下面直接给你一套**适合落地成 Python 脚本**的方案，重点放在你最关心的三件事：

1. 怎么从 PDF 准确提文本
2. 怎么把非结构化文本变成标准 JSON
3. 规则、优先级、容错怎么设计

---

## 一、先定结论：第一版最稳的技术路线

我建议你不要只用 `pypdf` 一把梭，而是采用**三级提取策略**：

### 第一级：PyMuPDF 提取块和词位置信息

PyMuPDF 官方文档明确支持 `Page.get_text("text")`、`"blocks"`、`"words"` 等多种抽取方式，并且 `sort=True` 可以按“从上到下、从左到右”重排，更接近自然阅读顺序；`"blocks"` 和 `"words"` 还能拿到坐标信息，适合做两栏简历、标题识别和条目聚合。([pymupdf.readthedocs.io][1])

### 第二级：pdfplumber 作为补充提取器

`pdfplumber` 官方 README 明确说明它擅长提取字符、线条、矩形等细粒度 PDF 对象，并且适合做可视化调试；但它也明确说**更适合 machine-generated PDF，而不是扫描件**。([GitHub][2])

### 第三级：OCR 回退

PyMuPDF 官方文档提供了 `page.get_textpage_ocr()` 的 OCR 路径；另外很多开源简历解析项目也会在 PDF 抽文本失败时走 `pdf2image + pytesseract` 作为兜底。([pymupdf.readthedocs.io][3])

这套分层策略，本质上借鉴了开源项目里最常见的设计：

* `SmartResume` 强调**layout-aware**、OCR + PDF 元数据、重建阅读顺序；
* 一些轻量项目则用 `pdfplumber + spaCy/regex` 做快速本地解析；
* 还有项目会给字段输出附带 confidence，方便人工校正。([GitHub][4])

而你的内部清单也明确要求第一版先走**PDF 文本抽取 + 规则引擎 + 标准 JSON**。

---

## 二、标准 JSON 先固定，不然后面规则会乱

你那份清单已经把第一版 JSON 结构定得很清楚了：

* `basic_info`
* `education`
* `work_experience`
* `projects`
* `skills.technical / tools / languages`
* `certifications` 

建议先固定成这样：

```python
from typing import Any

RESUME_JSON_TEMPLATE: dict[str, Any] = {
    "basic_info": {
        "name": None,
        "email": None,
        "phone": None,
        "location": None,
        "summary": None,
    },
    "education": [],
    "work_experience": [],
    "projects": [],
    "skills": {
        "technical": [],
        "tools": [],
        "languages": [],
    },
    "certifications": [],
    "_meta": {
        "parser_version": "0.1.0",
        "source_file": None,
        "extraction_method": None,
        "ocr_used": False,
        "warnings": [],
        "field_confidence": {},
    },
    "_debug": {
        "raw_text": None,
        "cleaned_lines": [],
        "sections": {},
        "section_order": [],
        "items": {},
    }
}
```

这里我额外加了两个字段：

* `_meta`：记录解析方式、告警、字段置信度
* `_debug`：保留中间结果，便于你调规则

这是第一版非常值得做的增强，因为开源库 `pyresume / leverparser` 明确把 **confidence scores** 作为工程特性之一。([GitHub][5])

---

## 三、整个脚本的目录结构

建议直接做成一个纯脚本包：

```text
resume_parser/
  __init__.py
  main.py
  config.py
  schemas.py
  extractor.py
  cleaner.py
  layout.py
  splitter.py
  itemizer.py
  parser.py
  rules.py
  utils.py
  sample_config.yaml
```

职责很明确：

* `extractor.py`：PDF → 原始文本/块/词
* `cleaner.py`：清洗乱码、空格、重复标题页眉
* `layout.py`：处理阅读顺序、两栏合并
* `splitter.py`：识别教育/工作/项目/技能等 section
* `itemizer.py`：把 section 文本组装成一条条经历
* `parser.py`：字段抽取
* `rules.py`：所有规则和词典配置
* `main.py`：命令行入口

---

## 四、第一部分：PDF 文本提取如何落地

---

### 1）提取目标不是“拿到一坨字符串”，而是拿到三层数据

第一版最好同时产出：

* `raw_text`：全文字符串
* `blocks`：文本块，带坐标
* `words`：词级别，带坐标

因为后面很多规则都依赖版面：

* 姓名通常在页面最上方
* 左右两栏需要重组阅读顺序
* section heading 常常字号大、单独成行、位于左边界
* 经历条目常常是“时间 + 公司 + 职位 + bullet”的组合

PyMuPDF 原生就支持块和词抽取。([pymupdf.readthedocs.io][1])

---

### 2）推荐的提取顺序

#### A. 先用 PyMuPDF 抽 `blocks`

因为它天然适合做 layout-aware 处理。

```python
# extractor.py
from __future__ import annotations
import fitz  # pymupdf
from dataclasses import dataclass, field


@dataclass
class TextBlock:
    page: int
    x0: float
    y0: float
    x1: float
    y1: float
    text: str
    block_no: int


@dataclass
class ExtractResult:
    raw_text: str
    blocks: list[TextBlock] = field(default_factory=list)
    method: str = "pymupdf"
    ocr_used: bool = False


class PdfExtractor:
    def extract(self, pdf_path: str) -> ExtractResult:
        doc = fitz.open(pdf_path)
        blocks: list[TextBlock] = []
        page_texts: list[str] = []

        for page_index, page in enumerate(doc):
            page_blocks = page.get_text("blocks", sort=True)
            current_page_lines: list[str] = []

            for b in page_blocks:
                x0, y0, x1, y1, text, block_no, block_type = b
                text = (text or "").strip()
                if not text:
                    continue
                # block_type == 0 usually text block
                if block_type != 0:
                    continue

                blocks.append(
                    TextBlock(
                        page=page_index,
                        x0=x0, y0=y0, x1=x1, y1=y1,
                        text=text,
                        block_no=block_no,
                    )
                )
                current_page_lines.append(text)

            page_texts.append("\n".join(current_page_lines))

        raw_text = "\n\n".join(page_texts).strip()
        return ExtractResult(raw_text=raw_text, blocks=blocks, method="pymupdf")
```

---

### 3）如何判断需不需要 OCR

不要一上来就 OCR。先做一个简单判断：

* 抽出的 `raw_text.strip()` 很短，比如少于 100 个可见字符
* 或页面里几乎都是图片，没有文本块
* 或文本充满乱码/不可见字符

这时再走 OCR 回退。

PyMuPDF 官方文档已经给出 OCR 路线：先 `get_textpage_ocr()`，再基于 OCR textpage 提取文字。([pymupdf.readthedocs.io][3])

```python
def needs_ocr(raw_text: str) -> bool:
    visible_chars = [c for c in raw_text if c.strip()]
    if len(visible_chars) < 100:
        return True
    return False
```

OCR 回退：

```python
def extract_with_ocr(pdf_path: str) -> ExtractResult:
    import fitz

    doc = fitz.open(pdf_path)
    page_texts: list[str] = []

    for page in doc:
        tp = page.get_textpage_ocr()
        txt = page.get_text(textpage=tp)
        page_texts.append(txt.strip())

    return ExtractResult(
        raw_text="\n\n".join(page_texts).strip(),
        blocks=[],
        method="pymupdf_ocr",
        ocr_used=True,
    )
```

---

### 4）为什么不用“只抽全文字符串”

因为简历很容易出现：

* 双栏
* 左右栏技能区
* 页眉页脚重复
* 表格式项目经历
* 同一行上同时出现公司、职位、时间

只拿纯文本，后面 section 切分和经历组装会很痛苦。
而 `blocks` / `words` 能帮你做最关键的两件事：

1. **重建阅读顺序**
2. **识别标题与条目边界**

这也是 `SmartResume` 强调“重建 reading order”的原因。([GitHub][4])

---

## 五、第二部分：从非结构化文本变成标准 JSON

这里不要直接全文正则乱扫。最稳的是**五段式解析**：

### 第一步：文本清洗

### 第二步：section 切分

### 第三步：section 内条目组装

### 第四步：字段抽取

### 第五步：去重 + 置信度 + 回退

---

## 六、清洗层怎么做

目标不是“美化文本”，而是为规则服务。

```python
# cleaner.py
import re
import unicodedata


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u00a0", " ")
    text = text.replace("\t", " ")
    text = text.replace("•", "- ")
    text = text.replace("●", "- ")
    text = text.replace("▪", "- ")
    text = re.sub(r"[ ]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def to_lines(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines()]
    return [line for line in lines if line]


def remove_repeated_headers(lines: list[str]) -> list[str]:
    # 简单版：重复出现 >= 2 次的短行，若出现在每页顶部附近，可当页眉候选删除
    # 第一版先做保守处理
    return lines
```

### 清洗必须做的几件事

1. Unicode 归一化
2. 合并连续空格
3. 统一 bullet 符号
4. 过滤页眉页脚候选
5. 去掉明显噪声，如“Page 1/2”

---

## 七、section 切分是整个规则系统的核心

你内部清单已经给出了第一版 section heading 词表：
教育、工作、项目、技能、证书等。 

建议把它配置化：

```python
# rules.py
SECTION_ALIASES = {
    "education": [
        "教育", "教育经历", "教育背景", "education", "academic background"
    ],
    "work_experience": [
        "工作经历", "实习经历", "职业经历", "experience", "professional experience"
    ],
    "projects": [
        "项目经历", "项目经验", "projects", "project experience"
    ],
    "skills": [
        "技能", "专业技能", "skills", "skill", "tech stack"
    ],
    "certifications": [
        "证书", "证书奖项", "获奖", "certifications", "awards"
    ],
}
```

section 切分器：

```python
# splitter.py
def normalize_heading(line: str) -> str:
    return line.strip().lower().replace("：", "").replace(":", "")


def detect_section_heading(line: str) -> str | None:
    norm = normalize_heading(line)
    for section, aliases in SECTION_ALIASES.items():
        if norm in [a.lower() for a in aliases]:
            return section
    return None


def split_sections(lines: list[str]) -> tuple[dict[str, list[str]], list[str]]:
    sections: dict[str, list[str]] = {"header": []}
    order: list[str] = ["header"]
    current = "header"

    for line in lines:
        sec = detect_section_heading(line)
        if sec:
            current = sec
            if sec not in sections:
                sections[sec] = []
                order.append(sec)
            continue
        sections.setdefault(current, []).append(line)

    return sections, order
```

---

## 八、section 之后一定要做“条目组装”

这一步很多简历解析项目会忽略，但它非常关键。

因为 `education` / `work_experience` / `projects` 不应该只是“所有行拼成数组”，而应该按一条条经历来组织。

### 条目组装的核心判断

把下面几类行当作“新条目起点”：

1. 包含时间范围

   * `2021-2024`
   * `2021.06 - 2024.03`
   * `Jan 2021 – Present`

2. 包含“公司/学校 + 职位/专业”模式

3. 行很短，像标题行

4. 前面不是 bullet，后面跟着多个 bullet 行

时间范围正则：

```python
DATE_RANGE_PATTERNS = [
    r"\b(19|20)\d{2}[./-]?(0?[1-9]|1[0-2])?\s*[-~–—至]+\s*((19|20)\d{2}[./-]?(0?[1-9]|1[0-2])?|至今|现在|present|current)\b",
    r"\b(19|20)\d{2}\s*[-~–—至]+\s*(19|20)\d{2}|至今|present\b",
]
```

条目组装器：

```python
# itemizer.py
import re

DATE_PATTERNS = [
    re.compile(r"\b(?:19|20)\d{2}(?:[./-](?:0?[1-9]|1[0-2]))?\s*[-~–—至]+\s*(?:(?:19|20)\d{2}(?:[./-](?:0?[1-9]|1[0-2]))?|至今|现在|present|current)\b", re.I),
]

def is_bullet_line(line: str) -> bool:
    return line.startswith(("-", "*", "•", "●", "▪"))

def looks_like_item_start(line: str) -> bool:
    if any(p.search(line) for p in DATE_PATTERNS):
        return True
    if len(line) <= 40 and not is_bullet_line(line):
        # 很短且像标题行，可作为候选
        return True
    return False

def group_lines_to_items(lines: list[str]) -> list[str]:
    items: list[list[str]] = []
    current: list[str] = []

    for line in lines:
        if looks_like_item_start(line):
            if current:
                items.append(current)
            current = [line]
        else:
            if not current:
                current = [line]
            else:
                current.append(line)

    if current:
        items.append(current)

    return [" | ".join(x) for x in items if x]
```

### 为什么这一步重要

因为你清单里虽然第一版允许 `education/work_experience/projects` 用字符串数组保留原文，但“每条字符串保留原文关键信息”这个要求，本质上就是在说：**要有条目边界，不是一整段乱拼。**

---

## 九、字段解析规则如何设计

你问的重点是“规则、优先级、容错机制”。这一部分我直接给你可执行的设计。

---

### A. 基础信息字段

你清单已经给了第一版建议规则：

* 姓名：前 5 行
* 邮箱：正则
* 电话：正则
* 地点：关键词
* 摘要：第 2-8 行非联系方式内容 

我建议把每个字段设计成：

* `candidate_rules`: 候选规则列表
* `scoring`: 每条规则打分
* `fallback`: 主规则失败后的回退

#### 1. name

优先级设计：

1. 页首前 5 行中，非邮箱/电话/section heading，长度合理
2. 若有字体/块信息，优先最大字号或最靠近页面上边的短文本
3. 若是英文简历，可用 spaCy NER 辅助
4. 都失败则返回 `None`

这和一些开源项目用 `spaCy` 辅助识别人名的思路一致。([GitHub][6])

```python
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?\d[\d\s\-()]{7,}\d)")

INVALID_NAME_WORDS = {
    "resume", "cv", "简历", "个人简历", "frontend engineer", "software engineer"
}

def parse_name(header_lines: list[str]) -> tuple[str | None, float]:
    for line in header_lines[:5]:
        s = line.strip()
        if not s:
            continue
        if EMAIL_RE.search(s) or PHONE_RE.search(s):
            continue
        if normalize_heading(s) in INVALID_NAME_WORDS:
            continue
        if len(s) > 32:
            continue
        return s, 0.85
    return None, 0.0
```

#### 2. email

```python
def parse_email(text: str) -> tuple[str | None, float]:
    m = EMAIL_RE.search(text)
    if not m:
        return None, 0.0
    return m.group(0), 0.99
```

#### 3. phone

```python
def parse_phone(text: str) -> tuple[str | None, float]:
    matches = PHONE_RE.findall(text)
    if not matches:
        return None, 0.0
    # 优先 11 位手机号 / 更长合法号码
    best = sorted(matches, key=lambda x: len(re.sub(r"\D", "", x)), reverse=True)[0]
    return best, 0.95
```

#### 4. location

地点建议不要只全文扫描，而是：

1. 优先 header 区域
2. 再扫全文
3. 命中多个地点时，优先出现在 header 的

```python
LOCATION_KEYWORDS = [
    "北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "苏州", "南京",
    "remote", "shanghai", "beijing", "guangzhou", "shenzhen"
]

def parse_location(header_text: str, full_text: str) -> tuple[str | None, float]:
    for city in LOCATION_KEYWORDS:
        if city.lower() in header_text.lower():
            return city, 0.8
    for city in LOCATION_KEYWORDS:
        if city.lower() in full_text.lower():
            return city, 0.6
    return None, 0.0
```

#### 5. summary

摘要不是全文第一段乱抓，而是：

* 只看 header 后面几行
* 排除联系方式
* 排除 section heading
* 最多取前 2-3 行

```python
def parse_summary(header_lines: list[str]) -> tuple[str | None, float]:
    buf = []
    for line in header_lines[1:8]:
        s = line.strip()
        if not s:
            continue
        if EMAIL_RE.search(s) or PHONE_RE.search(s):
            continue
        if detect_section_heading(s):
            continue
        buf.append(s)
        if len(buf) >= 3:
            break
    if not buf:
        return None, 0.0
    return " ".join(buf), 0.7
```

---

### B. 教育 / 工作 / 项目

这三类建议统一套路：

1. 先按 section 切出来
2. 再按时间行/标题行组装条目
3. 每条条目保留原文
4. 第一版不强拆太细字段

这和你内部清单完全一致：第一版先保留原文关键信息，便于后续校正和扩展。

```python
def parse_list_section(section_lines: list[str]) -> tuple[list[str], float]:
    items = group_lines_to_items(section_lines)
    items = [x.strip() for x in items if x.strip()]
    if not items:
        return [], 0.0
    return dedupe_keep_order(items), 0.8
```

---

### C. skills

技能是最适合规则引擎的部分。你的清单已经给了初始词表。

建议设计成外部可配置：

```python
SKILL_DICT = {
    "technical": [
        "Python", "Java", "JavaScript", "TypeScript", "React", "Vue",
        "Next.js", "FastAPI", "Django", "Flask", "SQL",
        "PostgreSQL", "MySQL", "Redis", "Node.js", "Excel", "Power BI", "Tableau"
    ],
    "tools": [
        "Git", "Docker", "Figma", "Postman", "Jira", "Linux", "Photoshop"
    ],
    "languages": [
        "英语", "英文", "English", "CET-4", "CET-6", "日语", "Japanese", "韩语", "Korean"
    ]
}
```

抽取策略：

1. 先扫 `skills` section
2. 如果没有 `skills` section，再扫全文
3. 先精确词匹配，再大小写无关匹配
4. 去重保留顺序

```python
def parse_skills(skills_text: str, full_text: str) -> tuple[dict, float]:
    source = skills_text if skills_text.strip() else full_text
    result = {"technical": [], "tools": [], "languages": []}

    lower_source = source.lower()
    for cat, vocab in SKILL_DICT.items():
        for term in vocab:
            if term.lower() in lower_source:
                result[cat].append(term)

    for k in result:
        result[k] = dedupe_keep_order(result[k])

    conf = 0.85 if skills_text.strip() else 0.55
    return result, conf
```

---

### D. certifications

和 section-based list 一样：

```python
def parse_certifications(lines: list[str]) -> tuple[list[str], float]:
    if not lines:
        return [], 0.0
    return dedupe_keep_order([x.strip() for x in lines if x.strip()]), 0.75
```

---

## 十、规则设计：优先级、容错、冲突处理

这部分是最关键的工程问题。

---

### 1. 每个字段都要有“候选值 + 分数”机制

不要写成“命中就返回”。
要写成：

* 收集候选
* 对候选打分
* 选最高分
* 分数不够则置空并记 warning

例如 name：

```python
@dataclass
class Candidate:
    value: str
    score: float
    source: str

def choose_best(candidates: list[Candidate], threshold: float = 0.5) -> tuple[str | None, float, str | None]:
    if not candidates:
        return None, 0.0, None
    best = sorted(candidates, key=lambda x: x.score, reverse=True)[0]
    if best.score < threshold:
        return None, best.score, best.source
    return best.value, best.score, best.source
```

这样以后你加 AI、加词典、加版面规则时，不会推翻现有结构。

---

### 2. 优先级顺序建议

#### 基础字段

**header 区域规则 > section 规则 > 全文规则 > NLP 辅助**

原因：

* header 最接近真实个人信息
* 全文扫描误伤最多
* NLP 在中文简历上不一定稳定

#### 列表字段

**明确 section > 相邻标题/时间行 > 全文启发式回退**

#### 技能

**skills section > 全文扫词典**

---

### 3. 容错机制要怎么安排

#### 容错 1：section 缺失

很多简历没有“项目经历”标题。
这时可以在全文里用关键词兜底：

* 项目：`项目`、`project`
* 教育：`大学`、`学院`、`本科`、`硕士`
* 工作：`公司`、`实习`、`工程师`

#### 容错 2：双栏顺序错乱

如果抽出来的 header 很奇怪，比如：

* 第一行是技能
* 第二行是电话
* 第三行才是名字

那通常是双栏顺序乱了。
解决办法：

* 对 blocks 先按 `y0` 分组，再按 `x0` 排序
* 或只在页面顶部一定区域内找 name/email/phone

这是我基于 PyMuPDF 的 block/word 能力给出的工程推断。([pymupdf.readthedocs.io][1])

#### 容错 3：OCR 误识别

OCR 容易把：

* `@` 识别错
* 电话分隔符识别错
* 英文大小写乱掉

所以 OCR 后要做轻度纠错：

* 替换常见误字符
* 电话只保留数字再格式化
* 邮箱做二次正则验证

#### 容错 4：重复字段

清单也写了，去重时做大小写归一化和空格清理，且保留首次出现顺序。 

```python
def dedupe_keep_order(items: list[str]) -> list[str]:
    seen = set()
    out = []
    for item in items:
        norm = re.sub(r"\s+", " ", item.strip()).lower()
        if not norm or norm in seen:
            continue
        seen.add(norm)
        out.append(item.strip())
    return out
```

---

## 十一、完整解析主流程应该长这样

```python
# main.py
from copy import deepcopy
from extractor import PdfExtractor, extract_with_ocr, needs_ocr
from cleaner import normalize_text, to_lines
from splitter import split_sections
from itemizer import group_lines_to_items
from parser import (
    parse_name, parse_email, parse_phone, parse_location,
    parse_summary, parse_list_section, parse_skills, parse_certifications
)
from schemas import RESUME_JSON_TEMPLATE


class ResumeParserPipeline:
    def parse(self, pdf_path: str) -> dict:
        result = deepcopy(RESUME_JSON_TEMPLATE)
        result["_meta"]["source_file"] = pdf_path

        extractor = PdfExtractor()
        ext = extractor.extract(pdf_path)

        if needs_ocr(ext.raw_text):
            ext = extract_with_ocr(pdf_path)

        cleaned = normalize_text(ext.raw_text)
        lines = to_lines(cleaned)
        sections, section_order = split_sections(lines)

        result["_meta"]["extraction_method"] = ext.method
        result["_meta"]["ocr_used"] = ext.ocr_used
        result["_debug"]["raw_text"] = ext.raw_text
        result["_debug"]["cleaned_lines"] = lines
        result["_debug"]["sections"] = sections
        result["_debug"]["section_order"] = section_order

        header_lines = sections.get("header", [])
        header_text = "\n".join(header_lines)

        name, c = parse_name(header_lines)
        result["basic_info"]["name"] = name
        result["_meta"]["field_confidence"]["basic_info.name"] = c

        email, c = parse_email(cleaned)
        result["basic_info"]["email"] = email
        result["_meta"]["field_confidence"]["basic_info.email"] = c

        phone, c = parse_phone(cleaned)
        result["basic_info"]["phone"] = phone
        result["_meta"]["field_confidence"]["basic_info.phone"] = c

        location, c = parse_location(header_text, cleaned)
        result["basic_info"]["location"] = location
        result["_meta"]["field_confidence"]["basic_info.location"] = c

        summary, c = parse_summary(header_lines)
        result["basic_info"]["summary"] = summary
        result["_meta"]["field_confidence"]["basic_info.summary"] = c

        edu_items, c = parse_list_section(sections.get("education", []))
        result["education"] = edu_items
        result["_meta"]["field_confidence"]["education"] = c

        work_items, c = parse_list_section(sections.get("work_experience", []))
        result["work_experience"] = work_items
        result["_meta"]["field_confidence"]["work_experience"] = c

        proj_items, c = parse_list_section(sections.get("projects", []))
        result["projects"] = proj_items
        result["_meta"]["field_confidence"]["projects"] = c

        skill_text = "\n".join(sections.get("skills", []))
        skills, c = parse_skills(skill_text, cleaned)
        result["skills"] = skills
        result["_meta"]["field_confidence"]["skills"] = c

        certs, c = parse_certifications(sections.get("certifications", []))
        result["certifications"] = certs
        result["_meta"]["field_confidence"]["certifications"] = c

        self._post_validate(result)
        return result

    def _post_validate(self, result: dict) -> None:
        if not result["basic_info"]["email"]:
            result["_meta"]["warnings"].append("email_not_found")
        if not result["basic_info"]["phone"]:
            result["_meta"]["warnings"].append("phone_not_found")
        if not any(result["skills"].values()):
            result["_meta"]["warnings"].append("skills_not_found")
```

命令行入口：

```python
if __name__ == "__main__":
    import json
    import sys

    pdf_path = sys.argv[1]
    parser = ResumeParserPipeline()
    data = parser.parse(pdf_path)
    print(json.dumps(data, ensure_ascii=False, indent=2))
```

---

## 十二、为什么我推荐“规则配置化”

因为你要求“逻辑清晰、规则可配置、便于扩展”，那就不要把规则散在代码里。

建议用 `yaml` 管：

```yaml
section_aliases:
  education: ["教育", "教育经历", "education"]
  work_experience: ["工作经历", "实习经历", "experience"]
  projects: ["项目经历", "projects"]
  skills: ["技能", "skills", "tech stack"]
  certifications: ["证书", "certifications", "awards"]

locations:
  - 北京
  - 上海
  - 深圳
  - Hangzhou
  - Remote

skills:
  technical:
    - Python
    - Java
    - JavaScript
    - TypeScript
    - React
    - Vue
    - FastAPI
  tools:
    - Git
    - Docker
    - Jira
    - Postman
  languages:
    - English
    - CET-4
    - CET-6
```

这样后续你只要改配置，不用改主流程。

---

## 十三、该借鉴哪些开源项目，借什么

这里我不建议你直接照搬某一个项目，而是“各取所长”。

### 1. `SmartResume`

它最值得借鉴的是**layout-aware**思路：OCR + PDF 元数据 + 阅读顺序重建。
你第一版不一定要上它那套完整系统，但“抽 blocks、保留版面信息、考虑 reading order”很值得吸收。([GitHub][4])

### 2. `pdfplumber`

值得借鉴的是：

* 细粒度字符/块级调试
* 适合 machine-generated PDF
* 可视化调试非常利于排查 PDF 提取异常。([GitHub][2])

### 3. `resume-parser-project`

值得借鉴的是：

* `pdfplumber + spaCy + JSON` 的轻量本地处理思路
* 清晰的模块结构，适合你做脚本版本。([GitHub][6])

### 4. `pyresume / leverparser`

值得借鉴的是：

* 模块化架构
* confidence scoring
* 本地解析优先、可选增强能力。([GitHub][5])

---

## 十四、我建议你第一版的字段规则这样排优先级

### 基础信息

* `name`: 页首前 5 行 > block 顶部短文本 > NER 辅助
* `email`: 正则全文 > OCR 修正后二次正则
* `phone`: 正则全文 > header 优先
* `location`: header 关键词 > 全文关键词
* `summary`: header 2-8 行非联系方式文本

这和你内部清单基本一致，只是把“header 优先”和“候选打分”补全了。

### 列表字段

* `education`: section > 关键词兜底
* `work_experience`: section > 时间行兜底
* `projects`: section > 项目关键词兜底
* `skills`: skills section > 全文词表
* `certifications`: section > 证书关键词兜底

---

## 十五、第一版最容易踩的坑

### 1. 扫描件 PDF

`pdfplumber` 官方自己就提醒它更适合 machine-generated PDF。([GitHub][2])
所以你必须有 OCR 回退，不然很多简历直接废掉。

### 2. 双栏顺序错乱

最常见表现就是：

* 姓名被识别成技能词
* 摘要被拼到工作经历里

解决办法就是 blocks + 排序，而不是只信纯文本。

### 3. section heading 多样化

“项目经历 / 项目经验 / 项目背景 / Projects” 都要纳入 alias。

### 4. 经历条目边界不清

这是为什么我强烈建议你加 `itemizer.py`。

---

## 十六、最小依赖建议

第一版建议：

```bash
pip install pymupdf pdfplumber pyyaml
```

可选增强：

```bash
pip install spacy
python -m spacy download en_core_web_sm
```

OCR 方案如果你要走 PyMuPDF OCR 或 Tesseract，环境会复杂一些。
如果你先只做文本型 PDF，完全可以先不上 OCR，只保留接口位置。

---

## 十七、给你的最终落地建议

先不要把目标定成“万能简历解析器”。
第一版只要做到这四点，就已经很强了：

1. **文本型 PDF 稳定抽取**
2. **section 切分稳定**
3. **education/work/projects 能分成条目**
4. **basic_info + skills 能稳定产出**

这完全符合你内部清单里“最小可交付版本：只支持 PDF、只支持规则引擎、不接 AI”的要求。

---

## 十八、压缩成一句话

你现在真正要开发的“核心功能”不是接口，而是这个脚本流水线：

```python
PDF
 -> blocks/text extraction
 -> OCR fallback if needed
 -> text normalize
 -> section split
 -> item grouping
 -> field parse with scoring
 -> dedupe + warnings + confidence
 -> standard JSON
```

如果你愿意，我下一条可以直接给你一份**完整可运行的单文件版 `resume_parser.py`**，把上面这些模块合并成一个脚本，复制到项目里就能跑。

[1]: https://pymupdf.readthedocs.io/en/latest/app1.html?utm_source=chatgpt.com "Appendix 1: Details on Text Extraction - PyMuPDF documentation"
[2]: https://github.com/jsvine/pdfplumber "GitHub - jsvine/pdfplumber: Plumb a PDF for detailed information about each char, rectangle, line, et cetera — and easily extract text and tables. · GitHub"
[3]: https://pymupdf.readthedocs.io/en/latest/the-basics.html?utm_source=chatgpt.com "The Basics - PyMuPDF documentation"
[4]: https://github.com/alibaba/SmartResume "GitHub - alibaba/SmartResume · GitHub"
[5]: https://github.com/wespiper/pyresume "GitHub - wespiper/pyresume: A simple, accurate resume parser for Python. Extract structured data from PDF, DOCX, and TXT resumes with high accuracy. · GitHub"
[6]: https://github.com/hadidadashzade/resume-parser-project "GitHub - hadidadashzade/resume-parser-project: Extract key info from resumes and recommend relevant job titles with Python and NLP. · GitHub"
