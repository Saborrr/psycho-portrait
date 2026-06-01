"""Pydantic-модели для представления результатов психологических тестов."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


class EmployeeInfo(BaseModel):
    """Шапка профиля — ФИО, должность, подразделение, возраст, стаж и т.п."""
    full_name: Optional[str] = None
    position: Optional[str] = None
    department: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    tenure_years: Optional[float] = None
    education: Optional[str] = None
    extra: dict = Field(default_factory=dict)


# === Методики ===

class Cattell16PF(BaseModel):
    """16PF Кеттелла — 16 первичных факторов, шкала стэнов 1-10."""
    # Буквенный код A, B, C, E, F, G, H, I, L, M, N, O, Q1, Q2, Q3, Q4
    A: Optional[float] = Field(None, description="Замкнутость — общительность")
    B: Optional[float] = Field(None, description="Низкий — высокий интеллект")
    C: Optional[float] = Field(None, description="Эмоц. неустойчивость — устойчивость")
    E: Optional[float] = Field(None, description="Подчиненность — доминирование")
    F: Optional[float] = Field(None, description="Сдержанность — экспрессивность")
    G: Optional[float] = Field(None, description="Низкая — высокая совестливость")
    H: Optional[float] = Field(None, description="Робость — смелость")
    I: Optional[float] = Field(None, description="Жесткость — чувствительность")
    L: Optional[float] = Field(None, description="Доверчивость — подозрительность")
    M: Optional[float] = Field(None, description="Практичность — мечтательность")
    N: Optional[float] = Field(None, description="Прямолинейность — дипломатичность")
    O: Optional[float] = Field(None, description="Уверенность — тревожность")
    Q1: Optional[float] = Field(None, description="Консерватизм — радикализм")
    Q2: Optional[float] = Field(None, description="Зависимость — самостоятельность")
    Q3: Optional[float] = Field(None, description="Низкий — высокий самоконтроль")
    Q4: Optional[float] = Field(None, description="Расслабленность — напряжённость")


class BigFive(BaseModel):
    """Big Five / NEO-PI-R. T-баллы или сырые — что укажешь в `scale`."""
    scale: str = Field("T", description="T (T-баллы) | raw (0-100)")
    openness: Optional[float] = Field(None, description="Открытость опыту")
    conscientiousness: Optional[float] = Field(None, description="Добросовестность")
    extraversion: Optional[float] = Field(None, description="Экстраверсия")
    agreeableness: Optional[float] = Field(None, description="Доброжелательность/Уживчивость")
    neuroticism: Optional[float] = Field(None, description="Нейротизм")


class MMPI(BaseModel):
    """MMPI / СМИЛ — 3 валид. + 10 клинических шкал, T-баллы (норма 50, SD 10)."""
    # Валидность
    L: Optional[float] = Field(None, description="Ложь")
    F: Optional[float] = Field(None, description="Достоверность (F)")
    K: Optional[float] = Field(None, description="Коррекция (K)")
    # Клинические
    Hs: Optional[float] = Field(None, description="1. Ипохондрия")
    D: Optional[float] = Field(None, description="2. Депрессия")
    Hy: Optional[float] = Field(None, description="3. Истерия / конверсия")
    Pd: Optional[float] = Field(None, description="4. Асоциальная психопатия")
    Mf: Optional[float] = Field(None, description="5. Маскулинность-фемининность")
    Pa: Optional[float] = Field(None, description="6. Паранойя")
    Pt: Optional[float] = Field(None, description="7. Психастения")
    Sc: Optional[float] = Field(None, description="8. Шизофрения")
    Ma: Optional[float] = Field(None, description="9. Гипомания")
    Si: Optional[float] = Field(None, description="0. Социальная интроверсия")


class DISC(BaseModel):
    """DISC — 4 оси, баллы от 0 до 100 (или нормализованные %)."""
    D: Optional[float] = Field(None, description="Dominance — доминирование")
    I: Optional[float] = Field(None, description="Influence — влияние")
    S: Optional[float] = Field(None, description="Steadiness — стабильность")
    C: Optional[float] = Field(None, description="Conscientiousness — соответствие")


class Holland(BaseModel):
    """HOLLAND RIASEC — 6 баллов + код (3 буквы)."""
    R: Optional[float] = Field(None, description="Realistic — реалистичный")
    I: Optional[float] = Field(None, description="Investigative — исследовательский")
    A: Optional[float] = Field(None, description="Artistic — артистический")
    S: Optional[float] = Field(None, description="Social — социальный")
    E: Optional[float] = Field(None, description="Enterprising — предприимчивый")
    C: Optional[float] = Field(None, description="Conventional — конвенциональный")
    code: Optional[str] = Field(None, description="3-буквенный код (напр. SAI)")


class MBTI(BaseModel):
    """MBTI — 4 дихотомии, в сумме 4 буквы."""
    E_I: Optional[str] = Field(None, description="E или I")
    S_N: Optional[str] = Field(None, description="S или N")
    T_F: Optional[str] = Field(None, description="T или F")
    J_P: Optional[str] = Field(None, description="J или P")
    type: Optional[str] = Field(None, description="Напр. INTJ, ESFP")


class Amthauer(BaseModel):
    """Тест Амтхауэра — IQ и субтесты."""
    iq: Optional[int] = Field(None, description="Общий IQ")
    subscales: dict = Field(default_factory=dict, description="Субтесты 1-9")


class MethodScores(BaseModel):
    """Собранный набор результатов по всем обнаруженным методикам."""
    cattell_16pf: Optional[Cattell16PF] = None
    big_five: Optional[BigFive] = None
    mmpi: Optional[MMPI] = None
    disc: Optional[DISC] = None
    holland: Optional[Holland] = None
    mbti: Optional[MBTI] = None
    amthauer: Optional[Amthauer] = None
    extra: dict = Field(default_factory=dict, description="Любые нераспознанные данные")


class ParsedProfile(BaseModel):
    """То, что парсер извлёк из PPTX — единый объект."""
    employee: EmployeeInfo
    methods: MethodScores
    raw_text: str = Field("", description="Весь текст презентации (для LLM-контекста)")
    slides_count: int = 0
    notes: list[str] = Field(default_factory=list, description="Заметки парсера (что не распозналось)")
