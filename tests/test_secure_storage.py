import sqlite3

from cryptography.fernet import Fernet

from app import storage
from app.models import EmployeeInfo, MethodScores, ParsedProfile, PsychologicalReport


def test_history_is_disabled_by_default(monkeypatch, tmp_path):
    monkeypatch.delenv("STORE_HISTORY", raising=False)
    monkeypatch.setenv("DB_PATH", str(tmp_path / "disabled.db"))
    profile = ParsedProfile(employee=EmployeeInfo(full_name="TEST_SUBJECT_001"), methods=MethodScores())
    assert storage.save_profile(profile, source_filename="test_subject_001.pptx", source_type="pptx", file_bytes=b"x") is None
    assert not (tmp_path / "disabled.db").exists()


def test_encrypted_storage_has_no_plaintext_pii(monkeypatch, tmp_path):
    db = tmp_path / "secure.db"
    monkeypatch.setenv("STORE_HISTORY", "true")
    monkeypatch.setenv("DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("DB_PATH", str(db))
    monkeypatch.setenv("DATA_RETENTION_DAYS", "7")
    storage.init_db()
    profile = ParsedProfile(
        employee=EmployeeInfo(full_name="TEST_SUBJECT_001", extra={"location": "PRIVATE_LOCATION"}),
        methods=MethodScores(), raw_text="секретный исходный текст",
    )
    report = PsychologicalReport(
        emotional_motivation="секретная мотивация", management_style="стиль", communication_style="общение",
        risk_factors="риски", recommendations=[f"совет {n}" for n in range(10)],
    )
    sid = storage.save_profile(
        profile, source_filename="test_subject_001.pptx", source_type="pptx", file_bytes=b"pptx", report=report,
    )
    raw = db.read_bytes()
    assert b"TEST_SUBJECT_001" not in raw
    assert b"PRIVATE_LOCATION" not in raw
    assert "мотивация".encode() not in raw
    restored = storage.get_session(sid)
    assert restored["employee_name"] == "TEST_SUBJECT_001"
    assert restored["profile"]["raw_text"] == ""
    assert restored["report"]["emotional_motivation"] == "секретная мотивация"
    with sqlite3.connect(db) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(secure_sessions)")}
    assert "employee_name" not in columns
