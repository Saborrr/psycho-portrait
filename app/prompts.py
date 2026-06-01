"""
Промпты для генерации психологической характеристики.
"""
from __future__ import annotations
from .models import ParsedProfile


SYSTEM_PROMPT = """Ты — опытный психолог-консультант, методолог, специалист по психодиагностике.
Твоя задача — на основе извлечённых результатов психологических тестов написать связную,
профессиональную психологическую характеристику сотрудника.

Требования к тексту:
- Язык: русский, профессиональный стиль психологического заключения.
- Без воды, без пафоса, без «воды» в духе «уникальная личность».
- Опора ТОЛЬКО на представленные данные. Не выдумывать факты.
- Где данных не хватает — так и пиши «данные не представлены».
- Не выходить за рамки психологической интерпретации (диагнозы не ставить, лечение не назначать).
- Не использовать шаблонные фразы типа «данный сотрудник является», «следует отметить».
- Соблюдать этический кодекс психолога: уважение к личности, конфиденциальность, без стигматизации.

Структура ответа (Markdown):

# Психологическая характеристика: Фамилия И. О.

## 1. Общие сведения
- Должность, подразделение, возраст, стаж, образование — что известно.

## 2. Методики и результаты
- Краткое перечисление методик с сырыми данными (таблица).

## 3. Личностный профиль
- Развёрнутая интерпретация каждой методики, со ссылкой на конкретные факторы/баллы.
- Стиль: «фактор X = 7 стэнов — это значит…».
- Без выдуманных трактовок.

## 4. Сильные стороны
- Пункты 3-5, опирающиеся на результаты.

## 5. Зоны развития и риски
- Пункты 3-5.

## 6. Рекомендации руководителю
- Конкретные рекомендации по управлению, мотивации, развитию, обучению.

## 7. Резюме
- 2-3 предложения, обобщающие психологический портрет.

## ⚠️ Ограничения
- Это программно-сгенерированный черновик на основе результатов тестов.
- Финальное заключение делает психолог с профильным образованием.
- Методики измеряют предпочтения и актуальные состояния, а не «истинную» личность.
"""


