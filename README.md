# 🧠 Psycho Portrait

**Загрузи PPTX с результатами психологических тестов → получи развёрнутую психологическую характеристику сотрудника.**

## Что делает

1. Ты загружаешь PowerPoint-презентацию с профилем сотрудника (ФИО, должность, баллы по методикам)
2. Парсер извлекает данные: ФИО, должность, возраст, баллы по тестам
3. Подключённая LLM (GLM 5.1, DeepSeek, Gemini, OpenAI — что настроишь) пишет связную психологическую характеристику в стиле "профиль сотрудника" — с интерпретацией каждого фактора, сильных сторон, зон развития, рекомендаций для руководителя
4. Результат можно скачать в Markdown / PDF / скопировать в Word

## Поддерживаемые методики (v0.1)

| Методика | Что считывается |
|----------|-----------------|
| **16PF Кеттелла** | 16 первичных факторов (стэны 1-10) |
| **Big Five (BFI / NEO-PI-R)** | O, C, E, A, N (баллы 0-100 или T-баллы) |
| **MMPI / СМИЛ** | 3 валид. + 10 клинич. шкал (T-баллы) |
| **DISC** | D, I, S, C (баллы по 4 осям) |
| **HOLLAND** | RIASEC (3 ведущих типа) |
| **MBTI** | 4 дихотомии → 16 типов |
| **Тест Амтхауэра** | IQ и субтесты |

Шаблон презентации — в `samples/template.pptx` (TODO) или в `docs/presentation_template.md`.

## Стек

- **Backend:** FastAPI (Python 3.11+)
- **Парсер:** python-pptx
- **LLM:** OpenAI-compatible API (z.ai, DeepSeek, OpenAI, Gemini)
- **Frontend:** HTML + vanilla JS (без сборки)
- **Деплой:** Docker / Vercel / любой VPS

## Запуск

```bash
# 1. Клонируй
git clone https://github.com/Saborrr/psycho-portrait.git
cd psycho-portrait

# 2. Виртуальное окружение
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Переменные окружения
cp .env.example .env
# Укажи LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

# 4. Старт
uvicorn app.main:app --reload --port 8000
```

Открой http://localhost:8000 → drag&drop PPTX → на выходе характеристика.

## Переменные окружения

```env
# LLM провайдер (любой OpenAI-compat)
LLM_BASE_URL=https://api.z.ai/api/coding/paas/v4
LLM_API_KEY=...
LLM_MODEL=glm-5.1
LLM_TEMPERATURE=0.4

# Сервер
HOST=0.0.0.0
PORT=8000
```

## Структура

```
psycho-portrait/
├── app/
│   ├── main.py             # FastAPI endpoints
│   ├── parser.py           # Извлечение данных из PPTX
│   ├── methods/            # Схемы методик
│   │   ├── cattell_16pf.py
│   │   ├── big_five.py
│   │   ├── mmpi.py
│   │   ├── disc.py
│   │   ├── holland.py
│   │   ├── mbti.py
│   │   └── amthauer.py
│   ├── llm.py              # Клиент LLM
│   ├── prompts.py          # Промпты для генерации
│   └── models.py           # Pydantic модели
├── static/
│   ├── index.html          # UI
│   ├── style.css
│   └── app.js
├── samples/                # Примеры презентаций
├── docs/                   # Шаблон структуры PPTX
├── tests/
├── requirements.txt
├── .env.example
├── Dockerfile
└── README.md
```

## Дальше (roadmap)

- [ ] Поддержка PDF-отчётов (PDF → текст → парсинг)
- [ ] Сохранение истории загрузок (SQLite)
- [ ] Генератор презентации-шаблона (чтобы не делать вручную)
- [ ] Telegram-бот (@my_amster_bot → загрузил файл → получил характеристику)
- [ ] Расширенные методики: КОТ, тест Роршаха, ТАТ, Люшер
- [ ] Сравнение с нормой (проф. группа, возраст, пол)
- [ ] Авторский стиль: настройка тона, длины, разделов

## ⚠️ Disclaimer

Это **инструмент-ассистент**, а не замена психологу. Финальное заключение, корректировка и подпись — за специалистом с профильным образованием. Автор не несёт ответственности за решения, принятые на основе сгенерированных текстов.

## Лицензия

MIT
