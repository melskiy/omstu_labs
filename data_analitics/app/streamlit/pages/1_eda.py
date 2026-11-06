"""
1_eda.py: Исследовательский анализ данных (ВОиАД Лабораторная работа №1).
Интерактивный анализ исходного набора music_tracks, выявление дефектов
и формулирование алгоритма очистки данных.
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
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from utils import load_raw_csv_data

st.set_page_config(page_title="Исследовательский анализ данных", page_icon="🔍", layout="wide")

st.title("🔍 Исследовательский анализ данных (EDA)")
st.markdown("""
**Дисциплина: «Высокопроизводительная обработка и анализ данных» (Лабораторная работа №1)**  
*Цель работы:* Комплексное исследование исходного набора данных `music_tracks`, оценка качества источника,
выявление аномалий и формирование формализованных правил очистки для последующего DWH-хранилища.
""")

# 1. Загрузка данных
with st.spinner("Загрузка исходного набора данных..."):
    df_raw = load_raw_csv_data()

# Сайдбар с фильтрами для интерактивного анализа
st.sidebar.header("🎛️ Интерактивные фильтры")
selected_city = st.sidebar.selectbox("Город:", ["Все города"] + sorted(list(df_raw['City'].dropna().unique())))
selected_day = st.sidebar.selectbox("День недели:", ["Все дни"] + sorted(list(df_raw['Day'].dropna().unique())))
top_n = st.sidebar.slider("Количество элементов в Топах:", min_value=5, max_value=30, value=10, step=5)

# Применение фильтров для динамических срезов
df_filtered = df_raw.copy()
if selected_city != "Все города":
    df_filtered = df_filtered[df_filtered['City'] == selected_city]
if selected_day != "Все дни":
    df_filtered = df_filtered[df_filtered['Day'] == selected_day]

st.divider()

# 2. Общие показатели источника
st.subheader("1. 📋 Общие показатели и размерность источника")

# Подсчет полных дубликатов
content_cols = ['userID', 'Track', 'artist', 'genre', 'City', 'time', 'Day']
duplicate_rows_count = df_raw.duplicated(subset=content_cols).sum()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Всего наблюдений", f"{len(df_raw):,}")
c2.metric("Количество атрибутов", f"{len(df_raw.columns)}")
c3.metric("Полных дубликатов", f"{duplicate_rows_count:,}", f"{duplicate_rows_count / len(df_raw):.1%}")
c4.metric("Пользователей (Unique ID)", f"{df_raw['userID'].nunique():,}")

with st.expander("👀 Первые 10 строк исходного набора данных"):
    st.dataframe(df_raw.head(10), use_container_width=True)

st.divider()

# 3. Анализ пропущенных значений и структуры атрибутов
st.subheader("2. 🧩 Анализ пропущенных значений и структуры данных")

# Составление сводной таблицы качества по атрибутам
quality_rows = []
for col in df_raw.columns:
    null_count = df_raw[col].isna().sum() + (df_raw[col].astype(str).str.strip().isin(['', 'nan', 'None', 'null'])).sum()
    null_pct = (null_count / len(df_raw)) * 100
    unique_count = df_raw[col].nunique()
    dtype_str = str(df_raw[col].dtype)
    quality_rows.append({
        "Атрибут": col,
        "Тип данных": dtype_str,
        "Заполнено": len(df_raw) - null_count,
        "Пропусков (кол-во)": null_count,
        "Доля пропусков (%)": round(null_pct, 2),
        "Уникальных значений": unique_count
    })

df_quality = pd.DataFrame(quality_rows)

q_col1, q_col2 = st.columns([3, 2])

with q_col1:
    st.markdown("**Сводная таблица заполненности атрибутов:**")
    st.dataframe(
        df_quality.style.format({
            "Заполнено": "{:,}",
            "Пропусков (кол-во)": "{:,}",
            "Доля пропусков (%)": "{:.2f}%",
            "Уникальных значений": "{:,}"
        }),
        use_container_width=True
    )

with q_col2:
    missing_df = df_quality[df_quality["Пропусков (кол-во)"] > 0]
    fig_missing = px.bar(
        missing_df,
        x="Атрибут",
        y="Доля пропусков (%)",
        text="Доля пропусков (%)",
        color="Доля пропусков (%)",
        color_continuous_scale="Reds",
        title="Доля пропусков по атрибутам"
    )
    fig_missing.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
    st.plotly_chart(fig_missing, use_container_width=True)

st.markdown("""
> **Вывод по пропускам:** В атрибутах `artist` (11.07%), `genre` (1.84%) и `Track` (1.89%) присутствуют пропуски.
> В обязательном поле пользователя `userID`, а также в `City`, `time`, `Day` пропусков не обнаружено.
""")

st.divider()

# 4. Анализ распределений признаков
st.subheader("3. 📊 Распределения признаков и паттерны поведения")

tab1, tab2, tab3 = st.tabs(["Временная динамика", "Популярность жанров", "Артисты и города"])

with tab1:
    st.markdown("#### Распределение прослушиваний по времени суток и дням недели")
    
    # Извлечение часа из поля time
    df_filtered['hour'] = pd.to_datetime(df_filtered['time'], format='%H:%M:%S', errors='coerce').dt.hour
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        hourly_counts = df_filtered.groupby('hour').size().reset_index(name='listens')
        fig_hour = px.line(
            hourly_counts, x='hour', y='listens', markers=True,
            title=f"Прослушивания по часам суток ({selected_city})",
            labels={'hour': 'Час суток (0-23)', 'listens': 'Количество прослушиваний'}
        )
        fig_hour.update_layout(xaxis=dict(tickmode='linear', tick0=0, dtick=2))
        st.plotly_chart(fig_hour, use_container_width=True)

    with col_t2:
        day_counts = df_raw.groupby(['Day', 'City']).size().reset_index(name='count')
        fig_day = px.bar(
            day_counts, x='Day', y='count', color='City', barmode='group',
            title="Активность по дням недели в Москве и Санкт-Петербурге",
            labels={'count': 'Количество треков', 'Day': 'День недели'}
        )
        st.plotly_chart(fig_day, use_container_width=True)

with tab2:
    st.markdown("#### Топ музыкальных жанров")
    clean_genres_df = df_filtered[df_filtered['genre'].notna() & (df_filtered['genre'].str.strip() != '')]
    genre_counts = clean_genres_df['genre'].str.strip().str.lower().value_counts().head(top_n).reset_index()
    genre_counts.columns = ['genre', 'count']

    fig_genre = px.bar(
        genre_counts, x='count', y='genre', orientation='h',
        title=f"Топ-{top_n} жанров ({selected_city})",
        labels={'count': 'Прослушиваний', 'genre': 'Жанр'},
        color='count', color_continuous_scale="Viridis"
    )
    fig_genre.update_layout(yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig_genre, use_container_width=True)

with tab3:
    col_a1, col_a2 = st.columns(2)
    with col_a1:
        st.markdown("#### Топ исполнителей")
        clean_artists_df = df_filtered[df_filtered['artist'].notna() & (df_filtered['artist'].str.strip() != '')]
        top_artists = clean_artists_df['artist'].str.strip().value_counts().head(top_n).reset_index()
        top_artists.columns = ['artist', 'count']

        fig_artists = px.bar(
            top_artists, x='count', y='artist', orientation='h',
            title=f"Топ-{top_n} артистов",
            labels={'count': 'Количество треков', 'artist': 'Артист'}
        )
        fig_artists.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_artists, use_container_width=True)

    with col_a2:
        st.markdown("#### Доля городов в объеме прослушиваний")
        city_dist = df_raw['City'].value_counts().reset_index()
        city_dist.columns = ['City', 'Count']
        fig_pie = px.pie(
            city_dist, values='Count', names='City',
            title="Распределение данных по городам",
            hole=0.4
        )
        st.plotly_chart(fig_pie, use_container_width=True)

st.divider()

# 5. Выявление аномалий и неявных дубликатов
st.subheader("4. ⚠️ Выявление аномалий и несогласованных категорий")

col_anom1, col_anom2 = st.columns(2)

with col_anom1:
    st.markdown("#### Неявные дубликаты в жанрах")
    st.write("Поиск вариаций написания одного и того же жанра (на примере хип-хопа и электроники):")
    
    # Поиск вариаций hip-hop
    genres_series = df_raw['genre'].dropna().str.strip().str.lower()
    hip_variants = genres_series[genres_series.str.contains('hip', na=False)].value_counts().reset_index()
    hip_variants.columns = ['Вариант написания', 'Количество строк']
    st.dataframe(hip_variants, use_container_width=True)

with col_anom2:
    st.markdown("#### Анализ полных и смысловых дубликатов")
    st.write(f"- Количество полных дубликатов строк: **{duplicate_rows_count}** ({duplicate_rows_count/len(df_raw):.2%}).")
    st.write("- **Причина:** Повторная отправка логов клиентским приложением при сетевых сбоях.")
    st.write("- **Решение:** Дедупликация на этапе инкрементальной загрузки в ODS по составному ключу.")

st.divider()

# 6. Предлагаемый алгоритм очистки данных (Требование ЛР 1)
st.subheader("5. 🛡️ Предлагаемый алгоритм очистки данных")
st.markdown("""
На основании проведенного исследовательского анализа сформирован формализованный алгоритм очистки данных
для реализации в SQL-процедуре инкрементальной загрузки `STAGING` $\\rightarrow$ `ODS`.
""")

cleaning_rules = [
    {
        "Проблема": "Пропущенные значения в названии трека (Track)",
        "Атрибут": "track",
        "Критерий выявления": "IS NULL или TRIM(track) = '' или значение 'nan'",
        "Способ обработки": "Заполнение константой 'unknown'",
        "Обоснование": "Позволяет сохранить факт прослушивания и пользователя без искажения агрегатов"
    },
    {
        "Проблема": "Пропущенные значения в исполнителе (artist)",
        "Атрибут": "artist",
        "Критерий выявления": "IS NULL или TRIM(artist) = '' или значение 'nan'",
        "Способ обработки": "Заполнение константой 'unknown'",
        "Обоснование": "Исполнитель неизвестен, но факт прослушивания валиден для анализа по городам и времени"
    },
    {
        "Проблема": "Пропущенные значения в жанре (genre)",
        "Атрибут": "genre",
        "Критерий выявления": "IS NULL или TRIM(genre) = '' или значение 'nan'",
        "Способ обработки": "Заполнение константой 'unknown'",
        "Обоснование": "Исключает отбрасывание записей; неопределенный жанр объединяется в отдельную категорию"
    },
    {
        "Проблема": "Несогласованные категории жанров (неявные дубли)",
        "Атрибут": "genre",
        "Критерий выявления": "LOWER(genre) IN ('hiphop', 'hip-hop') или 'электроника'",
        "Способ обработки": "Приведение к каноническому виду ('hip', 'electronic')",
        "Обоснование": "Устраняет дробление аналитики одного жанра на несколько строк"
    },
    {
        "Проблема": "Лишние пробелы в названиях и строках",
        "Атрибут": "Все строковые поля",
        "Критерий выявления": "Наличие начальных/конечных пробелов (TRIM)",
        "Способ обработки": "Применение функции TRIM() и нормализации регистра",
        "Обоснование": "Гарантирует однозначность объединения в измерениях DDS"
    },
    {
        "Проблема": "Полные дубликаты записей",
        "Атрибут": "Совокупность ключевых полей",
        "Критерий выявления": "Совпадение user_id, track, artist, genre, city, time, dt",
        "Способ обработки": "Оконная функция ROW_NUMBER() OVER (...) с сохранением одной записи",
        "Обоснование": "Предотвращает задвоение объемов прослушиваний в витринах"
    },
    {
        "Проблема": "Некорректный формат времени",
        "Атрибут": "time",
        "Критерий выявления": "Не соответствует шаблону регулярного выражения HH:MI:SS",
        "Способ обработки": "Приведение к формату TIME либо исключение строки с записью в журнал",
        "Обоснование": "Обеспечивает типизацию данных в реляционной СУБД"
    }
]

df_rules = pd.DataFrame(cleaning_rules)
st.table(df_rules)

st.markdown("""
### 🏁 Итоговые выводы по качеству источника:
1. Исходный датасет содержит **65 079 записей** и обладает высокой пригодностью для построения многослойного DWH.
2. Основные дефекты носят технический характер (пропуски метаданных треков/артистов и сетевые дубликаты) и полностью устраняются разработанным алгоритмом без потери бизнес-информации.
3. Разработанные правила очистки внедрены в PL/pgSQL функцию `public.load_staging_to_ods()`.
""")
