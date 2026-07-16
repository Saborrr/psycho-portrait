"""Опциональное зашифрованное хранилище результатов.

По умолчанию история выключена. При STORE_HISTORY=true все персональные данные
хранятся одним Fernet-зашифрованным блоком; в открытом виде остаются только
технические даты, тип источника и HMAC-отпечаток для дедупликации.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator, Optional

from cryptography.fernet import Fernet, InvalidToken

from .models import ParsedProfile, PsychologicalReport

log = logging.getLogger("psycho-portrait.storage")
DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "psycho_portrait.db"


def _truthy(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def history_enabled() -> bool:
    return _truthy("STORE_HISTORY")


def get_db_path() -> Path:
    return Path(os.getenv("DB_PATH", str(DEFAULT_DB)))


def _fernet() -> Fernet:
    value = os.getenv("DATA_ENCRYPTION_KEY", "").strip().encode()
    if not value:
        raise RuntimeError(
            "При STORE_HISTORY=true обязателен DATA_ENCRYPTION_KEY. "
            "Сгенерируйте его командой: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    try:
        return Fernet(value)
    except (ValueError, TypeError) as exc:
        raise RuntimeError("DATA_ENCRYPTION_KEY имеет неверный Fernet-формат") from exc


def _fingerprint(file_bytes: bytes) -> str:
    secret = os.getenv("FILE_HMAC_KEY") or os.getenv("DATA_ENCRYPTION_KEY")
    if not secret:
        raise RuntimeError("Для защищенного отпечатка не задан ключ")
    return hmac.new(secret.encode(), file_bytes, hashlib.sha256).hexdigest()


@contextmanager
def _conn() -> Iterator[sqlite3.Connection]:
    path = get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        yield connection
        connection.commit()
    finally:
        connection.close()
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def init_db() -> None:
    if not history_enabled():
        return
    _fernet()  # fail closed before creating a database
    with _conn() as connection:
        legacy = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='uploads'"
        ).fetchone()
        if legacy and connection.execute("SELECT COUNT(*) FROM uploads").fetchone()[0]:
            raise RuntimeError(
                "Обнаружена старая таблица uploads с незашифрованными персональными данными. "
                "Экспортируйте и безопасно удалите ее перед включением истории."
            )
        connection.execute("""
            CREATE TABLE IF NOT EXISTS secure_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                source_type TEXT NOT NULL CHECK(source_type IN ('pptx', 'pdf')),
                file_fingerprint TEXT NOT NULL,
                encrypted_payload BLOB NOT NULL,
                UNIQUE(source_type, file_fingerprint)
            )
        """)
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_secure_created ON secure_sessions(created_at DESC)"
        )
    purge_expired()


def _encrypt_payload(payload: dict) -> bytes:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return _fernet().encrypt(raw)


def _decrypt_payload(token: bytes) -> dict:
    try:
        return json.loads(_fernet().decrypt(token).decode("utf-8"))
    except (InvalidToken, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Не удалось расшифровать сохраненную запись") from exc


def save_profile(
    profile: ParsedProfile,
    *,
    source_filename: str,
    source_type: str,
    file_bytes: bytes,
    ocr_used: bool = False,
    report: PsychologicalReport | None = None,
) -> Optional[int]:
    if not history_enabled():
        return None
    if source_type not in {"pptx", "pdf"}:
        raise ValueError("source_type должен быть pptx или pdf")
    data = profile.model_dump(mode="json")
    if not _truthy("STORE_RAW_TEXT"):
        data["raw_text"] = ""
    now = datetime.now(timezone.utc)
    retention_days = max(1, int(os.getenv("DATA_RETENTION_DAYS", "30")))
    payload = {
        "source_filename": Path(source_filename).name,
        "ocr_used": bool(ocr_used),
        "profile": data,
        "report": report.model_dump(mode="json") if report else None,
    }
    fingerprint = _fingerprint(file_bytes)
    encrypted = _encrypt_payload(payload)
    with _conn() as connection:
        row = connection.execute("""
            INSERT INTO secure_sessions (
                created_at, expires_at, source_type, file_fingerprint, encrypted_payload
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(source_type, file_fingerprint) DO UPDATE SET
                created_at=excluded.created_at,
                expires_at=excluded.expires_at,
                encrypted_payload=excluded.encrypted_payload
            RETURNING id
        """, (
            now.isoformat(),
            (now + timedelta(days=retention_days)).isoformat(),
            source_type,
            fingerprint,
            encrypted,
        )).fetchone()
    log.info("saved encrypted session id=%s type=%s", row[0], source_type)
    return int(row[0])


def _public_row(row: sqlite3.Row, *, include_profile: bool = False) -> dict:
    payload = _decrypt_payload(row["encrypted_payload"])
    profile = payload["profile"]
    employee = profile.get("employee", {})
    result = {
        "id": row["id"],
        "created_at": row["created_at"],
        "expires_at": row["expires_at"],
        "source_type": row["source_type"],
        "source_filename": payload.get("source_filename"),
        "ocr_used": payload.get("ocr_used", False),
        "employee_name": employee.get("full_name"),
        "employee_age": employee.get("age"),
        "employee_gender": employee.get("gender"),
        "employee_position": employee.get("position"),
        "employee_department": employee.get("department"),
    }
    if include_profile:
        result["profile"] = profile
        result["report"] = payload.get("report")
        result["notes"] = profile.get("notes", [])
    return result


def purge_expired() -> int:
    if not history_enabled() or not get_db_path().exists():
        return 0
    with _conn() as connection:
        cursor = connection.execute(
            "DELETE FROM secure_sessions WHERE datetime(expires_at) <= datetime('now')"
        )
        return cursor.rowcount


def list_sessions(*, limit: int = 50, offset: int = 0, source_type: Optional[str] = None) -> list[dict]:
    if not history_enabled():
        return []
    purge_expired()
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)
    where, params = "", []
    if source_type in {"pptx", "pdf"}:
        where, params = "WHERE source_type=?", [source_type]
    with _conn() as connection:
        rows = connection.execute(
            f"SELECT * FROM secure_sessions {where} ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
            (*params, limit, offset),
        ).fetchall()
    return [_public_row(row) for row in rows]


def get_session(session_id: int) -> Optional[dict]:
    if not history_enabled():
        return None
    purge_expired()
    with _conn() as connection:
        row = connection.execute("SELECT * FROM secure_sessions WHERE id=?", (session_id,)).fetchone()
    return _public_row(row, include_profile=True) if row else None


def delete_session(session_id: int) -> bool:
    if not history_enabled():
        return False
    with _conn() as connection:
        cursor = connection.execute("DELETE FROM secure_sessions WHERE id=?", (session_id,))
        return cursor.rowcount > 0


def list_employees() -> list[dict]:
    grouped: dict[str, dict] = {}
    for session in list_sessions(limit=100):
        name = session.get("employee_name")
        if not name:
            continue
        item = grouped.setdefault(name, {
            "employee_name": name, "sessions": 0, "last_upload": session["created_at"],
            "last_age": session.get("employee_age"), "last_position": session.get("employee_position"),
            "last_department": session.get("employee_department"),
        })
        item["sessions"] += 1
    return list(grouped.values())


def list_employee_sessions(name: str) -> list[dict]:
    return [item for item in list_sessions(limit=100) if item.get("employee_name") == name]


def count_sessions() -> int:
    if not history_enabled() or not get_db_path().exists():
        return 0
    purge_expired()
    with _conn() as connection:
        return int(connection.execute("SELECT COUNT(*) FROM secure_sessions").fetchone()[0])
