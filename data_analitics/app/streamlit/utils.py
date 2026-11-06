"""
utils.py: Вспомогательные функции для подключения к БД и загрузки данных в Streamlit.
"""

import sys
from pathlib import Path

# Гарантированное добавление корня проекта (/app) и директории app/ в sys.path
STREAMLIT_DIR = Path(__file__).resolve().parent
APP_DIR = STREAMLIT_DIR.parent
PROJECT_ROOT = APP_DIR.parent

for p in (str(PROJECT_ROOT), str(APP_DIR), str(STREAMLIT_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import pandas as pd
import psycopg2
import clickhouse_connect
import streamlit as st

try:
    from app.config import (
        PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASSWORD,
        CH_HOST, CH_PORT, CH_DB, CH_USER, CH_PASSWORD, CSV_PATH
    )
except ImportError:
    from config import (
        PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASSWORD,
        CH_HOST, CH_PORT, CH_DB, CH_USER, CH_PASSWORD, CSV_PATH
    )


def get_pg_conn():
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


@st.cache_data(ttl=600)
def load_raw_csv_data() -> pd.DataFrame:
    """Загружает исходный датасет music_project.csv."""
    df = pd.read_csv(CSV_PATH)
    # Очищаем заголовки от пробелов
    df.columns = [col.strip() for col in df.columns]
    # Переименовываем первую колонку если она пустая
    if df.columns[0] == '' or 'Unnamed' in df.columns[0]:
        df.rename(columns={df.columns[0]: 'index_id'}, inplace=True)
    return df


@st.cache_data(ttl=60)
def query_postgres(query: str, params: tuple = None) -> pd.DataFrame:
    """Выполняет SQL-запрос к PostgreSQL и возвращает DataFrame."""
    conn = get_pg_conn()
    try:
        df = pd.read_sql_query(query, conn, params=params)
        return df
    finally:
        conn.close()


@st.cache_data(ttl=60)
def query_clickhouse(query: str) -> pd.DataFrame:
    """Выполняет запрос к ClickHouse и возвращает DataFrame."""
    client = get_ch_client()
    res = client.query_df(query)
    return res


def check_db_health() -> dict:
    """Проверяет доступность PostgreSQL и ClickHouse."""
    status = {"pg": False, "ch": False, "pg_err": None, "ch_err": None}
    try:
        conn = get_pg_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
        conn.close()
        status["pg"] = True
    except Exception as e:
        status["pg_err"] = str(e)

    try:
        client = get_ch_client()
        client.command("SELECT 1")
        status["ch"] = True
    except Exception as e:
        status["ch_err"] = str(e)

    return status
