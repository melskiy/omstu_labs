-- ============================================================================
-- Дисциплина: Построение аналитических приложений на базе СУБД
-- Тема: Строковые функции в SQL (на базе БД BOOKS)
-- Преподаватель: канд. тех. наук, доц. Озерова Г.П.
-- СУБД: PostgreSQL 16
-- ============================================================================

-- В рамках темы рассматриваются строковые функции преобразования, очистки,
-- форматирования, поиска, извлечения подстрок и групповой агрегации:
--   TRIM, LTRIM, RTRIM, LENGTH
--   UPPER, LOWER, INITCAP
--   LEFT, RIGHT, SUBSTRING
--   CONCAT, CONCAT_WS, оператор ||
--   POSITION, STRPOS, REPLACE
--   SPLIT_PART, LPAD, RPAD
--   STRING_AGG

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

-- Добавляем издательства со случайными пробелами для демонстрации TRIM
INSERT INTO Publishing_house (Publish, City) VALUES
('  Питер-Пресс  ', 'Санкт-Петербург'),
(' Эксмо ', 'Москва'),
('АСТ', ' Москва '),
('ДМК-Пресс', '  Москва  '),
('Наука', 'Новосибирск')
ON CONFLICT DO NOTHING;

INSERT INTO Books (Title_book, Code_author, Pages, Code_publish) VALUES
('Капитанская дочка', 1, 320, 2),
('Сказка о царе Салтане', 1, 64, 3),
('Война и мир: Том 1', 2, 1225, 2),
('Преступление и наказание', 3, 672, 1),
('Изучаем Python: Руководство', 4, 800, 1),
('PostgreSQL 16: Базовый курс', 4, 560, 4),
('1984', 5, 328, 2)
ON CONFLICT DO NOTHING;

INSERT INTO Deliveries (Name_delivery, Name_company, Address, Phone, INN) VALUES
('Курьер-Экспресс', 'ООО "Книга-Сервис"', 'г. Москва, ул. Тверская, д. 12', 79991112233, '7701102233'),
('Самовывоз СДЭК', 'ООО "СДЭК-Центр"', 'г. Санкт-Петербург, Невский пр., д. 45', 79112223344, '7802345678'),
('Почта России', 'АО "Почта России"', 'г. Москва, Варшавское шоссе, д. 37', 79003334455, '7724261610'),
('ИП Логистик', 'ИП "Васильев В.В."', 'г. Омск, пр. Мира, д. 11', 79045556677, '550123456789')
ON CONFLICT DO NOTHING;

INSERT INTO Purchases (Code_book, Date_order, Code_delivery, Type_purchase, Cost, Amount) VALUES
(1, '2024-03-01 10:00:00', 1, TRUE, 450.00, 2),
(3, '2024-03-04 15:20:00', 1, TRUE, 1200.00, 1),
(5, '2024-03-08 13:00:00', 2, TRUE, 1800.00, 1)
ON CONFLICT DO NOTHING;


-- ============================================================================
-- ПРИМЕР 1: Очистка и нормализация строк от пробелов (TRIM, LTRIM, RTRIM, LENGTH)
-- ============================================================================
-- Назначение:
--   Устранение случайных пробелов в начале и конце строк (data cleansing),
--   а также вычисление точного количества удаленных символов через разницу LENGTH.

SELECT 
    Code_publish,
    Publish AS original_publish,
    LENGTH(Publish) AS len_before,
    LTRIM(Publish) AS left_trimmed,
    RTRIM(Publish) AS right_trimmed,
    TRIM(Publish) AS clean_publish,
    LENGTH(TRIM(Publish)) AS len_after,
    (LENGTH(Publish) - LENGTH(TRIM(Publish))) AS removed_spaces_count
FROM Publishing_house;


-- ============================================================================
-- ПРИМЕР 2: Стандартизация регистра текста (UPPER, LOWER, INITCAP)
-- ============================================================================
-- Назначение:
--   Приведение текстовых полей к единому регистру:
--   - UPPER()   : перевод в верхний регистр (для логистических ярлыков доставки);
--   - LOWER()   : перевод в нижний регистр (для унификации наименований компаний);
--   - INITCAP() : капитализация первых букв каждого слова (для названий книг).

SELECT 
    Code_delivery,
    Name_delivery,
    UPPER(Name_delivery) AS delivery_type_upper,
    Name_company,
    LOWER(Name_company) AS company_lower,
    Address,
    INITCAP(LOWER(Address)) AS formatted_address
FROM Deliveries;


