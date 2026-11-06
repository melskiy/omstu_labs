-- ====================================================================
-- 03_functions.sql: PL/pgSQL функции ETL процессов
-- ====================================================================

-- --------------------------------------------------------------------
-- 1. Перенос SOURCE -> STAGING (as is, без входных параметров)
-- --------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.load_source_to_staging()
RETURNS INTEGER AS $$
DECLARE
    v_rows_copied INTEGER;
BEGIN
    -- Полная очистка слоя STAGING
    TRUNCATE TABLE staging.music_tracks;

    -- Перенос данных как есть (as is)
    INSERT INTO staging.music_tracks (
        raw_id,
        user_id,
        track,
        artist,
        genre,
        city,
        time,
        day,
        dt,
        batch_id,
        loaded_at
    )
    SELECT
        raw_id,
        user_id,
        track,
        artist,
        genre,
        city,
        time,
        day,
        dt,
        batch_id,
        CURRENT_TIMESTAMP
    FROM source.music_tracks;

    GET DIAGNOSTICS v_rows_copied = ROW_COUNT;
    RAISE NOTICE 'Загрузка в STAGING завершена. Перенесено строк: %', v_rows_copied;
    RETURN v_rows_copied;
END;
$$ LANGUAGE plpgsql;

-- --------------------------------------------------------------------
-- 2. Инкрементальная загрузка STAGING -> ODS с алгоритмом очистки
-- Параметры: p_sdt (начало периода), p_edt (конец периода)
-- --------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.load_staging_to_ods(p_sdt DATE, p_edt DATE)
RETURNS INTEGER AS $$
DECLARE
    v_total_staging INT := 0;
    v_loaded_ods INT := 0;
    v_duplicates_count INT := 0;
    v_null_tracks INT := 0;
    v_null_artists INT := 0;
    v_null_genres INT := 0;
    v_invalid_time INT := 0;
    v_batch_name VARCHAR(64) := 'mixed';