def build_user_prompt(profile: ParsedProfile) -> str:
    """Собирает user-сообщение с данными профиля."""
    parts = []

    emp = profile.employee
    parts.append("## Данные о сотруднике\n")
    parts.append(f"- ФИО: {emp.full_name or 'не указано'}")
    parts.append(f"- Должность: {emp.position or 'не указана'}")
    parts.append(f"- Подразделение: {emp.department or 'не указано'}")
    parts.append(f"- Возраст: {emp.age if emp.age is not None else 'не указан'}")
    parts.append(f"- Пол: {emp.gender or 'не указан'}")
    parts.append(f"- Стаж: {emp.tenure_years if emp.tenure_years is not None else 'не указан'}")
    parts.append(f"- Образование: {emp.education or 'не указано'}")

    parts.append("\n## Результаты методик\n")
    methods = profile.methods

    if methods.cattell_16pf and any(getattr(methods.cattell_16pf, f) is not None for f in methods.cattell_16pf.model_fields):
        parts.append("### 16PF Кеттелла (стэны 1-10, норма 5-6)\n")
        labels = {
            "A": "A — Замкнутость ↔ Общительность",
            "B": "B — Низкий ↔ Высокий интеллект",
            "C": "C — Эмоц. неустойчивость ↔ Устойчивость",
            "E": "E — Подчинённость ↔ Доминирование",
            "F": "F — Сдержанность ↔ Экспрессивность",
            "G": "G — Низкая ↔ Высокая совестливость",
            "H": "H — Робость ↔ Смелость",
            "I": "I — Жесткость ↔ Чувствительность",
            "L": "L — Доверчивость ↔ Подозрительность",
            "M": "M — Практичность ↔ Мечтательность",
            "N": "N — Прямолинейность ↔ Дипломатичность",
            "O": "O — Уверенность ↔ Тревожность",
            "Q1": "Q1 — Консерватизм ↔ Радикализм",
            "Q2": "Q2 — Зависимость ↔ Самостоятельность",
            "Q3": "Q3 — Низкий ↔ Высокий самоконтроль",
            "Q4": "Q4 — Расслабленность ↔ Напряжённость",
        }
        for f, label in labels.items():
            v = getattr(methods.cattell_16pf, f)
            if v is not None:
                parts.append(f"- **{label}**: {v}")

    if methods.big_five and any(getattr(methods.big_five, f) is not None for f in ["openness","conscientiousness","extraversion","agreeableness","neuroticism"]):
        parts.append("\n### Big Five (баллы)\n")
        bf = methods.big_five
        if bf.openness is not None:         parts.append(f"- **Открытость опыту**: {bf.openness}")
        if bf.conscientiousness is not None: parts.append(f"- **Добросовестность**: {bf.conscientiousness}")
        if bf.extraversion is not None:      parts.append(f"- **Экстраверсия**: {bf.extraversion}")
        if bf.agreeableness is not None:     parts.append(f"- **Доброжелательность**: {bf.agreeableness}")
        if bf.neuroticism is not None:       parts.append(f"- **Нейротизм**: {bf.neuroticism}")

    if methods.mmpi and any(getattr(methods.mmpi, f) is not None for f in methods.mmpi.model_fields):
        parts.append("\n### MMPI / СМИЛ (T-баллы, норма 50±10)\n")
        mm = methods.mmpi
        mmpi_labels = {
            "L": "L — Ложь", "F": "F — Достоверность", "K": "K — Коррекция",
            "Hs": "Hs — Ипохондрия", "D": "D — Депрессия", "Hy": "Hy — Истерия",
            "Pd": "Pd — Асоциальная психопатия", "Mf": "Mf — Маскулинность-фемининность",
            "Pa": "Pa — Паранойя", "Pt": "Pt — Психастения", "Sc": "Sc — Шизофрения",
            "Ma": "Ma — Гипомания", "Si": "Si — Социальная интроверсия",
        }
        for f, label in mmpi_labels.items():
            v = getattr(mm, f)
            if v is not None:
                parts.append(f"- **{label}**: {v}")

    if methods.disc and any(getattr(methods.disc, f) is not None for f in ["D","I","S","C"]):
        parts.append("\n### DISC (баллы 0-100)\n")
        d = methods.disc
        if d.D is not None: parts.append(f"- **D — Доминирование**: {d.D}")
        if d.I is not None: parts.append(f"- **I — Влияние**: {d.I}")
        if d.S is not None: parts.append(f"- **S — Стабильность**: {d.S}")
        if d.C is not None: parts.append(f"- **C — Соответствие**: {d.C}")

    if methods.holland and (any(getattr(methods.holland, f) is not None for f in ["R","I","A","S","E","C"]) or methods.holland.code):
        parts.append("\n### HOLLAND RIASEC\n")
        h = methods.holland
        if h.R is not None: parts.append(f"- R (Реалистичный): {h.R}")
        if h.I is not None: parts.append(f"- I (Исследовательский): {h.I}")
        if h.A is not None: parts.append(f"- A (Артистический): {h.A}")
        if h.S is not None: parts.append(f"- S (Социальный): {h.S}")
        if h.E is not None: parts.append(f"- E (Предприимчивый): {h.E}")
        if h.C is not None: parts.append(f"- C (Конвенциональный): {h.C}")
        if h.code: parts.append(f"- **Код Холланда**: {h.code}")

    if methods.mbti and methods.mbti.type:
        parts.append(f"\n### MBTI: {methods.mbti.type}")

    if methods.amthauer and (methods.amthauer.iq or methods.amthauer.subscales):
        parts.append("\n### Амтхауэр\n")
        if methods.amthauer.iq:
            parts.append(f"- **IQ**: {methods.amthauer.iq}")

    if profile.notes:
        parts.append("\n## Заметки парсера\n")
        for n in profile.notes:
            parts.append(f"- {n}")

    parts.append(
        "\n\nНапиши психологическую характеристику строго по указанной структуре. "
        "Опирайся только на представленные данные. Если какой-то раздел не подкреплён данными — "
        "напиши «данные не представлены» или опусти раздел."
    )

    return "\n".join(parts)
