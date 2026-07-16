"""Правила интерпретации из лекции НОЦ «Бирюч», актуализация 30.01.2025.

Модуль не ставит диагнозов. Он переводит числовые результаты в нейтральные
рабочие гипотезы и формирует обезличенный контекст для LLM.
"""
from __future__ import annotations

import json
from typing import Any

from .models import ParsedProfile


METHODOLOGY_VERSION = "efko-lecture-2025.01"


def three_level(value: float | None, low_max: float = 39, medium_max: float = 69) -> str | None:
    if value is None:
        return None
    if value <= low_max:
        return "низкий"
    if value <= medium_max:
        return "средний"
    return "высокий"


def _score(value: float | None, *, scheme: str = "standard") -> dict[str, Any] | None:
    if value is None:
        return None
    if scheme == "postmodern":
        level = "низкий" if value <= 20 else "средний" if value <= 50 else "высокий"
    elif scheme == "gentleman":
        level = "низкий" if value <= 24 else "средний" if value <= 44 else "высокий"
    elif scheme == "sanity":
        level = "низкий" if value <= 44 else "средний" if value <= 74 else "высокий"
    elif scheme == "intelligence":
        level = "ниже среднего" if value <= 44 else "средний" if value <= 69 else "высокий"
    elif scheme == "activity":
        level = "низкий" if value <= 39 else "средний" if value <= 69 else "высокий"
    else:
        level = three_level(value)
    return {"value": value, "level": level}


MMPI_DIRECTIONS = {
    "Hs": "при повышении усиливаются самоконтроль, осторожность и фиксация на самочувствии",
    "D": "при повышении усиливаются осторожный прогноз, чувствительность к неудаче и потребность в поддержке",
    "Hy": "при повышении усиливаются эмоциональная выразительность и потребность в признании",
    "Pd": "при повышении усиливаются самостоятельность, быстрота реакции и риск импульсивных решений",
    # Осознанное правило пользователя: одинаковое направление для мужчин и женщин.
    "Mf": "чем выше, тем больше феминизированность и эмоциональная чувствительность; чем ниже, тем больше мускулинность",
    "Pa": "при повышении усиливаются настойчивость, конкурентность и устойчивость позиции",
    "Pt": "при повышении усиливаются скрупулезность, сомнения и перепроверка",
    "Sc": "при повышении усиливаются независимость мышления и принятие нестандартных сочетаний",
    "Ma": "при повышении усиливаются энергия, оптимизм и потребность выделяться",
    "Si": "чем выше, тем больше интровертированность; чем ниже, тем больше экстравертированность",
}


def _mmpi_level(field: str, value: float) -> str:
    """Рабочие диапазоны из лекции, без клинических ярлыков."""
    if field in {"L", "F", "K"}:
        if value > 80: return "профиль ненадежен"
        if value >= 70: return "требует осторожности"
        return "приемлемый диапазон достоверности"
    if field == "Hs":
        return "выраженное проявление" if value > 65 else "умеренное проявление"
    if field == "D":
        return "выраженное проявление" if value > 60 else "умеренное проявление" if value > 50 else "сниженное проявление"
    if field == "Hy":
        return "выраженное проявление" if value > 65 else "оптимальный рабочий диапазон" if 40 <= value <= 45 else "умеренное проявление"
    if field == "Pd":
        return "зона повышенного риска" if value > 75 else "активное проявление" if value > 55 else "спокойное проявление" if value >= 45 else "сниженное проявление"
    if field == "Mf":
        return "в сторону феминизированности" if value > 55 else "в сторону мускулинности" if value < 45 else "сбалансированный диапазон"
    if field == "Pa":
        return "зона повышенного риска" if value > 75 else "активное проявление" if value > 55 else "крайне низкое значение" if value < 30 else "умеренное проявление"
    if field == "Pt":
        return "зона повышенного риска" if value > 75 else "активное проявление" if value > 60 else "умеренное проявление"
    if field == "Sc":
        return "выраженное проявление" if value > 65 else "умеренное проявление"
    if field == "Ma":
        return "очень выраженное проявление" if value > 80 else "активное проявление" if value > 60 else "умеренное проявление"
    if field == "Si":
        return "выраженная интровертированность" if value > 65 else "интровертированность" if value > 50 else "экстравертированность"
    return "без категории"


