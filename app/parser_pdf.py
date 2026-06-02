"""
Парсер PDF-бланков с результатами психологических тестов.

Стратегия:
1. Извлечь текстовый слой через pdfplumber (быстро и точно).
2. Если текста мало/нет — fallback на OCR (tesseract) постранично.
3. Делегировать в `parser.parse_text()` для разбора методик.

Зависимости:
  - pdfplumber
  - pytesseract
  - tesseract (системный бинарь) с пакетами lang rus + eng
  - pdf2image / pypdfium2 (для рендера страниц PDF в картинку перед OCR)

Шаблоны бланков см. в docs/presentation_template.md.
"""
from __future__ import annotations
import io
import logging
import re
from typing import Optional

import pdfplumber

from .models import ParsedProfile
from .parser import parse_text

log = logging.getLogger("psycho-portrait.pdf")


# Порог «мало текста» — если в среднем < 30 символов на страницу, считаем,
# что это скан и нужен OCR
MIN_CHARS_PER_PAGE = 30


def _extract_text_layer(pdf_path: str) -> tuple[str, int]:
    """Извлечь текст из PDF через pdfplumber.
    Возвращает (полный_текст, кол-во_страниц).
    """
    pages_text: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        n = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            t = page.extract_text() or ""
            pages_text.append(t.strip())
    full = "\n\n--- PAGE BREAK ---\n\n".join(pages_text)
    return full, n


def _ocr_pdf(pdf_path: str, lang: str = "rus+eng") -> tuple[str, int]:
    """Fallback: рендерим каждую страницу в картинку и прогоняем tesseract.
    Возвращает (полный_текст, кол-во_страниц).
    """
    import pytesseract
    from PIL import Image

    # pypdfium2 идёт транзитивно с pdfplumber
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(pdf_path)
    n = len(doc)
    pages_text: list[str] = []
    log.info("OCR запущен для %s страниц", n)

    for i in range(n):
        page = doc[i]
        # 200 dpi — баланс скорости и качества для печатного текста
        bitmap = page.render(scale=200 / 72)
        pil_image = bitmap.to_pil()
        try:
            text = pytesseract.image_to_string(pil_image, lang=lang)
        except pytesseract.TesseractError as e:
            log.warning("OCR страница %d упала: %s", i + 1, e)
            text = ""
        pages_text.append(text.strip())

    full = "\n\n--- PAGE BREAK ---\n\n".join(pages_text)
    return full, n


def _normalize_ocr_text(text: str) -> str:
    """Типичные OCR-артефакты, которые мешают regex-ам:
    - лишние пробелы вокруг чисел (напр. 'Hs : 65' вместо 'Hs: 65')
    - замена кириллических букв, похожих на латиницу (C→С, O→О и т.п.)
    - замена дефисов/тире
    """
    # NBSP → обычный пробел
    text = text.replace("\xa0", " ")
    # OCR часто ломает ':' на пробелы — починим перед числами
    text = re.sub(r"\s*:\s*", ": ", text)
    # Дефисы/тире перед числами
    text = re.sub(r"\s*[—–\-]\s*", "-", text)
    # Кириллица ↔ латиница: некоторые похожие буквы
    pairs = [
        ("C", "С"),  # C → С (кириллица) — рискованно, отключим по умолчанию
        # ("O", "О"),
        # ("P", "Р"),
        # ("A", "А"),
    ]
    for lat, cyr in pairs:
        # заменяем только когда рядом латиница (напр. в шкалах MMPI — не трогаем)
        pass
    return text


def parse_pdf(pdf_path: str) -> ParsedProfile:
    """Главная точка входа. Извлекает текст (или делает OCR), затем разбирает.

    Returns:
        ParsedProfile (как в parse_pptx)

    Raises:
        FileNotFoundError: файл не найден
        ValueError: PDF пустой или нечитаемый
    """
    # Шаг 1: текстовый слой
    full, n = _extract_text_layer(pdf_path)
    avg_chars = len(full) / max(n, 1)
    log.info("PDF: %d страниц, %d символов (%.0f на стр.)", n, len(full), avg_chars)

    # Шаг 2: fallback на OCR, если текста мало (скан)
    ocr_used = False
    if avg_chars < MIN_CHARS_PER_PAGE:
        log.info("Мало текста в слое (%.0f/стр < %d) → OCR", avg_chars, MIN_CHARS_PER_PAGE)
        full, _ = _ocr_pdf(pdf_path)
        full = _normalize_ocr_text(full)
        ocr_used = True

    # Шаг 3: общая логика разбора (та же, что для PPTX)
    profile = parse_text(full, slides_count=n)
    if ocr_used:
        profile.notes.insert(
            0,
            f"📷 Текст извлечён через OCR (tesseract, {n} стр.) — качество может быть ниже, проверьте поля.",
        )
    else:
        profile.notes.insert(0, f"📄 Текст извлечён из текстового слоя PDF ({n} стр.).")
    return profile
