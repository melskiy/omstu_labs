"""
clickhouse_transfer.py: Перенос аналитической витрины из PostgreSQL в ClickHouse
и контроль согласованности данных между двумя СУБД (АБД Лаб. 2).
"""

from datetime import date
from typing import Dict, Any, Tuple
import psycopg2
import clickhouse_connect

try:
    from app.config import (
        PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASSWORD,
        CH_HOST, CH_PORT, CH_DB, CH_USER, CH_PASSWORD
    )
except ImportError:
    from config import (
        PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASSWORD,
        CH_HOST, CH_PORT, CH_DB, CH_USER, CH_PASSWORD
    )


def get_pg_connection():
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD
    )


def get_ch_client():
    return clickhouse_connect.get_client(
        host=CH_HOST,
        port=CH_PORT,
        username=CH_USER,
        password=CH_PASSWORD,
        database=CH_DB
    )


def init_clickhouse_schema():
    """Создает базу данных и целевую аналитическую витрину в ClickHouse."""
    client = clickhouse_connect.get_client(
        host=CH_HOST,
        port=CH_PORT,
        username=CH_USER,
        password=CH_PASSWORD
    )
    
    print(f"[*] Инициализация схемы ClickHouse в базе '{CH_DB}'...")
    client.command(f"CREATE DATABASE IF NOT EXISTS {CH_DB}")

    # Создание таблицы с движком ReplacingMergeTree для обеспечения идемпотентности
    create_table_query = f"""
    CREATE TABLE IF NOT EXISTS {CH_DB}.city_genre_popularity (
        dt Date,
        year UInt16,
        month UInt8,
        day_of_week LowCardinality(String),
        city_name LowCardinality(String),
        genre_name LowCardinality(String),
        top_artist String,
        listens_count UInt64,
        unique_users_count UInt64,
        morning_listens UInt64,
        day_listens UInt64,
        evening_listens UInt64,
        night_listens UInt64,
        updated_at DateTime
    ) ENGINE = ReplacingMergeTree(updated_at)
    PARTITION BY toYYYYMM(dt)
    PRIMARY KEY (dt, city_name, genre_name)
    ORDER BY (dt, city_name, genre_name);
    """
    client.command(create_table_query)
    print(f"[+] Таблица {CH_DB}.city_genre_popularity в ClickHouse готова.")


def transfer_mart_to_clickhouse(p_sdt: date = None, p_edt: date = None) -> int:
    """
    Выгружает данные витрины из PostgreSQL и вставляет в ClickHouse.
    При повторном вызове ReplacingMergeTree заменяет строки новыми по updated_at.
    """
    init_clickhouse_schema()
    
    print("[*] Выгрузка данных витрины из PostgreSQL...")
    pg_conn = get_pg_connection()
    try:
        with pg_conn.cursor() as cur:
            if p_sdt and p_edt:
                query = """
                    SELECT
                        dt, year, month, day_of_week, city_name, genre_name,
                        top_artist, listens_count, unique_users_count,
                        morning_listens, day_listens, evening_listens, night_listens,
                        updated_at
                    FROM mart.city_genre_popularity
                    WHERE dt BETWEEN %s AND %s;
                """
                cur.execute(query, (p_sdt, p_edt))
            else:
                query = """
                    SELECT
                        dt, year, month, day_of_week, city_name, genre_name,
                        top_artist, listens_count, unique_users_count,
                        morning_listens, day_listens, evening_listens, night_listens,
                        updated_at
                    FROM mart.city_genre_popularity;
                """
                cur.execute(query)

            rows = cur.fetchall()
    finally:
        pg_conn.close()

    if not rows:
        print("[!] В исходной витрине PostgreSQL нет записей для переноса.")
        return 0

    print(f"[*] Получено {len(rows)} строк из PostgreSQL. Вставка в ClickHouse...")
    
    column_names = [
        'dt', 'year', 'month', 'day_of_week', 'city_name', 'genre_name',
        'top_artist', 'listens_count', 'unique_users_count',
        'morning_listens', 'day_listens', 'evening_listens', 'night_listens',
        'updated_at'
    ]

    ch_client = get_ch_client()
    
    # Очистка целевой таблицы перед вставкой для исключения расхождений со старыми данными
    if not p_sdt and not p_edt:
        ch_client.command(f"TRUNCATE TABLE {CH_DB}.city_genre_popularity")
    else:
        ch_client.command(f"ALTER TABLE {CH_DB}.city_genre_popularity DELETE WHERE dt BETWEEN '{p_sdt}' AND '{p_edt}'")

    # Вставка данных пакетом
    ch_client.insert(
        table='city_genre_popularity',
        data=rows,
        column_names=column_names
    )
    
    # Принудительная оптимизация для слияния дубликатов ReplacingMergeTree
    ch_client.command(f"OPTIMIZE TABLE {CH_DB}.city_genre_popularity FINAL")

    print(f"[+] Перенос успешно завершен. В ClickHouse загружено {len(rows)} строк.")
    return len(rows)


