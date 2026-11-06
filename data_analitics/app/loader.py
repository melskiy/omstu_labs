"""
loader.py: Загрузка исходных данных music_project.csv в таблицу source.music_tracks.
Формирует синтетическое поле dt (DATE), согласованное с днем недели Day.
"""

import csv
import sys
from datetime import date, timedelta
from pathlib import Path
import psycopg2
from psycopg2.extras import execute_values

try:
    from app.config import PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASSWORD, CSV_PATH
except ImportError:
    from config import PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASSWORD, CSV_PATH


def get_db_connection():
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD
    )


def generate_day_to_dates_mapping(start_date: date, end_date: date) -> dict:
    """
    Генерирует списки реальных календарных дат для каждого дня недели
    в заданном диапазоне (Monday, Wednesday, Friday).
    """
    mapping = {
        'Monday': [],
        'Wednesday': [],
        'Friday': [],
        'Tuesday': [],
        'Thursday': [],
        'Saturday': [],
        'Sunday': []
    }
    
    current = start_date
    while current <= end_date:
        day_name = current.strftime('%A')
        if day_name in mapping:
            mapping[day_name].append(current)
        current += timedelta(days=1)
        
    return mapping


def load_csv_to_source(csv_path: Path = CSV_PATH, batch_id: str = 'initial_load', 
                        start_date: date = date(2024, 1, 1), end_date: date = date(2024, 3, 31)):
    """
    Читает music_project.csv и загружает в таблицу source.music_tracks.
    Каждой записи присваивается календарная дата dt, соответствующая дню недели Day.
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"Файл {csv_path} не найден!")

    print(f"[*] Начало загрузки исходных данных из {csv_path}...")
    day_mapping = generate_day_to_dates_mapping(start_date, end_date)
    
    # Счетчики дат для равномерного распределения
    counters = {k: 0 for k in day_mapping.keys()}
    
    records = []
    with open(csv_path, mode='r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        # Ожидаемый заголовок: ['', '  userID', 'Track', 'artist', 'genre', '  City  ', 'time', 'Day']
        
        for idx, row in enumerate(reader):
            if not row or len(row) < 8:
                continue
                
            raw_id = row[0].strip() or str(idx)
            user_id = row[1].strip()
            track = row[2].strip()
            artist = row[3].strip()
            genre = row[4].strip()
            city = row[5].strip()
            time_val = row[6].strip()
            day_val = row[7].strip()

            # Определение даты на основе дня недели
            avail_dates = day_mapping.get(day_val, [])
            if avail_dates:
                assigned_dt = avail_dates[counters[day_val] % len(avail_dates)]
                counters[day_val] += 1
            else:
                # Резервная дата, если день не опознан
                assigned_dt = start_date

            records.append((
                int(raw_id) if raw_id.isdigit() else idx,
                user_id,
                track,
                artist,
                genre,
                city,
                time_val,
                day_val,
                assigned_dt,
                batch_id
            ))

    print(f"[*] Прочитано {len(records)} записей из CSV. Запись в БД PostgreSQL...")

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Очищаем таблицу source для партии initial_load
            if batch_id == 'initial_load':
                cur.execute("DELETE FROM source.music_tracks WHERE batch_id = %s;", (batch_id,))

            query = """
                INSERT INTO source.music_tracks (
                    raw_id, user_id, track, artist, genre, city, time, day, dt, batch_id
                ) VALUES %s;
            """
            
            # Вставляем пачками по 5000 записей
            page_size = 5000
            for i in range(0, len(records), page_size):
                chunk = records[i:i + page_size]
                execute_values(cur, query, chunk, page_size=page_size)
                print(f"    Загружено {min(i + page_size, len(records))} / {len(records)} строк...")

            conn.commit()
            print(f"[+] Успешно загружено {len(records)} записей в source.music_tracks с партией '{batch_id}'.")
    finally:
        conn.close()

    return len(records)


if __name__ == '__main__':
    load_csv_to_source()