def quality_warnings(profile: ParsedProfile) -> list[str]:
    warnings: list[str] = []
    mmpi = profile.methods.mmpi
    if mmpi:
        if mmpi.validity == "invalid":
            warnings.append(
                "Показатели достоверности превышают 80. Профиль ненадежен; нужны повторное тестирование и ручная проверка психологом."
            )
        elif mmpi.validity == "questionable":
            warnings.append(
                "Один или несколько показателей достоверности находятся в диапазоне 70-80. Выводы следует считать предварительными."
            )
        if mmpi.L is not None and mmpi.L > 60:
            warnings.append("Возможна выраженная социально желательная самопрезентация.")
        if mmpi.K is not None and mmpi.K > 70:
            warnings.append("Возможна защитная установка и недооценка собственных затруднений.")
        if mmpi.F is not None and mmpi.F > 55:
            warnings.append("Часть трудностей могла быть подчеркнута сильнее обычного.")
    if not profile.methods.efko and not profile.methods.mmpi:
        warnings.append("Недостаточно данных основных методик для надежной характеристики.")
    warnings.append(
        "Характеристика является гипотезой для профессиональной проверки и не должна быть единственным основанием кадрового решения."
    )
    return list(dict.fromkeys(warnings))


def _model_scores(model: Any, *, scheme: str = "standard") -> dict[str, Any]:
    if model is None:
        return {}
    return {
        field: _score(value, scheme=scheme)
        for field, value in model.model_dump().items()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    }


def build_interpretation_payload(profile: ParsedProfile) -> dict[str, Any]:
    """Обезличенный контекст: без ФИО, имени файла, raw_text и биографии."""
    payload: dict[str, Any] = {
        "methodology_version": METHODOLOGY_VERSION,
        "job_context": {
            "is_manager": bool(
                profile.employee.position
                and any(x in profile.employee.position.lower() for x in ("начальник", "руководитель", "мастер", "директор"))
            ),
        },
        "quality_warnings": quality_warnings(profile),
        "interpretation_rules": {
            "integrative": "учитывать сочетания, взаимное усиление и компенсацию показателей, а не трактовать их изолированно",
            "fifth_scale_override": MMPI_DIRECTIONS["Mf"],
            "social_introversion": MMPI_DIRECTIONS["Si"],
            "hr_limit": "не ставить диагнозы и не делать автоматический вывод о найме, увольнении или непригодности",
        },
    }

    mmpi = profile.methods.mmpi
    if mmpi:
        scales = {}
        for field in ("L", "F", "K", "Hs", "D", "Hy", "Pd", "Mf", "Pa", "Pt", "Sc", "Ma", "Si"):
            value = getattr(mmpi, field)
            if value is not None:
                item: dict[str, Any] = {"value": value, "level": _mmpi_level(field, value)}
                if field in MMPI_DIRECTIONS:
                    item["direction"] = MMPI_DIRECTIONS[field]
                scales[field] = item
        payload["smil"] = {
            "validity": mmpi.validity,
            "profile_code": mmpi.code,
            "scales": scales,
            "gentleman": _score(mmpi.gentleman, scheme="gentleman"),
            "sanity": _score(mmpi.sanity, scheme="sanity"),
        }

    efko = profile.methods.efko
    if efko:
        blocks: dict[str, Any] = {}
        for name, model, scheme in (
            ("intelligence", efko.intellekt, "intelligence"),
            ("activity", efko.aktivnost, "activity"),
            ("empathy", efko.empaty, "standard"),
            ("emotional_depth", efko.echv_echm, "standard"),
            ("life_gamble", efko.life_gamble, "standard"),
            ("harmony_and_decision", efko.harmony_decision, "standard"),
            ("work_discomfort", efko.work_discomfort, "standard"),
            ("achievement_model", efko.achievement_model, "standard"),
            ("personnel_types", efko.personnel_types, "standard"),
            ("safety_attitude", efko.safety_attitude, "standard"),
        ):
            values = _model_scores(model, scheme=scheme)
            if values:
                blocks[name] = values
        if efko.postmodern is not None:
            blocks["postmodern"] = _score(efko.postmodern, scheme="postmodern")
        if efko.employer_paradigm:
            blocks["employer_paradigm"] = {
                name: {
                    "conscious": _score(item.conscious),
                    "unconscious": _score(item.unconscious),
                }
                for name, item in efko.employer_paradigm
            }
        payload["corporate_methods"] = blocks
    return payload


def build_interpretation_context(profile: ParsedProfile) -> str:
    return json.dumps(build_interpretation_payload(profile), ensure_ascii=False, indent=2)
