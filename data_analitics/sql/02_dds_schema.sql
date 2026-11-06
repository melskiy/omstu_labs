-- ====================================================================
-- 02_dds_schema.sql: Схема аналитического хранилища DDS («снежинка»)
-- ====================================================================

-- --------------------------------------------------------------------
-- 1. Измерение артистов (dim_artists)
-- --------------------------------------------------------------------
DROP TABLE IF EXISTS dds.dim_artists CASCADE;
CREATE TABLE dds.dim_artists (
    artist_id SERIAL PRIMARY KEY,
    artist_name VARCHAR(512) NOT NULL UNIQUE
);

-- --------------------------------------------------------------------
-- 2. Измерение музыкальных жанров (dim_genres)
-- --------------------------------------------------------------------
DROP TABLE IF EXISTS dds.dim_genres CASCADE;
CREATE TABLE dds.dim_genres (
    genre_id SERIAL PRIMARY KEY,
    genre_name VARCHAR(256) NOT NULL UNIQUE
);

-- --------------------------------------------------------------------
-- 3. Измерение треков (dim_tracks)
-- Нормализованное измерение: ссылается на артиста и жанр (классическая «снежинка»)
-- --------------------------------------------------------------------
DROP TABLE IF EXISTS dds.dim_tracks CASCADE;
CREATE TABLE dds.dim_tracks (
    track_id SERIAL PRIMARY KEY,
    track_name VARCHAR(512) NOT NULL,
    artist_id INT NOT NULL REFERENCES dds.dim_artists(artist_id) ON DELETE RESTRICT,
    genre_id INT NOT NULL REFERENCES dds.dim_genres(genre_id) ON DELETE RESTRICT,
    CONSTRAINT uq_track_artist_genre UNIQUE (track_name, artist_id, genre_id)
);

CREATE INDEX IF NOT EXISTS idx_dim_tracks_artist ON dds.dim_tracks(artist_id);
CREATE INDEX IF NOT EXISTS idx_dim_tracks_genre ON dds.dim_tracks(genre_id);

-- --------------------------------------------------------------------
-- 4. Измерение пользователей (dim_users)
-- --------------------------------------------------------------------
DROP TABLE IF EXISTS dds.dim_users CASCADE;
CREATE TABLE dds.dim_users (
    user_id SERIAL PRIMARY KEY,
    user_code VARCHAR(64) NOT NULL UNIQUE
);

-- --------------------------------------------------------------------
-- 5. Измерение городов (dim_cities)
-- --------------------------------------------------------------------
DROP TABLE IF EXISTS dds.dim_cities CASCADE;
CREATE TABLE dds.dim_cities (
    city_id SERIAL PRIMARY KEY,
    city_name VARCHAR(128) NOT NULL UNIQUE
);

-- --------------------------------------------------------------------
-- 6. Измерение времени (dim_time)
-- Гранулярность: время суток, часы, дни недели
-- --------------------------------------------------------------------
DROP TABLE IF EXISTS dds.dim_time CASCADE;
CREATE TABLE dds.dim_time (
    time_id SERIAL PRIMARY KEY,
    listen_time TIME NOT NULL,
    hour INT NOT NULL,
    time_of_day VARCHAR(32) NOT NULL,
    day_of_week VARCHAR(32) NOT NULL,
    CONSTRAINT uq_time_day UNIQUE (listen_time, day_of_week)
);

CREATE INDEX IF NOT EXISTS idx_dim_time_hour ON dds.dim_time(hour);

-- --------------------------------------------------------------------
-- 7. Таблица фактов прослушиваний (fact_listens)
-- --------------------------------------------------------------------
DROP TABLE IF EXISTS dds.fact_listens CASCADE;
CREATE TABLE dds.fact_listens (
    listen_id BIGSERIAL PRIMARY KEY,
    track_id INT NOT NULL REFERENCES dds.dim_tracks(track_id) ON DELETE RESTRICT,
    user_id INT NOT NULL REFERENCES dds.dim_users(user_id) ON DELETE RESTRICT,
    city_id INT NOT NULL REFERENCES dds.dim_cities(city_id) ON DELETE RESTRICT,
    time_id INT NOT NULL REFERENCES dds.dim_time(time_id) ON DELETE RESTRICT,
    dt DATE NOT NULL,
    batch_id VARCHAR(64)
);

CREATE INDEX IF NOT EXISTS idx_fact_listens_dt ON dds.fact_listens(dt);
CREATE INDEX IF NOT EXISTS idx_fact_listens_track ON dds.fact_listens(track_id);
CREATE INDEX IF NOT EXISTS idx_fact_listens_user ON dds.fact_listens(user_id);
CREATE INDEX IF NOT EXISTS idx_fact_listens_city ON dds.fact_listens(city_id);
CREATE INDEX IF NOT EXISTS idx_fact_listens_time ON dds.fact_listens(time_id);
CREATE INDEX IF NOT EXISTS idx_fact_listens_batch ON dds.fact_listens(batch_id);
