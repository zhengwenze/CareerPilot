from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ResumeBasicInfo(BaseModel):
    name: str = ""
    title: str = ""
    status: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    links: list[str] = Field(default_factory=list)
    summary: str = ""


class ResumeSkills(BaseModel):
    technical: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)


class ResumeMeta(BaseModel):
    schema_version: int = 2
    language: str = "zh-CN"
    source_type: str = "pdf"
    parser_version: str = "resume-parser-v2"
    ai_correction_applied: bool = False


class ResumeEducationItem(BaseModel):
    id: str = ""
    school: str = ""
    degree: str = ""
    major: str = ""
    start_date: str = ""
    end_date: str = ""
    gpa: str = ""
    honors: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)


class ResumeExperienceBullet(BaseModel):
    id: str = ""
    text: str = ""
    kind: str = "responsibility"
    metrics: list[str] = Field(default_factory=list)
    skills_used: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)


class ResumeWorkExperienceItem(BaseModel):
    id: str = ""
    company: str = ""
    title: str = ""
    department: str = ""
    location: str = ""
    start_date: str = ""
    end_date: str = ""
    employment_type: str = ""
    bullets: list[ResumeExperienceBullet] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)


class ResumeProjectItem(BaseModel):
    id: str = ""
    name: str = ""
    role: str = ""
    start_date: str = ""
    end_date: str = ""
    summary: str = ""
    bullets: list[ResumeExperienceBullet] = Field(default_factory=list)
    skills_used: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)


class ResumeCertificationItem(BaseModel):
    id: str = ""
    name: str = ""
    issuer: str = ""
    date: str = ""
    source_refs: list[str] = Field(default_factory=list)


class ResumeCustomSectionItem(BaseModel):
    id: str = ""
    title: str = ""
    subtitle: str = ""
    years: str = ""
    description: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)


class ResumeCustomSection(BaseModel):
    id: str = ""
    title: str = ""
    items: list[ResumeCustomSectionItem] = Field(default_factory=list)


class ResumeStructuredData(BaseModel):
    meta: ResumeMeta = Field(default_factory=ResumeMeta)
    basic_info: ResumeBasicInfo = Field(default_factory=ResumeBasicInfo)
    education: list[str] = Field(default_factory=list)
    education_items: list[ResumeEducationItem] = Field(default_factory=list)
    work_experience: list[str] = Field(default_factory=list)
    work_experience_items: list[ResumeWorkExperienceItem] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    project_items: list[ResumeProjectItem] = Field(default_factory=list)
    skills: ResumeSkills = Field(default_factory=ResumeSkills)
    certifications: list[str] = Field(default_factory=list)
    certification_items: list[ResumeCertificationItem] = Field(default_factory=list)
    awards: list[str] = Field(default_factory=list)
    custom_sections: list[ResumeCustomSection] = Field(default_factory=list)

    @model_validator(mode="after")
    def _sync_legacy_and_canonical(self) -> "ResumeStructuredData":
        if self.education_items and not self.education:
            self.education = [_education_item_to_text(item) for item in self.education_items]
        elif self.education and not self.education_items:
            self.education_items = [
                ResumeEducationItem(id=f"edu_{index}", school=value)
                for index, value in enumerate(self.education, start=1)
            ]

        if self.work_experience_items and not self.work_experience:
            self.work_experience = [
                _work_item_to_text(item) for item in self.work_experience_items
            ]
        elif self.work_experience and not self.work_experience_items:
            self.work_experience_items = [
                ResumeWorkExperienceItem(
                    id=f"work_{index}",
                    company=value,
                    bullets=[
                        ResumeExperienceBullet(
                            id=f"work_{index}_b1",
                            text=value,
                        )
                    ],
                )
                for index, value in enumerate(self.work_experience, start=1)
            ]

        if self.project_items and not self.projects:
            self.projects = [_project_item_to_text(item) for item in self.project_items]
        elif self.projects and not self.project_items:
            self.project_items = [
                ResumeProjectItem(
                    id=f"proj_{index}",
                    name=value,
                    summary=value,
                    bullets=[
                        ResumeExperienceBullet(
                            id=f"proj_{index}_b1",
                            text=value,
                        )
                    ],
                )
                for index, value in enumerate(self.projects, start=1)
            ]

        if self.certification_items and not self.certifications:
            self.certifications = [
                _certification_item_to_text(item) for item in self.certification_items
            ]
        elif self.certifications and not self.certification_items:
            self.certification_items = [
                ResumeCertificationItem(id=f"cert_{index}", name=value)
                for index, value in enumerate(self.certifications, start=1)
            ]
        return self


