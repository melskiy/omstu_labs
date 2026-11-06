import os
from pathlib import Path
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Определение, находимся ли мы внутри docker-контейнера
IS_IN_DOCKER = os.path.exists('/.dockerenv') or os.getenv('IS_DOCKER', 'false').lower() == 'true'

# PostgreSQL настройки
PG_HOST = os.getenv('POSTGRES_HOST', 'postgres' if IS_IN_DOCKER else 'localhost')
# Если не в docker, а в env указано postgres, подставляем localhost для хоста
if not IS_IN_DOCKER and PG_HOST == 'postgres':
    PG_HOST = os.getenv('HOST_POSTGRES_HOST', 'localhost')

PG_PORT = int(os.getenv('POSTGRES_PORT', 5432))
PG_DB = os.getenv('POSTGRES_DB', 'music_dwh')
PG_USER = os.getenv('POSTGRES_USER', 'dwh_user')
PG_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'dwh_password')

# ClickHouse настройки
CH_HOST = os.getenv('CLICKHOUSE_HOST', 'clickhouse' if IS_IN_DOCKER else 'localhost')
if not IS_IN_DOCKER and CH_HOST == 'clickhouse':
    CH_HOST = os.getenv('HOST_CLICKHOUSE_HOST', 'localhost')

CH_PORT = int(os.getenv('CLICKHOUSE_PORT', 8123))
CH_DB = os.getenv('CLICKHOUSE_DB', 'music_analytics')
CH_USER = os.getenv('CLICKHOUSE_USER', 'default')
CH_PASSWORD = os.getenv('CLICKHOUSE_PASSWORD', 'ch_password')

# Пути к файлам
BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / 'music_project.csv'
SQL_DIR = BASE_DIR / 'sql'
