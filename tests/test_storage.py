"""
Тест storage: init, save, list, get, dedup, list_employees.
Использует временный DB_PATH, чтобы не пачкать основную базу.
"""
import os
import sys
import json
import tempfile
from pathlib import Path

# Подменяем DB_PATH до импорта
TMP_DIR = tempfile.mkdtemp(prefix="psycho_test_")
os.environ["DB_PATH"] = str(Path(TMP_DIR) / "test.db")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import storage  # noqa: E402
from app.models import (  # noqa: E402
    ParsedProfile, EmployeeInfo, MethodScores, Cattell16PF, MMPI, BigFive,
)


def make_profile(name: str, age: int = 30) -> ParsedProfile:
    """Собрать минимальный ParsedProfile для теста."""
    return ParsedProfile(
        employee=EmployeeInfo(full_name=name, age=age, position="Engineer", department="R&D"),
        methods=MethodScores(
            cattell_16pf=Cattell16PF(A=5, B=6, C=7),
            mmpi=MMPI(L=51, F=47, K=56, Hs=65, D=72, code="2-4"),
            big_five=BigFive(openness=70, conscientiousness=80),
        ),
        raw_text=f"sample raw text for {name}",
        slides_count=1,
        notes=[],
    )


def main():
    # Чистая база
    storage.init_db()
    assert storage.count_sessions() == 0
    print("✅ init_db, count=0")

    # Сохраняем 3 сессии (2 разных сотрудника + 1 повтор)
    p1 = make_profile("Иванов Иван", 35)
    p2 = make_profile("Петров Пётр", 42)
    p1_again = make_profile("Иванов Иван", 35)  # те же данные

    b1 = b"file content 1"
    b2 = b"file content 2"
    b1_dup = b"file content 1"  # те же байты = тот же хэш

    sid1 = storage.save_profile(p1, source_filename="ivanov.pptx", source_type="pptx", file_bytes=b1)
    sid2 = storage.save_profile(p2, source_filename="petrov.pptx", source_type="pptx", file_bytes=b2)
    sid1_dup = storage.save_profile(
        p1_again, source_filename="ivanov.pptx", source_type="pptx", file_bytes=b1_dup,
    )

    assert sid1 == sid1_dup, f"дедуп не сработал: {sid1} != {sid1_dup}"
    assert sid1 != sid2
    assert storage.count_sessions() == 2, f"после дедупа должно быть 2, есть {storage.count_sessions()}"
    print(f"✅ save_profile x3, дедуп работает (id={sid1} заменил сам себя)")

    # list_sessions
    sessions = storage.list_sessions(limit=10)
    assert len(sessions) == 2
    assert sessions[0]["employee_name"] == "Петров Пётр"  # более новый
    print(f"✅ list_sessions: {[s['employee_name'] for s in sessions]}")

    # get_session
    data = storage.get_session(sid1)
    assert data is not None
    assert data["profile"]["employee"]["full_name"] == "Иванов Иван"
    assert data["profile"]["methods"]["cattell_16pf"]["A"] == 5
    assert data["ocr_used"] is False
    assert isinstance(data["notes"], list)
    print(f"✅ get_session({sid1}): {data['employee_name']}, {data['employee_position']}")

    # list_employees
    emps = storage.list_employees()
    assert len(emps) == 2
    assert {e["employee_name"] for e in emps} == {"Иванов Иван", "Петров Пётр"}
    assert all(e["sessions"] == 1 for e in emps)
    print(f"✅ list_employees: {[e['employee_name'] for e in emps]}")

    # list_employee_sessions
    iv = storage.list_employee_sessions("Иванов Иван")
    assert len(iv) == 1
    assert iv[0]["id"] == sid1
    print(f"✅ list_employee_sessions('Иванов Иван'): {len(iv)} сессия")

    # delete
    assert storage.delete_session(sid2) is True
    assert storage.count_sessions() == 1
    assert storage.delete_session(99999) is False
    print("✅ delete_session работает")

    # Повторный save с OCR
    p1_ocr = make_profile("Сидоров Сидор", 28)
    sid3 = storage.save_profile(
        p1_ocr, source_filename="sidorov.pdf", source_type="pdf", file_bytes=b"pdf bytes",
        ocr_used=True,
    )
    d = storage.get_session(sid3)
    assert d["ocr_used"] is True
    assert d["source_type"] == "pdf"
    print(f"✅ save с ocr_used=True: session #{sid3}")

    # list_sessions с фильтром по source_type
    pdfs = storage.list_sessions(source_type="pdf")
    assert len(pdfs) == 1
    pptxs = storage.list_sessions(source_type="pptx")
    assert len(pptxs) == 1
    print(f"✅ filter source_type: pdf={len(pdfs)}, pptx={len(pptxs)}")

    # Чистим за собой
    import shutil
    shutil.rmtree(TMP_DIR, ignore_errors=True)
    # И основную базу, если случайно создали
    main_db = Path(__file__).parent.parent / "psycho_portrait.db"
    main_db.unlink(missing_ok=True)

    print("\n🎉 Все проверки storage прошли.")


if __name__ == "__main__":
    main()
