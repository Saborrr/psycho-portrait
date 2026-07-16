"""
ЭФКО-корпоративные методики.

⚠️ Это **внутренние методики** ГК «ЭФКО» — НЕ стандартные психологические тесты.
Они используются для HR-отбора и развития сотрудников предприятий ЭФКО.

15 тестовых блоков, встречающихся в предоставленных материалах:
  1. Служебные отношения 1
  2. Служебные отношения 2
  3. Логическое мышление
  4. Лексика
  5. Жизненные парадигмы
  6. Визуальные образы
  7. Восприятие отношений
  8. Образное мышление
  9. Социальные отношения 1
 10. Социокультурный взгляд 1
 11. Социальные ориентиры
 12. Социокультурный взгляд 2
 13. Организация труда
 14. Предпочтения в деятельности
 15. Социальные отношения 2

+ блоки ЭЧВ/ЭЧМ (Эмоционально-Чувственное Восприятие / Моделирование).

Пороговые диапазоны и правила интерпретации вынесены в ``app.methodology`` и
основаны на приложенной лекции «Психологическое тестирование кандидатов»,
актуализация 30.01.2025. Эти проценты нельзя называть популяционными
перцентилями или клиническими показателями.
"""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


# === Тесты интеллекта (3 из 15) ===

class LogicheskoeMyshlenie(BaseModel):
    """Тест «Логическое мышление»."""
    score: Optional[float] = Field(None, description="Балл / процентиль (T-шкала или %)")


class Leksika(BaseModel):
    """Тест «Лексика» (вербальные способности)."""
    score: Optional[float] = Field(None, description="Балл / процентиль")


class ObraznoeMyshlenie(BaseModel):
    """Тест «Образное мышление»."""
    score: Optional[float] = Field(None, description="Балл / процентиль")


class VizualnyeObrazy(BaseModel):
    """Тест «Визуальные образы» (зрительное восприятие и память)."""
    score: Optional[float] = Field(None, description="Балл / процентиль")


# === Социально-психологические (6 из 15) ===

class SluzhebnyeOtnosheniya1(BaseModel):
    """Тест «Служебные отношения 1»."""
    score: Optional[float] = Field(None, description="Балл / процентиль")
    extra: dict = Field(default_factory=dict)


class SluzhebnyeOtnosheniya2(BaseModel):
    """Тест «Служебные отношения 2»."""
    score: Optional[float] = Field(None, description="Балл / процентиль")
    extra: dict = Field(default_factory=dict)


class SocialnyeOtnosheniya1(BaseModel):
    """Тест «Социальные отношения 1»."""
    score: Optional[float] = Field(None)
    extra: dict = Field(default_factory=dict)


class SocialnyeOtnosheniya2(BaseModel):
    """Тест «Социальные отношения 2»."""
    score: Optional[float] = Field(None)
    extra: dict = Field(default_factory=dict)


class SociokulturnyiVzglyad1(BaseModel):
    """Тест «Социокультурный взгляд 1»."""
    score: Optional[float] = Field(None)
    extra: dict = Field(default_factory=dict)


class SociokulturnyiVzglyad2(BaseModel):
    """Тест «Социокультурный взгляд 2»."""
    score: Optional[float] = Field(None)
    extra: dict = Field(default_factory=dict)


# === Жизненные и социокультурные (2 из 15) ===

class ZhiznennyeParadigmy(BaseModel):
    """Тест «Жизненные парадигмы» — содержательно: азарт к жизни, гармония радости/дискомфорта,
    парадигма «Я не могу это не сделать», отношение к модели достижения успеха.
    Бессознательная и сознательная оценка (%)."""
    azart: Optional[float] = Field(None, description="Азарт к жизни, %")
    garmonia_radosti: Optional[float] = Field(None, description="Гармония радости/дискомфорта, %")
    ne_mogu_ne_sdelat: Optional[float] = Field(None, description="Парадигма «Я не могу это не сделать», %")
    otnoshenie_k_uspehu: Optional[float] = Field(None, description="Отношение к модели достижения успеха, %")
    conscious: Optional[bool] = Field(None, description="Сознательная оценка? (если True — осознанно, иначе бессознательно)")


class SocialnyeOrientiry(BaseModel):
    """Тест «Социальные ориентиры» — содержательно: типы персонала по отношению
    к работе и развитию, возможно парадигма отношения к работодателю."""
    score: Optional[float] = Field(None)
    extra: dict = Field(default_factory=dict)


# === Трудовые и мотивационные (4 из 15) ===

