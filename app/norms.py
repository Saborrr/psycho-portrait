"""
Нормы по психологическим методикам + расчёт отклонений.

Что здесь:
  - Базовая таблица норм (mean, std) по каждой шкале каждой методики
  - Скелет для дробления по полу / возрасту / проф-группе (заполняется отдельно)
  - Расчёт Z-скоров, T-скоров, перцентилей и категорий

Источники общепопуляционных норм (для уже стандартизованных шкал —
это часть самих методик):
  - 16PF Кеттелла: стэны 1-10, mean=5.5, SD=2.0 (по определению)
  - MMPI/СМИЛ: T-баллы mean=50, SD=10 (по определению)
  - Амтхауэр: IQ mean=100, SD=15 (по определению)
  - Big Five (T-шкала): mean=50, SD=10 (как у MMPI)
  - DISC / HOLLAND: 0-100, общепопуляционные средние — приблизительные

Демографические нормы (по полу / возрасту / проф-группам) —
ЗАГЛУШКИ. Их нужно наполнять из реальных данных обследований сотрудников.

Пример вызова:
    from app.norms import compute_deviations
    result = compute_deviations(profile, employee)
    # result = {"mmpi": {"D": {"raw": 72, "z": 2.2, "t": 72, "pct": 98.6, "cat": "very_high"}}, ...}
"""
from __future__ import annotations
import math
import statistics
from typing import Optional
from dataclasses import dataclass, field

from .models import (
    ParsedProfile, EmployeeInfo,
    Cattell16PF, BigFive, MMPI, DISC, Holland, MBTI, Amthauer,
)


# === Скелет норм по демографии (ЗАГЛУШКИ) ===
# Формат: {method: {scale: {"all": (mean, std), "by_gender": {...}, "by_age": {...}, "by_prof": {...}}}}
#
# Пример, как заполнять реальные нормы:
#   "Hs": {
#       "all": (50, 10),
#       "by_gender": {
#           "мужской": (48, 9),
#           "женский": (53, 11),
#       },
#       "by_age": {
#           "20-30": (50, 10),
#           "30-40": (51, 10),
#           ...
#       },
#   }

AGE_BUCKETS = [
    (20, 30, "20-30"),
    (30, 40, "30-40"),
    (40, 50, "40-50"),
    (50, 100, "50+"),
]


def _age_bucket(age: Optional[int]) -> Optional[str]:
    if age is None:
        return None
    for lo, hi, name in AGE_BUCKETS:
        if lo <= age <= hi:
            return name
    return None


# === Общепопуляционные нормы ===

# 16PF — стэны. (mean=5.5, std=2) — это часть самой шкалы.
PF16_NORMS = {
    "A": (5.5, 2.0), "B": (5.5, 2.0), "C": (5.5, 2.0), "E": (5.5, 2.0),
    "F": (5.5, 2.0), "G": (5.5, 2.0), "H": (5.5, 2.0), "I": (5.5, 2.0),
    "L": (5.5, 2.0), "M": (5.5, 2.0), "N": (5.5, 2.0), "O": (5.5, 2.0),
    "Q1": (5.5, 2.0), "Q2": (5.5, 2.0), "Q3": (5.5, 2.0), "Q4": (5.5, 2.0),
}

# MMPI / СМИЛ — T-баллы. mean=50, std=10.
# По Собчик есть нюансы по полу (Mf, Pa, Si) — оставим заглушки.
MMPI_NORMS = {
    "L":  (50, 10), "F":  (50, 10), "K":  (50, 10),
    "Hs": (50, 10), "D":  (50, 10), "Hy": (50, 10), "Pd": (50, 10),
    "Mf": (50, 10), "Pa": (50, 10), "Pt": (50, 10), "Sc": (50, 10),
    "Ma": (50, 10), "Si": (50, 10),
    "gentleman": (50, 10),  # корпоративная шкала — заглушка
    "sanity":    (50, 10),  # корпоративная шкала — заглушка
}

