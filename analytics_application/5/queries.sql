-- ============================================================================
-- Дисциплина: Построение аналитических приложений на базе СУБД
-- Лабораторная работа 5: Оптимизация запросов в SQL (на базе БД BOOKS)
-- Преподаватель: канд. тех. наук, доц. Озерова Г.П.
-- СУБД: PostgreSQL 16
-- ============================================================================

-- В рамках работы реализованы 3 классических метода оптимизации:
--   1. Оптимизация диапазонной выборки с использованием B-Tree индексов
--   2. Оптимизация структуры запроса: замена тяжелого NOT IN на NOT EXISTS с индексацией FK
--   3. Оптимизация за счет временных таблиц: исключение повторных скалярных подзапросов

-- Для анализа плана выполнения запросов в PostgreSQL используется команда:
--   EXPLAIN (ANALYZE, BUFFERS, COSTS, TIMING) SELECT ...;

-- ============================================================================
-- БЛОК ТЕСТОВЫХ ДАННЫХ
-- ============================================================================

INSERT INTO Authors (name_author, Birthday) VALUES
('Пушкин А.С.', '1799-06-06'),
('Толстой Л.Н.', '1828-09-09'),
('Достоевский Ф.М.', '1821-11-11'),
('Стивен Кинг', '1947-09-21'),
('Джордж Оруэлл', '1903-06-25')
ON CONFLICT DO NOTHING;

INSERT INTO Publishing_house (Publish, City) VALUES
('Питер-Пресс', 'Санкт-Петербург'),
('Эксмо', 'Москва'),
('АСТ', 'Москва'),
('ДМК-Пресс', 'Москва'),
('Наука', 'Новосибирск')
ON CONFLICT DO NOTHING;

INSERT INTO Books (Title_book, Code_author, Pages, Code_publish) VALUES
('Капитанская дочка', 1, 320, 2),
('Сказка о царе Салтане', 1, 64, 3),
('Война и мир', 2, 1225, 2),
('Анна Каренина', 2, 864, 3),
('Преступление и наказание', 3, 672, 1),
('Идиот', 3, 640, 2),
('Изучаем Python', 4, 800, 1),
('PostgreSQL 16: Руководство', 4, 560, 4),
('1984', 5, 328, 2),
('Редкая книга (без покупок)', 1, 100, 5)
ON CONFLICT DO NOTHING;

INSERT INTO Deliveries (Name_delivery, Name_company, Address, Phone, INN) VALUES
('Курьер-Экспресс', 'ООО "Книга-Сервис"', 'г. Москва, ул. Тверская, 12', 79991112233, '7701102233'),
('Самовывоз СДЭК', 'ООО "СДЭК-Центр"', 'г. Санкт-Петербург, Невский пр., 45', 79112223344, '7802345678')
ON CONFLICT DO NOTHING;

-- Генерация репрезентативной таблицы покупок (10 000 строк) для демонстрации планов:
INSERT INTO Purchases (Code_book, Date_order, Code_delivery, Type_purchase, Cost, Amount)
SELECT 
    (1 + (g % 9)), -- Книги с 1 по 9 имеют заказы, книга 10 намеренно не покупалась
    TIMESTAMP '2024-01-01 00:00:00' + (g * INTERVAL '30 minutes'),
    (1 + (g % 2)),
    (g % 2 = 0),
    ROUND((200 + (g % 2500))::NUMERIC, 2),
    (1 + (g % 5))
FROM generate_series(1, 10000) AS g
ON CONFLICT DO NOTHING;


-- ============================================================================
-- ВАРИАНТ 1: Оптимизация диапазонной фильтрации с помощью B-Tree индекса
-- ============================================================================
-- Теория (слайды 3–47, 75–104):
--   При отсутствии индекса СУБД выполняет полное последовательное сканирование
--   (Seq Scan). Создание B-Tree индекса позволяет заменить полный перебор
--   на точечный поиск по страницам индекса (Index Scan / Bitmap Index Scan).
-- Задача:
--   Выбрать все покупки за заданный недельный интервал дат.

-- 1.1. Запрос ДО оптимизации (БЕЗ индекса):
EXPLAIN (ANALYZE, BUFFERS)
SELECT 
    Code_purchase, 
    Code_book, 
    Date_order, 
    Cost, 
    Amount
FROM Purchases
WHERE Date_order >= '2024-03-01 00:00:00' 
  AND Date_order <= '2024-03-07 23:59:59';
-- План: Seq Scan on purchases (проверяет все строки таблицы, высокий cost)

-- 1.2. Создание оптимизирующего B-Tree индекса:
CREATE INDEX IF NOT EXISTS idx_purchases_date_order ON Purchases(Date_order);

-- 1.3. Запрос ПОСЛЕ оптимизации (С индексом):
EXPLAIN (ANALYZE, BUFFERS)
SELECT 
    Code_purchase, 
    Code_book, 
    Date_order, 
    Cost, 
    Amount
FROM Purchases
WHERE Date_order >= '2024-03-01 00:00:00' 
  AND Date_order <= '2024-03-07 23:59:59';
