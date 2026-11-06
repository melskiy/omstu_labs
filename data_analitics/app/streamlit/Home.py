"""
Home.py: Главная страница интерактивного аналитического приложения Streamlit.
Объединяет функционал лабораторных работ по дисциплинам АБД и ВОиАД.
"""

import sys
from pathlib import Path

# Гарантированное добавление путей в sys.path
STREAMLIT_DIR = Path(__file__).resolve().parent
APP_DIR = STREAMLIT_DIR.parent
PROJECT_ROOT = APP_DIR.parent

for p in (str(PROJECT_ROOT), str(APP_DIR), str(STREAMLIT_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import streamlit as st
import pandas as pd
from datetime import date
from utils import check_db_health, query_postgres, get_pg_conn

try:
    from app.loader import load_csv_to_source
    from app.generator import generate_two_sequential_batches
    from app.etl import init_database_schemas, run_source_to_staging, run_staging_to_ods, run_ods_to_dds, run_refresh_mart
    from app.clickhouse_transfer import transfer_mart_to_clickhouse
except ImportError:
    from loader import load_csv_to_source
    from generator import generate_two_sequential_batches
    from etl import init_database_schemas, run_source_to_staging, run_staging_to_ods, run_ods_to_dds, run_refresh_mart
    from clickhouse_transfer import transfer_mart_to_clickhouse

st.set_page_config(
    page_title="Music Tracks Analytics DWH",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🎵 Платформа аналитики музыкальных треков (DWH & Analytics)")
st.markdown("""
**Единое интерактивное аналитическое приложение**, объединяющее требования двух дисциплин:
- **«Администрирование больших данных»** (Лабораторные работы №1 и №2):
  * Многослойное DWH: `SOURCE` $\\rightarrow$ `STAGING` $\\rightarrow$ `ODS` $\\rightarrow$ `DDS` («снежинка»)
  * Инкрементальная загрузка, генерация синтетических данных, аналитическая витрина, перенос в ClickHouse.
- **«Высокопроизводительная обработка и анализ данных»** (Лабораторные работы №1 и №2):
  * Интерактивный исследовательский анализ данных (EDA) и формулирование алгоритмов очистки.
  * Анализ и сопоставление данных хранилища, оценка качества, аудит и сверка витрин (PostgreSQL vs ClickHouse).
""")

st.divider()

# 1. Проверка состояния инфраструктуры
st.subheader("🖥️ Состояние сервисов и баз данных")
col1, col2 = st.columns(2)

db_status = check_db_health()

with col1:
    if db_status["pg"]:
        st.success("🟢 **PostgreSQL**: Подключено (Слои SOURCE, STAGING, ODS, DDS, MART)")
    else:
        st.error(f"🔴 **PostgreSQL**: Ошибка подключения ({db_status['pg_err']})")

with col2:
    if db_status["ch"]:
        st.success("🟢 **ClickHouse**: Подключено (Целевая аналитическая витрина)")
    else:
        st.warning(f"🟡 **ClickHouse**: Недоступен или не инициализирован ({db_status['ch_err']})")

st.divider()

# 2. Метрики состояния слоев хранилища
st.subheader("📊 Текущие объемы данных по слоям DWH")

if db_status["pg"]:
    try:
        layers_stats_query = """
            SELECT
                (SELECT COUNT(*) FROM source.music_tracks) AS source_count,
                (SELECT COUNT(*) FROM staging.music_tracks) AS staging_count,
                (SELECT COUNT(*) FROM ods.music_tracks) AS ods_count,
                (SELECT COUNT(*) FROM dds.fact_listens) AS dds_facts_count,
                (SELECT COUNT(*) FROM mart.city_genre_popularity) AS mart_count;
        """
        stats_df = query_postgres(layers_stats_query)
        
        m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
        m_col1.metric("1. SOURCE", f"{stats_df['source_count'].iloc[0]:,} строк")
        m_col2.metric("2. STAGING", f"{stats_df['staging_count'].iloc[0]:,} строк")
        m_col3.metric("3. ODS (очищено)", f"{stats_df['ods_count'].iloc[0]:,} строк")
        m_col4.metric("4. DDS (факты)", f"{stats_df['dds_facts_count'].iloc[0]:,} строк")
        m_col5.metric("5. MART (витрина)", f"{stats_df['mart_count'].iloc[0]:,} строк")

    except Exception as e:
        st.info("Таблицы хранилища еще не инициализированы. Воспользуйтесь панелью управления ниже.")
else:
    st.info("Запустите PostgreSQL для отображения статистики слоев хранилища.")

st.divider()

# 3. Панель пошагового управления ETL процессами
st.subheader("⚙️ Панель управления ETL-пайплайном")
st.caption("Позволяет выполнить каждый шаг лабораторных работ или запустить сквозной процесс.")

if st.button("🚀 ВЫПОЛНИТЬ СКВОЗНОЙ ETL (SOURCE → STAGING → ODS → DDS → MART → ClickHouse)", type="primary", use_container_width=True):
    with st.spinner("Запуск сквозного пайплайна для всех партий данных..."):
        try:
            # 1. Перенос в staging
            run_source_to_staging()
            # 2. Инкремент в ods
            run_staging_to_ods(date(2024, 1, 1), date(2024, 6, 30))
            # 3. DDS снежинка
            run_ods_to_dds(date(2024, 1, 1), date(2024, 6, 30))
            # 4. Обновление витрины
            run_refresh_mart(date(2024, 1, 1), date(2024, 6, 30))
            # 5. Синхронизация с ClickHouse
            transfer_mart_to_clickhouse()
            st.success("🎉 Полный цикл успешно выполнен! Все слои DWH и витрина ClickHouse на 100% согласованы!")
            st.rerun()
        except Exception as e:
            st.error(f"Ошибка выполнения сквозного пайплайна: {e}")

ctrl_col1, ctrl_col2, ctrl_col3 = st.columns(3)

with ctrl_col1:
    st.markdown("#### Шаг 1: Инициализация")
    if st.button("🛠️ 1. Накатить DDL схемы и процедуры", use_container_width=True):
        with st.spinner("Инициализация схем PostgreSQL..."):
            try:
                init_database_schemas()
                st.success("Схемы SOURCE, STAGING, ODS, DDS, MART успешно созданы!")
                st.rerun()
            except Exception as e:
                st.error(f"Ошибка: {e}")

    if st.button("📥 2. Загрузить исходный CSV в SOURCE", use_container_width=True):
        with st.spinner("Загрузка music_project.csv с генерацией dt..."):
            try:
                rows = load_csv_to_source()
                st.success(f"Загружено {rows:,} строк в source.music_tracks!")
                st.rerun()
            except Exception as e:
                st.error(f"Ошибка: {e}")

with ctrl_col2:
    st.markdown("#### Шаг 2: Обработка данных")
    if st.button("🔄 3. Перенести SOURCE → STAGING (as is)", use_container_width=True):
        with st.spinner("Перенос данных as is..."):
            try:
                rows = run_source_to_staging()
                st.success(f"Перенесено {rows:,} строк в STAGING!")
                st.rerun()
            except Exception as e:
                st.error(f"Ошибка: {e}")

    if st.button("🧹 4. Инкремент STAGING → ODS (очистка)", use_container_width=True):
        with st.spinner("Инкрементальная загрузка и очистка..."):
            try:
                rows = run_staging_to_ods(date(2024, 1, 1), date(2024, 6, 30))
                st.success(f"Очищено и загружено в ODS: {rows:,} строк!")
                st.rerun()
            except Exception as e:
                st.error(f"Ошибка: {e}")

with ctrl_col3:
    st.markdown("#### Шаг 3: DDS, Витрины и Синтетика")
    if st.button("❄️ 5. Загрузить ODS → DDS («снежинка»)", use_container_width=True):
        with st.spinner("Обновление измерений и фактов DDS..."):
            try:
                facts = run_ods_to_dds(date(2024, 1, 1), date(2024, 6, 30))
                st.success(f"Загружено фактов в DDS: {facts:,}!")
                st.rerun()
            except Exception as e:
                st.error(f"Ошибка: {e}")

    if st.button("📈 6. Обновить аналитическую витрину", use_container_width=True):
        with st.spinner("Пересчет витрины mart.city_genre_popularity..."):
            try:
                m_rows = run_refresh_mart(date(2024, 1, 1), date(2024, 6, 30))
                st.success(f"Витрина сформирована ({m_rows:,} записей)!")
                st.rerun()
            except Exception as e:
                st.error(f"Ошибка: {e}")

    if st.button("🚀 7. Сгенерировать партии синтетики (Лаб 2)", use_container_width=True):
        with st.spinner("Генерация 2-х партий данных с контролируемыми дефектами..."):
            try:
                generate_two_sequential_batches()
                st.success("Сгенерированы и загружены партии synthetic_batch_1 и synthetic_batch_2!")
                st.rerun()
            except Exception as e:
                st.error(f"Ошибка: {e}")

    if st.button("🏎️ 8. Перенести витрину в ClickHouse", use_container_width=True):
        with st.spinner("Перенос аналитической витрины в ClickHouse..."):
            try:
                ch_rows = transfer_mart_to_clickhouse()
                st.success(f"В ClickHouse перенесено {ch_rows:,} строк!")
                st.rerun()
            except Exception as e:
                st.error(f"Ошибка: {e}")

st.divider()

st.info("💡 **Для детального анализа перейдите в меню слева:**\n"
        "- 📑 **1_eda**: Исследовательский анализ данных (ВОиАД Лаб. №1)\n"
        "- 📊 **2_comparison**: Анализ и сопоставление слоев, аудит очистки, сверка PostgreSQL vs ClickHouse (ВОиАД Лаб. №2)")