# Big Five — T-баллы по дефолту.
B5_NORMS = {
    "openness":          (50, 10),
    "conscientiousness": (50, 10),
    "extraversion":      (50, 10),
    "agreeableness":     (50, 10),
    "neuroticism":       (50, 10),
}

# DISC / HOLLAND — сырые 0-100, общепопуляционная середина ~50, SD ~20.
DISC_NORMS = {"D": (50, 20), "I": (50, 20), "S": (50, 20), "C": (50, 20)}
HOLLAND_NORMS = {"R": (50, 20), "I": (50, 20), "A": (50, 20),
                 "S": (50, 20), "E": (50, 20), "C": (50, 20)}

# MBTI — частотности типов (приблизительные, Briggs-Katherine-Cook Briggs).
# Используем для контекста, не для Z-скоров.
MBTI_TYPE_FREQ = {
    "ISTJ": 11.6, "ISFJ": 13.8, "INFJ": 1.5, "INTJ": 2.1,
    "ISTP": 5.4,  "ISFP": 8.8,  "INFP": 4.4,  "INTP": 3.3,
    "ESTP": 4.3,  "ESFP": 8.5,  "ENFP": 8.1,  "ENTP": 3.2,
    "ESTJ": 8.7,  "ESFJ": 12.3, "ENFJ": 2.5,  "ENTJ": 1.8,
}

# Амтхауэр — IQ. mean=100, SD=15.
AMTHAUER_IQ_NORM = (100, 15)


# === Категории отклонений ===

def _category_from_t(t: float) -> str:
    """Классификация по T-шкале (mean=50, SD=10)."""
    if t < 35:
        return "very_low"      # очень низкий
    if t < 45:
        return "low"           # сниженный
    if t <= 55:
        return "normal"        # норма
    if t <= 65:
        return "high"          # повышенный
    if t <= 75:
        return "very_high"     # высокий
    return "extremely_high"    # экстремально высокий


def _category_ru(cat: str) -> str:
    return {
        "very_low":        "очень низкий",
        "low":             "сниженный",
        "normal":          "норма",
        "high":            "повышенный",
        "very_high":       "высокий",
        "extremely_high":  "экстремально высокий",
    }.get(cat, cat)


