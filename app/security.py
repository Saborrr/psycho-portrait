"""Аутентификация, лимиты загрузок и безопасная проверка контейнеров."""
from __future__ import annotations

import hmac
import io
import os
import re
import zipfile
from pathlib import Path

from fastapi import Header, HTTPException, UploadFile, status


def _truthy(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


async def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    expected = os.getenv("APP_API_KEY", "")
    if not expected:
        if _truthy("ALLOW_INSECURE_LOCALHOST"):
            return
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Доступ не настроен: администратор должен задать APP_API_KEY",
        )
    if not x_api_key or not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный или отсутствующий X-API-Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )


def safe_filename(name: str | None) -> str:
    value = Path(name or "upload").name
    return re.sub(r"[^A-Za-zА-Яа-яЁё0-9._ -]+", "_", value)[:180]


async def read_limited_upload(file: UploadFile, allowed: set[str]) -> tuple[bytes, str]:
    filename = safe_filename(file.filename)
    suffix = Path(filename).suffix.lower()
    if suffix not in allowed:
        raise HTTPException(400, f"Допустимые форматы: {', '.join(sorted(allowed))}")
    limit = max(1, int(os.getenv("MAX_UPLOAD_MB", "25"))) * 1024 * 1024
    chunks, size = [], 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        size += len(chunk)
        if size > limit:
            raise HTTPException(413, f"Файл превышает лимит {limit // 1024 // 1024} МБ")
        chunks.append(chunk)
    data = b"".join(chunks)
    if not data:
        raise HTTPException(400, "Файл пуст")
    if suffix == ".pptx":
        validate_pptx(data)
    elif suffix == ".pdf":
        validate_pdf(data)
    return data, filename


def validate_pdf(data: bytes) -> None:
    if not data.startswith(b"%PDF-"):
        raise HTTPException(400, "Файл не является корректным PDF")


def validate_pptx(data: bytes) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            infos = archive.infolist()
            names = {item.filename for item in infos}
            if "[Content_Types].xml" not in names or "ppt/presentation.xml" not in names:
                raise HTTPException(400, "Файл не является корректной презентацией PPTX")
            if len(infos) > 3000:
                raise HTTPException(400, "В PPTX слишком много вложенных объектов")
            total = 0
            for item in infos:
                path = Path(item.filename)
                if path.is_absolute() or ".." in path.parts:
                    raise HTTPException(400, "В PPTX обнаружен небезопасный путь")
                total += item.file_size
                if item.compress_size and item.file_size / item.compress_size > 200:
                    raise HTTPException(400, "PPTX имеет подозрительно высокий коэффициент сжатия")
            max_unpacked = max(100, int(os.getenv("MAX_UNPACKED_MB", "150"))) * 1024 * 1024
            if total > max_unpacked:
                raise HTTPException(400, "Распакованный PPTX превышает допустимый размер")
    except zipfile.BadZipFile as exc:
        raise HTTPException(400, "Поврежденный PPTX-контейнер") from exc
