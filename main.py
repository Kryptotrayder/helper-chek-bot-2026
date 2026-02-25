# main.py

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import logging

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Проверка счётчиков — Telegram Mini App backend")

# Пути
BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "checks.json"
STATIC_DIR = BASE_DIR / "static"

# Создаём папку static, если её нет
STATIC_DIR.mkdir(exist_ok=True)

# Подключаем статические файлы (index.html должен лежать в static/)
app.mount("/static", StaticFiles(directory=STATIC_DIR, html=True), name="static")

# Модель данных
class CheckData(BaseModel):
    numberChecked: str
    numberChecker: str
    fio: str
    wishCount: str
    shortNumber: str = ""
    user: dict | None = None
    timestamp: str | None = None

# ────────────────────────────────────────────────
# Вспомогательные функции для работы с файлом
# ────────────────────────────────────────────────

def load_checks() -> list[dict]:
    if not DATA_FILE.exists():
        logger.info(f"Файл {DATA_FILE} не найден → создаём пустой список")
        return []
    
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return []
            data = json.loads(content)
            if not isinstance(data, list):
                logger.warning("Данные в файле не являются списком → возвращаем пустой список")
                return []
            return data
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка чтения JSON: {e}")
        return []
    except Exception as e:
        logger.error(f"Не удалось прочитать файл: {e}")
        return []

def save_check(new_check: dict):
    checks = load_checks()
    checks.append(new_check)
    
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(checks, f, ensure_ascii=False, indent=2)
        logger.info(f"Сохранена новая проверка. Всего записей: {len(checks)}")
    except Exception as e:
        logger.error(f"Ошибка записи в файл: {e}")
        raise

# ────────────────────────────────────────────────
# Маршруты
# ────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return index_path.read_text(encoding="utf-8")
    return """
    <h1 style="text-align:center; margin-top:100px; color:#e74c3c;">
        Файл static/index.html не найден
    </h1>
    <p style="text-align:center;">Положите ваш index.html в папку static/</p>
    """

@app.get("/checks", response_class=HTMLResponse)
async def show_checks():
    checks = load_checks()
    
    rows_html = ""
    for entry in checks:
        ts_raw = entry.get("timestamp")
        if ts_raw:
            try:
                dt = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                ts_display = dt.astimezone().strftime("%d.%m.%Y %H:%M")
            except:
                ts_display = ts_raw
        else:
            ts_display = "—"

        user_id = entry.get("user", {}).get("id", "—") if entry.get("user") else "—"

        rows_html += f"""
        <tr>
            <td>{ts_display}</td>
            <td>{user_id}</td>
            <td>{entry.get("numberChecked", "—")}</td>
            <td>{entry.get("numberChecker", "—")}</td>
            <td>{entry.get("fio", "—")}</td>
            <td>{entry.get("wishCount", "—")}</td>
            <td>{entry.get("shortNumber") or "—"}</td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Анкеты проверок</title>
    <style>
        body {{
            font-family: system-ui, -apple-system, sans-serif;
            background: #f5f7fa;
            color: #2c3e50;
            margin: 0;
            padding: 20px;
            line-height: 1.5;
        }}
        .container {{
            max-width: 1100px;
            margin: 0 auto;
        }}
        h1 {{
            text-align: center;
            margin-bottom: 24px;
            color: #34495e;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }}
        th, td {{
            padding: 14px 12px;
            text-align: left;
            border-bottom: 1px solid #ebedf0;
        }}
        th {{
            background: #ecf0f1;
            color: #34495e;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.85rem;
        }}
        tr:last-child td {{
            border-bottom: none;
        }}
        tr:nth-child(even) {{
            background: #f9fbfc;
        }}
        .count {{
            text-align: center;
            font-size: 1.1rem;
            margin: 16px 0;
            color: #7f8c8d;
        }}
        @media (max-width: 768px) {{
            table, thead, tbody, th, td, tr {{
                display: block;
            }}
            thead tr {{
                display: none;
            }}
            tr {{
                margin-bottom: 16px;
                border: 1px solid #ddd;
                border-radius: 8px;
            }}
            td {{
                border: none;
                border-bottom: 1px solid #eee;
                position: relative;
                padding-left: 50%;
            }}
            td:before {{
                position: absolute;
                top: 14px;
                left: 12px;
                width: 45%;
                padding-right: 10px;
                white-space: nowrap;
                font-weight: bold;
                content: attr(data-label);
                color: #34495e;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Собранные анкеты</h1>
        <div class="count">Всего записей: {len(checks)}</div>

        <table>
            <thead>
                <tr>
                    <th>Время</th>
                    <th>TG ID</th>
                    <th>№ проверяемого</th>
                    <th>№ проверяющего</th>
                    <th>ФИО владельца</th>
                    <th>Пожелания</th>
                    <th>Короткий №</th>
                </tr>
            </thead>
            <tbody>
                {rows_html or '<tr><td colspan="7" style="text-align:center; padding:40px; color:#95a5a6;">Пока нет записей</td></tr>'}
            </tbody>
        </table>
    </div>
</body>
</html>"""

    return html

@app.post("/api/save")
async def save_data(check: CheckData):
    try:
        data_dict = check.model_dump(exclude_none=True)
        
        # Добавляем время, если не пришло
        if "timestamp" not in data_dict or not data_dict["timestamp"]:
            data_dict["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        save_check(data_dict)
        logger.info(f"Успешно сохранено: {data_dict.get('numberChecked')} — {data_dict.get('fio')[:30]}...")
        
        return {"ok": True, "saved": True}
    except Exception as e:
        logger.exception("Ошибка при сохранении данных")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,                # авто-перезапуск при изменении кода
        log_level="info"
    )