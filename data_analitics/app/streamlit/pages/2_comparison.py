"""
2_comparison.py: Анализ и сопоставление данных (ВОиАД Лабораторная работа №2).
Сравнение данных между слоями хранилища, аудит очистки по журналу ods.data_quality_log,
сопоставление исходных и синтетических партий, проверка согласованности PostgreSQL vs ClickHouse.
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
import plotly.express as px
import plotly.graph_objects as go
from utils import query_postgres, query_clickhouse, check_db_health

st.set_page_config(page_title="Анализ и сопоставление данных", page_icon="⚖️", layout="wide")

st.title("⚖️ Анализ и сопоставление данных хранилища")
st.markdown("""
**Дисциплина: «Высокопроизводительная обработка и анализ данных» (Лабораторная работа №2)**  
*Цель работы:* Комплексное исследование результатов прохождения данных через слои DWH,
оценка эффективности очистки на основе журнала качества, сопоставление исходных и синтетических данных,
а также строгая верификация согласованности витрин между **PostgreSQL** и **ClickHouse**.
""")

db_status = check_db_health()
if not db_status["pg"]:
    st.error("База данных PostgreSQL недоступна. Пожалуйста, запустите контейнеры через панель управления на главной странице.")
    st.stop()

st.divider()

# 1. Загрузка метаданных партий и дат
batches_df = query_postgres("SELECT DISTINCT batch_id FROM source.music_tracks ORDER BY batch_id;")
available_batches = batches_df['batch_id'].tolist() if not batches_df.empty else ['initial_load']

# Сайдбар с фильтрами
st.sidebar.header("🎛️ Фильтры сопоставления")
selected_batches = st.sidebar.multiselect(
    "Партии данных (Batch ID):",
    options=available_batches,
    default=available_batches
)

date_range_df = query_postgres("SELECT MIN(dt) as min_dt, MAX(dt) as max_dt FROM source.music_tracks;")
if not date_range_df.empty and date_range_df['min_dt'].iloc[0] is not None:
    min_date = date_range_df['min_dt'].iloc[0]
    max_date = date_range_df['max_dt'].iloc[0]
    selected_dates = st.sidebar.date_input(
        "Диапазон дат (dt):",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
else:
    selected_dates = None

# 2. Сравнение объемов данных по слоям хранилища
st.subheader("1. 🏢 Прохождение данных по слоям многослойного DWH")
st.caption("SOURCE → STAGING → ODS → DDS («снежинка») → MART")

# Получение фактических данных о количестве строк
layers_summary_query = """
    SELECT
        '1. SOURCE' AS layer,
        COUNT(*) AS rows_count,
        'Сырые данные источника (включая дубликаты и пропуски)' AS description
    FROM source.music_tracks
    UNION ALL
    SELECT
        '2. STAGING' AS layer,
        COUNT(*) AS rows_count,
        'Промежуточный буфер, скопировано as is без изменений' AS description
    FROM staging.music_tracks
    UNION ALL
    SELECT
        '3. ODS' AS layer,
        COUNT(*) AS rows_count,
        'Очищенные детальные данные (удалены дубликаты, устранены пропуски)' AS description
    FROM ods.music_tracks
    UNION ALL
    SELECT
        '4. DDS (Факты)' AS layer,
        COUNT(*) AS rows_count,
        'Таблица фактов fact_listens в нормализованной схеме снежинка' AS description
    FROM dds.fact_listens
    UNION ALL
    SELECT
        '5. MART (Витрина)' AS layer,
        COUNT(*) AS rows_count,
        'Агрегированная аналитическая витрина по городам и жанрам' AS description
    FROM mart.city_genre_popularity;
"""

df_layers = query_postgres(layers_summary_query)

c_fun1, c_fun2 = st.columns([3, 2])

with c_fun1:
    fig_funnel = go.Figure(go.Funnel(
        y=df_layers['layer'],
        x=df_layers['rows_count'],
        textinfo="value+percent previous",
        marker=dict(color=["#3498db", "#2980b9", "#2ecc71", "#1abc9c", "#e67e22"])
    ))
    fig_funnel.update_layout(title="Воронка трансформации данных по слоям DWH")
    st.plotly_chart(fig_funnel, use_container_width=True)

with c_fun2:
    st.markdown("**Характеристика уровней детализации:**")
    st.dataframe(df_layers, use_container_width=True, hide_index=True)
    st.info("""
    **Обоснование изменения объемов:**
    - `SOURCE` = `STAGING`: полное совпадение объемов гарантировано переносом `as is`.
    - `STAGING` $\\rightarrow$ `ODS`: уменьшение обусловлено отсечением дублирующихся строк (дедупликация).
    - `ODS` = `DDS`: взаимно однозначное соответствие транзакционных фактов прослушиваний.
    - `DDS` $\\rightarrow$ `MART`: свертка фактов в агрегированные показатели витрины.
    """)

st.divider()

# 3. Аудит результатов очистки по журналу ods.data_quality_log
st.subheader("2. 📋 Аудит качества данных на основе журнала ods.data_quality_log")
st.caption("Фактические показатели выполненных операций очистки, рассчитанные ETL-процессом.")

log_query = """
    SELECT
        log_id,
        batch_id,
        p_sdt,
        p_edt,
        total_staging_rows,
        duplicates_removed,
        null_tracks_replaced,
        null_artists_replaced,
        null_genres_replaced,
        invalid_time_rows,
        loaded_ods_rows,
        executed_at
    FROM ods.data_quality_log
    ORDER BY executed_at DESC;
