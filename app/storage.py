"""
SQLite-хранилище для загруженных профилей.

Одна таблица `uploads` (для простоты). Внутри:
  - метаданные (имя файла, тип, ocr_used, время, file_hash для дедупа)
  - денормализованные поля сотрудника (имя, возраст, должность, отдел) — для быстрого поиска
  - весь ParsedProfile как JSON в `profile_json`

DB-файл: по умолчанию `psycho_portrait.db` в корне проекта.
Путь переопределяется через env `DB_PATH`.
"""
from __future__ import annotations
import hashlib
import json
import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from .models import ParsedProfile

log = logging.getLogger("psycho-portrait.storage")

DEFAULT_DB = Path(__file__).resolve().parent.parent / "psycho_portrait.db"


def get_db_path() -> Path:
    import os
    p = os.getenv("DB_PATH")
    return Path(p) if p else DEFAULT_DB


@contextmanager
def _conn() -> Iterator[sqlite3.Connection]:
    """Контекстный менеджер для соединения с row_factory=Row."""
    p = get_db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(p)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init_db() -> None:
    """Создать таблицы, если их ещё нет. Идемпотентно."""
    with _conn() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS uploads (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            source_filename TEXT    NOT NULL,
            source_type     TEXT    NOT NULL,        -- 'pptx' | 'pdf'
            file_hash       TEXT    NOT NULL,        -- sha256 контента (для дедупа)
            ocr_used        INTEGER NOT NULL DEFAULT 0,
            notes           TEXT    NOT NULL DEFAULT '[]',  -- JSON list

            employee_name   TEXT,
            employee_age    INTEGER,
            employee_gender TEXT,
            employee_position   TEXT,
            employee_department  TEXT,

            profile_json    TEXT    NOT NULL,        -- полный ParsedProfile.json()
            raw_text_preview TEXT                    -- первые 500 символов (для превью)
        );
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_uploads_created ON uploads(created_at DESC);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_uploads_emp ON uploads(employee_name, created_at DESC);")
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS uniq_uploads_file ON uploads(source_filename, source_type, file_hash);")


def _hash_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _preview(text: str, n: int = 500) -> str:
    return (text or "")[:n]


def save_profile(
    profile: ParsedProfile,
    *,
    source_filename: str,
    source_type: str,             # "pptx" | "pdf"
    file_bytes: bytes,
    ocr_used: bool = False,
) -> int:
    """Сохранить (или перезаписать при дубле) ParsedProfile. Возвращает id.

    Дедупликация: уникальный ключ (source_filename, source_type, file_hash).
    Если уже есть запись с таким ключом — обновляем её (replace), а не плодим дубли.
    """
    file_hash = _hash_bytes(file_bytes)
    emp = profile.employee
    profile_json = profile.model_dump_json()

    with _conn() as c:
        cur = c.execute("""
        INSERT INTO uploads (
            source_filename, source_type, file_hash, ocr_used, notes,
            employee_name, employee_age, employee_gender,
            employee_position, employee_department,
            profile_json, raw_text_preview
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(source_filename, source_type, file_hash) DO UPDATE SET
            created_at = datetime('now'),
            ocr_used = excluded.ocr_used,
            notes = excluded.notes,
            employee_name = excluded.employee_name,
            employee_age = excluded.employee_age,
            employee_gender = excluded.employee_gender,
            employee_position = excluded.employee_position,
            employee_department = excluded.employee_department,
            profile_json = excluded.profile_json,
            raw_text_preview = excluded.raw_text_preview
        RETURNING id
        """, (
            source_filename,
            source_type,
            file_hash,
            1 if ocr_used else 0,
            json.dumps(profile.notes, ensure_ascii=False),
            emp.full_name,
            emp.age,
            emp.gender,
            emp.position,
            emp.department,
            profile_json,
            _preview(profile.raw_text),
        ))
        new_id = cur.fetchone()[0]
        log.info("saved upload id=%s type=%s emp=%r", new_id, source_type, emp.full_name)
        return new_id


def list_sessions(*, limit: int = 50, offset: int = 0, source_type: Optional[str] = None) -> list[dict]:
    """Список загрузок (без profile_json — он тяжёлый)."""
    where = ""
    params: tuple = (limit, offset)
    if source_type:
        where = "WHERE source_type = ?"
        params = (source_type, limit, offset)
    with _conn() as c:
        rows = c.execute(f"""
        SELECT id, created_at, source_filename, source_type, ocr_used,
               employee_name, employee_age, employee_gender,
               employee_position, employee_department,
               substr(raw_text_preview, 1, 200) AS preview
        FROM uploads
        {where}
        ORDER BY created_at DESC, id DESC
        LIMIT ? OFFSET ?
        """, params).fetchall()
        return [dict(r) for r in rows]


def get_session(session_id: int) -> Optional[dict]:
    """Получить одну загрузку с полным профилем."""
    with _conn() as c:
        row = c.execute("SELECT * FROM uploads WHERE id = ?", (session_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["profile"] = json.loads(d.pop("profile_json"))
        d["notes"] = json.loads(d.pop("notes"))
        d["ocr_used"] = bool(d["ocr_used"])
        return d


def delete_session(session_id: int) -> bool:
    with _conn() as c:
        cur = c.execute("DELETE FROM uploads WHERE id = ?", (session_id,))
        return cur.rowcount > 0


def list_employees() -> list[dict]:
    """Список уникальных сотрудников с количеством загрузок и датами."""
    with _conn() as c:
        rows = c.execute("""
        SELECT employee_name, COUNT(*) AS sessions,
               MAX(created_at) AS last_upload,
               MAX(employee_age) AS last_age,
               MAX(employee_position) AS last_position,
               MAX(employee_department) AS last_department
        FROM uploads
        WHERE employee_name IS NOT NULL AND employee_name != ''
        GROUP BY employee_name
        ORDER BY last_upload DESC
        """).fetchall()
        return [dict(r) for r in rows]


def list_employee_sessions(name: str) -> list[dict]:
    """Все загрузки по сотруднику (без profile_json)."""
    with _conn() as c:
        rows = c.execute("""
        SELECT id, created_at, source_filename, source_type, ocr_used,
               employee_age, employee_position, employee_department,
               substr(raw_text_preview, 1, 200) AS preview
        FROM uploads
        WHERE employee_name = ?
        ORDER BY created_at DESC, id DESC
        """, (name,)).fetchall()
        return [dict(r) for r in rows]


def count_sessions() -> int:
    with _conn() as c:
        return c.execute("SELECT COUNT(*) FROM uploads").fetchone()[0]
