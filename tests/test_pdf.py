"""
Smoke-тест PDF-парсера: генерирует простой PDF с известным текстом
и проверяет, что parse_pdf корректно его разбирает.
"""
import os
import sys
import tempfile
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# 1) Сгенерируем простой PDF
import reportlab.pdfgen.canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Попробуем найти шрифт с поддержкой кириллицы (для теста)
font_path = None
for cand in ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
             "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]:
    if os.path.exists(cand):
        font_path = cand
        break
if font_path:
    pdfmetrics.registerFont(TTFont("CustomFont", font_path))


SAMPLE_TEXT = [
    "Отчёт психологического обследования",
    "ФИО: Иванов Иван Иванович",
    "Должность: Начальник цеха",
    "Подразделение: Цех №5",
    "Возраст: 42",
    "Пол: мужской",
    "",
    "Методика: 16PF Кеттелла",
    "A: 7   B: 6   C: 5   E: 8   F: 4   G: 7   H: 6   I: 5",
    "L: 4   M: 5   N: 6   O: 4   Q1: 7   Q2: 6   Q3: 8   Q4: 5",
    "",
    "Методика: MMPI (СМИЛ)",
    "L: 51  F: 47  K: 56",
    "Hs: 65  D: 72  Hy: 58  Pd: 75  Mf: 50",
    "Pa: 80  Pt: 68  Sc: 55  Ma: 60  Si: 45",
    "Код: 4-6-7",
    "Тип профиля: пиковый",
    "",
    "Методика: Big Five",
    "Openness: 62   Conscientiousness: 75   Extraversion: 58   Agreeableness: 70   Neuroticism: 45",
    "",
    "Методика: DISC",
    "D: 70  I: 50  S: 40  C: 75",
    "",
    "Методика: HOLLAND (RIASEC)",
    "R: 40  I: 70  A: 55  S: 60  E: 75  C: 50",
    "Код: IES",
    "",
    "Методика: MBTI",
    "INTJ",
    "",
    "Методика: Амтхауэр",
    "IQ: 128",
]


def make_test_pdf(path: str) -> None:
    c = reportlab.pdfgen.canvas.Canvas(path, pagesize=A4)
    w, h = A4
    y = h - 50
    if font_path:
        c.setFont("CustomFont", 11)
    for line in SAMPLE_TEXT:
        if y < 50:
            c.showPage()
            y = h - 50
            if font_path:
                c.setFont("CustomFont", 11)
        c.drawString(50, y, line)
        y -= 16
    c.save()


def main():
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.close()
    pdf_path = tmp.name
    print(f"PDF: {pdf_path}")
    make_test_pdf(pdf_path)

    # 2) Прогоним через parse_pdf
    from app.parser_pdf import parse_pdf
    profile = parse_pdf(pdf_path)
    print("=== Notes ===")
    for n in profile.notes:
        print(f"  - {n}")
    print("=== Employee ===")
    print(json.dumps(profile.employee.model_dump(), indent=2, ensure_ascii=False))
    print("=== Methods ===")
    print(json.dumps(profile.methods.model_dump(), indent=2, ensure_ascii=False))

    # 3) Проверим, что ключевые поля распознаны
    m = profile.methods
    assert m.cattell_16pf, "16PF не распознан"
    assert m.mmpi and m.mmpi.code, "MMPI код не распознан"
    assert m.big_five, "Big Five не распознан"
    assert m.disc, "DISC не распознан"
    assert m.holland and m.holland.code == "IES", f"HOLLAND код: {m.holland.code!r}"
    assert m.mbti and m.mbti.type == "INTJ", f"MBTI type: {m.mbti.type!r}"
    assert m.amthauer and m.amthauer.iq == 128, f"Amthauer IQ: {m.amthauer.iq!r}"
    assert profile.employee.full_name and "Иванов" in profile.employee.full_name
    print("\n✅ Все проверки прошли.")

    os.unlink(pdf_path)


if __name__ == "__main__":
    main()
