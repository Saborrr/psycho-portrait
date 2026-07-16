"""FastAPI-приложение для локальной обработки результатов тестирования."""
from __future__ import annotations

import logging
import os
import tempfile
import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from fastapi import APIRouter, Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from . import storage
from .excel_export import ExportRecord, build_excel
from .llm import get_active_provider, get_model, list_providers
from .models import ParsedProfile
from .parser import parse_pptx
from .parser_pdf import parse_pdf
from .pptx_structured import extract_employee_photo
from .reporting import ReportValidationError, generate_report, report_to_markdown
from .security import read_limited_upload, require_api_key


logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
log = logging.getLogger("psycho-portrait")

storage.init_db()

docs_enabled = os.getenv("ENABLE_API_DOCS", "false").lower() == "true"
app = FastAPI(
    title="Psycho Portrait",
    description="Защищенная подготовка черновиков психологических характеристик.",
    version="1.0.0",
    contact={"name": "Saborrr", "url": "https://github.com/Saborrr"},
    license_info={"name": "MIT", "url": "https://github.com/Saborrr/psycho-portrait/blob/main/LICENSE"},
    docs_url="/docs" if docs_enabled else None,
    redoc_url=None,
    openapi_url="/openapi.json" if docs_enabled else None,
)

origins = [
    item.strip() for item in os.getenv(
        "CORS_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000"
    ).split(",") if item.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-API-Key"],
)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; style-src 'self'; script-src 'self'; "
        "img-src 'self' data: blob:; connect-src 'self'; frame-ancestors 'none'"
    )
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
    return response


STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
api = APIRouter(prefix="/api", dependencies=[Depends(require_api_key)])


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "psycho-portrait", "version": app.version}


@app.get("/sw.js", include_in_schema=False)
async def service_worker() -> FileResponse:
    return FileResponse(
        STATIC_DIR / "sw.js",
        media_type="application/javascript",
        headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"},
    )


def _has_data(profile: ParsedProfile) -> bool:
    return bool(profile.methods.model_dump(exclude_none=True, exclude={"extra"}))


def _client_profile(profile: ParsedProfile) -> dict:
    result = profile.model_dump(mode="json", exclude={"raw_text"})
    # Биография и место проживания нужны парсеру, но не отображаются без необходимости.
    result["employee"]["extra"] = {}
    return result


def _parse_bytes(data: bytes, filename: str) -> tuple[ParsedProfile, tuple[bytes, str] | None, bool]:
    suffix = Path(filename).suffix.lower()
    path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
            handle.write(data)
            path = handle.name
        if suffix == ".pptx":
            profile = parse_pptx(path, source_filename=filename)
            photo = extract_employee_photo(path)
            ocr_used = False
        else:
            profile = parse_pdf(path)
            profile.source_filename = filename
            photo = None
            ocr_used = any("OCR" in note for note in profile.notes)
        max_pages = max(1, int(os.getenv("MAX_SLIDES", "50")))
        if profile.slides_count > max_pages:
            raise HTTPException(400, f"Документ содержит больше {max_pages} страниц или слайдов")
        return profile, photo, ocr_used
    finally:
        if path:
            Path(path).unlink(missing_ok=True)


async def _read_and_parse(file: UploadFile) -> tuple[bytes, str, ParsedProfile, tuple[bytes, str] | None, bool]:
    data, filename = await read_limited_upload(file, {".pptx", ".pdf"})
    try:
        profile, photo, ocr_used = _parse_bytes(data, filename)
    except HTTPException:
        raise
    except Exception:
        request_id = uuid.uuid4().hex[:10]
        log.exception("parse failed request_id=%s", request_id)
        raise HTTPException(422, f"Не удалось разобрать файл. Код ошибки: {request_id}")
    if not _has_data(profile):
        raise HTTPException(422, detail={
            "message": "Не удалось распознать результаты методик",
            "notes": profile.notes,
        })
    return data, filename, profile, photo, ocr_used


