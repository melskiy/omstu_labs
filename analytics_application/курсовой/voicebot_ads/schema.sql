-- ============================================================
-- База данных: Голосовой бот аварийно-диспетчерской службы
-- СУБД: PostgreSQL
-- Студент: Малицкий Александр Сергеевич, ФИТм-251
-- ============================================================

-- Удаление таблиц (если существуют) в порядке зависимостей
DROP TABLE IF EXISTS CallLogs CASCADE;
DROP TABLE IF EXISTS Calls CASCADE;
DROP TABLE IF EXISTS Incidents CASCADE;
DROP TABLE IF EXISTS Operators CASCADE;
DROP TABLE IF EXISTS Statuses CASCADE;
DROP TABLE IF EXISTS IncidentTypes CASCADE;

-- ------------------------------------------------------------
-- 1. Справочник статусов обращений
-- ------------------------------------------------------------
CREATE TABLE Statuses (
    status_id   SERIAL PRIMARY KEY,
    status_name VARCHAR(50) NOT NULL UNIQUE,
    description VARCHAR(200)
);

-- ------------------------------------------------------------
-- 2. Справочник типов инцидентов
-- ------------------------------------------------------------
CREATE TABLE IncidentTypes (
    type_id     SERIAL PRIMARY KEY,
    type_name   VARCHAR(100) NOT NULL UNIQUE,
    priority    SMALLINT NOT NULL DEFAULT 2
                CONSTRAINT chk_priority CHECK (priority BETWEEN 1 AND 3)
                -- 1 = Высокий, 2 = Средний, 3 = Низкий
);

-- ------------------------------------------------------------
-- 3. Справочник операторов / диспетчеров
-- ------------------------------------------------------------
CREATE TABLE Operators (
    operator_id   SERIAL PRIMARY KEY,
    full_name     VARCHAR(100) NOT NULL,
    phone         CHAR(11),
    shift         VARCHAR(20) NOT NULL DEFAULT 'День',
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT chk_shift CHECK (shift IN ('День', 'Ночь', 'Сутки'))
);

-- ------------------------------------------------------------
-- 4. Таблица инцидентов
-- ------------------------------------------------------------
CREATE TABLE Incidents (
    incident_id   SERIAL PRIMARY KEY,
    type_id       INT NOT NULL
                  REFERENCES IncidentTypes(type_id) ON DELETE RESTRICT,
    address       VARCHAR(200) NOT NULL,
    description   TEXT,
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    closed_at     TIMESTAMP,
    status_id     INT NOT NULL
                  REFERENCES Statuses(status_id) ON DELETE RESTRICT,
    operator_id   INT
                  REFERENCES Operators(operator_id) ON DELETE SET NULL,
    CONSTRAINT chk_dates CHECK (closed_at IS NULL OR closed_at >= created_at)
);

-- ------------------------------------------------------------
-- 5. Центральная таблица звонков (обращений через бота)
-- ------------------------------------------------------------
CREATE TABLE Calls (
    call_id        SERIAL PRIMARY KEY,
    caller_phone   CHAR(11) NOT NULL,
    received_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    duration_sec   INT CONSTRAINT chk_duration CHECK (duration_sec >= 0),
    incident_id    INT
                   REFERENCES Incidents(incident_id) ON DELETE SET NULL,
    status_id      INT NOT NULL
                   REFERENCES Statuses(status_id) ON DELETE RESTRICT,
    bot_handled    BOOLEAN NOT NULL DEFAULT TRUE
                   -- TRUE = бот обработал полностью, FALSE = переведён оператору
);

-- ------------------------------------------------------------
-- 6. История действий бота (лог диалога)
-- ------------------------------------------------------------
CREATE TABLE CallLogs (
    log_id      SERIAL PRIMARY KEY,
    call_id     INT NOT NULL
                REFERENCES Calls(call_id) ON DELETE CASCADE,
    log_time    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    step_name   VARCHAR(100) NOT NULL,
    bot_phrase  TEXT,
    user_input  TEXT
);

-- PostgreSQL проверяет данные другой таблицы через триггер.
CREATE OR REPLACE FUNCTION check_call_log_time() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM Calls
        WHERE call_id = NEW.call_id AND received_at > NEW.log_time
    ) THEN
        RAISE EXCEPTION 'Реплика записана раньше начала звонка %', NEW.call_id;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER chk_log_time_order
BEFORE INSERT OR UPDATE OF call_id, log_time ON CallLogs
FOR EACH ROW EXECUTE FUNCTION check_call_log_time();

