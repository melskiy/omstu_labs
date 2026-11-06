-- ====================================================================
-- 01_init_schema.sql: Создание схем, таблиц SOURCE, STAGING, ODS и журнала
-- ====================================================================

CREATE SCHEMA IF NOT EXISTS source;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS ods;
CREATE SCHEMA IF NOT EXISTS dds;
CREATE SCHEMA IF NOT EXISTS mart;

-- --------------------------------------------------------------------
-- 1. Таблица-источник (SOURCE)
-- Данные в максимально близком к исходному набору виде + синтетическое поле dt
-- --------------------------------------------------------------------
DROP TABLE IF EXISTS source.music_tracks CASCADE;
CREATE TABLE source.music_tracks (
    raw_id BIGINT,
    user_id TEXT,
    track TEXT,
    artist TEXT,
    genre TEXT,
    city TEXT,
    time TEXT,
    day TEXT,
    dt DATE NOT NULL,
    batch_id VARCHAR(64) DEFAULT 'initial',
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_source_dt ON source.music_tracks(dt);
CREATE INDEX IF NOT EXISTS idx_source_batch ON source.music_tracks(batch_id);

-- --------------------------------------------------------------------
-- 2. Таблица промежуточного хранения (STAGING)
-- Хранение данных as is (без изменений) для переноса из источника
-- --------------------------------------------------------------------
DROP TABLE IF EXISTS staging.music_tracks CASCADE;
CREATE TABLE staging.music_tracks (
    raw_id BIGINT,
    user_id TEXT,
    track TEXT,
    artist TEXT,
    genre TEXT,
    city TEXT,
    time TEXT,
    day TEXT,
    dt DATE,
    batch_id VARCHAR(64),
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_staging_dt ON staging.music_tracks(dt);
CREATE INDEX IF NOT EXISTS idx_staging_batch ON staging.music_tracks(batch_id);

-- --------------------------------------------------------------------
-- 3. Журнал качества данных и аудита ETL (ODS Quality Log)
-- --------------------------------------------------------------------
DROP TABLE IF EXISTS ods.data_quality_log CASCADE;
CREATE TABLE ods.data_quality_log (
    log_id BIGSERIAL PRIMARY KEY,
    batch_id VARCHAR(64),
    p_sdt DATE,
    p_edt DATE,
    total_staging_rows INT,
    duplicates_removed INT,
    null_tracks_replaced INT,
    null_artists_replaced INT,
    null_genres_replaced INT,
    invalid_time_rows INT,
    loaded_ods_rows INT,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- --------------------------------------------------------------------
-- 4. Слой детальных очищенных данных (ODS)
-- --------------------------------------------------------------------
DROP TABLE IF EXISTS ods.music_tracks CASCADE;
CREATE TABLE ods.music_tracks (
    track_record_id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    track_name TEXT NOT NULL,
    artist_name TEXT NOT NULL,
    genre_name TEXT NOT NULL,
    city_name TEXT NOT NULL,
    listen_time TIME NOT NULL,
    day_of_week VARCHAR(32) NOT NULL,
    dt DATE NOT NULL,
    batch_id VARCHAR(64),
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ods_dt ON ods.music_tracks(dt);
CREATE INDEX IF NOT EXISTS idx_ods_user ON ods.music_tracks(user_id);
CREATE INDEX IF NOT EXISTS idx_ods_genre ON ods.music_tracks(genre_name);
CREATE INDEX IF NOT EXISTS idx_ods_city ON ods.music_tracks(city_name);
CREATE INDEX IF NOT EXISTS idx_ods_batch ON ods.music_tracks(batch_id);
