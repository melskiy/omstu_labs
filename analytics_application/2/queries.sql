-- ============================================================================
-- Дисциплина: Построение аналитических приложений на базе СУБД
-- Тема: Оконные функции в SQL (на базе БД BOOKS)
-- Преподаватель: канд. тех. наук, доц. Озерова Г.П.
-- СУБД: PostgreSQL 16
-- ============================================================================

-- Оконные функции производят вычисления над набором строк (окном),
-- логически связанных с текущей строкой, сохраняя индивидуальные строки запроса.
-- Синтаксис описания окна:
--   WINDOW имя_окна AS (
--       PARTITION BY столбец_1, ...  -- секционирование данных
--       ORDER BY столбец_sort ...    -- сортировка внутри окна
--       ROWS BETWEEN ...             -- спецификация ограничения строк (фрейм)
--   )

-- ============================================================================
-- БЛОК ТЕСТОВЫХ ДАННЫХ (Для проверки работы запросов)
-- ============================================================================

INSERT INTO Authors (name_author, Birthday) VALUES
('Пушкин А.С.', '1799-06-06'),
('Толстой Л.Н.', '1828-09-09'),
('Достоевский Ф.М.', '1821-11-11'),
('Чехов А.П.', '1860-01-29'),
('Стивен Кинг', '1947-09-21'),
('Джордж Оруэлл', '1903-06-25'),
('Лермонтов М.Ю.', '1814-10-15')
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
('Руслан и Людмила', 1, 160, 2),
('Война и мир', 2, 1225, 2),
('Анна Каренина', 2, 864, 3),
('Преступление и наказание', 3, 672, 1),
('Идиот', 3, 640, 2),
('Изучаем Python', 5, 800, 1),
('PostgreSQL 16: Руководство', 5, 560, 4),
('1984', 6, 328, 2),
('Скотный двор', 6, 160, 3),
('Мцыри', 7, 48, 5)
ON CONFLICT DO NOTHING;

INSERT INTO Deliveries (Name_delivery, Name_company, Address, Phone, INN) VALUES
('Курьер-Экспресс', 'ООО Книга-Сервис', 'г. Москва, ул. Тверская, 12', 79991112233, '7701102233'),
('Самовывоз СДЭК', 'ООО СДЭК-Центр', 'г. Санкт-Петербург, Невский пр., 45', 79112223344, '7802345678'),
('Почта России', 'АО Почта России', 'г. Москва, Варшавское шоссе, 37', 79003334455, '7724261610'),
('ИП Логистик', 'ИП Васильев В.В.', 'г. Омск, пр. Мира, 11', 79045556677, '550123456789')
ON CONFLICT DO NOTHING;

INSERT INTO Purchases (Code_book, Date_order, Code_delivery, Type_purchase, Cost, Amount) VALUES
(1, '2024-03-01 10:00:00', 1, TRUE, 450.00, 2),
(1, '2024-03-03 14:30:00', 1, TRUE, 480.00, 1),
(1, '2024-03-10 11:15:00', 2, TRUE, 500.00, 3),
(3, '2024-03-02 12:00:00', 2, TRUE, 350.00, 4),
(4, '2024-03-04 15:20:00', 1, TRUE, 1200.00, 1),
(4, '2024-03-08 16:45:00', 3, FALSE, 1250.00, 2),
(6, '2024-03-05 17:10:00', 3, TRUE, 750.00, 2),
(8, '2024-03-06 13:00:00', 4, TRUE, 1800.00, 1),
(8, '2024-03-12 18:00:00', 4, TRUE, 1950.00, 2),
(10, '2024-03-07 09:30:00', 2, TRUE, 400.00, 5)
ON CONFLICT DO NOTHING;


-- ============================================================================
-- ЗАПРОС 1: Ранжирование и нумерация книг внутри издательств
-- ============================================================================
-- Цель: Для каждого издательства пронумеровать и проранжировать книги по убыванию
--       количества страниц (Pages), сравнив результаты функций:
--       - ROW_NUMBER() : сквозной номер строки в группе;
--       - RANK()       : ранг с пропуском номеров при совпадающих значениях;
--       - DENSE_RANK() : плотный ранг без пропуска номеров.
-- Демонстрирует: PARTITION BY, ORDER BY и именованное окно WINDOW.

SELECT 
    p.Publish,
    b.Title_book,
    b.Pages,
    ROW_NUMBER() OVER win_pub AS row_num,
    RANK() OVER win_pub AS rnk,
    DENSE_RANK() OVER win_pub AS dense_rnk
FROM Books b
JOIN Publishing_house p ON b.Code_publish = p.Code_publish
WINDOW win_pub AS (
    PARTITION BY b.Code_publish 
    ORDER BY b.Pages DESC
)
ORDER BY p.Publish, row_num;


