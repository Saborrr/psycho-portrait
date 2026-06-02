"""
FastAPI-приложение Psycho Portrait.
"""
from __future__ import annotations
import os
import json
import tempfile
import logging
from pathlib import Path
from dotenv import load_dotenv

# Загружаем .env из корня проекта
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from .parser import parse_pptx
from .models import ParsedProfile
from .llm import chat
from .prompts import SYSTEM_PROMPT, build_user_prompt
from .parser_pdf import parse_pdf
from . import storage


logging.basicConfig(level=logging.INFO)
log = logging.getLogger("psycho-portrait")

# === Init storage на старте ===
storage.init_db()

app = FastAPI(
    title="Psycho Portrait",
    description="Загрузи PPTX с результатами психологических тестов → получи психологическую характеристику сотрудника.",
    version="0.1.0",
)

# CORS — для разработки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "psycho-portrait", "version": app.version}


@app.post("/api/parse")
async def api_parse(file: UploadFile = File(...)) -> dict:
    """
    Только парсинг PPTX → JSON с извлечёнными данными.
    Полезно для отладки шаблона.
    """
    if not file.filename or not file.filename.lower().endswith(".pptx"):
        raise HTTPException(400, "Загрузи .pptx файл")
    max_mb = int(os.getenv("MAX_UPLOAD_MB", "25"))
    contents = await file.read()
    if len(contents) > max_mb * 1024 * 1024:
        raise HTTPException(413, f"Файл больше {max_mb} МБ")
    with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name
    try:
        profile = parse_pptx(tmp_path)
    except Exception as e:
        log.exception("parse failed")
        raise HTTPException(500, f"Ошибка парсинга: {e}")
    finally:
        try: os.unlink(tmp_path)
        except OSError: pass
    # Сохраняем в историю (дедуп по (filename, sha256))
    sid = storage.save_profile(
        profile, source_filename=file.filename, source_type="pptx",
        file_bytes=contents, ocr_used=False,
    )
    payload = json.loads(profile.model_dump_json(indent=2))
    payload["_session_id"] = sid
    return payload


@app.post("/api/generate")
async def api_generate(
    file: UploadFile = File(...),
    style: str = Form("default"),
) -> dict:
    """
    Полный цикл: PPTX → парсинг → LLM → психологическая характеристика.
    """
    if not file.filename or not file.filename.lower().endswith(".pptx"):
        raise HTTPException(400, "Загрузи .pptx файл")
    max_mb = int(os.getenv("MAX_UPLOAD_MB", "25"))
    contents = await file.read()
    if len(contents) > max_mb * 1024 * 1024:
        raise HTTPException(413, f"Файл больше {max_mb} МБ")

    with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name
    try:
        profile = parse_pptx(tmp_path)
    except Exception as e:
        log.exception("parse failed")
        raise HTTPException(500, f"Ошибка парсинга: {e}")
    finally:
        try: os.unlink(tmp_path)
        except OSError: pass

    # Проверим, что хоть что-то распознано
    has_data = any([
        profile.methods.cattell_16pf and any(getattr(profile.methods.cattell_16pf, f) is not None for f in profile.methods.cattell_16pf.model_fields),
        profile.methods.big_five and any(getattr(profile.methods.big_five, f) is not None for f in ["openness","conscientiousness","extraversion","agreeableness","neuroticism"]),
        profile.methods.mmpi and any(getattr(profile.methods.mmpi, f) is not None for f in profile.methods.mmpi.model_fields),
        profile.methods.disc and any(getattr(profile.methods.disc, f) is not None for f in ["D","I","S","C"]),
        profile.methods.holland and (any(getattr(profile.methods.holland, f) is not None for f in ["R","I","A","S","E","C"]) or profile.methods.holland.code),
        profile.methods.mbti and profile.methods.mbti.type,
        profile.methods.amthauer and (profile.methods.amthauer.iq or profile.methods.amthauer.subscales),
    ])

    if not has_data:
        return JSONResponse(
            status_code=422,
            content={
                "error": "Не удалось распознать ни одной методики.",
                "details": profile.notes,
                "raw_text_preview": profile.raw_text[:2000],
            },
        )

    # Генерация
    user_prompt = build_user_prompt(profile)
    system = SYSTEM_PROMPT
    if style == "brief":
        system += "\n\nДополнительное требование: максимально кратко — не более 800 слов."

    try:
        text = await chat([
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ], max_tokens=3000)
    except Exception as e:
        log.exception("llm failed")
        raise HTTPException(502, f"Ошибка LLM: {e}")

    # Сохраняем в историю
    sid = storage.save_profile(
        profile, source_filename=file.filename, source_type="pptx",
        file_bytes=contents, ocr_used=False,
    )
    return {
        "session_id": sid,
        "profile": json.loads(profile.model_dump_json()),
        "characteristics_markdown": text,
        "model": os.getenv("LLM_MODEL", "glm-5.1"),
    }