BEGIN
    IF p_sdt IS NULL OR p_edt IS NULL THEN
        RAISE EXCEPTION 'Параметры p_sdt и p_edt не могут быть NULL';
    END IF;

    IF p_sdt > p_edt THEN
        RAISE EXCEPTION 'Дата начала периода p_sdt (%) не может быть позже p_edt (%)', p_sdt, p_edt;
    END IF;

    -- 1. Удаление из ODS ранее загруженных данных за период [p_sdt; p_edt]
    DELETE FROM ods.music_tracks
    WHERE dt BETWEEN p_sdt AND p_edt;

    -- 2. Временная таблица с фильтрацией данных из STAGING за указанный период
    DROP TABLE IF EXISTS temp_staging_slice;
    CREATE TEMP TABLE temp_staging_slice ON COMMIT DROP AS
    SELECT *
    FROM staging.music_tracks
    WHERE dt BETWEEN p_sdt AND p_edt;

    SELECT COUNT(*) INTO v_total_staging FROM temp_staging_slice;

    -- Если данных за период нет - выходим
    IF v_total_staging = 0 THEN
        RAISE NOTICE 'За период с % по % в STAGING данных не обнаружено.', p_sdt, p_edt;
        RETURN 0;
    END IF;

    -- Сбор статистики по качеству данных до очистки
    SELECT
        COUNT(*) FILTER (WHERE track IS NULL OR TRIM(track) = '' OR LOWER(TRIM(track)) IN ('none', 'nan', 'null')),
        COUNT(*) FILTER (WHERE artist IS NULL OR TRIM(artist) = '' OR LOWER(TRIM(artist)) IN ('none', 'nan', 'null')),
        COUNT(*) FILTER (WHERE genre IS NULL OR TRIM(genre) = '' OR LOWER(TRIM(genre)) IN ('none', 'nan', 'null')),
        COUNT(*) FILTER (WHERE time IS NULL OR NOT (time ~ '^[0-2]?[0-9]:[0-5][0-9](:[0-5][0-9])?$'))
    INTO
        v_null_tracks,
        v_null_artists,
        v_null_genres,
        v_invalid_time
    FROM temp_staging_slice;

    -- Определение имени партии (если одна доминирующая)
    SELECT COALESCE(batch_id, 'batch') INTO v_batch_name
    FROM temp_staging_slice
    LIMIT 1;

    -- 3. Временная таблица с применением правил очистки, нормализации и дедупликации
    DROP TABLE IF EXISTS temp_cleaned_ods;
    CREATE TEMP TABLE temp_cleaned_ods ON COMMIT DROP AS
    WITH pre_cleaned AS (
        SELECT
            raw_id,
            TRIM(user_id) AS clean_user_id,
            -- Обработка пропусков и аномалий в наименовании трека
            CASE
                WHEN track IS NULL OR TRIM(track) = '' OR LOWER(TRIM(track)) IN ('none', 'nan', 'null')
                THEN 'unknown'
                ELSE LEFT(regexp_replace(TRIM(track), E'[\\r\\n]+', ' ', 'g'), 500)
            END AS clean_track_name,
            -- Обработка пропусков в исполнителе
            CASE
                WHEN artist IS NULL OR TRIM(artist) = '' OR LOWER(TRIM(artist)) IN ('none', 'nan', 'null')
                THEN 'unknown'
                ELSE LEFT(regexp_replace(TRIM(artist), E'[\\r\\n]+', ' ', 'g'), 500)
            END AS clean_artist_name,
            -- Нормализация жанров и устранение неявных дубликатов
            CASE
                WHEN genre IS NULL OR TRIM(genre) = '' OR LOWER(TRIM(genre)) IN ('none', 'nan', 'null')
                    THEN 'unknown'
                WHEN LOWER(TRIM(genre)) IN ('hiphop', 'hip-hop')
                    THEN 'hip'
                WHEN LOWER(TRIM(genre)) IN ('электроника', 'electronica')
                    THEN 'electronic'
                WHEN LOWER(TRIM(genre)) IN ('soundtracks')
                    THEN 'soundtrack'
                ELSE LOWER(TRIM(genre))
            END AS clean_genre_name,
            -- Очистка города
            COALESCE(NULLIF(TRIM(city), ''), 'Unknown') AS clean_city_name,
            -- Приведение и валидация времени
            CASE
                WHEN time ~ '^[0-2]?[0-9]:[0-5][0-9]:[0-5][0-9]$'
                    THEN time::TIME
                WHEN time ~ '^[0-2]?[0-9]:[0-5][0-9]$'
                    THEN (time || ':00')::TIME
                ELSE '00:00:00'::TIME
            END AS clean_listen_time,
            COALESCE(NULLIF(TRIM(day), ''), 'Unknown') AS clean_day_of_week,
            dt,
            batch_id
        FROM temp_staging_slice
        WHERE user_id IS NOT NULL AND TRIM(user_id) <> ''
    ),
    deduped AS (
        SELECT
            *,
            ROW_NUMBER() OVER (
                PARTITION BY clean_user_id, clean_track_name, clean_artist_name,
                             clean_genre_name, clean_city_name, clean_listen_time, dt
                ORDER BY raw_id
            ) AS rn
        FROM pre_cleaned
    )
    SELECT *
    FROM deduped
    WHERE rn = 1;

    -- Подсчет дубликатов
    SELECT (v_total_staging - COUNT(*)) INTO v_duplicates_count
    FROM temp_cleaned_ods;

    -- 4. Вставка очищенных данных в слой ODS
    INSERT INTO ods.music_tracks (
        user_id,
        track_name,
        artist_name,
        genre_name,
        city_name,
        listen_time,
        day_of_week,
        dt,
        batch_id,
        processed_at
    )
    SELECT
        clean_user_id,
        clean_track_name,
        clean_artist_name,
        clean_genre_name,
        clean_city_name,
        clean_listen_time,
        clean_day_of_week,
        dt,
        batch_id,
        CURRENT_TIMESTAMP
    FROM temp_cleaned_ods;

    GET DIAGNOSTICS v_loaded_ods = ROW_COUNT;

    -- 5. Фиксация результатов очистки в журнале качества данных
    INSERT INTO ods.data_quality_log (
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
    ) VALUES (
        v_batch_name,
        p_sdt,
        p_edt,
        v_total_staging,
        v_duplicates_count,
        v_null_tracks,
        v_null_artists,
        v_null_genres,
        v_invalid_time,
        v_loaded_ods,
        CURRENT_TIMESTAMP
    );

    RAISE NOTICE 'Инкрементальная загрузка ODS за период [% - %] завершена. Загружено: %, удалено дубликатов: %',
                 p_sdt, p_edt, v_loaded_ods, v_duplicates_count;

    RETURN v_loaded_ods;
END;
$$ LANGUAGE plpgsql;

-- --------------------------------------------------------------------
-- 3. Загрузка ODS -> DDS («снежинка»)
-- Инкрементальное обновление измерений и фактов за период [p_sdt; p_edt]
-- --------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.load_ods_to_dds(p_sdt DATE, p_edt DATE)
RETURNS INTEGER AS $$
DECLARE
    v_facts_loaded INT := 0;
