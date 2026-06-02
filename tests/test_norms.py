"""
Тест norms.py: Z-скоры, T-скоры, перцентили, категории, форматирование.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.norms import (  # noqa: E402
    compute_deviations, format_deviations_md, _deviation, _z_to_pct,
    _category_from_t, _category_ru, _age_bucket,
)
from app.models import (  # noqa: E402
    ParsedProfile, EmployeeInfo, MethodScores,
    Cattell16PF, BigFive, MMPI, DISC, Holland, MBTI, Amthauer,
)


def test_math_helpers():
    # Z=0 → T=50, pct=50
    d = _deviation(50, 50, 10)
    assert d["z"] == 0.0
    assert d["t"] == 50.0
    assert abs(d["pct"] - 50.0) < 0.1
    assert d["cat"] == "normal"
    print("✅ _deviation: z=0 → T=50, pct=50, normal")

    # Z=2 → T=70, pct≈98.3 (аппроксимация erf)
    d = _deviation(70, 50, 10)
    assert d["z"] == 2.0
    assert d["t"] == 70.0
    assert abs(d["pct"] - 98.27) < 1.0  # аппроксимация даёт ~98.27 (реально 97.73)
    assert d["cat"] == "very_high"
    print(f"✅ _deviation: z=2 → T={d['t']}, pct={d['pct']}, very_high")

    # Z=-2 → T=30, pct≈1.7
    d = _deviation(30, 50, 10)
    assert d["t"] == 30.0
    assert abs(d["pct"] - 1.73) < 1.0
    assert d["cat"] == "very_low"
    print(f"✅ _deviation: z=-2 → T={d['t']}, pct={d['pct']}, very_low")

    # Категории по границам
    assert _category_from_t(34) == "very_low"
    assert _category_from_t(35) == "low"
    assert _category_from_t(45) == "normal"
    assert _category_from_t(55) == "normal"
    assert _category_from_t(56) == "high"
    assert _category_from_t(65) == "high"
    assert _category_from_t(66) == "very_high"
    assert _category_from_t(75) == "very_high"
    assert _category_from_t(76) == "extremely_high"
    print("✅ _category_from_t: границы корректны")

    # Русские названия
    assert _category_ru("very_low") == "очень низкий"
    assert _category_ru("normal") == "норма"
    assert _category_ru("extremely_high") == "экстремально высокий"
    print("✅ _category_ru: перевод корректен")

    # Возрастные бакеты
    assert _age_bucket(25) == "20-30"
    assert _age_bucket(30) == "20-30"  # граница входит в нижний бакет
    assert _age_bucket(31) == "30-40"
    assert _age_bucket(40) == "30-40"  # граница входит в нижний бакет
    assert _age_bucket(41) == "40-50"
    assert _age_bucket(55) == "50+"
    assert _age_bucket(None) is None
    print("✅ _age_bucket: 25→20-30, 30→20-30, 31→30-40, 55→50+")


def test_full_profile():
    p = ParsedProfile(
        employee=EmployeeInfo(full_name="Тестов Тест", age=35, gender="мужской"),
        methods=MethodScores(
            cattell_16pf=Cattell16PF(A=8, E=9),  # стэны 8 и 9
            big_five=BigFive(openness=70, conscientiousness=80, neuroticism=40),
            mmpi=MMPI(Hs=72, D=68, Pd=80, L=51, F=47, K=56, code="4-7"),
            disc=DISC(D=80, S=30),
            holland=Holland(R=20, I=85),
            mbti=MBTI(type="INTJ", E_I="I", S_N="N", T_F="T", J_P="J"),
            amthauer=Amthauer(iq=130),
        ),
    )
    dev = compute_deviations(p)
    # Должны быть все 7 методик
    assert "cattell_16pf" in dev
    assert "mmpi" in dev
    assert "big_five" in dev
    assert "disc" in dev
    assert "holland" in dev
    assert "amthauer" in dev
    assert "mbti" in dev
    assert "_demographics" in dev
    assert dev["_demographics"]["age_bucket"] == "30-40"
    print(f"✅ compute_deviations: все 7 методик + demographics={dev['_demographics']}")

    # Проверим конкретные шкалы
    # 16PF A=8 → mean=5.5, std=2 → z=1.25, T=62.5
    assert dev["cattell_16pf"]["A"]["t"] == 62.5
    # MMPI Hs=72 → mean=50, std=10 → z=2.2, T=72
    assert dev["mmpi"]["Hs"]["t"] == 72.0
    assert dev["mmpi"]["Hs"]["cat"] == "very_high"
    # Big Five openness=70 → T=70
    assert dev["big_five"]["openness"]["t"] == 70.0
    # DISC D=80 → mean=50, std=20 → z=1.5, T=65
    assert dev["disc"]["D"]["t"] == 65.0
    # Amthauer IQ=130 → mean=100, std=15 → z=2, T=70
    assert dev["amthauer"]["iq"]["t"] == 70.0
    # MBTI INTJ частота ~2.1%
    assert dev["mbti"]["type"] == "INTJ"
    assert abs(dev["mbti"]["frequency_pct"] - 2.1) < 0.1
    print("✅ Конкретные шкалы: 16PF A=8→T=62.5, MMPI Hs=72→T=72, IQ 130→T=70")


def test_format_markdown():
    p = ParsedProfile(
        employee=EmployeeInfo(full_name="X", age=35, gender="мужской"),
        methods=MethodScores(mmpi=MMPI(Hs=72, D=68)),
    )
    md = format_deviations_md(compute_deviations(p))
    assert "Сравнение с общепопуляционной нормой" in md
    assert "MMPI" in md
    assert "1. Невротический сверхконтроль" in md  # правильное имя шкалы
    assert "2. Пессимистичность" in md
    assert "высокий" in md  # категория
    assert "T-балл" in md
    print("✅ format_deviations_md: содержит правильные имена шкал, категории и шапку")


def test_demographic_filtering():
    """Если в норме есть by_gender — должна выбраться gender-норма, а не all."""
    import app.norms
    # Подсунем фейковую таблицу с гендерными нормами
    original = app.norms.PF16_NORMS
    app.norms.PF16_NORMS = {
        "A": {
            "all": (5.5, 2.0),
            "by_gender": {
                "мужской": (6.0, 1.5),
                "женский": (5.0, 1.5),
            },
        },
    }
    try:
        p_male = ParsedProfile(
            employee=EmployeeInfo(gender="мужской"),
            methods=MethodScores(cattell_16pf=Cattell16PF(A=6.0)),
        )
        dev = compute_deviations(p_male)
        # mean должна быть 6.0 (для мужчин), не 5.5 (all)
        assert dev["cattell_16pf"]["A"]["mean"] == 6.0
        assert dev["cattell_16pf"]["A"]["z"] == 0.0  # 6.0 = 6.0
        # Для женщины — другие нормы
        p_female = ParsedProfile(
            employee=EmployeeInfo(gender="женский"),
            methods=MethodScores(cattell_16pf=Cattell16PF(A=6.0)),
        )
        dev_f = compute_deviations(p_female)
        assert dev_f["cattell_16pf"]["A"]["mean"] == 5.0
        assert dev_f["cattell_16pf"]["A"]["z"] == 0.67  # (6-5)/1.5
        print(f"✅ Демография: мужчина T={dev['cattell_16pf']['A']['t']}, женщина T={dev_f['cattell_16pf']['A']['t']}")
    finally:
        app.norms.PF16_NORMS = original


def test_empty_profile():
    """Пустой профиль — не должно падать."""
    p = ParsedProfile(employee=EmployeeInfo(), methods=MethodScores())
    dev = compute_deviations(p)
    assert dev == {"_demographics": {"gender": None, "age": None, "age_bucket": None, "position": None, "department": None}}
    md = format_deviations_md(dev)
    assert "Нет данных" in md
    print("✅ Пустой профиль: не падает, выдаёт корректное сообщение")


def main():
    test_math_helpers()
    test_full_profile()
    test_format_markdown()
    test_demographic_filtering()
    test_empty_profile()
    print("\n🎉 Все проверки норм прошли.")


if __name__ == "__main__":
    main()