@app.post("/api/raw-text")
async def api_raw_text(file: UploadFile = File(...)) -> PlainTextResponse:
    """Только текст из PPTX — для отладки."""
    contents = await file.read()
    with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name
    try:
        from .parser import extract_all_text
        full, _, n = extract_all_text(tmp_path)
        return PlainTextResponse(f"# {n} слайдов\n\n{full}")
    finally:
        try: os.unlink(tmp_path)
        except OSError: pass


# === PDF-эндпоинты (text-layer + OCR fallback) ===

@app.post("/api/parse-pdf")
async def api_parse_pdf(file: UploadFile = File(...)) -> dict:
    """Только парсинг PDF → JSON с извлечёнными данными.
    Использует pdfplumber для текстового слоя; если его нет (скан) — OCR tesseract.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Загрузи .pdf файл")
    max_mb = int(os.getenv("MAX_UPLOAD_MB", "25"))
    contents = await file.read()
    if len(contents) > max_mb * 1024 * 1024:
        raise HTTPException(413, f"Файл больше {max_mb} МБ")
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name
    try:
        profile = parse_pdf(tmp_path)
    except FileNotFoundError:
        raise HTTPException(400, "PDF не найден")
    except Exception as e:
        log.exception("pdf parse failed")
        raise HTTPException(500, f"Ошибка парсинга PDF: {e}")
    finally:
        try: os.unlink(tmp_path)
        except OSError: pass
    # Сохраняем в историю
    sid = storage.save_profile(
        profile, source_filename=file.filename, source_type="pdf",
        file_bytes=contents, ocr_used=bool(profile.notes and any("OCR" in n for n in profile.notes)),
    )
    payload = json.loads(profile.model_dump_json(indent=2))
    payload["_session_id"] = sid
    return payload


@app.post("/api/generate-pdf")
async def api_generate_pdf(
    file: UploadFile = File(...),
    style: str = Form("default"),
) -> dict:
    """Полный цикл: PDF (text-layer или скан) → парсинг → LLM → характеристика."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Загрузи .pdf файл")
    max_mb = int(os.getenv("MAX_UPLOAD_MB", "25"))
    contents = await file.read()
    if len(contents) > max_mb * 1024 * 1024:
        raise HTTPException(413, f"Файл больше {max_mb} МБ")
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name
    try:
        profile = parse_pdf(tmp_path)
    except Exception as e:
        log.exception("pdf parse failed")
        raise HTTPException(500, f"Ошибка парсинга PDF: {e}")
    finally:
        try: os.unlink(tmp_path)
        except OSError: pass

    has_data = any([
        profile.methods.cattell_16pf and any(getattr(profile.methods.cattell_16pf, f) is not None for f in profile.methods.cattell_16pf.model_fields),
        profile.methods.big_five and any(getattr(profile.methods.big_five, f) is not None for f in ["openness","conscientiousness","extraversion","agreeableness","neuroticism"]),
        profile.methods.mmpi and any(getattr(profile.methods.mmpi, f) is not None for f in profile.methods.mmpi.model_fields),
        profile.methods.disc and any(getattr(profile.methods.disc, f) is not None for f in ["D","I","S","C"]),
        profile.methods.holland and (any(getattr(profile.methods.holland, f) is not None for f in ["R","I","A","S","E","C"]) or profile.methods.holland.code),
        profile.methods.mbti and profile.methods.mbti.type,
        profile.methods.amthauer and (profile.methods.amthauer.iq or profile.methods.amthauer.subscales),
    ])

    if not has_data:
        return JSONResponse(
            status_code=422,
            content={
                "error": "Не удалось распознать ни одной методики.",
                "details": profile.notes,
                "raw_text_preview": profile.raw_text[:2000],
            },
        )

    user_prompt = build_user_prompt(profile)
    system = SYSTEM_PROMPT
    if style == "brief":
        system += "\n\nДополнительное требование: максимально кратко — не более 800 слов."

    try:
        text = await chat([
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ], max_tokens=3000)
    except Exception as e:
        log.exception("llm failed")
        raise HTTPException(502, f"Ошибка LLM: {e}")

    # Сохраняем в историю
    sid = storage.save_profile(
        profile, source_filename=file.filename, source_type="pdf",
        file_bytes=contents, ocr_used=bool(profile.notes and any("OCR" in n for n in profile.notes)),
    )
    return {
        "session_id": sid,
        "profile": json.loads(profile.model_dump_json()),
        "characteristics_markdown": text,
        "model": os.getenv("LLM_MODEL", "glm-5.1"),
    }