BEGIN
    IF p_sdt IS NULL OR p_edt IS NULL THEN
        RAISE EXCEPTION 'Параметры p_sdt и p_edt не могут быть NULL';
    END IF;

    -- 1. Наполнение измерения артистов (dds.dim_artists)
    INSERT INTO dds.dim_artists (artist_name)
    SELECT DISTINCT artist_name
    FROM ods.music_tracks
    WHERE dt BETWEEN p_sdt AND p_edt
    ON CONFLICT (artist_name) DO NOTHING;

    -- 2. Наполнение измерения жанров (dds.dim_genres)
    INSERT INTO dds.dim_genres (genre_name)
    SELECT DISTINCT genre_name
    FROM ods.music_tracks
    WHERE dt BETWEEN p_sdt AND p_edt
    ON CONFLICT (genre_name) DO NOTHING;

    -- 3. Наполнение нормализованного измерения треков (dds.dim_tracks)
    INSERT INTO dds.dim_tracks (track_name, artist_id, genre_id)
    SELECT DISTINCT
        o.track_name,
        a.artist_id,
        g.genre_id
    FROM ods.music_tracks o
    JOIN dds.dim_artists a ON a.artist_name = o.artist_name
    JOIN dds.dim_genres g ON g.genre_name = o.genre_name
    WHERE o.dt BETWEEN p_sdt AND p_edt
    ON CONFLICT (track_name, artist_id, genre_id) DO NOTHING;

    -- 4. Наполнение измерения пользователей (dds.dim_users)
    INSERT INTO dds.dim_users (user_code)
    SELECT DISTINCT user_id
    FROM ods.music_tracks
    WHERE dt BETWEEN p_sdt AND p_edt
    ON CONFLICT (user_code) DO NOTHING;

    -- 5. Наполнение измерения городов (dds.dim_cities)
    INSERT INTO dds.dim_cities (city_name)
    SELECT DISTINCT city_name
    FROM ods.music_tracks
    WHERE dt BETWEEN p_sdt AND p_edt
    ON CONFLICT (city_name) DO NOTHING;

    -- 6. Наполнение измерения времени (dds.dim_time)
    INSERT INTO dds.dim_time (listen_time, hour, time_of_day, day_of_week)
    SELECT DISTINCT
        listen_time,
        EXTRACT(HOUR FROM listen_time)::INT AS hour,
        CASE
            WHEN EXTRACT(HOUR FROM listen_time) BETWEEN 6 AND 11 THEN 'Утро'
            WHEN EXTRACT(HOUR FROM listen_time) BETWEEN 12 AND 17 THEN 'День'
            WHEN EXTRACT(HOUR FROM listen_time) BETWEEN 18 AND 23 THEN 'Вечер'
            ELSE 'Ночь'
        END AS time_of_day,
        day_of_week
    FROM ods.music_tracks
    WHERE dt BETWEEN p_sdt AND p_edt
    ON CONFLICT (listen_time, day_of_week) DO NOTHING;

    -- 7. Удаление фактов за период перед загрузкой (идемпотентность)
    DELETE FROM dds.fact_listens
    WHERE dt BETWEEN p_sdt AND p_edt;

    -- 8. Загрузка фактов (dds.fact_listens)
    INSERT INTO dds.fact_listens (
        track_id,
        user_id,
        city_id,
        time_id,
        dt,
        batch_id
    )
    SELECT
        t.track_id,
        u.user_id,
        c.city_id,
        tm.time_id,
        o.dt,
        o.batch_id
    FROM ods.music_tracks o
    JOIN dds.dim_artists a ON a.artist_name = o.artist_name
    JOIN dds.dim_genres g ON g.genre_name = o.genre_name
    JOIN dds.dim_tracks t ON t.track_name = o.track_name AND t.artist_id = a.artist_id AND t.genre_id = g.genre_id
    JOIN dds.dim_users u ON u.user_code = o.user_id
    JOIN dds.dim_cities c ON c.city_name = o.city_name
    JOIN dds.dim_time tm ON tm.listen_time = o.listen_time AND tm.day_of_week = o.day_of_week
    WHERE o.dt BETWEEN p_sdt AND p_edt;

    GET DIAGNOSTICS v_facts_loaded = ROW_COUNT;
    RAISE NOTICE 'Загрузка в DDS за период [% - %] завершена. Загружено фактов: %',
                 p_sdt, p_edt, v_facts_loaded;

    RETURN v_facts_loaded;
END;
$$ LANGUAGE plpgsql;