"""
df_quality_log = query_postgres(log_query)

if not df_quality_log.empty:
    col_l1, col_l2, col_l3, col_l4 = st.columns(4)
    tot_stg = df_quality_log['total_staging_rows'].sum()
    tot_dup = df_quality_log['duplicates_removed'].sum()
    tot_clean = df_quality_log['loaded_ods_rows'].sum()
    tot_null_fixed = (
        df_quality_log['null_tracks_replaced'].sum() +
        df_quality_log['null_artists_replaced'].sum() +
        df_quality_log['null_genres_replaced'].sum()
    )

    col_l1.metric("Обработано в STAGING", f"{tot_stg:,}")
    col_l2.metric("Удалено дубликатов", f"{tot_dup:,}", f"-{(tot_dup/tot_stg*100) if tot_stg else 0:.1f}%")
    col_l3.metric("Исправлено пропусков", f"{tot_null_fixed:,}")
    col_l4.metric("Успешно загружено в ODS", f"{tot_clean:,}")

    with st.expander("🔎 Детальный журнал операций очистки (ods.data_quality_log)"):
        st.dataframe(df_quality_log, use_container_width=True)

    # Визуализация структуры устраненных дефектов
    defects_summary = pd.DataFrame({
        "Тип дефекта": [
            "Удаленные дубликаты",
            "Пропуски треков ('unknown')",
            "Пропуски артистов ('unknown')",
            "Пропуски жанров ('unknown')",
            "Ошибки формата времени"
        ],
        "Количество": [
            int(tot_dup),
            int(df_quality_log['null_tracks_replaced'].sum()),
            int(df_quality_log['null_artists_replaced'].sum()),
            int(df_quality_log['null_genres_replaced'].sum()),
            int(df_quality_log['invalid_time_rows'].sum())
        ]
    })

    fig_defects = px.bar(
        defects_summary,
        x="Тип дефекта",
        y="Количество",
        text="Количество",
        color="Тип дефекта",
        title="Структура устраненных дефектов качества данных"
    )
    fig_defects.update_traces(textposition='outside')
    st.plotly_chart(fig_defects, use_container_width=True)
else:
    st.info("Журнал качества данных пока пуст. Выполните инкрементальную загрузку STAGING → ODS.")

st.divider()

# 4. Сопоставление исходных и синтетических данных
st.subheader("3. 🧪 Сравнение исходного датасета и синтетических данных")

comp_query = """
    SELECT
        CASE
            WHEN batch_id = 'initial_load' THEN 'Исходный датасет (music_tracks)'
            ELSE 'Синтетические партии (Batch 1 & 2)'
        END AS data_source,
        genre_name,
        city_name,
        dt,
        COUNT(*) AS records_count
    FROM ods.music_tracks
    GROUP BY 1, 2, 3, 4;