@app.post("/api/raw-text-pdf")
async def api_raw_text_pdf(file: UploadFile = File(...)) -> PlainTextResponse:
    """Только текст из PDF (text-layer или OCR) — для отладки."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Загрузи .pdf файл")
    contents = await file.read()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name
    try:
        from .parser_pdf import _extract_text_layer, _ocr_pdf, MIN_CHARS_PER_PAGE
        full, n = _extract_text_layer(tmp_path)
        avg = len(full) / max(n, 1)
        used_ocr = False
        if avg < MIN_CHARS_PER_PAGE:
            full, _ = _ocr_pdf(tmp_path)
            used_ocr = True
        src = "OCR" if used_ocr else "text-layer"
        return PlainTextResponse(f"# {n} страниц ({src})\n\n{full}")
    finally:
        try: os.unlink(tmp_path)
        except OSError: pass


# === История загрузок (SQLite) ===

@app.get("/api/sessions")
async def api_sessions(limit: int = 50, offset: int = 0, source_type: str | None = None) -> dict:
    """Список всех сохранённых загрузок (без profile_json).
    Query: ?limit=&offset=&source_type=pptx|pdf
    """
    st = source_type if source_type in ("pptx", "pdf") else None
    return {
        "total": storage.count_sessions(),
        "limit": limit,
        "offset": offset,
        "sessions": storage.list_sessions(limit=limit, offset=offset, source_type=st),
    }


@app.get("/api/sessions/{session_id}")
async def api_session_detail(session_id: int) -> dict:
    """Полный профиль одной загрузки (с ParsedProfile)."""
    data = storage.get_session(session_id)
    if not data:
        raise HTTPException(404, f"Сессия #{session_id} не найдена")
    return data


@app.delete("/api/sessions/{session_id}")
async def api_session_delete(session_id: int) -> dict:
    """Удалить загрузку из истории."""
    ok = storage.delete_session(session_id)
    if not ok:
        raise HTTPException(404, f"Сессия #{session_id} не найдена")
    return {"deleted": session_id}


@app.get("/api/employees")
async def api_employees() -> dict:
    """Список уникальных сотрудников с количеством загрузок."""
    return {"employees": storage.list_employees()}


@app.get("/api/employees/{name:path}/sessions")
async def api_employee_sessions(name: str) -> dict:
    """Все загрузки конкретного сотрудника (по полному имени).
    Поддерживает кириллицу и пробелы в имени (FastAPI path-параметр).
    """
    sessions = storage.list_employee_sessions(name)
    if not sessions:
        raise HTTPException(404, f"Сотрудник {name!r} не найден в истории")
    return {"employee": name, "sessions": sessions}


@app.get("/api/db/stats")
async def api_db_stats() -> dict:
    """Статистика по базе (для отладки)."""
    return {
        "total_uploads": storage.count_sessions(),
        "db_path": str(storage.get_db_path()),
    }


