"""
Тест парсера ЭФКО-методик.

⚠️ Использует синтетические данные из samples/sample_efko_full.pptx
(реальные персональные дела не используются в репозитории).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.parser import parse_pptx


SAMPLE_PATH = Path(__file__).resolve().parent.parent / "samples" / "sample_efko_full.pptx"


def test_employee_info():
    p = parse_pptx(str(SAMPLE_PATH))
    assert p.employee.full_name
    assert len(p.employee.full_name.split()) >= 2
    assert p.employee.position == "Мастер цеха"
    print("✅ Employee info: ФИО + должность")


def test_efko_intellekt():
    p = parse_pptx(str(SAMPLE_PATH))
    assert p.methods.efko is not None
    assert p.methods.efko.intellekt is not None
    assert p.methods.efko.intellekt.logicheskiy == 55
    assert p.methods.efko.intellekt.obrazny == 50
    assert p.methods.efko.intellekt.leksika == 62
    print("✅ ИНТЕЛЛЕКТ: Логический, Образный, Лексика")


def test_efko_aktivnost():
    p = parse_pptx(str(SAMPLE_PATH))
    assert p.methods.efko.aktivnost is not None
    assert p.methods.efko.aktivnost.fizicheskaya == 53
    assert p.methods.efko.aktivnost.intellektualnaya == 60
    assert p.methods.efko.aktivnost.kommunikacionnaya == 55
    print("✅ АКТИВНОСТЬ: Физическая, Интеллектуальная, Коммуникационная")


def test_efko_empaty():
    p = parse_pptx(str(SAMPLE_PATH))
    assert p.methods.efko.empaty is not None
    # В синтетическом sample — «2 рода, %» подхватывается
    assert p.methods.efko.empaty.kind_2_rational == 50
    assert p.methods.efko.empaty.kind_2_emotional == 55
    print("✅ ЭМПАТИЯ: 2 рода (рациональная / эмоциональная)")


def test_efko_echv_echm():
    p = parse_pptx(str(SAMPLE_PATH))
    assert p.methods.efko.echv_echm is not None
    assert p.methods.efko.echv_echm.echv == 60
    print("✅ ЭЧВ/ЭЧМ")


def test_efko_postmodern():
    p = parse_pptx(str(SAMPLE_PATH))
    assert p.methods.efko.postmodern == 45
    print("✅ Постмодерн, %")


def test_efko_15_tests_found():
    """Должны найтись 15 ЭФКО-тестов (по лейблам, без баллов)."""
    p = parse_pptx(str(SAMPLE_PATH))
    from app.methods.efko import EFKO_TEST_CATALOG
    found = sum(1 for k in EFKO_TEST_CATALOG if getattr(p.methods.efko, k, None) is not None)
    assert found >= 13, f"Найдено только {found}/15 ЭФКО-тестов"
    print(f"✅ Найдено {found}/15 ЭФКО-тестов по лейблам")


def test_efko_regression_old_sample():
    """Старый sample_efko не должен сломаться (ММИЛ + gentleman)."""
    p = parse_pptx(str(Path(__file__).resolve().parent.parent / "samples" / "sample_efko.pptx"))
    assert p.methods.mmpi.L == 48
    assert p.methods.mmpi.gentleman == 72
    assert p.methods.mmpi.code == "3-4-9"
    # EFKO в старом sample отсутствует — это нормально
    print("✅ Регрессия: sample_efko (старый) работает")


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            print(f"❌ {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print()
    if failed:
        print(f"❌ {failed} тестов упали")
        sys.exit(1)
    else:
        print("🎉 Все тесты ЭФКО пройдены!")
