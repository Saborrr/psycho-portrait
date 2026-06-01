"""
Тест парсера: парсим строку-эмуляцию PPTX и проверяем, что находятся все методики.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Чтобы не зависеть от python-pptx в smoke-тесте, имитируем extract_all_text
import app.parser as parser
from app.models import ParsedProfile


SAMPLE = """
ФИО: Петров Пётр Петрович
Должность: Старший мастер
Подразделение: Цех №5
Возраст: 42
Пол: мужской
Стаж: 12
Образование: высшее техническое

16PF Кеттелла (стэны 1-10):
A: 7
B: 6
C: 5
E: 8
F: 5
G: 9
H: 6
I: 5
L: 4
M: 5
N: 6
O: 3
Q1: 5
Q2: 7
Q3: 7
Q4: 4

Big Five (баллы 0-100):
Открытость: 65
Добросовестность: 78
Экстраверсия: 55
Доброжелательность: 70
Нейротизм: 35

MMPI (T-баллы):
L: 52  F: 48  K: 56
Hs: 55  D: 62  Hy: 50  Pd: 48
Mf: 50  Pa: 55  Pt: 60  Sc: 45
Ma: 50  Si: 55
Код: 2-4-7
Тип профиля: пиковый

DISC:
D: 70  I: 50  S: 60  C: 75

HOLLAND RIASEC:
R: 30  I: 70  A: 45  S: 65  E: 80  C: 50
Код: ESC

MBTI: INTJ

Амтхауэр:
IQ: 115
"""


def test_all_methods():
    profile = ParsedProfile(
        employee=parser.parse_employee_info(SAMPLE),
        methods=parser.MethodScores(),
        raw_text=SAMPLE,
        slides_count=1,
        notes=[],
    )

    # 16PF
    block = parser.detect_method_blocks(SAMPLE)["cattell_16pf"]
    c, _ = parser.parse_cattell(block)
    assert c.A == 7
    assert c.E == 8
    assert c.O == 3
    print(f"✅ 16PF: {sum(1 for f in c.model_fields if getattr(c, f) is not None)}/16 факторов")

    # Big Five
    block = parser.detect_method_blocks(SAMPLE)["big_five"]
    bf, _ = parser.parse_big_five(block)
    assert bf.openness == 65
    assert bf.conscientiousness == 78
    assert bf.neuroticism == 35
    print(f"✅ Big Five: O={bf.openness}, C={bf.conscientiousness}, E={bf.extraversion}, A={bf.agreeableness}, N={bf.neuroticism}")

    # MMPI / СМИЛ — НОВОЕ: валидность, код профиля, тип
    block = parser.detect_method_blocks(SAMPLE)["mmpi"]
    mm, _ = parser.parse_mmpi(block)
    assert mm.L == 52, f"L != 52, got {mm.L}"
    assert mm.F == 48, f"F != 48, got {mm.F}"
    assert mm.K == 56, f"K != 56, got {mm.K}"
    assert mm.D == 62
    assert mm.Pt == 60
    assert mm.code == "2-4-7", f"code != 2-4-7, got {mm.code}"
    assert mm.profile_type == "пиковый"
    assert mm.validity == "valid", f"validity != valid, got {mm.validity}"
    print(f"✅ СМИЛ: L={mm.L}, F={mm.F}, K={mm.K}, D={mm.D}, Pt={mm.Pt}, код={mm.code}, тип={mm.profile_type}, валидность={mm.validity}")

    # MMPI — кейс с сомнительной валидностью
    SUSPICIOUS = """
MMPI:
L: 35  F: 85  K: 38
Hs: 50  D: 55  Hy: 52  Pd: 60
Mf: 50  Pa: 55  Pt: 60  Sc: 45
Ma: 50  Si: 55
"""
    mm2, _ = parser.parse_mmpi(SUSPICIOUS)
    assert mm2.validity == "questionable", f"validity != questionable, got {mm2.validity}"
    print(f"✅ СМИЛ валидность (сомнительный): L={mm2.L}, F={mm2.F}, K={mm2.K} → {mm2.validity}")

    # MMPI — кейс с невалидным
    INVALID = """
MMPI:
L: 50  F: 110  K: 50
Hs: 50  D: 55
"""
    mm3, _ = parser.parse_mmpi(INVALID)
    assert mm3.validity == "invalid", f"validity != invalid, got {mm3.validity}"
    print(f"✅ СМИЛ валидность (невалидный): F={mm3.F} → {mm3.validity}")

    # DISC
    block = parser.detect_method_blocks(SAMPLE)["disc"]
    d, _ = parser.parse_disc(block)
    assert d.D == 70
    assert d.C == 75
    print(f"✅ DISC: D={d.D}, I={d.I}, S={d.S}, C={d.C}")

    # HOLLAND
    block = parser.detect_method_blocks(SAMPLE)["holland"]
    h, _ = parser.parse_holland(block)
    assert h.E == 80
    assert h.code == "ESC"
    print(f"✅ HOLLAND: E={h.E}, S={h.S}, C={h.C}, code={h.code}")

    # MBTI
    block = parser.detect_method_blocks(SAMPLE)["mbti"]
    m, _ = parser.parse_mbti(block)
    assert m.type == "INTJ"
    print(f"✅ MBTI: {m.type}")

    # Amthauer
    block = parser.detect_method_blocks(SAMPLE)["amthauer"]
    a, _ = parser.parse_amthauer(block)
    assert a.iq == 115
    print(f"✅ Амтхауэр: IQ={a.iq}")

    # Employee
    e = parser.parse_employee_info(SAMPLE)
    assert e.full_name == "Петров Пётр Петрович"
    assert e.position == "Старший мастер"
    assert e.age == 42
    assert e.gender == "мужской"
    assert e.tenure_years == 12.0
    print(f"✅ Шапка: {e.full_name}, {e.position}, {e.age} лет, стаж {e.tenure_years}")

    print("\n🎉 Все тесты пройдены!")


if __name__ == "__main__":
    test_all_methods()