-- ============================================================================
-- ЗАПРОС 2: Анализ динамики изменения цен с помощью функций смещения LAG и LEAD
-- ============================================================================
-- Цель: Для каждой книги в хронологическом порядке заказов (Date_order):
--       - получить стоимость предыдущего заказа с помощью LAG();
--       - рассчитать разницу в стоимости (текущая цена минус предыдущая);
--       - определить дату следующего заказа с помощью LEAD().
-- Демонстрирует: функции смещения LAG/LEAD и временной анализ внутри секции книги.

SELECT 
    p.Code_purchase,
    b.Title_book,
    p.Date_order,
    p.Cost,
    LAG(p.Cost, 1) OVER win_book AS prev_cost,
    ROUND(p.Cost - LAG(p.Cost, 1) OVER win_book, 2) AS cost_diff,
    LEAD(p.Date_order, 1) OVER win_book AS next_order_date
FROM Purchases p
JOIN Books b ON p.Code_book = b.Code_book
WINDOW win_book AS (
    PARTITION BY p.Code_book 
    ORDER BY p.Date_order
)
ORDER BY p.Code_book, p.Date_order;


-- ============================================================================
-- ЗАПРОС 3: Нарастающий итог выручки и скользящее среднее (ROWS BETWEEN)
-- ============================================================================
-- Цель: Рассчитать для всей хронологии заказов:
--       - суммарную выручку нарастающим итогом (running total) от первого заказа
--         до текущего (ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW);
--       - трехточечное скользящее среднее стоимости заказа (предыдущий, текущий 
--         и следующий заказы: ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING).
-- Демонстрирует: спецификацию ограничения строк (фреймы окна ROWS BETWEEN).

SELECT 
    p.Code_purchase,
    p.Date_order,
    b.Title_book,
    (p.Cost * p.Amount) AS total_order_cost,
    SUM(p.Cost * p.Amount) OVER (
        ORDER BY p.Date_order 
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS running_total_revenue,
    ROUND(AVG(p.Cost) OVER (
        ORDER BY p.Date_order 
        ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING
    ), 2) AS moving_avg_cost
FROM Purchases p
JOIN Books b ON p.Code_book = b.Code_book
ORDER BY p.Date_order;


-- ============================================================================
-- ЗАПРОС 4: Крайние значения группы (FIRST_VALUE, LAST_VALUE) и процентная доля
-- ============================================================================
-- Цель: Для каждого автора:
--       - вывести самую толстую книгу автора (FIRST_VALUE);
--       - вывести самую тонкую книгу автора (LAST_VALUE);
--       - подсчитать общее количество страниц всех книг автора;
--       - вычислить процентную долю объема текущей книги от общего числа страниц автора.
-- Демонстрирует: FIRST_VALUE, LAST_VALUE с полным фреймом
-- (ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) и расчет процентных долей.

SELECT 
    a.name_author,
    b.Title_book,
    b.Pages,
    FIRST_VALUE(b.Title_book) OVER win_auth AS thickest_book,
    LAST_VALUE(b.Title_book) OVER win_auth AS thinnest_book,
    SUM(b.Pages) OVER (PARTITION BY b.Code_author) AS author_total_pages,
    ROUND((b.Pages::NUMERIC / SUM(b.Pages) OVER (PARTITION BY b.Code_author)) * 100, 2) AS page_share_percent
FROM Books b
JOIN Authors a ON b.Code_author = a.Code_author
WINDOW win_auth AS (
    PARTITION BY b.Code_author 
    ORDER BY b.Pages DESC 
    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
)
ORDER BY a.name_author, b.Pages DESC;


-- ============================================================================
-- ЗАПРОС 5: Фильтрация Топ-2 самых дорогих заказов по службам доставки (CTE + ROW_NUMBER)
-- ============================================================================
-- Цель: Для каждой компании доставки (Deliveries) отобрать Топ-2 самых крупных заказа
--       по итоговой стоимости (Cost * Amount).
--       Оконные функции вычисляются после условий WHERE/HAVING, поэтому фильтрация
--       по результату оконной функции выполняется через CTE (WITH ... AS (...)).
-- Демонстрирует: структуру запроса с табличными выражениями (CTE) и фильтрацию рангов.

WITH RankedPurchases AS (
    SELECT 
        d.Name_company,
        d.Name_delivery,
        b.Title_book,
        p.Date_order,
        p.Cost,
        p.Amount,
        (p.Cost * p.Amount) AS total_sum,
        ROW_NUMBER() OVER win_del AS rnk
    FROM Purchases p
    JOIN Deliveries d ON p.Code_delivery = d.Code_delivery
    JOIN Books b ON p.Code_book = b.Code_book
    WINDOW win_del AS (
        PARTITION BY p.Code_delivery 
        ORDER BY (p.Cost * p.Amount) DESC
    )
)
SELECT 
    Name_company,
    Name_delivery,
    Title_book,
    Date_order,
    total_sum,
    rnk
FROM RankedPurchases
WHERE rnk <= 2
ORDER BY Name_company, rnk;
