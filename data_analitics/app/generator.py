"""
generator.py: Генератор синтетических данных для Лабораторной работы №2.
Создает реалистичные партии данных с атрибутом dt и контролируемыми дефектами
для проверки алгоритмов очистки данных.
"""

import random
import uuid
from datetime import date, timedelta
from typing import List, Tuple
import psycopg2
from psycopg2.extras import execute_values
from faker import Faker

try:
    from app.config import PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASSWORD
except ImportError:
    from config import PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASSWORD

fake = Faker('ru_RU')

# Словари предметной области (на основе датасета и реальных исполнителей)
BASE_ARTISTS = [
    'The Mass Missile', 'Andreas Rönnberg', 'Fire + Ice', 'Mario Lanza',
    'Queen', 'Metallica', 'Daft Punk', 'Eminem', 'Linkin Park', 'The Beatles',
    'Кино', 'Би-2', 'Земфира', 'Сплин', 'Oxxxymiron', 'Баста', 'Скриптонит',
    'Miyagi & Andy Panda', 'Монеточка', 'Макс Корж', 'Coldplay', 'Radiohead'
]

BASE_TRACKS = [
    'Kamigata To Boots', 'Delayed Because of Accident', 'Dragons in the Sunset',
    'Funiculì funiculà', 'Bohemian Rhapsody', 'Enter Sandman', 'Get Lucky',
    'Lose Yourself', 'Numb', 'Yesterday', 'Группа крови', 'Полковнику никто не пишет',
    'Искала', 'Выхода нет', 'Город под подошвой', 'Сансара', 'Положение',
    'I Got Love', 'Каждый раз', 'Жить в кайф', 'Fix You', 'Creep'
]

BASE_GENRES = [
    'rock', 'pop', 'dance', 'electronic', 'hip', 'classical',
    'alternative', 'world', 'ruspop', 'rusrap', 'jazz', 'metal', 'soundtrack', 'folk'
]

# Варианты с дефектами жанров (для проверки очистки)
DEFECTIVE_GENRES = ['hiphop', 'hip-hop', 'электроника', 'soundtracks', '  pop  ', '']

CITIES = ['Moscow', 'Saint-Petersburg', 'Novosibirsk', 'Ekaterinburg', 'Kazan']
DAYS = ['Monday', 'Wednesday', 'Friday']


def get_db_connection():
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD
    )


def generate_synthetic_records(
    count: int,
    start_date: date,
    end_date: date,
    batch_id: str,
    defect_rate: float = 0.05
) -> List[Tuple]:
    """
    Генерирует список синтетических записей с контролируемой долей дефектов.
    """
    records = []
    days_range = (end_date - start_date).days
    if days_range <= 0:
        days_range = 1

    # Пул известных пользователей для реалистичной повторной активности
    user_pool = [uuid.uuid4().hex[:8].upper() for _ in range(max(100, count // 10))]

    for i in range(count):
        raw_id = 1_000_000 + i
        user_id = random.choice(user_pool)
        track = random.choice(BASE_TRACKS)
        artist = random.choice(BASE_ARTISTS)
        genre = random.choice(BASE_GENRES)
        city = random.choice(CITIES)

        # Выбираем случайную дату в заданном диапазоне
        offset = random.randint(0, days_range)
        rec_date = start_date + timedelta(days=offset)
        day_val = rec_date.strftime('%A')

        # Формируем реалистичное время
        hour = random.randint(0, 23)
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        time_val = f"{hour:02d}:{minute:02d}:{second:02d}"

        # Намеренное внесение дефектов качества данных
        if random.random() < defect_rate:
            defect_type = random.choice(['null_track', 'null_artist', 'null_genre', 'defective_genre', 'bad_time'])
            if defect_type == 'null_track':
                track = ''
            elif defect_type == 'null_artist':
                artist = ''
            elif defect_type == 'null_genre':
                genre = ''
            elif defect_type == 'defective_genre':
                genre = random.choice(DEFECTIVE_GENRES)
            elif defect_type == 'bad_time':
                time_val = '99:99:99'

        records.append((
            raw_id,
            user_id,
            track,
            artist,
            genre,
            city,
            time_val,
            day_val,
            rec_date,
            batch_id
        ))

    # Намеренное добавление полных дубликатов для проверки алгоритма дедупликации
    duplicate_count = int(count * (defect_rate / 2))
    for _ in range(duplicate_count):
        src = random.choice(records)
        # Создаем копию с новым raw_id
        dup_rec = (src[0] + 500_000, src[1], src[2], src[3], src[4], src[5], src[6], src[7], src[8], batch_id)
        records.append(dup_rec)

    return records


def load_synthetic_batch_to_source(
    batch_id: str,
    count: int = 5000,
    start_date: date = date(2024, 4, 1),
    end_date: date = date(2024, 4, 30),
    defect_rate: float = 0.05
) -> int:
    """
    Генерирует партию синтетических данных и загружает её в source.music_tracks.
    """
    print(f"[*] Генерация партии '{batch_id}' ({count} записей, период: {start_date} - {end_date})...")
    records = generate_synthetic_records(count, start_date, end_date, batch_id, defect_rate)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Удаляем старую версию этой же партии, если была
            cur.execute("DELETE FROM source.music_tracks WHERE batch_id = %s;", (batch_id,))

            query = """
                INSERT INTO source.music_tracks (
                    raw_id, user_id, track, artist, genre, city, time, day, dt, batch_id
                ) VALUES %s;
            """
            execute_values(cur, query, records, page_size=2000)
            conn.commit()
            print(f"[+] Партия '{batch_id}' ({len(records)} строк с учетом дубликатов) загружена в source.music_tracks.")
    finally:
        conn.close()

    return len(records)


def generate_two_sequential_batches():
    """
    Генерирует и загружает две последовательные партии синтетических данных (АБД Лаб. 2).
    """
    print("[*] Запуск генерации двух последовательных партий данных...")
    b1 = load_synthetic_batch_to_source(
        batch_id='synthetic_batch_1',
        count=5000,
        start_date=date(2024, 4, 1),
        end_date=date(2024, 4, 30),
        defect_rate=0.06
    )
    b2 = load_synthetic_batch_to_source(
        batch_id='synthetic_batch_2',
        count=5000,
        start_date=date(2024, 5, 1),
        end_date=date(2024, 5, 31),
        defect_rate=0.06
    )
    print(f"[+] Обе партии успешно сформированы и сохранены в таблицу-источник. Всего новых записей: {b1 + b2}")


if __name__ == '__main__':
    generate_two_sequential_batches()
