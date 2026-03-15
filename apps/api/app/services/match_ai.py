from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

import httpx

from app.core.config import Settings


@dataclass(slots=True)
class AIMatchCorrectionRequest:
    resume_snapshot: dict[str, object]
    job_snapshot: dict[str, object]
    rule_score: float
    dimension_scores: dict[str, float]
    strengths: list[dict[str, object]]
    gaps: list[dict[str, object]]
    actions: list[dict[str, object]]


@dataclass(slots=True)
class AIMatchCorrectionResult:
    provider: str
    model: str | None
    status: str
    delta: float = 0.0
    reasoning: str = ""
    confidence: float | None = None
    strengths: list[dict[str, object]] = field(default_factory=list)
    gaps: list[dict[str, object]] = field(default_factory=list)
    actions: list[dict[str, object]] = field(default_factory=list)

    def to_metadata(self) -> dict[str, object]:
        payload = asdict(self)
        payload["delta"] = round(float(self.delta), 2)
        return payload


class AIMatchCorrectionProvider:
    async def correct(self, payload: AIMatchCorrectionRequest) -> AIMatchCorrectionResult:
        raise NotImplementedError


class DisabledAIMatchCorrectionProvider(AIMatchCorrectionProvider):
    async def correct(self, payload: AIMatchCorrectionRequest) -> AIMatchCorrectionResult:
        return AIMatchCorrectionResult(
            provider="disabled",
            model=None,
            status="skipped",
            delta=0.0,
            reasoning="AI correction is disabled",
        )


class OpenAICompatibleAIMatchCorrectionProvider(AIMatchCorrectionProvider):
    def __init__(
        self,
        *,
        provider: str,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: int,
    ) -> None:
        self.provider = provider
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def correct(self, payload: AIMatchCorrectionRequest) -> AIMatchCorrectionResult:
        prompt = (
            "You are a resume-job matching reviewer. "
            "Do not rebuild the full score from scratch. "
            "Only make a small correction based on semantics missed by the rules. "
            "Return strict JSON with keys: score_delta, reasoning, confidence, "
            "strengths, gaps, actions. "
            "score_delta must be between -10 and 10. "
            "strengths/gaps/actions can be empty arrays."
        )

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "temperature": 0.1,
                    "messages": [
                        {"role": "system", "content": prompt},
                        {
                            "role": "user",
                            "content": json.dumps(asdict(payload), ensure_ascii=False),
                        },
                    ],
                },
            )
            response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(_extract_json_object(content))
        delta = max(-10.0, min(10.0, float(parsed.get("score_delta", 0.0))))

        return AIMatchCorrectionResult(
            provider=self.provider,
            model=self.model,
            status="applied",
            delta=delta,
            reasoning=str(parsed.get("reasoning", "")).strip(),
            confidence=float(parsed["confidence"])
            if parsed.get("confidence") is not None
            else None,
            strengths=list(parsed.get("strengths", [])),
            gaps=list(parsed.get("gaps", [])),
            actions=list(parsed.get("actions", [])),
        )


def _extract_json_object(content: str) -> str:
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("AI response did not contain a JSON object")
    return content[start : end + 1]


def build_ai_match_correction_provider(settings: Settings) -> AIMatchCorrectionProvider:
    provider = settings.match_ai_provider.strip().lower()
    if provider in {"", "disabled", "none", "off"}:
        return DisabledAIMatchCorrectionProvider()

    if (
        not settings.match_ai_base_url
        or not settings.match_ai_api_key
        or not settings.match_ai_model
    ):
        return DisabledAIMatchCorrectionProvider()

    return OpenAICompatibleAIMatchCorrectionProvider(
        provider=provider,
        base_url=settings.match_ai_base_url,
        api_key=settings.match_ai_api_key,
        model=settings.match_ai_model,
        timeout_seconds=settings.match_ai_timeout_seconds,
    )