class OrganizaciyaTruda(BaseModel):
    """Тест «Организация труда» — содержательно: активность (физическая, интеллектуальная,
    коммуникационная), отношение к дискомфорту в работе (ВТР, СЭДО, Опрятность, Норматив командировок)."""
    fizicheskaya: Optional[float] = Field(None, description="Активность физическая, %")
    intellektualnaya: Optional[float] = Field(None, description="Активность интеллектуальная, %")
    kommunikacionnaya: Optional[float] = Field(None, description="Активность коммуникационная, %")
    vtr: Optional[float] = Field(None, description="ВТР (внутренняя трудовая регуляция?), %")
    sedo: Optional[float] = Field(None, description="СЭДО, %")
    opryatnost: Optional[float] = Field(None, description="Опрятность, %")
    normativ_komandirovok: Optional[float] = Field(None, description="Норматив командировок, %")


class PredpochteniyaVDeatelnosti(BaseModel):
    """Тест «Предпочтения в деятельности» — содержательно: модель по отношению
    к правилам безопасности (Обезбашенный герой, Безынициативный исполнитель, Защитник)."""
    obezbashennyy_geroy: Optional[float] = Field(None, description="Обезбашенный герой, %")
    bezyniciativnyy_ispolnitel: Optional[float] = Field(None, description="Безынициативный исполнитель, %")
    zashitnik: Optional[float] = Field(None, description="Защитник, %")


# === Восприятие и социокультурные (1 из 15) ===

class VospriyatieOtnosheniy(BaseModel):
    """Тест «Восприятие отношений» — содержательно: «Постмодерн, %»."""
    postmodern: Optional[float] = Field(None, description="Постмодерн, %")


# === Блоки ЭЧВ/ЭЧМ (из задания, не тесты, а глубина восприятия) ===

class EchvEchm(BaseModel):
    """Глубина ЭЧВ (эмоционально-чувственное восприятие) и ЭЧМ (эмоционально-чувственное моделирование).
    Хранится как % по двум шкалам; диапазоны берутся из приложенной лекции."""
    echv: Optional[float] = Field(None, description="Глубина ЭЧВ (эмоционально-чувственного восприятия), %")
    echm: Optional[float] = Field(None, description="Глубина ЭЧМ (эмоционально-чувственного моделирования), %")


# === Эмпатия (из реальных pptx) ===

class Empaty(BaseModel):
    """Эмпатия — сознательная + бессознательная, 2 рода (видимо, рациональная + эмоциональная)."""
    conscious: Optional[float] = Field(None, description="Сознательная эмпатия, %")
    unconscious: Optional[float] = Field(None, description="Бессознательная эмпатия, %")
    kind_2_rational: Optional[float] = Field(None, description="Эмпатия рациональная (2 рода), %")
    kind_2_emotional: Optional[float] = Field(None, description="Эмпатия эмоциональная (2 рода), %")


# === Активность (отдельный блок в pptx) ===

class Aktivnost(BaseModel):
    """Активность — физическая, интеллектуальная, коммуникационная, %."""
    fizicheskaya: Optional[float] = Field(None, description="Физическая, %")
    intellektualnaya: Optional[float] = Field(None, description="Интеллектуальная, %")
    kommunikacionnaya: Optional[float] = Field(None, description="Коммуникационная, %")


# === Интеллект (3 шкалы из pptx) ===

class IntellektEfk(BaseModel):
    """Интеллект (по pptx): Логический, Образный, Лексика, %."""
    logicheskiy: Optional[float] = Field(None, description="Логический интеллект, %")
    obrazny: Optional[float] = Field(None, description="Образный интеллект, %")
    leksika: Optional[float] = Field(None, description="Лексика, %")


class ConsciousUnconsciousScore(BaseModel):
    """Одна шкала с сознательной и бессознательной оценкой, %."""
    conscious: Optional[float] = None
    unconscious: Optional[float] = None


class EmployerParadigm(BaseModel):
    """Парадигма отношения к работодателю."""
    nothing_personal: ConsciousUnconsciousScore = Field(default_factory=ConsciousUnconsciousScore)
    partnership: ConsciousUnconsciousScore = Field(default_factory=ConsciousUnconsciousScore)
    solidarity: ConsciousUnconsciousScore = Field(default_factory=ConsciousUnconsciousScore)


class LifeGamble(BaseModel):
    """Азарт к жизни, бессознательная оценка, %."""
    creative: Optional[float] = Field(None, description="Созидательный азарт")
    idle: Optional[float] = Field(None, description="Праздный азарт")
    passivity: Optional[float] = Field(None, description="Пассивность")


class HarmonyDecision(BaseModel):
    """Гармония радости/дискомфорта и решительность, %."""
    discomfort_harmony: Optional[float] = Field(None, description="Гармония дискомфорта")
    decisiveness: Optional[float] = Field(None, description="Решительность")
    joy_harmony: Optional[float] = Field(None, description="Гармония радости")
    caution: Optional[float] = Field(None, description="Осторожность")


class WorkDiscomfort(BaseModel):
    """Принятие корпоративных норм и служебного дискомфорта, %."""
    vtr: Optional[float] = None
    sedo: Optional[float] = None
    neatness: Optional[float] = None
    business_trips: Optional[float] = None