-- ============================================================================
-- ПРИМЕР 3: Извлечение фрагментов строк по краям и позиции (LEFT, RIGHT, SUBSTRING)
-- ============================================================================
-- Назначение:
--   - LEFT(INN, 2)            : извлечение кода региона РФ из ИНН (первые 2 цифры);
--   - RIGHT(Phone::TEXT, 4)   : извлечение последних 4 цифр номера телефона;
--   - SUBSTRING(Phone::TEXT FROM 2 FOR 3) : выделение кода мобильного оператора (со 2-й позиции, 3 цифры).

SELECT 
    Code_delivery,
    Name_company,
    INN,
    LEFT(INN, 2) AS rf_region_code,
    Phone,
    RIGHT(Phone::TEXT, 4) AS phone_last_digits,
    SUBSTRING(Phone::TEXT FROM 2 FOR 3) AS mobile_operator_code
FROM Deliveries;


-- ============================================================================
-- ПРИМЕР 4: Склеивание строк и конкатенация с разделителем (CONCAT, CONCAT_WS, ||)
-- ============================================================================
-- Назначение:
--   Формирование полной стандартизированной библиографической карточки книги
--   путем объединения автора, названия, издательства, города и объема страниц.
--   CONCAT_WS() автоматически игнорирует NULL-значения и вставляет разделитель ' — '.

SELECT 
    b.Code_book,
    CONCAT_WS(
        ' — ',
        a.name_author,
        b.Title_book,
        CONCAT(TRIM(p.Publish), ', г. ', TRIM(p.City)),
        b.Pages || ' с.'
    ) AS full_bibliographic_entry
FROM Books b
JOIN Authors a ON b.Code_author = a.Code_author
JOIN Publishing_house p ON b.Code_publish = p.Code_publish
ORDER BY b.Code_book;


-- ============================================================================
-- ПРИМЕР 5: Поиск подстроки и замена текста (POSITION, STRPOS, REPLACE)
-- ============================================================================
-- Назначение:
--   - POSITION(':' IN Title_book) : определение позиции символа двоеточия;
--   - Выделение основного названия книги (до двоеточия) с помощью SUBSTRING;
--   - REPLACE() : замена двоеточия ':' на тире ' -', либо замена сокращения 'г. ' на 'город '.

SELECT 
    Code_book,
    Title_book,
    POSITION(':' IN Title_book) AS colon_position,
    CASE 
        WHEN POSITION(':' IN Title_book) > 0 
        THEN SUBSTRING(Title_book FROM 1 FOR POSITION(':' IN Title_book) - 1)
        ELSE Title_book
    END AS main_title_only,
    REPLACE(Title_book, ':', ' -') AS title_with_dash
FROM Books;


-- ============================================================================
-- ПРИМЕР 6: Разделение строк и форматирование с заполнением (SPLIT_PART, LPAD, RPAD)
-- ============================================================================
-- Назначение:
--   - SPLIT_PART(Address, ',', 1) : извлечение города из адреса;
--   - SPLIT_PART(Address, ',', 2) : извлечение улицы из адреса;
--   - LPAD(Code_delivery::TEXT, 6, '0') : формирование шестизначного штрихкод-идентификатора с нулями слева;
--   - RPAD(LEFT(Phone::TEXT, 4), 11, '*') : безопасное маскирование номера телефона звездочками.

SELECT 
    Code_delivery,
    LPAD(Code_delivery::TEXT, 6, '0') AS padded_barcode_id,
    Address,
    TRIM(SPLIT_PART(Address, ',', 1)) AS city_extracted,
    TRIM(SPLIT_PART(Address, ',', 2)) AS street_extracted,
    RPAD(LEFT(Phone::TEXT, 4), 11, '*') AS masked_safe_phone
FROM Deliveries;


-- ============================================================================
-- ПРИМЕР 7: Групповая агрегация строк в единый перечень (STRING_AGG с сортировкой)
-- ============================================================================
-- Назначение:
--   Формирование аналитического реестра по каждому автору:
--   - Подсчет общего количества книг автора COUNT(*);
--   - Агрегация всех наименований книг в единую строку через запятую с сортировкой
--     по убыванию страниц: STRING_AGG(b.Title_book, ', ' ORDER BY b.Pages DESC).

SELECT 
    a.Code_author,
    a.name_author,
    COUNT(b.Code_book) AS total_books_count,
    STRING_AGG(
        CONCAT(b.Title_book, ' (', b.Pages, ' с.)'), 
        '; ' 
        ORDER BY b.Pages DESC
    ) AS catalog_of_books
FROM Authors a
JOIN Books b ON a.Code_author = b.Code_author
GROUP BY a.Code_author, a.name_author
ORDER BY total_books_count DESC, a.name_author;