def verify_consistency() -> Dict[str, Any]:
    """
    Проверяет согласованность аналитических витрин между PostgreSQL и ClickHouse.
    Возвращает словарь с показателями и флагами совпадения.
    """
    # 1. Метрики из PostgreSQL
    pg_conn = get_pg_connection()
    try:
        with pg_conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COUNT(*) AS total_rows,
                    COALESCE(SUM(listens_count), 0) AS total_listens,
                    COUNT(DISTINCT city_name) AS unique_cities,
                    COUNT(DISTINCT genre_name) AS unique_genres,
                    COALESCE(SUM(morning_listens), 0) AS total_morning,
                    COALESCE(SUM(day_listens), 0) AS total_day,
                    COALESCE(SUM(evening_listens), 0) AS total_evening,
                    COALESCE(SUM(night_listens), 0) AS total_night
                FROM mart.city_genre_popularity;
            """)
            pg_res = cur.fetchone()
    finally:
        pg_conn.close()

    # 2. Метрики из ClickHouse
    try:
        ch_client = get_ch_client()
        ch_res = ch_client.query("""
            SELECT
                count() AS total_rows,
                sum(listens_count) AS total_listens,
                uniqExact(city_name) AS unique_cities,
                uniqExact(genre_name) AS unique_genres,
                sum(morning_listens) AS total_morning,
                sum(day_listens) AS total_day,
                sum(evening_listens) AS total_evening,
                sum(night_listens) AS total_night
            FROM city_genre_popularity FINAL
        """).result_rows[0]
    except Exception as e:
        print(f"[!] Ошибка подключения к ClickHouse: {e}")
        ch_res = (0, 0, 0, 0, 0, 0, 0, 0)

    metrics = [
        "Количество записей в витрине",
        "Общее число прослушиваний (SUM)",
        "Количество уникальных городов",
        "Количество уникальных жанров",
        "Утренние прослушивания (06:00-12:00)",
        "Дневные прослушивания (12:00-18:00)",
        "Вечерние прослушивания (18:00-24:00)",
        "Ночные прослушивания (00:00-06:00)"
    ]

    report = []
    all_matched = True
    for name, pg_val, ch_val in zip(metrics, pg_res, ch_res):
        pg_v = int(pg_val)
        ch_v = int(ch_val)
        diff = abs(pg_v - ch_v)
        is_matched = (diff == 0)
        if not is_matched:
            all_matched = False
        report.append({
            "Показатель": name,
            "PostgreSQL": pg_v,
            "ClickHouse": ch_v,
            "Расхождение": diff,
            "Результат проверки": "✅ Совпадает" if is_matched else "❌ Не совпадает"
        })

    return {
        "report": report,
        "all_matched": all_matched
    }


if __name__ == '__main__':
    transfer_mart_to_clickhouse()
    res = verify_consistency()
    print("\nРезультаты проверки согласованности:")
    for r in res['report']:
        print(f" - {r['Показатель']}: PG={r['PostgreSQL']}, CH={r['ClickHouse']} | {r['Результат проверки']}")
