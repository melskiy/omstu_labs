-- Запустить после schema.sql. Запросы 1–4 определены там как представления.

-- Запрос 5. Распределение инцидентов по статусам
SELECT s.status_name AS status,
       COUNT(i.incident_id) AS incident_count
FROM Statuses s
LEFT JOIN Incidents i ON i.status_id = s.status_id
GROUP BY s.status_id, s.status_name
ORDER BY incident_count DESC, s.status_id;

-- Запрос 6. Нагрузка по часам суток
SELECT EXTRACT(HOUR FROM received_at)::int AS call_hour,
       COUNT(*) AS call_count
FROM Calls
GROUP BY call_hour
ORDER BY call_count DESC, call_hour;

-- Запрос 7. Критические инциденты, открытые на контрольную дату
WITH cutoff(ts) AS (VALUES (TIMESTAMP '2026-10-07 14:00'))
SELECT i.incident_id, i.address,
       cutoff.ts - i.created_at AS open_for
FROM Incidents i
JOIN IncidentTypes t ON t.type_id = i.type_id
CROSS JOIN cutoff
WHERE t.priority = 1 AND i.created_at <= cutoff.ts
  AND (i.closed_at IS NULL OR i.closed_at > cutoff.ts)
ORDER BY open_for DESC, i.incident_id;

-- Запрос 8. Нагрузка диспетчеров по назначенным заявкам
SELECT o.full_name, o.shift,
       COUNT(i.incident_id) AS assigned,
       COUNT(*) FILTER (WHERE s.status_name = 'В работе') AS in_progress,
       COUNT(*) FILTER (WHERE s.status_name = 'Выполнен') AS completed
FROM Operators o
LEFT JOIN Incidents i ON i.operator_id = o.operator_id
LEFT JOIN Statuses s ON s.status_id = i.status_id
GROUP BY o.operator_id, o.full_name, o.shift
ORDER BY assigned DESC, o.operator_id;

-- Запрос 9. Накопительное число звонков по дням
WITH daily AS (
    SELECT received_at::date AS call_day, COUNT(*) AS call_count
    FROM Calls
    GROUP BY call_day
)
SELECT call_day, call_count,
       SUM(call_count) OVER (ORDER BY call_day) AS running_total
FROM daily
ORDER BY call_day;

-- Запрос 10. Звонки дольше среднего для своего обработчика
SELECT c.call_id, c.bot_handled, c.duration_sec
FROM Calls c
WHERE c.duration_sec > (
    SELECT AVG(peer.duration_sec)
    FROM Calls peer
    WHERE peer.bot_handled = c.bot_handled
)
ORDER BY c.duration_sec DESC, c.call_id;

-- Запрос 11. Продолжительность записанной части диалога
SELECT call_id, COUNT(*) AS step_count,
       MAX(log_time) - MIN(log_time) AS logged_span
FROM CallLogs
GROUP BY call_id
HAVING COUNT(*) >= 2
ORDER BY logged_span DESC, call_id;

-- Запрос 12. Медианное время устранения по категориям
SELECT t.type_name, COUNT(*) AS completed,
       percentile_cont(0.5) WITHIN GROUP (
           ORDER BY i.closed_at - i.created_at
       ) AS median_resolution
FROM Incidents i
JOIN IncidentTypes t ON t.type_id = i.type_id
JOIN Statuses s ON s.status_id = i.status_id
WHERE s.status_name = 'Выполнен' AND i.closed_at IS NOT NULL
GROUP BY t.type_id, t.type_name
ORDER BY median_resolution DESC, t.type_id;

-- Запрос 13. Интервал от первого звонка до регистрации инцидента
WITH first_call AS (
    SELECT incident_id, MIN(received_at) AS first_received
    FROM Calls
    WHERE incident_id IS NOT NULL
    GROUP BY incident_id
)
SELECT i.incident_id, i.address,
       i.created_at - f.first_received AS registration_delay
FROM Incidents i
JOIN first_call f ON f.incident_id = i.incident_id
WHERE f.first_received <= i.created_at
ORDER BY registration_delay DESC, i.incident_id;

-- Запрос 14. Звонки, обработанные ботом, без записей диалога
SELECT c.call_id, c.received_at
FROM Calls c
WHERE c.bot_handled AND NOT EXISTS (
    SELECT 1 FROM CallLogs l WHERE l.call_id = c.call_id
)
ORDER BY c.received_at, c.call_id;

-- Запрос 15. Сводка звонков за период через хранимую процедуру
CREATE OR REPLACE PROCEDURE summarize_calls(
    IN period_start timestamp, IN period_end timestamp,
    INOUT total_calls bigint, INOUT bot_calls bigint
)
LANGUAGE plpgsql AS $$
BEGIN
    SELECT COUNT(*), COUNT(*) FILTER (WHERE bot_handled)
    INTO total_calls, bot_calls
    FROM Calls
    WHERE received_at >= period_start AND received_at < period_end;
END;
$$;

CALL summarize_calls('2026-10-01', '2026-10-08', NULL, NULL);