def _join_non_empty(parts: list[str]) -> str:
    return " ".join(part.strip() for part in parts if part and part.strip()).strip()


def _education_item_to_text(item: ResumeEducationItem) -> str:
    return _join_non_empty(
        [
            item.school,
            item.major,
            item.degree,
            item.start_date,
            item.end_date,
            item.gpa,
            " ".join(item.honors),
        ]
    )


def _work_item_to_text(item: ResumeWorkExperienceItem) -> str:
    bullet_text = " ".join(bullet.text.strip() for bullet in item.bullets if bullet.text.strip())
    return _join_non_empty(
        [
            item.company,
            item.title,
            item.start_date,
            item.end_date,
            bullet_text,
        ]
    )


def _project_item_to_text(item: ResumeProjectItem) -> str:
    bullet_text = " ".join(bullet.text.strip() for bullet in item.bullets if bullet.text.strip())
    return _join_non_empty(
        [
            item.name,
            item.role,
            item.start_date,
            item.end_date,
            item.summary,
            bullet_text,
        ]
    )


def _certification_item_to_text(item: ResumeCertificationItem) -> str:
    return _join_non_empty([item.name, item.issuer, item.date])


class ResumeParsePipelineStage(BaseModel):
    stage: str
    status: str
    message: str = ""
    started_at: datetime | None = None
    finished_at: datetime | None = None


class ResumeParsePipeline(BaseModel):
    current_stage: str = "uploaded"
    history: list[ResumeParsePipelineStage] = Field(default_factory=list)


class ResumeParseDocumentBlock(BaseModel):
    id: str
    page: int = 1
    type: str = "paragraph"
    text: str = ""
    bbox: list[int] = Field(default_factory=list)


class ResumeParseOCRInfo(BaseModel):
    used: bool = False
    engine: str = "none"
    avg_confidence: float | None = None


class ResumeParseQualityInfo(BaseModel):
    text_extractable: bool = False
    layout_complexity: str = "low"
    parser_confidence: float = 0.0


class ResumeParseArtifactsData(BaseModel):
    pipeline: ResumeParsePipeline = Field(default_factory=ResumeParsePipeline)
    document_blocks: list[ResumeParseDocumentBlock] = Field(default_factory=list)
    ocr: ResumeParseOCRInfo = Field(default_factory=ResumeParseOCRInfo)
    quality: ResumeParseQualityInfo = Field(default_factory=ResumeParseQualityInfo)
    canonical_resume_md: str = ""
    meta: dict[str, Any] = Field(default_factory=dict)


class ResumeParseJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    attempt_count: int
    ai_status: str | None
    ai_message: str | None
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ResumeResponse(BaseModel):
    id: UUID
    user_id: UUID
    file_name: str
    file_url: str
    storage_bucket: str
    storage_object_key: str
    content_type: str
    file_size: int
    parse_status: str
    parse_error: str | None
    raw_text: str | None = None
    structured_json: ResumeStructuredData | None = None
    parse_artifacts_json: ResumeParseArtifactsData | None = None
    latest_version: int
    created_at: datetime
    updated_at: datetime
    latest_parse_job: ResumeParseJobResponse | None = None
    download_url: str | None = None


class ResumeDownloadUrlResponse(BaseModel):
    download_url: str
    expires_in: int


class ResumeDeleteResponse(BaseModel):
    message: str


class ResumeStructuredUpdateRequest(BaseModel):
    structured_json: ResumeStructuredData
    markdown: str | None = None
