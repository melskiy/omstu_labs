"""
Аналитическое приложение: Голосовой бот аварийно-диспетчерской службы
Студент: Малицкий Александр Сергеевич, ФИТм-251
СУБД: PostgreSQL | Фреймворк: FastAPI
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import psycopg2
import psycopg2.extras
import json
from datetime import datetime

# ─── Настройки подключения к PostgreSQL ───────────────────────────────────────
DB_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "database": "voicebot_ads",
    "user":     "postgres",
    "password": "password"   # замените на свой пароль
}

app = FastAPI(
    title="Голосовой бот АДС — Аналитическое приложение",
    description="Аналитика обращений граждан в аварийно-диспетчерскую службу",
    version="1.0.0"
)

# ─── Вспомогательная функция подключения ──────────────────────────────────────
def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def query_to_list(sql: str, params=None) -> list[dict]:
    """Выполняет SQL-запрос и возвращает список словарей."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]


# ─── Маршрут: главная страница (дашборд) ──────────────────────────────────────
@app.get("/", response_class=HTMLResponse, tags=["UI"])
def index():
    with open("templates/index.html", encoding="utf-8") as f:
        return f.read()


# ─── API: дашборд (общая статистика) ──────────────────────────────────────────
@app.get("/api/dashboard", tags=["Аналитика"])
def api_dashboard():
    """Общая статистика: звонки, инциденты, доля бота."""
    rows = query_to_list("SELECT * FROM v_dashboard")
    return rows[0] if rows else {}


# ─── API: статистика по типам инцидентов ──────────────────────────────────────
@app.get("/api/calls-by-type", tags=["Аналитика"])
def api_calls_by_type():
    """Количество звонков и среднее время по каждому типу инцидента."""
    return query_to_list("SELECT * FROM v_calls_by_type")


# ─── API: среднее время обработки ─────────────────────────────────────────────
@app.get("/api/avg-handling", tags=["Аналитика"])
def api_avg_handling():
    """Среднее время звонка: бот vs оператор."""
    return query_to_list("SELECT * FROM v_avg_bot_handling")


# ─── API: список инцидентов с фильтром по статусу ─────────────────────────────
@app.get("/api/incidents", tags=["Инциденты"])
def api_incidents(
    status: str = Query(None, description="Фильтр по статусу: 'Принят', 'В работе', 'Выполнен', …")
):
    """Список инцидентов. Опционально фильтр по статусу."""
    if status:
        sql = """
            SELECT * FROM v_incidents_with_status
            WHERE "Статус" = %s
        """
        return query_to_list(sql, (status,))
    return query_to_list("SELECT * FROM v_incidents_with_status")


# ─── API: список всех звонков ─────────────────────────────────────────────────
@app.get("/api/calls", tags=["Звонки"])
def api_calls():
    """Список всех звонков с привязкой к инцидентам."""
    sql = """
        SELECT
            c.call_id                        AS "ID",
            c.caller_phone                   AS "Телефон",
            c.received_at                    AS "Время звонка",
            c.duration_sec                   AS "Длительность (сек)",
            CASE WHEN c.bot_handled THEN 'Бот' ELSE 'Оператор' END AS "Обработчик",
            s.status_name                    AS "Статус",
            i.address                        AS "Адрес инцидента",
            it.type_name                     AS "Тип инцидента"
        FROM Calls c
        JOIN Statuses s          ON c.status_id = s.status_id
        LEFT JOIN Incidents i    ON c.incident_id = i.incident_id
        LEFT JOIN IncidentTypes it ON i.type_id = it.type_id
        ORDER BY c.received_at DESC
    """
    return query_to_list(sql)


# ─── API: лог диалога бота по звонку ─────────────────────────────────────────
@app.get("/api/calls/{call_id}/log", tags=["Звонки"])
def api_call_log(call_id: int):
    """История диалога бота для конкретного звонка."""
    sql = """
        SELECT
            log_id      AS "ID лога",
            log_time    AS "Время",
            step_name   AS "Шаг бота",
            bot_phrase  AS "Фраза бота",
            user_input  AS "Ответ пользователя"
        FROM CallLogs
        WHERE call_id = %s
        ORDER BY log_time
    """
    rows = query_to_list(sql, (call_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Звонок не найден или лог пуст")
    return rows


# ─── API: список операторов ───────────────────────────────────────────────────
@app.get("/api/operators", tags=["Операторы"])
def api_operators():
    """Список всех диспетчеров/операторов."""
    sql = """
        SELECT
            operator_id AS "ID",
            full_name   AS "ФИО",
            phone       AS "Телефон",
            shift       AS "Смена",
            is_active   AS "Активен"
        FROM Operators
        ORDER BY operator_id
    """
    return query_to_list(sql)


# ─── API: статистика по операторам ───────────────────────────────────────────
@app.get("/api/operators/stats", tags=["Операторы"])
def api_operators_stats():
    """Количество инцидентов на каждого оператора."""
    sql = """
        SELECT
            o.full_name                     AS "Оператор",
            o.shift                         AS "Смена",
            COUNT(i.incident_id)            AS "Инцидентов принято",
            SUM(CASE WHEN s.status_name = 'Выполнен' THEN 1 ELSE 0 END) AS "Закрыто",
            ROUND(AVG(
                CASE WHEN i.closed_at IS NOT NULL
                     THEN EXTRACT(EPOCH FROM (i.closed_at - i.created_at))/3600
                     ELSE NULL
                END
            ), 2)                           AS "Среднее время закрытия (ч)"
        FROM Operators o
        LEFT JOIN Incidents i ON i.operator_id = o.operator_id
        LEFT JOIN Statuses s  ON i.status_id = s.status_id
        GROUP BY o.operator_id, o.full_name, o.shift
        ORDER BY COUNT(i.incident_id) DESC
    """
    return query_to_list(sql)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
