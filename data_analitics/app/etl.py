"""
etl.py: Модуль оркестрации ETL-процессов.
Управляет выполнением SQL-процедур между слоями:
SOURCE -> STAGING -> ODS -> DDS -> MART
"""

from datetime import date
from pathlib import Path
import psycopg2

try:
    from app.config import PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASSWORD, SQL_DIR
except ImportError:
    from config import PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASSWORD, SQL_DIR


def get_db_connection():
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD
    )


def apply_sql_file(file_name: str):
    """Применяет SQL скрипт к базе данных PostgreSQL."""
    sql_path = SQL_DIR / file_name
    if not sql_path.exists():
        raise FileNotFoundError(f"Файл {sql_path} не найден!")

    print(f"[*] Применение скрипта {file_name}...")
    with open(sql_path, mode='r', encoding='utf-8') as f:
        sql = f.read()

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            conn.commit()
            print(f"[+] Скрипт {file_name} успешно применен.")
    finally:
        conn.close()


def init_database_schemas():
    """Создает схемы, таблицы, функции и витрины."""
    scripts = [
        '01_init_schema.sql',
        '02_dds_schema.sql',
        '03_functions.sql',
        '04_mart.sql'
    ]
    for script in scripts:
        apply_sql_file(script)


def run_source_to_staging() -> int:
    """Вызов PL/pgSQL функции перекладывания SOURCE -> STAGING (as is, без параметров)."""
    print("[*] Выполнение перекладывания данных SOURCE -> STAGING (as is)...")
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT public.load_source_to_staging();")
            rows = cur.fetchone()[0]
            conn.commit()
            print(f"[+] Перенесено в STAGING: {rows} строк.")
            return rows
    finally:
        conn.close()


def run_staging_to_ods(p_sdt: date, p_edt: date) -> int:
    """Вызов PL/pgSQL функции инкрементальной загрузки и очистки STAGING -> ODS."""
    print(f"[*] Выполнение инкрементальной загрузки STAGING -> ODS за период [{p_sdt} - {p_edt}]...")
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT public.load_staging_to_ods(%s, %s);", (p_sdt, p_edt))
            rows = cur.fetchone()[0]
            conn.commit()
            print(f"[+] Загружено и очищено в ODS: {rows} строк.")
            return rows
    finally:
        conn.close()


def run_ods_to_dds(p_sdt: date, p_edt: date) -> int:
    """Вызов PL/pgSQL функции загрузки данных ODS -> DDS («снежинка»)."""
    print(f"[*] Выполнение загрузки ODS -> DDS («снежинка») за период [{p_sdt} - {p_edt}]...")
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT public.load_ods_to_dds(%s, %s);", (p_sdt, p_edt))
            facts = cur.fetchone()[0]
            conn.commit()
            print(f"[+] Загружено фактов в DDS: {facts}.")
            return facts
    finally:
        conn.close()


def run_refresh_mart(p_sdt: date, p_edt: date) -> int:
    """Вызов PL/pgSQL функции пересчета витрины mart.city_genre_popularity."""
    print(f"[*] Обновление аналитической витрины за период [{p_sdt} - {p_edt}]...")
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT public.refresh_mart(%s, %s);", (p_sdt, p_edt))
            rows = cur.fetchone()[0]
            conn.commit()
            print(f"[+] Записей в аналитической витрине: {rows}.")
            return rows
    finally:
        conn.close()


def run_full_pipeline(p_sdt: date = date(2024, 1, 1), p_edt: date = date(2024, 5, 31)):
    """Выполняет полный цикл обработки данных через все слои DWH."""
    print(f"================================================================")
    print(f"[*] Запуск сквозного ETL-пайплайна за период [{p_sdt} - {p_edt}]")
    print(f"================================================================")
    
    stg_rows = run_source_to_staging()
    ods_rows = run_staging_to_ods(p_sdt, p_edt)
    dds_facts = run_ods_to_dds(p_sdt, p_edt)
    mart_rows = run_refresh_mart(p_sdt, p_edt)

    print(f"================================================================")
    print(f"[+] Сквозной пайплайн успешно завершен!")
    print(f"    STAGING: {stg_rows} | ODS: {ods_rows} | DDS: {dds_facts} | MART: {mart_rows}")
    print(f"================================================================")


if __name__ == '__main__':
    run_full_pipeline()