@api.get("/settings")
async def api_settings() -> dict:
    return {
        "history_enabled": storage.history_enabled(),
        "raw_text_storage": os.getenv("STORE_RAW_TEXT", "false").lower() == "true",
        "retention_days": int(os.getenv("DATA_RETENTION_DAYS", "30")),
    }


@api.get("/llm/providers")
async def api_llm_providers() -> dict:
    return {
        "active": {"provider": get_active_provider(), "model": get_model()},
        "providers": list_providers(),
    }


@api.post("/parse")
async def api_parse(file: UploadFile = File(...)) -> dict:
    data, filename, profile, _photo, ocr_used = await _read_and_parse(file)
    sid = storage.save_profile(
        profile, source_filename=filename, source_type=Path(filename).suffix[1:],
        file_bytes=data, ocr_used=ocr_used,
    )
    return {"session_id": sid, "profile": _client_profile(profile)}


@api.post("/generate")
async def api_generate(file: UploadFile = File(...)) -> dict:
    data, filename, profile, _photo, ocr_used = await _read_and_parse(file)
    try:
        report = await generate_report(profile)
    except ReportValidationError:
        request_id = uuid.uuid4().hex[:10]
        log.exception("report quality failed request_id=%s", request_id)
        raise HTTPException(502, f"Модель не сформировала корректный отчет. Код ошибки: {request_id}")
    except Exception:
        request_id = uuid.uuid4().hex[:10]
        log.exception("llm failed request_id=%s", request_id)
        raise HTTPException(502, f"Сервис генерации временно недоступен. Код ошибки: {request_id}")
    sid = storage.save_profile(
        profile, source_filename=filename, source_type=Path(filename).suffix[1:],
        file_bytes=data, ocr_used=ocr_used, report=report,
    )
    return {
        "session_id": sid,
        "profile": _client_profile(profile),
        "report": report.model_dump(mode="json"),
        "characteristics_markdown": report_to_markdown(report),
        "model": get_model(),
    }


@api.post("/batch/generate-xlsx")
async def api_batch_generate_xlsx(files: list[UploadFile] = File(...)) -> Response:
    max_files = max(1, int(os.getenv("MAX_BATCH_FILES", "25")))
    if not files or len(files) > max_files:
        raise HTTPException(400, f"За один раз можно обработать от 1 до {max_files} файлов")
    records: list[ExportRecord] = []
    for file in files:
        _data, _filename, profile, photo, _ocr_used = await _read_and_parse(file)
        try:
            report = await generate_report(profile)
        except Exception:
            request_id = uuid.uuid4().hex[:10]
            log.exception("batch generation failed request_id=%s", request_id)
            raise HTTPException(
                502,
                f"Не удалось сформировать один из отчетов. Ничего не сохранено. Код ошибки: {request_id}",
            )
        records.append(ExportRecord(profile=profile, report=report, photo=photo))
    content = build_excel(records)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="psychological_characteristics.xlsx"'},
    )


@api.get("/sessions")
async def api_sessions(limit: int = 50, offset: int = 0, source_type: str | None = None) -> dict:
    return {
        "enabled": storage.history_enabled(),
        "total": storage.count_sessions(),
        "sessions": storage.list_sessions(limit=limit, offset=offset, source_type=source_type),
    }


@api.get("/sessions/{session_id}")
async def api_session_detail(session_id: int) -> dict:
    data = storage.get_session(session_id)
    if not data:
        raise HTTPException(404, "Запись не найдена или срок хранения истек")
    return data


@api.delete("/sessions/{session_id}")
async def api_session_delete(session_id: int) -> dict:
    if not storage.delete_session(session_id):
        raise HTTPException(404, "Запись не найдена")
    return {"deleted": session_id}


@api.get("/employees")
async def api_employees() -> dict:
    return {"employees": storage.list_employees()}


app.include_router(api)
