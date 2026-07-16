import json

import pytest

from app.models import EmployeeInfo, MMPI, MethodScores, ParsedProfile
from app.prompts import build_user_prompt
from app.reporting import ReportValidationError, parse_and_validate_report, word_count


def profile():
    return ParsedProfile(
        employee=EmployeeInfo(
            full_name="TEST_SUBJECT_001",
            position="Начальник отдела",
            extra={"location": "Алексеевка", "employment_history": "секретная биография"},
        ),
        methods=MethodScores(mmpi=MMPI(L=50, F=48, K=55, Mf=72, Si=65, validity="valid")),
        raw_text="ФИО и весь исходный документ",
    )


def paragraph():
    sentence = "Сотрудник обычно сопоставляет задачи с доступными ресурсами, учитывает последствия решений и сохраняет внимание к рабочим отношениям."
    return " ".join([sentence] * 11)


def payload():
    return {
        "emotional_motivation": paragraph(),
        "management_style": paragraph(),
        "communication_style": paragraph(),
        "risk_factors": paragraph(),
        "recommendations": [f"Проводить практическое действие номер {n} каждую рабочую неделю." for n in range(1, 11)],
    }


def test_prompt_is_pseudonymized_and_contains_user_rules():
    prompt = build_user_prompt(profile())
    assert "TEST_SUBJECT_001" not in prompt
    assert "Алексеевка" not in prompt
    assert "Начальник отдела" not in prompt
    assert "секретная биография" not in prompt
    assert "весь исходный документ" not in prompt
    assert "феминизированность" in prompt
    assert "интровертированность" in prompt


def test_report_validation_enforces_100_words_and_ten_recommendations():
    report = parse_and_validate_report(json.dumps(payload(), ensure_ascii=False), profile())
    assert word_count(report.emotional_motivation) >= 100
    assert len(report.recommendations) == 10
    assert "—" not in report.emotional_motivation


def test_report_validation_rejects_short_or_clinical_text():
    data = payload()
    data["risk_factors"] = "Слишком короткий текст про депрессию."
    with pytest.raises(ReportValidationError):
        parse_and_validate_report(json.dumps(data, ensure_ascii=False), profile())
