"""Генерация, разбор и контроль качества психологической характеристики."""
from __future__ import annotations

import json
import re
from typing import Any

from pydantic import ValidationError

from .llm import chat
from .methodology import quality_warnings
from .models import ParsedProfile, PsychologicalReport
from .prompts import SYSTEM_PROMPT, build_user_prompt


NARRATIVE_FIELDS = (
    "emotional_motivation",
    "management_style",
    "communication_style",
    "risk_factors",
)
FIELD_TITLES = {
    "emotional_motivation": "Эмоциональная природа мотивации",
    "management_style": "Стиль управления",
    "communication_style": "Стиль коммуникации",
    "risk_factors": "Факторы риска",
}
BANNED_OUTPUT_TERMS = (
    "mmpi", "см ил", "смил", "ммил", "шкала l", "шкала f", "шкала k",
    "ипохондр", "депресси", "истери", "психопат", "параной", "психастен",
    "шизоид", "шизофрен", "гипоман", "клиническ",
)


class ReportValidationError(ValueError):
    pass


def word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-zА-Яа-яЁё0-9]+(?:-[A-Za-zА-Яа-яЁё0-9]+)?", text))


def _extract_json(text: str) -> dict[str, Any]:
    value = text.strip()
    if value.startswith("```"):
        value = re.sub(r"^```(?:json)?\s*|\s*```$", "", value, flags=re.IGNORECASE)
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        start, end = value.find("{"), value.rfind("}")
        if start < 0 or end <= start:
            raise ReportValidationError("Модель не вернула JSON-объект")
        try:
            parsed = json.loads(value[start:end + 1])
        except json.JSONDecodeError as exc:
            raise ReportValidationError(f"Некорректный JSON: {exc.msg}") from exc
    if not isinstance(parsed, dict):
        raise ReportValidationError("В ответе ожидался JSON-объект")
    return parsed


def _normalize_text(value: str) -> str:
    value = value.replace("—", "-").replace("–", "-")
    return re.sub(r"[ \t]+", " ", value).strip()


def validate_report_payload(payload: dict[str, Any], profile: ParsedProfile) -> PsychologicalReport:
    clean = dict(payload)
    for field in NARRATIVE_FIELDS:
        if isinstance(clean.get(field), str):
            clean[field] = _normalize_text(clean[field])
    if isinstance(clean.get("recommendations"), list):
        clean["recommendations"] = [
            _normalize_text(str(item)) for item in clean["recommendations"] if str(item).strip()
        ]
    clean["quality_warnings"] = quality_warnings(profile)
    try:
        report = PsychologicalReport.model_validate(clean)
    except ValidationError as exc:
        raise ReportValidationError(str(exc)) from exc

    errors = []
    for field in NARRATIVE_FIELDS:
        count = word_count(getattr(report, field))
        if count < 100:
            errors.append(f"{field}: {count} слов вместо минимум 100")
    output_text = " ".join(
        [*(getattr(report, f) for f in NARRATIVE_FIELDS), *report.recommendations]
    )
    complete_text = output_text.lower()
    found = sorted(term for term in BANNED_OUTPUT_TERMS if term in complete_text)
    code_match = re.search(r"(?<![A-Za-zА-Яа-яЁё])(?:Hs|Hy|Pd|Mf|Pa|Pt|Sc|Ma|Si|L|F|K)(?![A-Za-zА-Яа-яЁё])", output_text)
    if code_match:
        found.append(f"код {code_match.group(0)}")
    if found:
        errors.append("технические или клинические термины: " + ", ".join(found))
    normalized_recs = {re.sub(r"\W+", " ", r.lower()).strip() for r in report.recommendations}
    if len(normalized_recs) < 10:
        errors.append("нужно не менее 10 различных рекомендаций")
    if errors:
        raise ReportValidationError("; ".join(errors))
    return report


def parse_and_validate_report(text: str, profile: ParsedProfile) -> PsychologicalReport:
    return validate_report_payload(_extract_json(text), profile)


async def generate_report(profile: ParsedProfile) -> PsychologicalReport:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(profile)},
    ]
    raw = await chat(messages, max_tokens=5000)
    try:
        return parse_and_validate_report(raw, profile)
    except ReportValidationError as first_error:
        repair = f"""Исправь свой предыдущий ответ. Ошибки контроля качества: {first_error}.
Верни только полный JSON установленной структуры. Каждый из первых четырех разделов должен содержать не менее 100 слов, рекомендации должны включать не менее 10 различных пунктов. Удали технические и клинические термины и длинные тире.

Предыдущий ответ:
{raw}
"""
        repaired = await chat(messages + [
            {"role": "assistant", "content": raw},
            {"role": "user", "content": repair},
        ], temperature=0.2, max_tokens=5500)
        try:
            return parse_and_validate_report(repaired, profile)
        except ReportValidationError as second_error:
            raise ReportValidationError(
                f"Отчет не прошел проверку после повторной генерации: {second_error}"
            ) from second_error


def report_to_markdown(report: PsychologicalReport) -> str:
    parts = []
    for field in NARRATIVE_FIELDS:
        parts.extend((f"## {FIELD_TITLES[field]}", "", getattr(report, field), ""))
    parts.extend(("## Рекомендации", ""))
    parts.extend(f"{index}. {item}" for index, item in enumerate(report.recommendations, 1))
    if report.quality_warnings:
        parts.extend(("", "## Ограничения", ""))
        parts.extend(f"- {item}" for item in report.quality_warnings)
    return "\n".join(parts).strip()
