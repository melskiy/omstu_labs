"""
3_db_viewer.py: Интерактивный веб-интерфейс для инспекции слоев баз данных (DB Explorer).
Позволяет исследовать структуры и содержимое таблиц PostgreSQL (SOURCE, STAGING, ODS, DDS, MART)
и ClickHouse, а также выполнять произвольные SQL-запросы.
"""

import sys
from pathlib import Path

# Гарантированное добавление путей в sys.path
STREAMLIT_DIR = Path(__file__).resolve().parent.parent
APP_DIR = STREAMLIT_DIR.parent
PROJECT_ROOT = APP_DIR.parent

for p in (str(PROJECT_ROOT), str(APP_DIR), str(STREAMLIT_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import streamlit as st
import pandas as pd
from utils import query_postgres, query_clickhouse, check_db_health, get_pg_conn, get_ch_client

st.set_page_config(page_title="Просмотр слоев БД (DB Explorer)", page_icon="🗄️", layout="wide")

st.title("🗄️ Веб-инспектор баз данных и слоев хранения")
st.markdown("""
Интерактивный интерфейс инспекции состояния многослойного DWH в **PostgreSQL** и аналитической витрины в **ClickHouse**.
Позволяет просматривать структуру таблиц, исследовать данные по слоям и выполнять произвольные SQL-запросы.
""")

# Ссылка на встроенный веб-интерфейс ClickHouse Play
st.info("💡 **Для ClickHouse также доступен встроенный официальный веб-клиент:** [http://localhost:8123/play](http://localhost:8123/play) (пользователь `default`, пароль `ch_password`)")

db_status = check_db_health()

db_choice = st.radio(
    "Выберите СУБД для исследования:",
    ["🐘 PostgreSQL (DWH: SOURCE, STAGING, ODS, DDS, MART)", "⚡ ClickHouse (OLAP витрина)"],
    horizontal=True
)

st.divider()

if "PostgreSQL" in db_choice:
    if not db_status["pg"]:
        st.error("PostgreSQL недоступен. Проверьте запуск контейнера.")
        st.stop()

    tab_tables, tab_sql = st.tabs(["📋 Просмотр таблиц по слоям", "💻 SQL-консоль (PostgreSQL)"])

    with tab_tables:
        col_s1, col_s2, col_s3 = st.columns([1, 2, 1])

        # Получаем список всех схем и таблиц
        tables_query = """
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_schema IN ('source', 'staging', 'ods', 'dds', 'mart')
            ORDER BY table_schema, table_name;
        """
        all_tables_df = query_postgres(tables_query)

        available_schemas = sorted(all_tables_df['table_schema'].unique().tolist())
        
        with col_s1:
            selected_schema = st.selectbox("1. Слой хранения (Схема):", available_schemas)

        filtered_tables = all_tables_df[all_tables_df['table_schema'] == selected_schema]['table_name'].tolist()

        with col_s2:
            selected_table = st.selectbox("2. Таблица слоя:", filtered_tables)

        with col_s3:
            limit_rows = st.number_input("Лимит строк:", min_value=10, max_value=5000, value=50, step=50)

        full_table_name = f"{selected_schema}.{selected_table}"

        # Статистика таблицы
        count_res = query_postgres(f"SELECT COUNT(*) AS total FROM {full_table_name};")
        total_rows = count_res['total'].iloc[0] if not count_res.empty else 0

        st.markdown(f"### Таблица: `{full_table_name}` — Всего записей: **{total_rows:,}**")

        # Информация о столбцах
        cols_query = f"""
            SELECT
                column_name AS "Столбец",
                data_type AS "Тип данных",
                character_maximum_length AS "Макс. длина",
                is_nullable AS "NULLable"
            FROM information_schema.columns
            WHERE table_schema = '{selected_schema}' AND table_name = '{selected_table}'
            ORDER BY ordinal_position;
        """
        cols_df = query_postgres(cols_query)

        with st.expander("📐 Структура атрибутов (DDL Schema)", expanded=False):
            st.dataframe(cols_df, use_container_width=True, hide_index=True)

        # Данные таблицы
        data_df = query_postgres(f"SELECT * FROM {full_table_name} LIMIT {limit_rows};")
        st.dataframe(data_df, use_container_width=True)

        # Выгрузка в CSV
        csv = data_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="💾 Скачать показанный срез в CSV",
            data=csv,
            file_name=f"{full_table_name}_sample.csv",
            mime='text/csv'
        )

    with tab_sql:
        st.markdown("#### Выполнение произвольного SQL-запроса к PostgreSQL")
        default_query = """SELECT * FROM ods.data_quality_log ORDER BY executed_at DESC LIMIT 10;"""
        custom_query = st.text_area("SQL-запрос (только чтение):", value=default_query, height=120)

        if st.button("▶️ Выполнить запрос (PostgreSQL)", use_container_width=True):
            if not custom_query.strip().lower().startswith("select") and not custom_query.strip().lower().startswith("with"):
                st.warning("⚠️ Для безопасности разрешены только запросы на чтение (SELECT / WITH).")
            else:
                try:
                    with st.spinner("Выполнение запроса..."):
                        res_df = query_postgres(custom_query)
                        st.success(f"Запрос успешно выполнен! Получено строк: {len(res_df)}")
                        st.dataframe(res_df, use_container_width=True)
                except Exception as e:
                    st.error(f"Ошибка выполнения SQL: {e}")

else:
    # ClickHouse
    if not db_status["ch"]:
        st.error("ClickHouse недоступен. Проверьте запуск контейнера.")
        st.stop()

    tab_ch_tables, tab_ch_sql = st.tabs(["📋 Таблицы ClickHouse", "💻 SQL-консоль (ClickHouse)"])

    with tab_ch_tables:
        ch_tables_df = query_clickhouse("SHOW TABLES FROM music_analytics;")
        ch_tables = ch_tables_df.iloc[:, 0].tolist() if not ch_tables_df.empty else []

        c_ch1, c_ch2 = st.columns([2, 1])
        with c_ch1:
            sel_ch_table = st.selectbox("Таблица в базе music_analytics:", ch_tables)
        with c_ch2:
            ch_limit = st.number_input("Лимит строк ClickHouse:", min_value=10, max_value=5000, value=50, step=50)

        if sel_ch_table:
            ch_full_name = f"music_analytics.{sel_ch_table}"
            ch_count = query_clickhouse(f"SELECT count() as total FROM {ch_full_name};").iloc[0]['total']
            st.markdown(f"### Таблица: `{ch_full_name}` — Всего записей: **{ch_count:,}**")

            # Структура таблицы ClickHouse
            ch_desc = query_clickhouse(f"DESCRIBE TABLE {ch_full_name};")
            with st.expander("📐 Описание типов данных ClickHouse (DESCRIBE)", expanded=False):
                st.dataframe(ch_desc, use_container_width=True)

            # Содержимое таблицы
            ch_data = query_clickhouse(f"SELECT * FROM {ch_full_name} LIMIT {ch_limit};")
            st.dataframe(ch_data, use_container_width=True)

    with tab_ch_sql:
        st.markdown("#### Выполнение произвольного SQL-запроса к ClickHouse")
        default_ch_query = """SELECT city_name, sum(listens_count) AS total_listens, count() AS rows_count
FROM music_analytics.city_genre_popularity FINAL
GROUP BY city_name
ORDER BY total_listens DESC;"""
        custom_ch_sql = st.text_area("SQL-запрос к ClickHouse:", value=default_ch_query, height=120)

        if st.button("▶️ Выполнить запрос (ClickHouse)", use_container_width=True):
            try:
                with st.spinner("Выполнение запроса в ClickHouse..."):
                    res_ch = query_clickhouse(custom_ch_sql)
                    st.success(f"Запрос выполнен! Получено строк: {len(res_ch)}")
                    st.dataframe(res_ch, use_container_width=True)
            except Exception as e:
                st.error(f"Ошибка ClickHouse: {e}")