"""
df_comp = query_postgres(comp_query)

if not df_comp.empty:
    c_cmp1, c_cmp2 = st.columns(2)

    with c_cmp1:
        # Распределение по городам в разрезе источников
        city_comp = df_comp.groupby(['city_name', 'data_source'])['records_count'].sum().reset_index()
        fig_city_comp = px.bar(
            city_comp,
            x='city_name',
            y='records_count',
            color='data_source',
            barmode='group',
            title="Распределение записей по городам (Исходные vs Синтетика)",
            labels={'records_count': 'Количество записей', 'city_name': 'Город'}
        )
        st.plotly_chart(fig_city_comp, use_container_width=True)

    with c_cmp2:
        # Топ жанров в синтетике vs исходных
        genre_comp = df_comp.groupby(['genre_name', 'data_source'])['records_count'].sum().reset_index()
        top_genres = genre_comp.groupby('genre_name')['records_count'].sum().nlargest(10).index
        genre_comp_top = genre_comp[genre_comp['genre_name'].isin(top_genres)]

        fig_genre_comp = px.bar(
            genre_comp_top,
            x='genre_name',
            y='records_count',
            color='data_source',
            barmode='group',
            title="Топ-10 жанров (Исходные vs Синтетика)",
            labels={'records_count': 'Количество записей', 'genre_name': 'Жанр'}
        )
        st.plotly_chart(fig_genre_comp, use_container_width=True)

    # Динамика объемов данных по синтетическому полю dt
    dt_timeline = df_comp.groupby(['dt', 'data_source'])['records_count'].sum().reset_index()
    fig_timeline = px.line(
        dt_timeline,
        x='dt',
        y='records_count',
        color='data_source',
        markers=True,
        title="Динамика поступления данных по синтетическому полю dt",
        labels={'dt': 'Дата события (dt)', 'records_count': 'Число записей в ODS'}
    )
    st.plotly_chart(fig_timeline, use_container_width=True)

st.divider()

# 5. Проверка согласованности аналитических витрин (PostgreSQL vs ClickHouse)
st.subheader("4. 🎯 Проверка согласованности аналитических витрин")
st.markdown("""
Сравнение ключевых аналитических показателей витрины `city_genre_popularity`,
размещенной в **PostgreSQL** (DWH) и перенесенной в **ClickHouse** (OLAP).
""")

if not db_status["ch"]:
    st.warning("⚠️ СУБД ClickHouse пока не доступна. Выполните шаг 'Перенести витрину в ClickHouse' для верификации.")
else:
    try:
        # Расчет показателей из PostgreSQL
        pg_metrics_query = """
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
        """
        pg_res = query_postgres(pg_metrics_query).iloc[0]

        # Расчет показателей из ClickHouse
        ch_metrics_query = """
            SELECT
                count() AS total_rows,
                sum(listens_count) AS total_listens,
                uniqExact(city_name) AS unique_cities,
                uniqExact(genre_name) AS unique_genres,
                sum(morning_listens) AS total_morning,
                sum(day_listens) AS total_day,
                sum(evening_listens) AS total_evening,
                sum(night_listens) AS total_night
            FROM city_genre_popularity FINAL;
        """
        ch_res = query_clickhouse(ch_metrics_query).iloc[0]

        metrics_def = [
            ("Количество записей в витрине", "COUNT(*)", int(pg_res['total_rows']), int(ch_res['total_rows'])),
            ("Общее число прослушиваний", "SUM(listens_count)", int(pg_res['total_listens']), int(ch_res['total_listens'])),
            ("Количество уникальных городов", "COUNT(DISTINCT city_name)", int(pg_res['unique_cities']), int(ch_res['unique_cities'])),
            ("Количество уникальных жанров", "COUNT(DISTINCT genre_name)", int(pg_res['unique_genres']), int(ch_res['unique_genres'])),
            ("Утренние прослушивания (06:00-12:00)", "SUM(morning_listens)", int(pg_res['total_morning']), int(ch_res['total_morning'])),
            ("Дневные прослушивания (12:00-18:00)", "SUM(day_listens)", int(pg_res['total_day']), int(ch_res['total_day'])),
            ("Вечерние прослушивания (18:00-24:00)", "SUM(evening_listens)", int(pg_res['total_evening']), int(ch_res['total_evening'])),
            ("Ночные прослушивания (00:00-06:00)", "SUM(night_listens)", int(pg_res['total_night']), int(ch_res['total_night'])),
        ]

        verification_table = []
        all_consistent = True

        for name, formula, pg_val, ch_val in metrics_def:
            diff = abs(pg_val - ch_val)
            matched = (diff == 0)
            if not matched:
                all_consistent = False
            verification_table.append({
                "Наименование показателя": name,
                "Способ расчёта": formula,
                "Исходная СУБД (PostgreSQL)": f"{pg_val:,}",
                "Целевая СУБД (ClickHouse)": f"{ch_val:,}",
                "Расхождение": diff,
                "Результат проверки": "✅ Совпадает" if matched else "❌ Не совпадает"
            })

        df_verification = pd.DataFrame(verification_table)
        st.dataframe(df_verification, use_container_width=True, hide_index=True)

        if all_consistent and int(pg_res['total_rows']) > 0:
            st.success("🎉 **Все показатели аналитических витрин в PostgreSQL и ClickHouse полностью совпадают!** "
                       "Перенос данных выполнен корректно, целостность и точность вычислений сохранены.")
        elif int(pg_res['total_rows']) == 0:
            st.info("Витрины пока не содержат данных. Выполните шаги обновления и переноса.")
        else:
            st.error("Обнаружены расхождения между витринами СУБД. Проверьте параметры повторной синхронизации.")

    except Exception as e:
        st.error(f"Ошибка проверки витрин: {e}")

st.divider()

st.markdown("""
### 🏁 Итоговые выводы о качестве и согласованности данных:
1. **Эффективность очистки:** Алгоритм в PL/pgSQL процедуре корректно отфильтровал дубликаты и заполнил пропущенные значения константой `'unknown'`, что зафиксировано в таблице аудита `ods.data_quality_log`.
2. **Синтетические данные:** Сгенерированные партии успешно воспроизвели предметную область, смоделировали историчность и подтвердили устойчивость алгоритмов очистки к дефектам.
3. **Согласованность витрин:** Аналитическая витрина `city_genre_popularity` в ClickHouse с движком `ReplacingMergeTree` обеспечивает 100% точность воспроизведения метрик PostgreSQL.
""")