-- ============================================================
-- ЗАПОЛНЕНИЕ СПРАВОЧНИКОВ
-- ============================================================

INSERT INTO Statuses (status_name, description) VALUES
    ('Принят',      'Звонок принят ботом, ожидает обработки'),
    ('В работе',    'Инцидент передан оператору / бригаде'),
    ('Выполнен',    'Инцидент устранён'),
    ('Отменён',     'Обращение отменено'),
    ('Дублирующий', 'Повторное сообщение о том же инциденте');

INSERT INTO IncidentTypes (type_name, priority) VALUES
    ('Авария на газопроводе',         1),
    ('Прорыв водопровода',            1),
    ('Отключение электроэнергии',     2),
    ('Засор канализации',             3),
    ('Повреждение теплосети',         1),
    ('Неисправность лифта',           2),
    ('Пожар / задымление',            1),
    ('Другое',                        3);

INSERT INTO Operators (full_name, phone, shift) VALUES
    ('Смирнова Ольга Ивановна',  '79131110001', 'День'),
    ('Петров Дмитрий Алексеевич','79131110002', 'Ночь'),
    ('Козлова Анна Николаевна',  '79131110003', 'Сутки'),
    ('Иванов Сергей Владимирович','79131110004', 'День');

-- ============================================================
-- ТЕСТОВЫЕ ДАННЫЕ
-- ============================================================

INSERT INTO Incidents (type_id, address, description, status_id, operator_id,
                       created_at, closed_at) VALUES
    (1, 'ул. Ленина, 42',       'Запах газа в подъезде',         2, 1, '2026-10-01 08:12:00', NULL),
    (2, 'пр. Мира, 7',          'Прорыв трубы в подвале',         3, 2, '2026-10-01 09:00:00', '2026-10-01 11:30:00'),
    (3, 'ул. Гагарина, 15',     'Отключение 3 домов',             3, 1, '2026-10-02 14:00:00', '2026-10-02 18:00:00'),
    (6, 'ул. Кирова, 3',        'Лифт не работает (этаж 9)',      2, 3, '2026-10-03 10:05:00', NULL),
    (1, 'ул. Маркса, 88',       'Утечка газа во дворе',           1, NULL,'2026-10-04 07:55:00', NULL),
    (5, 'пр. Комсомольский, 21','Порыв теплотрассы',              2, 4, '2026-10-05 06:30:00', NULL),
    (7, 'ул. Пушкина, 1',       'Задымление на 5 этаже',          3, 2, '2026-10-05 20:00:00', '2026-10-05 20:45:00'),
    (4, 'ул. Декабристов, 55',  'Засор стояка',                   3, 3, '2026-10-06 11:00:00', '2026-10-06 14:00:00'),
    (2, 'ул. Добролюбова, 10',  'Вода в подвале',                 2, 1, '2026-10-07 09:15:00', NULL),
    (8, 'ул. Звёздная, 2',      'Вопрос по квитанции',            4, NULL,'2026-10-07 13:30:00', '2026-10-07 13:35:00');

INSERT INTO Calls (caller_phone, received_at, duration_sec, incident_id, status_id, bot_handled) VALUES
    ('79131234567', '2026-10-01 08:10:00',  180, 1, 2, FALSE),
    ('79135556677', '2026-10-01 08:58:00',   95, 2, 3, TRUE),
    ('79133334455', '2026-10-02 13:55:00',  210, 3, 3, FALSE),
    ('79139998877', '2026-10-03 10:00:00',   60, 4, 2, TRUE),
    ('79136661122', '2026-10-04 07:50:00',  130, 5, 1, TRUE),
    ('79137773344', '2026-10-05 06:25:00',  245, 6, 2, FALSE),
    ('79132223344', '2026-10-05 19:58:00',   75, 7, 3, TRUE),
    ('79134445566', '2026-10-06 10:55:00',   90, 8, 3, TRUE),
    ('79138887766', '2026-10-07 09:10:00',  155, 9, 2, TRUE),
    ('79131112233', '2026-10-07 13:28:00',   40,10, 4, TRUE);

