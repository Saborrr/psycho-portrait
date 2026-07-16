"""Осторожное представление стандартизованных отклонений.

Z-скоры и перцентили считаются только для шкал, для которых стандартная шкала
является частью самой методики. Для DISC, Holland и корпоративных процентов
фиктивные популяционные нормы не создаются.
"""
from __future__ import annotations

import math

from .methodology import build_interpretation_payload, three_level
from .models import Cattell16PF, ParsedProfile


def _category_t(value: float) -> str:
    if value < 35: return "очень низкий"
    if value < 45: return "сниженный"
    if value <= 55: return "средний"
    if value <= 65: return "повышенный"
    if value <= 75: return "высокий"
    return "очень высокий"


def _pct(z: float) -> float:
    return round((1 + math.erf(z / math.sqrt(2))) * 50, 1)


def _standardized(value: float, mean: float, std: float) -> dict:
    z = (value - mean) / std
    t = 50 + 10 * z
    return {
        "raw": round(float(value), 2), "z": round(z, 2), "t": round(t, 1),
        "pct": _pct(z), "cat_ru": _category_t(t), "basis": "standardized_scale",
    }


def _relative_block(model, fields: list[str]) -> dict:
    values = {field: getattr(model, field) for field in fields if getattr(model, field) is not None}
    if not values:
        return {}
    maximum = max(values.values())
    return {
        field: {
            "raw": value,
            "relative": "ведущий показатель" if value == maximum else "сравнивать только внутри профиля",
            "basis": "no_population_norm",
        }
        for field, value in values.items()
    }


def compute_deviations(profile: ParsedProfile, employee=None) -> dict:
    methods = profile.methods
    out: dict = {
        "_warnings": [
            "Перцентили рассчитаны только для стандартизованных шкал. Корпоративные проценты не являются популяционными перцентилями."
        ]
    }
    if methods.cattell_16pf:
        block = {}
        for field in Cattell16PF.model_fields:
            value = getattr(methods.cattell_16pf, field)
            if value is not None:
                block[field] = _standardized(value, 5.5, 2.0)
        if block: out["cattell_16pf"] = block

    if methods.mmpi:
        block = {}
        for field in ("L", "F", "K", "Hs", "D", "Hy", "Pd", "Mf", "Pa", "Pt", "Sc", "Ma", "Si"):
            value = getattr(methods.mmpi, field)
            if value is not None:
                block[field] = {
                    "raw": value, "t": value, "pct": _pct((value - 50) / 10),
                    "cat_ru": _category_t(value), "basis": "reported_t_score",
                }
        if block: out["mmpi"] = block

    if methods.big_five:
        fields = ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]
        if methods.big_five.scale.upper() == "T":
            out["big_five"] = {
                field: _standardized(getattr(methods.big_five, field), 50, 10)
                for field in fields if getattr(methods.big_five, field) is not None
            }
        else:
            out["big_five"] = {
                field: {"raw": getattr(methods.big_five, field), "level": three_level(getattr(methods.big_five, field)), "basis": "raw_range_only"}
                for field in fields if getattr(methods.big_five, field) is not None
            }

    if methods.disc:
        out["disc"] = _relative_block(methods.disc, ["D", "I", "S", "C"])
    if methods.holland:
        out["holland"] = _relative_block(methods.holland, ["R", "I", "A", "S", "E", "C"])
    if methods.amthauer and methods.amthauer.iq is not None:
        out["amthauer"] = {"iq": _standardized(methods.amthauer.iq, 100, 15)}
    if methods.mbti and methods.mbti.type:
        out["mbti"] = {"type": methods.mbti.type, "basis": "typology_no_rank"}
    if methods.efko:
        out["corporate_methods"] = build_interpretation_payload(profile).get("corporate_methods", {})
    return out


def format_deviations_md(deviations: dict) -> str:
    lines = []
    for warning in deviations.get("_warnings", []):
        lines.append(f"> {warning}")
    for method, block in deviations.items():
        if method.startswith("_"):
            continue
        lines.extend(("", f"### {method}", "", "```json"))
        import json
        lines.append(json.dumps(block, ensure_ascii=False, indent=2))
        lines.append("```")
    return "\n".join(lines).strip() or "Нет данных."