class AchievementModel(BaseModel):
    """Отношение к модели достижения успеха, %."""
    rational_enterprising: Optional[float] = None
    enabling_entrepreneurs: Optional[float] = None
    public_dismissal_significance: Optional[float] = None


class PersonnelTypes(BaseModel):
    """Типы персонала по отношению к работе и развитию, %."""
    worker: Optional[float] = Field(None, description="Труженик")
    evolutionary_development: Optional[float] = None
    leadership: Optional[float] = None
    duelist: Optional[float] = Field(None, description="Поединщик")


class SafetyAttitude(BaseModel):
    """Модели отношения к правилам безопасности, %."""
    reckless_hero: Optional[float] = None
    passive_executor: Optional[float] = None
    protector: Optional[float] = None


# === Сводный блок ЭФКО-методик (всё вместе) ===

class EFKOSet(BaseModel):
    """Полный набор ЭФКО-методик. Хранится как Optional-слова для совместимости
    с пустыми файлами (Кононов, Олемская в присланной пачке)."""
    # Тесты (15)
    sluzhebnye_otnosheniya_1: Optional[SluzhebnyeOtnosheniya1] = None
    sluzhebnye_otnosheniya_2: Optional[SluzhebnyeOtnosheniya2] = None
    logicheskoe_myshlenie: Optional[LogicheskoeMyshlenie] = None
    leksika: Optional[Leksika] = None
    zhiznennye_paradigmy: Optional[ZhiznennyeParadigmy] = None
    vizualnye_obrazy: Optional[VizualnyeObrazy] = None
    vospriyatie_otnosheniy: Optional[VospriyatieOtnosheniy] = None
    obraznoe_myshlenie: Optional[ObraznoeMyshlenie] = None
    socialnye_otnosheniya_1: Optional[SocialnyeOtnosheniya1] = None
    sociokulturnyi_vzglyad_1: Optional[SociokulturnyiVzglyad1] = None
    socialnye_orientiry: Optional[SocialnyeOrientiry] = None
    sociokulturnyi_vzglyad_2: Optional[SociokulturnyiVzglyad2] = None
    organizaciya_truda: Optional[OrganizaciyaTruda] = None
    predpochteniya_v_deyatelnosti: Optional[PredpochteniyaVDeatelnosti] = None
    socialnye_otnosheniya_2: Optional[SocialnyeOtnosheniya2] = None
    # Блоки из реальных pptx (помимо тестов)
    intellekt: Optional[IntellektEfk] = Field(None, description="ИНТЕЛЛЕКТ: Логический, Образный, Лексика")
    aktivnost: Optional[Aktivnost] = Field(None, description="АКТИВНОСТЬ: Физ/Инт/Коммун")
    empaty: Optional[Empaty] = Field(None, description="ЭМПАТИЯ: созн/бессозн, 2 рода")
    echv_echm: Optional[EchvEchm] = Field(None, description="Глубина ЭЧВ и ЭЧМ")
    # Прочие блоки из реальных pptx
    postmodern: Optional[float] = Field(None, description="Постмодерн, %")
    employer_paradigm: Optional[EmployerParadigm] = None
    life_gamble: Optional[LifeGamble] = None
    harmony_decision: Optional[HarmonyDecision] = None
    work_discomfort: Optional[WorkDiscomfort] = None
    achievement_model: Optional[AchievementModel] = None
    personnel_types: Optional[PersonnelTypes] = None
    safety_attitude: Optional[SafetyAttitude] = None
    # Оставлено для обратной совместимости со старыми JSON.
    paradigma_k_rabotodatelyu: Optional[str] = Field(None, description="Устаревшее текстовое поле")
    gotovnost_k_komandirovkam: Optional[str] = Field(None, description="Готовность к командировкам/переезду")
    # Свободные поля (для новых блоков, которые не распознались)
    extra: dict = Field(default_factory=dict)


# Каталог для динамической работы (например, в промптах)
EFKO_TEST_CATALOG = {
    "sluzhebnye_otnosheniya_1": "Служебные отношения 1",
    "sluzhebnye_otnosheniya_2": "Служебные отношения 2",
    "logicheskoe_myshlenie": "Логическое мышление",
    "leksika": "Лексика",
    "zhiznennye_paradigmy": "Жизненные парадигмы",
    "vizualnye_obrazy": "Визуальные образы",
    "vospriyatie_otnosheniy": "Восприятие отношений",
    "obraznoe_myshlenie": "Образное мышление",
    "socialnye_otnosheniya_1": "Социальные отношения 1",
    "sociokulturnyi_vzglyad_1": "Социокультурный взгляд 1",
    "socialnye_orientiry": "Социальные ориентиры",
    "sociokulturnyi_vzglyad_2": "Социокультурный взгляд 2",
    "organizaciya_truda": "Организация труда",
    "predpochteniya_v_deyatelnosti": "Предпочтения в деятельности",
    "socialnye_otnosheniya_2": "Социальные отношения 2",
}
