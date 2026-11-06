-- ====================================================================
-- 04_mart.sql: Аналитическая витрина "Популярность жанров по городам и периодам"
-- ====================================================================

DROP TABLE IF EXISTS mart.city_genre_popularity CASCADE;
CREATE TABLE mart.city_genre_popularity (
    mart_id BIGSERIAL PRIMARY KEY,
    dt DATE NOT NULL,
    year INT NOT NULL,
    month INT NOT NULL,
    day_of_week VARCHAR(32) NOT NULL,
    city_name VARCHAR(128) NOT NULL,
    genre_name VARCHAR(256) NOT NULL,
    top_artist VARCHAR(512),
    listens_count BIGINT NOT NULL,
    unique_users_count BIGINT NOT NULL,
    morning_listens BIGINT NOT NULL,
    day_listens BIGINT NOT NULL,
    evening_listens BIGINT NOT NULL,
    night_listens BIGINT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_mart_period_city_genre UNIQUE (dt, city_name, genre_name)
);

CREATE INDEX IF NOT EXISTS idx_mart_dt ON mart.city_genre_popularity(dt);
CREATE INDEX IF NOT EXISTS idx_mart_city ON mart.city_genre_popularity(city_name);
CREATE INDEX IF NOT EXISTS idx_mart_genre ON mart.city_genre_popularity(genre_name);

-- --------------------------------------------------------------------
-- Функция пересчета аналитической витрины из слоя DDS
-- --------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.refresh_mart(p_sdt DATE, p_edt DATE)
RETURNS INTEGER AS $$
DECLARE
    v_rows_inserted INT := 0;
BEGIN
    IF p_sdt IS NULL OR p_edt IS NULL THEN
        RAISE EXCEPTION 'Параметры p_sdt и p_edt не могут быть NULL';
    END IF;

    -- 1. Удаление существующих записей витрины за указанный период
    DELETE FROM mart.city_genre_popularity
    WHERE dt BETWEEN p_sdt AND p_edt;

    -- 2. Расчет агрегированных аналитических показателей
    WITH base_data AS (
        SELECT
            f.dt,
            EXTRACT(YEAR FROM f.dt)::INT AS year,
            EXTRACT(MONTH FROM f.dt)::INT AS month,
            tm.day_of_week,
            c.city_name,
            g.genre_name,
            a.artist_name,
            f.user_id,
            tm.time_of_day
        FROM dds.fact_listens f
        JOIN dds.dim_tracks t ON t.track_id = f.track_id
        JOIN dds.dim_artists a ON a.artist_id = t.artist_id
        JOIN dds.dim_genres g ON g.genre_id = t.genre_id
        JOIN dds.dim_cities c ON c.city_id = f.city_id
        JOIN dds.dim_time tm ON tm.time_id = f.time_id
        WHERE f.dt BETWEEN p_sdt AND p_edt
    ),
    artist_ranked AS (
        SELECT
            dt,
            city_name,
            genre_name,
            artist_name,
            COUNT(*) AS artist_listens,
            ROW_NUMBER() OVER(
                PARTITION BY dt, city_name, genre_name
                ORDER BY COUNT(*) DESC, artist_name ASC
            ) AS rn
        FROM base_data
        GROUP BY dt, city_name, genre_name, artist_name
    ),
    aggregated AS (
        SELECT
            b.dt,
            b.year,
            b.month,
            b.day_of_week,
            b.city_name,
            b.genre_name,
            COUNT(*) AS listens_count,
            COUNT(DISTINCT b.user_id) AS unique_users_count,
            COUNT(*) FILTER (WHERE b.time_of_day = 'Утро') AS morning_listens,
            COUNT(*) FILTER (WHERE b.time_of_day = 'День') AS day_listens,
            COUNT(*) FILTER (WHERE b.time_of_day = 'Вечер') AS evening_listens,
            COUNT(*) FILTER (WHERE b.time_of_day = 'Ночь') AS night_listens
        FROM base_data b
        GROUP BY b.dt, b.year, b.month, b.day_of_week, b.city_name, b.genre_name
    )
    INSERT INTO mart.city_genre_popularity (
        dt,
        year,
        month,
        day_of_week,
        city_name,
        genre_name,
        top_artist,
        listens_count,
        unique_users_count,
        morning_listens,
        day_listens,
        evening_listens,
        night_listens,
        updated_at
    )
    SELECT
        agg.dt,
        agg.year,
        agg.month,
        agg.day_of_week,
        agg.city_name,
        agg.genre_name,
        COALESCE(ar.artist_name, 'unknown') AS top_artist,
        agg.listens_count,
        agg.unique_users_count,
        agg.morning_listens,
        agg.day_listens,
        agg.evening_listens,
        agg.night_listens,
        CURRENT_TIMESTAMP
    FROM aggregated agg
    LEFT JOIN artist_ranked ar
      ON ar.dt = agg.dt
     AND ar.city_name = agg.city_name
     AND ar.genre_name = agg.genre_name
     AND ar.rn = 1;

    GET DIAGNOSTICS v_rows_inserted = ROW_COUNT;
    RAISE NOTICE 'Витрина mart.city_genre_popularity обновлена за [% - %]. Вставлено строк: %',
                 p_sdt, p_edt, v_rows_inserted;

    RETURN v_rows_inserted;
END;
$$ LANGUAGE plpgsql;