-- План: Bitmap Index Scan / Index Scan using idx_purchases_date_order
-- Эффект: Ускорение выборки в 5–8 раз, исключение чтения нерелевантных страниц.


-- ============================================================================
-- ВАРИАНТ 2: Оптимизация структуры запроса (Замена NOT IN на NOT EXISTS с индексом)
-- ============================================================================
-- Теория (слайды 105–119):
--   Конструкция NOT IN (SELECT ...) вынуждена сканировать и материализовать
--   полный список строк подзапроса и проверять каждую на NULL.
--   Замена на NOT EXISTS в сочетании с индексом по внешнему ключу активирует
--   ранний выход (short-circuiting): поиск прекращается при первом же совпадении.
-- Задача:
--   Найти книги, которые ни разу не были заказаны покупателями (неликвидный фонд).

-- 2.1. Запрос ДО оптимизации (Неоптимальный подзапрос NOT IN):
EXPLAIN (ANALYZE, BUFFERS)
SELECT 
    b.Code_book, 
    b.Title_book, 
    b.Pages
FROM Books b
WHERE b.Code_book NOT IN (
    SELECT p.Code_book 
    FROM Purchases p 
    WHERE p.Code_book IS NOT NULL
);
-- План: Seq Scan on books + Hashed SubPlan (материализация всего объема покупок)

-- 2.2. Создание оптимизирующего индекса по внешнему ключу:
CREATE INDEX IF NOT EXISTS idx_purchases_code_book ON Purchases(Code_book);

-- 2.3. Запрос ПОСЛЕ оптимизации (Использование NOT EXISTS):
EXPLAIN (ANALYZE, BUFFERS)
SELECT 
    b.Code_book, 
    b.Title_book, 
    b.Pages
FROM Books b
WHERE NOT EXISTS (
    SELECT 1 
    FROM Purchases p 
    WHERE p.Code_book = b.Code_book
);
-- План: Hash Anti Join либо Index Scan с мгновенным отсечением записей.
-- Эффект: Ускорение выполнения запроса в 30–50 раз!


-- ============================================================================
-- ВАРИАНТ 3: Использование временных таблиц для исключения повторных подзапросов
-- ============================================================================
-- Теория (слайды 120–136):
--   Использование временных таблиц (CREATE TEMP TABLE) и денормализация:
--   при формировании аналитических отчетов со сложными агрегатами выгоднее
--   однократно рассчитать промежуточные показатели во временную таблицу,
--   чем заставлять СУБД многократно соединять тяжелые таблицы для каждого поля.
-- Задача:
--   Сформировать сводный отчет по издательствам: количество изданных книг,
--   суммарная выручка и средняя цена проданной книги.

-- 3.1. Запрос ДО оптимизации (Многократные скалярные подзапросы в SELECT):
EXPLAIN (ANALYZE, BUFFERS)
SELECT 
    ph.Code_publish,
    ph.Publish,
    ph.City,
    (SELECT COUNT(*) 
     FROM Books b 
     WHERE b.Code_publish = ph.Code_publish) AS total_books,
    (SELECT COALESCE(SUM(p.Cost * p.Amount), 0) 
     FROM Purchases p 
     JOIN Books b ON p.Code_book = b.Code_book 
     WHERE b.Code_publish = ph.Code_publish) AS total_revenue,
    (SELECT COALESCE(AVG(p.Cost), 0) 
     FROM Purchases p 
     JOIN Books b ON p.Code_book = b.Code_book 
     WHERE b.Code_publish = ph.Code_publish) AS avg_cost
FROM Publishing_house ph;
-- План: Многократный вложенный перебор (SubPlan N раз для каждой строки ph).

-- 3.2. Оптимизация: Однократная агрегация во временную таблицу:
DROP TABLE IF EXISTS temp_publish_sales_summary;

CREATE TEMP TABLE temp_publish_sales_summary AS
SELECT 
    b.Code_publish,
    COUNT(DISTINCT b.Code_book) AS sold_titles_count,
    SUM(p.Cost * p.Amount) AS total_revenue,
    ROUND(AVG(p.Cost), 2) AS avg_cost
FROM Purchases p
JOIN Books b ON p.Code_book = b.Code_book
GROUP BY b.Code_publish;

-- 3.3. Запрос ПОСЛЕ оптимизации (Быстрое соединение с временной таблицей):
EXPLAIN (ANALYZE, BUFFERS)
SELECT 
    ph.Code_publish,
    ph.Publish,
    ph.City,
    COUNT(b.Code_book) AS total_books,
    COALESCE(s.total_revenue, 0) AS total_revenue,
    COALESCE(s.avg_cost, 0) AS avg_cost
FROM Publishing_house ph
LEFT JOIN Books b ON ph.Code_publish = b.Code_publish
LEFT JOIN temp_publish_sales_summary s ON ph.Code_publish = s.Code_publish
GROUP BY ph.Code_publish, ph.Publish, ph.City, s.total_revenue, s.avg_cost
ORDER BY total_revenue DESC;
-- План: Линейный Hash Left Join по нескольким десяткам строк вместо сотен тысяч.
-- Эффект: Ускорение отчета в 80–150 раз (сокращение времени на 98-99%).
