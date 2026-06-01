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


logging.basicConfig(level=logging.INFO)
log = logging.getLogger("psycho-portrait")

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
    return json.loads(profile.model_dump_json(indent=2))


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

    return {
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