def _z_to_pct(z: float) -> float:
    """Z → перцентиль по нормальному распределению (аппроксимация CDF)."""
    # Аппроксимация Абрамовица-Стегуна: erf(z/sqrt(2))
    t = 1.0 / (1.0 + 0.3275911 * abs(z))
    y = 1.0 - (
        ((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t
        + 0.254829592
    ) * t * math.exp(-z * z / 2.0)
    erf = math.copysign(y, z)
    return 0.5 * (1.0 + erf) * 100.0


def _deviation(value: float, mean: float, std: float) -> dict:
    if value is None or mean is None or std is None or std == 0:
        return None
    z = (value - mean) / std
    t = 50 + 10 * z
    pct = _z_to_pct(z)
    return {
        "raw": round(float(value), 2),
        "mean": round(float(mean), 2),
        "std": round(float(std), 2),
        "z": round(z, 2),
        "t": round(t, 1),
        "pct": round(pct, 1),
        "cat": _category_from_t(t),
        "cat_ru": _category_ru(_category_from_t(t)),
    }


def _pick_norm(norms_table: dict, scale: str, employee: EmployeeInfo):
    """Выбрать норму с учётом демографии.
    Приоритет: by_gender > by_age > all.
    Если есть by_prof, его можно добавить позже.
    """
    if scale not in norms_table:
        return None
    entry = norms_table[scale]
    # Если это уже tuple — упрощённый формат
    if isinstance(entry, tuple) and len(entry) == 2:
        return entry
    # Полная структура
    if not isinstance(entry, dict):
        return None
    if employee.gender and "by_gender" in entry:
        g = employee.gender.lower()
        if g in entry["by_gender"]:
            return entry["by_gender"][g]
    if employee.age is not None and "by_age" in entry:
        bucket = _age_bucket(employee.age)
        if bucket and bucket in entry["by_age"]:
            return entry["by_age"][bucket]
    return entry.get("all")


def compute_deviations(profile: ParsedProfile, employee: Optional[EmployeeInfo] = None) -> dict:
    """Посчитать отклонения по всем заполненным шкалам.

    Returns:
        {
          "cattell_16pf": {"A": {...}, "B": {...}, ...},
          "mmpi":         {"Hs": {...}, ...},
          "big_five":     {"openness": {...}, ...},
          "disc":         {"D": {...}, ...},
          "holland":      {"R": {...}, ...},
          "amthauer":     {"iq": {...}},
          "mbti":         {"type": "INTJ", "frequency_pct": 2.1},
          "_demographics": {...},  # что использовалось при подборе нормы
        }
    """
    emp = employee or profile.employee
    methods = profile.methods
    out: dict = {"_demographics": _demographics_str(emp)}

    # 16PF
    if methods.cattell_16pf:
        block = {}
        for scale in Cattell16PF.model_fields:
            v = getattr(methods.cattell_16pf, scale)
            if v is None:
                continue
            norm = _pick_norm(PF16_NORMS, scale, emp)
            if norm:
                d = _deviation(v, *norm)
                if d:
                    block[scale] = d
        if block:
            out["cattell_16pf"] = block

    # MMPI
    if methods.mmpi:
        block = {}
        for scale in ["L", "F", "K", "Hs", "D", "Hy", "Pd", "Mf",
                      "Pa", "Pt", "Sc", "Ma", "Si", "gentleman", "sanity"]:
            v = getattr(methods.mmpi, scale, None)
            if v is None:
                continue
            norm = _pick_norm(MMPI_NORMS, scale, emp)
            if norm:
                d = _deviation(v, *norm)
                if d:
                    block[scale] = d
        if block:
            out["mmpi"] = block

    # Big Five
    if methods.big_five:
        block = {}
        for scale in ["openness", "conscientiousness", "extraversion",
                      "agreeableness", "neuroticism"]:
            v = getattr(methods.big_five, scale)
            if v is None:
                continue
            norm = _pick_norm(B5_NORMS, scale, emp)
            if norm:
                d = _deviation(v, *norm)
                if d:
                    block[scale] = d
        if block:
            out["big_five"] = block

    # DISC
    if methods.disc:
        block = {}
        for scale in ["D", "I", "S", "C"]:
            v = getattr(methods.disc, scale)
            if v is None:
                continue
            norm = _pick_norm(DISC_NORMS, scale, emp)
            if norm:
                d = _deviation(v, *norm)
                if d:
                    block[scale] = d
        if block:
            out["disc"] = block

    # HOLLAND
    if methods.holland:
        block = {}
        for scale in ["R", "I", "A", "S", "E", "C"]:
            v = getattr(methods.holland, scale)
            if v is None:
                continue
            norm = _pick_norm(HOLLAND_NORMS, scale, emp)
            if norm:
                d = _deviation(v, *norm)
                if d:
                    block[scale] = d
        if block:
            out["holland"] = block

    # Amthauer
    if methods.amthauer and methods.amthauer.iq is not None:
        d = _deviation(methods.amthauer.iq, *AMTHAUER_IQ_NORM)
        if d:
            out["amthauer"] = {"iq": d}

    # MBTI — без Z, просто частота типа
    if methods.mbti and methods.mbti.type:
        out["mbti"] = {
            "type": methods.mbti.type,
            "frequency_pct": MBTI_TYPE_FREQ.get(methods.mbti.type),
        }

    return out


def _demographics_str(emp: EmployeeInfo) -> dict:
    return {
        "gender": emp.gender,
        "age": emp.age,
        "age_bucket": _age_bucket(emp.age),
        "position": emp.position,
        "department": emp.department,
    }


# === Человекочитаемая табличка для LLM и UI ===

def format_deviations_md(deviations: dict) -> str:
    """Сводная таблица отклонений в Markdown (для промпта LLM и UI)."""
    method_blocks = [k for k in deviations if not k.startswith("_")]
    if not method_blocks:
        return "_Нет данных для сравнения с нормой._"
    lines = ["**Сравнение с общепопуляционной нормой** "
             f"(использованы: {deviations.get('_demographics', {})})", ""]

    METHOD_TITLES = {
        "cattell_16pf": "16PF Кеттелла (стэны, норма M=5.5, SD=2)",
        "mmpi":         "MMPI / СМИЛ (T-баллы, M=50, SD=10)",
        "big_five":     "Big Five (T-баллы, M=50, SD=10)",
        "disc":         "DISC (0-100, норма ~50, SD≈20)",
        "holland":      "HOLLAND (0-100, норма ~50, SD≈20)",
        "amthauer":     "Амтхауэр (IQ, M=100, SD=15)",
        "mbti":         "MBTI (частота типа в популяции)",
    }

    SCALE_NAMES_BY_METHOD = {
        "cattell_16pf": {
            "A": "A — Замкнутость↔Общительность", "B": "B — Интеллект",
            "C": "C — Эмоц. устойчивость", "E": "E — Подчиненность↔Доминирование",
            "F": "F — Сдержанность↔Экспрессивность", "G": "G — Совестливость",
            "H": "H — Робость↔Смелость", "I": "I — Жесткость↔Чувствительность",
            "L": "L — Доверчивость↔Подозрительность", "M": "M — Мечтательность",
            "N": "N — Прямолинейность↔Дипломатичность", "O": "O — Тревожность",
            "Q1": "Q1 — Радикализм", "Q2": "Q2 — Самостоятельность",
            "Q3": "Q3 — Самоконтроль", "Q4": "Q4 — Напряжённость",
        },
        "mmpi": {
            "L": "L (ложь)", "F": "F (достоверность)", "K": "K (коррекция)",
            "Hs": "1. Невротический сверхконтроль", "D": "2. Пессимистичность",
            "Hy": "3. Эмоц. лабильность", "Pd": "4. Импульсивность",
            "Mf": "5. Маскулинность-фемининность", "Pa": "6. Ригидность",
            "Pt": "7. Тревожность", "Sc": "8. Индивидуалистичность",
            "Ma": "9. Оптимизм и активность", "Si": "0. Социальная интроверсия",
            "gentleman": "Джентльмен (ЭФКО)", "sanity": "Здравомыслие (ЭФКО)",
        },
        "big_five": {
            "openness": "Открытость", "conscientiousness": "Добросовестность",
            "extraversion": "Экстраверсия", "agreeableness": "Доброжелательность",
            "neuroticism": "Нейротизм",
        },
        "disc": {
            "D": "D (доминирование)", "I": "I (влияние)",
            "S": "S (стабильность)", "C": "C (соответствие)",
        },
        "holland": {
            "R": "R (реалистичный)", "I": "I (исследовательский)",
            "A": "A (артистический)", "S": "S (социальный)",
            "E": "E (предприимчивый)", "C": "C (конвенциональный)",
        },
    }

    names = SCALE_NAMES_BY_METHOD

    for method_key, block in deviations.items():
        if method_key.startswith("_"):
            continue
        title = METHOD_TITLES.get(method_key, method_key)
        lines.append(f"### {title}")
        if method_key == "mbti":
            t = block.get("type", "?")
            freq = block.get("frequency_pct")
            freq_s = f"~{freq}% в популяции" if freq else "нет данных о частоте"
            lines.append(f"- Тип: **{t}** — {freq_s}")
            lines.append("")
            continue
        # Таблица: Шкала | Raw | T | Категория
        lines.append("| Шкала | Балл | T-балл | % | Категория |")
        lines.append("|-------|------|--------|---|-----------|")
        for scale, dev in block.items():
            name = names.get(method_key, {}).get(scale, scale)
            if "iq" == scale:
                name = "IQ"
            lines.append(
                f"| {name} | {dev['raw']} | {dev['t']} | {dev['pct']} | {dev['cat_ru']} |"
            )
        lines.append("")

    return "\n".join(lines)