INSERT INTO CallLogs (call_id, log_time, step_name, bot_phrase, user_input) VALUES
    (1,'2026-10-01 08:10:05','Приветствие',    'Здравствуйте! Аварийная служба. Опишите проблему.',           'Пахнет газом'),
    (1,'2026-10-01 08:10:30','Уточнение адреса','Укажите адрес, пожалуйста.',                                 'Ленина 42'),
    (1,'2026-10-01 08:11:00','Перевод оператору','Соединяю с оператором. Оставайтесь на линии.',              NULL),
    (2,'2026-10-01 08:58:05','Приветствие',    'Здравствуйте! Аварийная служба. Опишите проблему.',           'Прорыв трубы'),
    (2,'2026-10-01 08:58:40','Уточнение адреса','Укажите адрес.',                                             'Мира 7, подвал'),
    (2,'2026-10-01 08:59:15','Подтверждение',  'Заявка принята. Бригада выедет в течение 30 минут. Спасибо.', NULL),
    (5,'2026-10-04 07:50:10','Приветствие',    'Здравствуйте! Аварийная служба. Опишите проблему.',           'Газ во дворе'),
    (5,'2026-10-04 07:51:00','Уточнение адреса','Укажите адрес.',                                             'Маркса 88'),
    (5,'2026-10-04 07:51:40','Подтверждение',  'Заявка зарегистрирована. Аварийная бригада уже направлена.',  NULL);

-- ============================================================
-- АНАЛИТИЧЕСКИЕ ЗАПРОСЫ
-- ============================================================

-- ЗАПРОС 1: Статистика звонков по типам инцидентов
CREATE VIEW v_calls_by_type AS
SELECT
    it.type_name                        AS "Тип инцидента",
    it.priority                         AS "Приоритет",
    COUNT(c.call_id)                    AS "Количество звонков",
    SUM(CASE WHEN c.bot_handled THEN 1 ELSE 0 END) AS "Обработано ботом",
    ROUND(AVG(c.duration_sec), 1)       AS "Среднее время звонка (сек)"
FROM Calls c
JOIN Incidents i  ON c.incident_id = i.incident_id
JOIN IncidentTypes it ON i.type_id = it.type_id
GROUP BY it.type_name, it.priority
ORDER BY it.priority, COUNT(c.call_id) DESC;

-- ЗАПРОС 2: Список инцидентов с фильтрацией по статусу
CREATE VIEW v_incidents_with_status AS
SELECT
    i.incident_id                       AS "ID инцидента",
    it.type_name                        AS "Тип",
    i.address                           AS "Адрес",
    i.description                       AS "Описание",
    s.status_name                       AS "Статус",
    o.full_name                         AS "Оператор",
    i.created_at                        AS "Дата создания",
    i.closed_at                         AS "Дата закрытия",
    CASE WHEN i.closed_at IS NOT NULL
         THEN EXTRACT(EPOCH FROM (i.closed_at - i.created_at))/3600
         ELSE NULL
    END                                 AS "Время решения (ч)"
FROM Incidents i
JOIN IncidentTypes it ON i.type_id = it.type_id
JOIN Statuses s       ON i.status_id = s.status_id
LEFT JOIN Operators o ON i.operator_id = o.operator_id
ORDER BY i.created_at DESC;

-- ЗАПРОС 3: Среднее время обработки звонка ботом
CREATE VIEW v_avg_bot_handling AS
SELECT
    CASE WHEN bot_handled THEN 'Бот' ELSE 'Оператор' END AS "Обработчик",
    COUNT(*)                                AS "Количество",
    ROUND(AVG(duration_sec), 1)             AS "Среднее время (сек)",
    MIN(duration_sec)                       AS "Мин. время (сек)",
    MAX(duration_sec)                       AS "Макс. время (сек)"
FROM Calls
GROUP BY bot_handled;

-- ЗАПРОС 4: Дашборд — общая статистика за период
CREATE VIEW v_dashboard AS
SELECT
    COUNT(DISTINCT c.call_id)            AS "Всего звонков",
    COUNT(DISTINCT i.incident_id)        AS "Всего инцидентов",
    SUM(CASE WHEN s.status_name = 'В работе'  THEN 1 ELSE 0 END) AS "Открытых инцидентов",
    SUM(CASE WHEN s.status_name = 'Выполнен'  THEN 1 ELSE 0 END) AS "Закрытых инцидентов",
    ROUND(AVG(c.duration_sec), 1)        AS "Среднее время звонка (сек)",
    SUM(CASE WHEN c.bot_handled THEN 1 ELSE 0 END) AS "Обработано ботом",
    ROUND(100.0 * SUM(CASE WHEN c.bot_handled THEN 1 ELSE 0 END) / COUNT(c.call_id), 1)
                                         AS "Доля бота (%)"
FROM Calls c
LEFT JOIN Incidents i ON c.incident_id = i.incident_id
LEFT JOIN Statuses s  ON i.status_id = s.status_id;
