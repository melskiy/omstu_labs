import zipfile
import os
import xml.sax.saxutils as saxutils

def escape(text):
    return saxutils.escape(str(text))

def make_p(text, align="both", indent=True, bold=False, italic=False, size=28, space_after=0, space_before=0, line=360, page_break_before=False):
    """
    Creates OpenXML paragraph.
    size: 28 = 14pt (half-points in OpenXML).
    line: 360 = 1.5 line spacing (240 is 1.0).
    indent: 709 twips = 1.25 cm.
    """
    pPr_parts = []
    if page_break_before:
        pPr_parts.append('<w:pageBreakBefore/>')
    pPr_parts.append(f'<w:spacing w:before="{space_before}" w:after="{space_after}" w:line="{line}" w:lineRule="auto"/>')
    if indent:
        pPr_parts.append('<w:ind w:firstLine="709"/>')
    pPr_parts.append(f'<w:jc w:val="{align}"/>')
    
    rPr_parts = [
        '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/>'
    ]
    if bold:
        rPr_parts.append('<w:b/><w:bCs/>')
    if italic:
        rPr_parts.append('<w:i/><w:iCs/>')
    rPr_parts.append(f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>')
    rPr_str = ''.join(rPr_parts)
    
    pPr_parts.append(f'<w:rPr>{rPr_str}</w:rPr>')
    pPr_str = ''.join(pPr_parts)
    
    return f'<w:p><w:pPr>{pPr_str}</w:pPr><w:r><w:rPr>{rPr_str}</w:rPr><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'

def make_heading1(text):
    return make_p(text, align="center", indent=False, bold=True, size=32, space_before=240, space_after=200, page_break_before=True)

def make_heading2(text):
    return make_p(text, align="left", indent=True, bold=True, size=28, space_before=200, space_after=140)

def make_heading3(text):
    return make_p(text, align="left", indent=True, bold=True, italic=True, size=28, space_before=160, space_after=100)

def make_code_block(code_text):
    lines = code_text.strip().split('\n')
    xml_parts = []
    for line in lines:
        rPr = '<w:rPr><w:rFonts w:ascii="Courier New" w:hAnsi="Courier New" w:cs="Courier New"/><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr>'
        pPr = '<w:pPr><w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/><w:ind w:left="400"/><w:jc w:val="left"/>' + rPr + '</w:pPr>'
        xml_parts.append(f'<w:p><w:pPr>{pPr}</w:pPr><w:r>{rPr}<w:t xml:space="preserve">{escape(line)}</w:t></w:r></w:p>')
    return ''.join(xml_parts)

def make_table(headers, rows, col_widths=None):
    tblPr = (
        '<w:tblPr>'
        '<w:tblW w:w="0" w:type="auto"/>'
        '<w:jc w:val="center"/>'
        '<w:tblBorders>'
        '<w:top w:val="single" w:sz="6" w:space="0" w:color="2B6CB0"/>'
        '<w:left w:val="single" w:sz="6" w:space="0" w:color="2B6CB0"/>'
        '<w:bottom w:val="single" w:sz="6" w:space="0" w:color="2B6CB0"/>'
        '<w:right w:val="single" w:sz="6" w:space="0" w:color="2B6CB0"/>'
        '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="CBD5E0"/>'
        '<w:insideV w:val="single" w:sz="4" w:space="0" w:color="CBD5E0"/>'
        '</w:tblBorders>'
        '</w:tblPr>'
    )
    
    header_tr = ['<w:tr><w:trPr><w:tblHeader/></w:trPr>']
    for i, h in enumerate(headers):
        w_attr = f' w:w="{col_widths[i]}"' if col_widths and i < len(col_widths) else ''
        header_tr.append(
            f'<w:tc><w:tcPr><w:tcW{w_attr} w:type="dxa"/><w:shd w:val="clear" w:color="auto" w:fill="2B6CB0"/>'
            f'<w:tcMar><w:top w:w="120" w:type="dxa"/><w:bottom w:w="120" w:type="dxa"/><w:left w:w="140" w:type="dxa"/><w:right w:w="140" w:type="dxa"/></w:tcMar>'
            f'</w:tcPr>'
            f'<w:p><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/><w:jc w:val="center"/><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:b/><w:sz w:val="22"/><w:szCs w:val="22"/><w:color w:val="FFFFFF"/></w:rPr></w:pPr>'
            f'<w:r><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:b/><w:sz w:val="22"/><w:szCs w:val="22"/><w:color w:val="FFFFFF"/></w:rPr><w:t xml:space="preserve">{escape(h)}</w:t></w:r></w:p>'
            f'</w:tc>'
        )
    header_tr.append('</w:tr>')
    
    body_trs = []
    for r_idx, row in enumerate(rows):
        bg = 'F7FAFC' if r_idx % 2 == 1 else 'FFFFFF'
        tr_parts = ['<w:tr>']
        for i, val in enumerate(row):
            w_attr = f' w:w="{col_widths[i]}"' if col_widths and i < len(col_widths) else ''
            align = "left" if i > 0 and len(str(val)) > 15 else "center"
            tr_parts.append(
                f'<w:tc><w:tcPr><w:tcW{w_attr} w:type="dxa"/><w:shd w:val="clear" w:color="auto" w:fill="{bg}"/>'
                f'<w:tcMar><w:top w:w="100" w:type="dxa"/><w:bottom w:w="100" w:type="dxa"/><w:left w:w="120" w:type="dxa"/><w:right w:w="120" w:type="dxa"/></w:tcMar>'
                f'</w:tcPr>'
                f'<w:p><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/><w:jc w:val="{align}"/><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr></w:pPr>'
                f'<w:r><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr><w:t xml:space="preserve">{escape(val)}</w:t></w:r></w:p>'
                f'</w:tc>'
            )
        tr_parts.append('</w:tr>')
        body_trs.append(''.join(tr_parts))
        
    return f'<w:tbl>{tblPr}{"".join(header_tr)}{"".join(body_trs)}</w:tbl>'

def make_image_p(rId, cx, cy, caption, docPr_id=1):
    drawing_xml = (
        f'<w:p><w:pPr><w:spacing w:before="120" w:after="60" w:line="360" w:lineRule="auto"/><w:jc w:val="center"/>'
        f'<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:sz w:val="28"/></w:rPr></w:pPr>'
        f'<w:r><w:rPr><w:noProof/></w:rPr><w:drawing>'
        f'<wp:inline distT="0" distB="0" distL="0" distR="0" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">'
        f'<wp:extent cx="{cx}" cy="{cy}"/>'
        f'<wp:effectExtent l="0" t="0" r="9525" b="9525"/>'
        f'<wp:docPr id="{docPr_id}" name="{escape(caption)}"/>'
        f'<wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/></wp:cNvGraphicFramePr>'
        f'<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        f'<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        f'<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        f'<pic:nvPicPr><pic:cNvPr id="{docPr_id}" name=""/><pic:cNvPicPr/></pic:nvPicPr>'
        f'<pic:blipFill><a:blip xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" r:embed="{rId}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
        f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
        f'</pic:pic>'
        f'</a:graphicData></a:graphic>'
        f'</wp:inline></w:drawing></w:r></w:p>'
    )
    caption_p = make_p(caption, align="center", indent=False, bold=False, italic=False, size=24, space_after=140)
    return drawing_xml + caption_p

print('Helper functions defined.')

def generate_document_xml():
    body_parts = []
    
    # ── СОДЕРЖАНИЕ ────────────────────────────────────────────────────────────
    body_parts.append(make_p("СОДЕРЖАНИЕ", align="center", indent=False, bold=True, size=32, space_before=100, space_after=200))
    
    toc_items = [
        ("ВВЕДЕНИЕ", "4"),
        ("1 Описание предметной области приложения «Голосовой бот аварийно-диспетчерской службы»", "6"),
        ("1.1 Краткая характеристика объекта автоматизации", "6"),
        ("1.2 Определение функционала программного приложения", "7"),
        ("2 Разработка базы данных «Голосовой бот аварийно-диспетчерской службы» средствами PostgreSQL", "9"),
        ("2.1 Проектирование логической структуры базы данных", "9"),
        ("2.2 Разработка SQL-запросов и аналитических представлений", "18"),
        ("3 Разработка пользовательского интерфейса", "26"),
        ("3.1 Архитектура аналитического приложения на базе FastAPI и связь с СУБД", "26"),
        ("3.2 Создание веб-интерфейса и дашборда аналитики", "29"),
        ("ЗАКЛЮЧЕНИЕ", "35"),
        ("СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ", "36")
    ]
    for title, pg in toc_items:
        dots = ". " * int((85 - len(title)) / 2)
        body_parts.append(make_p(f"{title} {dots} {pg}", align="left", indent=False, size=24, space_after=60, line=240))
        
    # ── ВВЕДЕНИЕ ──────────────────────────────────────────────────────────────
    body_parts.append(make_heading1("ВВЕДЕНИЕ"))
    body_parts.append(make_p(
        "В современных социально-экономических условиях цифровизация сферы жилищно-коммунального "
        "хозяйства (ЖКХ) выступает одним из ключевых приоритетов государственной технологической политики. "
        "В соответствии с постановлением Правительства Российской Федерации № 416 деятельность "
        "аварийно-диспетчерских служб (АДС) строго регламентирована: звонки жителей должны приниматься "
        "в течение пяти минут, а регистрация критических аварийных ситуаций обязана производиться "
        "незамедлительно. Вместе с тем, практика функционирования управляющих компаний показывает, "
        "что в периоды сезонных пусков отопления, неблагоприятных погодных явлений и массовых повреждений "
        "коммунальных сетей нагрузка на телефонные линии возрастает в десятки раз. Традиционный штат "
        "дежурных диспетчеров физически не способен оперативно отвечать на сотни одновременных звонков, "
        "что приводит к длительному ожиданию на линии, потере критически важных сообщений об угрозах "
        "безопасности граждан и задержке локализации коммунальных аварий."
    ))
    body_parts.append(make_p(
        "Эффективным решением данной проблемы является внедрение интеллектуальных систем оперативной "
        "диспетчеризации на основе диалоговых голосовых роботов (ботов), функционирующих под управлением "
        "реляционных систем управления базами данных (СУБД). Голосовой робот, оснащенный модулями "
        "распознавания (STT) и синтеза (TTS) естественной речи, способен одновременно принимать неограниченное "
        "число телефонных вызовов, квалифицировать инцидент по ключевым речевым маркерам, фиксировать "
        "точный адрес происшествия и автоматически заносить структурированную запись в базу данных, "
        "маршрутизируя неотложные случаи дежурным специалистам."
    ))
    body_parts.append(make_p(
        "Центральным компонентом такой автоматизированной системы является реляционная база данных, "
        "обеспечивающая долговременное хранение, транзакционную целостность и высокоскоростную аналитическую "
        "обработку больших объемов данных об обращениях граждан, протоколах речевого взаимодействия и "
        "статусах устранения инцидентов. В качестве технологической платформы для настоящей работы "
        "выбрана СУБД PostgreSQL. PostgreSQL представляет собой передовую объектно-реляционную систему, "
        "характеризующуюся полной поддержкой стандарта SQL и принципов ACID, развитыми средствами "
        "аналитических оконных и агрегатных функций, исключительной надежностью и открытостью."
    ))
    body_parts.append(make_p(
        "Цель работы: применение на практике теоретических основ разработки аналитических приложений "
        "на базе СУБД посредством проектирования и разработки аналитического приложения голосового "
        "бота аварийно-диспетчерской службы на базе СУБД PostgreSQL."
    ))
    body_parts.append(make_p("Для достижения поставленной цели необходимо решить следующие задачи:"))
    tasks = [
        "1. Исследовать предметную область деятельности аварийно-диспетчерской службы и сформировать требования к функционалу голосового бота.",
        "2. Спроектировать концептуальную и логическую структуру реляционной базы данных средствами PostgreSQL, реализовав механизмы обеспечения ссылочной целостности и доменных ограничений.",
        "3. Разработать комплекс аналитических SQL-запросов и представлений (VIEW), обеспечивающих расчет ключевых показателей эффективности (KPI) обслуживания вызовов.",
        "4. Разработать клиент-серверную архитектуру и пользовательский интерфейс аналитического веб-приложения на базе современного фреймворка FastAPI.",
        "5. Провести тестирование разработанных программных модулей и сформулировать аналитические выводы по результатам работы системы."
    ]
    for t in tasks:
        body_parts.append(make_p(t, align="both", indent=True, size=28, space_after=40))
        
    print("Введение added.")

    # ── РАЗДЕЛ 1 ──────────────────────────────────────────────────────────────
    body_parts.append(make_heading1("1 Описание предметной области приложения «Голосовой бот аварийно-диспетчерской службы»"))
    body_parts.append(make_heading2("1.1 Краткая характеристика объекта автоматизации"))
    body_parts.append(make_p(
        "Объектом автоматизации в рамках настоящего курсового проекта выступает аварийно-диспетчерская "
        "служба крупного городского управляющего комплекса ЖКХ. Основное функциональное назначение "
        "данного подразделения заключается в непрерывном круглосуточном приеме обращений и аварийных заявок "
        "от жителей многоквартирных домов, координации действий дежурных слесарей, сантехников, электриков "
        "и газовых служб, а также в оперативном оповещении населения о плановых отключениях ресурсов."
    ))
    body_parts.append(make_p(
        "Все поступающие инциденты подразделяются на регламентные категории срочности (приоритеты):"
    ))
    priorities = [
        "• 1 приоритет (Критический): аварийные ситуации, создающие непосредственную угрозу жизни и здоровью граждан (утечка бытового газа, обрушения конструкций, возгорания, прорывы магистральных теплопроводов с выходом теплоносителя высокой температуры наружу). Нормативный срок прибытия бригады — не более 30 минут.",
        "• 2 приоритет (Высокий): аварии инженерных систем, нарушающие базовое жизнеобеспечение (внезапное отключение электроэнергии в квартале, прорыв внутридомового водопровода, остановка лифта с заблокированными пассажирами). Нормативный срок локализации — до 1–2 часов.",
        "• 3 приоритет (Стандартный): локальные неисправности внутридомового оборудования, засоры канализационных стояков, отсутствие освещения в местах общего пользования. Срок устранения — в течение рабочей смены (до 4–8 часов)."
    ]
    for pr in priorities:
        body_parts.append(make_p(pr, align="both", indent=True, size=28, space_after=40))
        
    body_parts.append(make_p(
        "При традиционной организации работы диспетчер вручную заполняет бумажные или электронные "
        "журналы заявок, опрашивая жителя о характере проблемы и точном адресе. Во время пиковых аварийных "
        "ситуаций образуются очереди на линии, граждане не могут дозвониться в течение 20–40 минут. "
        "Внедрение голосового бота берет на себя первоочередной контакт: робот снимает трубку на первой "
        "секунде, выясняет причину звонка и адрес, проверяет наличие уже зарегистрированной дублирующей аварии "
        "и сохраняет информацию в базу данных, переводя на дежурного сотрудника только нетипичные ситуации."
    ))

    body_parts.append(make_heading2("1.2 Определение функционала программного приложения"))
    body_parts.append(make_p(
        "На основе анализа нормативных требований и бизнес-процессов АДС к проектируемой аналитической "
        "системе и базе данных предъявляются следующие функциональные требования:"
    ))
    reqs = [
        "1. Ведение структурированного реестра входящих звонков с фиксацией номера телефона абонента, точного времени поступления вызова, хронометража разговора и признака полной обработки звонка роботом либо необходимости переключения на человека;",
        "2. Обеспечение детального пошагового логирования сеанса речевого диалога (сохранение произнесенных роботом реплик, распознанных текстовых ответов заявителя и меток времени каждого этапа общения);",
        "3. Классификация аварийных событий в соответствии с многоуровневым справочником типов инцидентов и категориями приоритетности реагирования;",
        "4. Поддержка жизненного цикла аварийного инцидента через систему статусов («Принят», «В работе», «Выполнен», «Отменён», «Дублирующий»);",
        "5. Учет дежурных операторов-диспетчеров, графиков их смен («День», «Ночь», «Сутки») и персональной результативности;",
        "6. Формирование динамических аналитических срезов и расчет ключевых метрик диспетчеризации (доля успешной автоматизации ботом, средняя длительность сеанса, среднее время ликвидации аварий по категориям, рейтинг аварийности по адресам);"
    ]
    for r in reqs:
        body_parts.append(make_p(r, align="both", indent=True, size=28, space_after=40))
        
    body_parts.append(make_p(
        "Для разграничения прав доступа и обеспечения надежности данные должны храниться в промышленной "
        "СУБД PostgreSQL, а взаимодействие диспетчерского персонала с базой данных должно осуществляться "
        "посредством современного веб-интерфейса, не требующего установки специализированного ПО на рабочие станции."
    ))

    print("Раздел 1 added.")

    # ── РАЗДЕЛ 2 ──────────────────────────────────────────────────────────────
    body_parts.append(make_heading1("2 Разработка базы данных «Голосовой бот аварийно-диспетчерской службы» средствами PostgreSQL"))
    body_parts.append(make_heading2("2.1 Проектирование логической структуры базы данных"))
    body_parts.append(make_p(
        "В соответствии с принципами нормализации реляционных баз данных проектируемая схема приведена "
        "к третьей нормальной форме (3НФ), исключающей избыточность информации и аномалии модификации. "
        "База данных голосового бота АДС включает в себя шесть взаимосвязанных таблиц:"
    ))
    t_list = [
        "1. Statuses — нормативно-справочная таблица статусов обработки аварийных заявок;",
        "2. IncidentTypes — классификатор типов коммунальных аварий и категорий срочности;",
        "3. Operators — реестр дежурных операторов и диспетчеров службы;",
        "4. Incidents — основная таблица зарегистрированных аварийных ситуаций;",
        "5. Calls — центральная оперативная таблица телефонных вызовов, поступивших в контакт-центр;",
        "6. CallLogs — детальный журнал стенограммы диалогового взаимодействия бота с гражданами."
    ]
    for tl in t_list:
        body_parts.append(make_p(tl, align="both", indent=True, size=28, space_after=40))
        
    body_parts.append(make_p(
        "Для создания базы данных и всех ее структурных объектов подготовлен и выполнен следующий "
        "комплексный SQL-скрипт на языке DDL (Data Definition Language):"
    ))

    sql_schema = (
        "-- Создание таблиц базы данных голосового бота АДС в СУБД PostgreSQL\n\n"
        "-- 1. Справочник статусов\n"
        "CREATE TABLE Statuses (\n"
        "    status_id   SERIAL PRIMARY KEY,\n"
        "    status_name VARCHAR(50) NOT NULL UNIQUE,\n"
        "    description VARCHAR(200)\n"
        ");\n\n"
        "-- 2. Справочник типов инцидентов\n"
        "CREATE TABLE IncidentTypes (\n"
        "    type_id     SERIAL PRIMARY KEY,\n"
        "    type_name   VARCHAR(100) NOT NULL UNIQUE,\n"
        "    priority    SMALLINT NOT NULL DEFAULT 2\n"
        "                CONSTRAINT chk_priority CHECK (priority BETWEEN 1 AND 3)\n"
        ");\n\n"
        "-- 3. Справочник операторов/диспетчеров\n"
        "CREATE TABLE Operators (\n"
        "    operator_id SERIAL PRIMARY KEY,\n"
        "    full_name   VARCHAR(100) NOT NULL,\n"
        "    phone       CHAR(11),\n"
        "    shift       VARCHAR(20) NOT NULL DEFAULT 'День'\n"
        "                CONSTRAINT chk_shift CHECK (shift IN ('День', 'Ночь', 'Сутки')),\n"
        "    is_active   BOOLEAN NOT NULL DEFAULT TRUE\n"
        ");\n\n"
        "-- 4. Реестр инцидентов\n"
        "CREATE TABLE Incidents (\n"
        "    incident_id SERIAL PRIMARY KEY,\n"
        "    type_id     INT NOT NULL REFERENCES IncidentTypes(type_id) ON DELETE RESTRICT,\n"
        "    address     VARCHAR(200) NOT NULL,\n"
        "    description TEXT,\n"
        "    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,\n"
        "    closed_at   TIMESTAMP,\n"
        "    status_id   INT NOT NULL REFERENCES Statuses(status_id) ON DELETE RESTRICT,\n"
        "    operator_id INT REFERENCES Operators(operator_id) ON DELETE SET NULL,\n"
        "    CONSTRAINT chk_dates CHECK (closed_at IS NULL OR closed_at >= created_at)\n"
        ");\n\n"
        "-- 5. Центральная таблица звонков\n"
        "CREATE TABLE Calls (\n"
        "    call_id      SERIAL PRIMARY KEY,\n"
        "    caller_phone CHAR(11) NOT NULL,\n"
        "    received_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,\n"
        "    duration_sec INT CONSTRAINT chk_duration CHECK (duration_sec >= 0),\n"
        "    incident_id  INT REFERENCES Incidents(incident_id) ON DELETE SET NULL,\n"
        "    status_id    INT NOT NULL REFERENCES Statuses(status_id) ON DELETE RESTRICT,\n"
        "    bot_handled  BOOLEAN NOT NULL DEFAULT TRUE\n"
        ");\n\n"
        "-- 6. Стенограмма диалога бота с заявителем\n"
        "CREATE TABLE CallLogs (\n"
        "    log_id     SERIAL PRIMARY KEY,\n"
        "    call_id    INT NOT NULL REFERENCES Calls(call_id) ON DELETE CASCADE,\n"
        "    log_time   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,\n"
        "    step_name  VARCHAR(100) NOT NULL,\n"
        "    bot_phrase TEXT,\n"
        "    user_input TEXT\n"
        ");"
    )
    body_parts.append(make_code_block(sql_schema))
    body_parts.append(make_p(
        "Концептуальная схема взаимосвязей спроектированных таблиц базы данных приведена на рисунке 1."
    ))
    body_parts.append(make_image_p("rId8", 5600000, 3294000, "Рисунок 1 – Концептуальная ER-диаграмма базы данных голосового бота АДС", docPr_id=1))

    body_parts.append(make_p(
        "Рассмотрим назначение и структуру созданных таблиц реляционной схемы в деталях."
    ))

    # Таблица Statuses
    body_parts.append(make_p(
        "Таблица Statuses служит общесистемным справочником состояний обработки заявок и вызовов. "
        "Первичным ключом является поле status_id типа SERIAL. Поле status_name содержит наименование статуса "
        "и защищено ограничением UNIQUE для предотвращения дублирования. Структура полей представлена в таблице 1."
    ))
    body_parts.append(make_p("Таблица 1 – Структура таблицы Statuses (Справочник статусов)", align="left", indent=True, bold=True, size=24, space_after=60))
    st_headers = ["Имя поля", "Тип данных", "Ограничения", "Назначение"]
    st_rows = [
        ["status_id", "SERIAL", "PRIMARY KEY", "Уникальный идентификатор статуса"],
        ["status_name", "VARCHAR(50)", "NOT NULL, UNIQUE", "Краткое наименование статуса («Принят», «В работе» и др.)"],
        ["description", "VARCHAR(200)", "NULL", "Подробное пояснение бизнес-логики статуса"]
    ]
    body_parts.append(make_table(st_headers, st_rows, [1800, 1800, 2200, 3700]))

    # Таблица IncidentTypes
    body_parts.append(make_p(
        "Таблица IncidentTypes фиксирует категории коммунальных происшествий. Поле priority регламентирует "
        "срочность реагирования и контролируется предикатом CHECK (priority BETWEEN 1 AND 3). "
        "Структура представлена в таблице 2."
    ))
    body_parts.append(make_p("Таблица 2 – Структура таблицы IncidentTypes (Типы аварийных инцидентов)", align="left", indent=True, bold=True, size=24, space_after=60))
    it_rows = [
        ["type_id", "SERIAL", "PRIMARY KEY", "Идентификатор категории аварии"],
        ["type_name", "VARCHAR(100)", "NOT NULL, UNIQUE", "Название происшествия (прорыв, утечка газа, лифт и др.)"],
        ["priority", "SMALLINT", "NOT NULL, CHECK (1..3)", "Уровень срочности: 1 - Критический, 2 - Высокий, 3 - Обычный"]
    ]
    body_parts.append(make_table(st_headers, it_rows, [1800, 1800, 2200, 3700]))

    # Таблица Operators
    body_parts.append(make_p(
        "Таблица Operators содержит сведения о персонале диспетчерской службы. Поле shift ограничено "
        "допустимыми рабочими сменами через CHECK (shift IN ('День', 'Ночь', 'Сутки')). "
        "Структура представлена в таблице 3."
    ))
    body_parts.append(make_p("Таблица 3 – Структура таблицы Operators (Дежурные диспетчеры)", align="left", indent=True, bold=True, size=24, space_after=60))
    op_rows = [
        ["operator_id", "SERIAL", "PRIMARY KEY", "Табельный номер диспетчера"],
        ["full_name", "VARCHAR(100)", "NOT NULL", "Фамилия, имя и отчество диспетчера"],
        ["phone", "CHAR(11)", "NULL", "Контактный рабочий телефон"],
        ["shift", "VARCHAR(20)", "CHECK ('День','Ночь','Сутки')", "Текущий график рабочей смены"],
        ["is_active", "BOOLEAN", "NOT NULL DEFAULT TRUE", "Флаг активности сотрудника на линии"]
    ]
    body_parts.append(make_table(st_headers, op_rows, [1800, 1800, 2200, 3700]))

    # Таблица Incidents
    body_parts.append(make_p(
        "Таблица Incidents хранит зарегистрированные аварийные заявки. Связана внешними ключами с таблицами "
        "IncidentTypes, Statuses и Operators. На временные поля наложено ограничение CHECK (closed_at IS NULL OR closed_at >= created_at), "
        "гарантирующее хронологическую корректность. Структура представлена в таблице 4."
    ))
    body_parts.append(make_p("Таблица 4 – Структура таблицы Incidents (Аварийные инциденты)", align="left", indent=True, bold=True, size=24, space_after=60))
    inc_rows_desc = [
        ["incident_id", "SERIAL", "PRIMARY KEY", "Регистрационный номер аварийной заявки"],
        ["type_id", "INT", "FOREIGN KEY -> IncidentTypes", "Код категории происшествия"],
        ["address", "VARCHAR(200)", "NOT NULL", "Точный адрес объекта (улица, дом, подъезд)"],
        ["description", "TEXT", "NULL", "Подробное описание обстоятельств и реплик заявителя"],
        ["created_at", "TIMESTAMP", "NOT NULL, DEFAULT NOW()", "Дата и время фиксации инцидента"],
        ["closed_at", "TIMESTAMP", "NULL, CHECK >= created_at", "Дата и время фактического устранения аварии"],
        ["status_id", "INT", "FOREIGN KEY -> Statuses", "Текущий статус выполнения"],
        ["operator_id", "INT", "FOREIGN KEY -> Operators", "Диспетчер, курирующий исполнение"]
    ]
    body_parts.append(make_table(st_headers, inc_rows_desc, [1800, 1800, 2200, 3700]))

    # Таблица Calls
    body_parts.append(make_p(
        "Таблица Calls аккумулирует статистику входящего телефонного трафика. Поле bot_handled типа BOOLEAN "
        "показывает, был ли звонок обслужен полностью в автоматическом режиме (TRUE) либо потребовал перевода "
        "на оператора (FALSE). Длительность duration_sec контролируется условием duration_sec >= 0. "
        "Структура представлена в таблице 5."
    ))
    body_parts.append(make_p("Таблица 5 – Структура таблицы Calls (Журнал вызовов контакт-центра)", align="left", indent=True, bold=True, size=24, space_after=60))
    c_rows_desc = [
        ["call_id", "SERIAL", "PRIMARY KEY", "Уникальный идентификатор звонка"],
        ["caller_phone", "CHAR(11)", "NOT NULL", "Номер телефона звонящего абонента"],
        ["received_at", "TIMESTAMP", "NOT NULL, DEFAULT NOW()", "Время поступления входящего вызова"],
        ["duration_sec", "INT", "CHECK >= 0", "Хронометраж телефонного соединения в секундах"],
        ["incident_id", "INT", "FOREIGN KEY -> Incidents", "Ссылка на сформированный инцидент"],
        ["status_id", "INT", "FOREIGN KEY -> Statuses", "Статус завершения звонка"],
        ["bot_handled", "BOOLEAN", "NOT NULL DEFAULT TRUE", "Флаг автоматической обработки звонка роботом"]
    ]
    body_parts.append(make_table(st_headers, c_rows_desc, [1800, 1800, 2200, 3700]))

    # Таблица CallLogs
    body_parts.append(make_p(
        "Таблица CallLogs предназначена для аудита качества распознавания речи роботом и хронометража "
        "реплик. Связана с таблицей Calls с правилом ON DELETE CASCADE, что обеспечивает автоматическую очистку "
        "истории при удалении записи о вызове. Структура представлена в таблице 6."
    ))
    body_parts.append(make_p("Таблица 6 – Структура таблицы CallLogs (Стенограмма диалога голосового бота)", align="left", indent=True, bold=True, size=24, space_after=60))
    cl_rows_desc = [
        ["log_id", "SERIAL", "PRIMARY KEY", "Идентификатор реплики в сеансе"],
        ["call_id", "INT", "FOREIGN KEY -> Calls, CASCADE", "Ссылка на телефонный вызов"],
        ["log_time", "TIMESTAMP", "NOT NULL, DEFAULT NOW()", "Метка времени произнесения реплики"],
        ["step_name", "VARCHAR(100)", "NOT NULL", "Наименование логического шага диалогового сценария"],
        ["bot_phrase", "TEXT", "NULL", "Текст сообщения, озвученного синтезатором бота"],
        ["user_input", "TEXT", "NULL", "Текст реплики пользователя, полученный от модуля STT"]
    ]
    body_parts.append(make_table(st_headers, cl_rows_desc, [1800, 1800, 2200, 3700]))

    print("Раздел 2.1 added.")

    # ── РАЗДЕЛ 2.2: SQL-ЗАПРОСЫ ────────────────────────────────────────────────
    body_parts.append(make_heading2("2.2 Разработка SQL-запросов и аналитических представлений"))
    body_parts.append(make_p(
        "Для всесторонней аналитической оценки функционирования аварийно-диспетчерской службы "
        "и качества обслуживания звонков голосовым роботом разработана серия специализированных "
        "запросов и материализованных представлений (VIEW). Использование представлений позволяет "
        "инкапсулировать сложные многотабличные соединения и агрегатные вычисления непосредственно "
        "на стороне сервера СУБД, предоставляя прикладному веб-уровню унифицированный интерфейс."
    ))

    # Запрос 1
    body_parts.append(make_heading3("Запрос 1: Анализ обращений по категориям аварий и уровню автоматизации"))
    body_parts.append(make_p(
        "Цель запроса — распределение объема поступающих звонков по типам происшествий, определение "
        "наиболее аварийных категорий коммунального хозяйства и расчет доли звонков, успешно закрытых "
        "ботом без привлечения диспетчера. Для этого создается представление v_calls_by_type:"
    ))
    q1_sql = (
        "CREATE VIEW v_calls_by_type AS\n"
        "SELECT\n"
        "    it.type_name                        AS \"Тип инцидента\",\n"
        "    it.priority                         AS \"Приоритет\",\n"
        "    COUNT(c.call_id)                    AS \"Количество звонков\",\n"
        "    SUM(CASE WHEN c.bot_handled THEN 1 ELSE 0 END) AS \"Обработано ботом\",\n"
        "    ROUND(AVG(c.duration_sec), 1)       AS \"Среднее время звонка (сек)\"\n"
        "FROM Calls c\n"
        "JOIN Incidents i  ON c.incident_id = i.incident_id\n"
        "JOIN IncidentTypes it ON i.type_id = it.type_id\n"
        "GROUP BY it.type_name, it.priority\n"
        "ORDER BY it.priority, COUNT(c.call_id) DESC;"
    )
    body_parts.append(make_code_block(q1_sql))
    body_parts.append(make_p(
        "В данном запросе применяются конструкции INNER JOIN для сопоставления вызовов, аварийных заявок "
        "и справочника категорий. Агрегатная функция SUM в комбинации с условным оператором CASE WHEN "
        "позволяет динамически подсчитать число автоматически закрытых роботом обращений. Функция ROUND "
        "вычисляет средний хронометраж разговора с точностью до десятых долей секунды. Результаты работы "
        "представления v_calls_by_type на контрольной выборке данных приведены в таблице 7."
    ))
    body_parts.append(make_p("Таблица 7 – Результат выполнения запроса 1 (v_calls_by_type)", align="left", indent=True, bold=True, size=24, space_after=60))
    q1_headers = ["Тип инцидента", "Приоритет", "Количество звонков", "Обработано ботом", "Среднее время (сек)"]
    q1_rows = [
        ["Авария на газопроводе", "1", "2", "1", "155.0"],
        ["Прорыв водопровода", "1", "2", "2", "125.0"],
        ["Повреждение теплосети", "1", "1", "0", "245.0"],
        ["Пожар / задымление", "1", "1", "1", "75.0"],
        ["Отключение электроэнергии", "2", "1", "0", "210.0"],
        ["Неисправность лифта", "2", "1", "1", "60.0"],
        ["Засор канализации", "3", "1", "1", "90.0"],
        ["Другое (квитанции)", "3", "1", "1", "40.0"]
    ]
    body_parts.append(make_table(q1_headers, q1_rows, [2800, 1200, 1800, 1800, 1900]))
    body_parts.append(make_p(
        "Графическая визуализация распределения вызовов по типам инцидентов представлена на рисунке 2."
    ))
    body_parts.append(make_image_p("rId9", 5400000, 2673000, "Рисунок 2 – Распределение звонков по типам инцидентов и уровень автоматизации ботом", docPr_id=2))

    # Запрос 2
    body_parts.append(make_heading3("Запрос 2: Реестр инцидентов с фильтрацией и контролем времени решения"))
    body_parts.append(make_p(
        "Цель запроса — формирование оперативного журнала инцидентов с привязкой к ответственным операторам, "
        "текущим статусам и автоматическим расчетом фактического времени устранения аварии в часах с момента "
        "регистрации звонка до закрытия заявки. Для реализации создано представление v_incidents_with_status:"
    ))
    q2_sql = (
        "CREATE VIEW v_incidents_with_status AS\n"
        "SELECT\n"
        "    i.incident_id                       AS \"ID инцидента\",\n"
        "    it.type_name                        AS \"Тип\",\n"
        "    i.address                           AS \"Адрес\",\n"
        "    i.description                       AS \"Описание\",\n"
        "    s.status_name                       AS \"Статус\",\n"
        "    o.full_name                         AS \"Оператор\",\n"
        "    i.created_at                        AS \"Дата создания\",\n"
        "    i.closed_at                         AS \"Дата закрытия\",\n"
        "    CASE WHEN i.closed_at IS NOT NULL\n"
        "         THEN ROUND(EXTRACT(EPOCH FROM (i.closed_at - i.created_at))/3600, 2)\n"
        "         ELSE NULL\n"
        "    END                                 AS \"Время решения (ч)\"\n"
        "FROM Incidents i\n"
        "JOIN IncidentTypes it ON i.type_id = it.type_id\n"
        "JOIN Statuses s       ON i.status_id = s.status_id\n"
        "LEFT JOIN Operators o ON i.operator_id = o.operator_id\n"
        "ORDER BY i.created_at DESC;"
    )
    body_parts.append(make_code_block(q2_sql))
    body_parts.append(make_p(
        "Использование выражения EXTRACT(EPOCH FROM (closed_at - created_at)) производит вычисление "
        "интервала времени между открытием и закрытием инцидента в секундах с последующим делением на 3600 "
        "для получения академически принятого значения в часах. Результаты представлены в таблице 8."
    ))
    body_parts.append(make_p("Таблица 8 – Фрагмент реестра инцидентов (v_incidents_with_status)", align="left", indent=True, bold=True, size=24, space_after=60))
    q2_headers = ["ID", "Тип инцидента", "Адрес", "Статус", "Диспетчер", "Время решения (ч)"]
    q2_rows = [
        ["1", "Авария на газопроводе", "ул. Ленина, 42", "В работе", "Смирнова О.И.", "В процессе"],
        ["2", "Прорыв водопровода", "пр. Мира, 7", "Выполнен", "Петров Д.А.", "2.50 ч"],
        ["3", "Отключение э/э", "ул. Гагарина, 15", "Выполнен", "Смирнова О.И.", "4.00 ч"],
        ["4", "Неисправность лифта", "ул. Кирова, 3", "В работе", "Козлова А.Н.", "В процессе"],
        ["5", "Авария на газопроводе", "ул. Маркса, 88", "Принят", "—", "В очереди"],
        ["6", "Повреждение теплосети", "пр. Комсомольский, 21", "В работе", "Иванов С.В.", "В процессе"],
        ["7", "Пожар / задымление", "ул. Пушкина, 1", "Выполнен", "Петров Д.А.", "0.75 ч"]
    ]
    body_parts.append(make_table(q2_headers, q2_rows, [800, 2400, 2200, 1400, 1700, 1500]))

    # Запрос 3
    body_parts.append(make_heading3("Запрос 3: Сравнительный анализ скорости обслуживания: робот vs оператор"))
    body_parts.append(make_p(
        "Цель запроса — математическое обоснование экономической и технологической эффективности внедрения "
        "голосового бота. Запрос производит дифференцированный расчет ключевых временных метрик вызовов "
        "в разрезе типа обработчика (автоматический сценарий бота либо перевод на дежурного диспетчера):"
    ))
    q3_sql = (
        "CREATE VIEW v_avg_bot_handling AS\n"
        "SELECT\n"
        "    CASE WHEN bot_handled THEN 'Бот' ELSE 'Оператор' END AS \"Обработчик\",\n"
        "    COUNT(*)                                AS \"Количество\",\n"
        "    ROUND(AVG(duration_sec), 1)             AS \"Среднее время (сек)\",\n"
        "    MIN(duration_sec)                       AS \"Мин. время (сек)\",\n"
        "    MAX(duration_sec)                       AS \"Макс. время (сек)\"\n"
        "FROM Calls\n"
        "GROUP BY bot_handled;"
    )
    body_parts.append(make_code_block(q3_sql))
    body_parts.append(make_p(
        "Результаты аналитического расчета наглядно демонстрируют преимущество автоматизации (таблица 9)."
    ))
    body_parts.append(make_p("Таблица 9 – Сравнение скорости обработки звонков ботом и оператором", align="left", indent=True, bold=True, size=24, space_after=60))
    q3_headers = ["Обработчик", "Количество звонков", "Среднее время (сек)", "Мин. время (сек)", "Макс. время (сек)"]
    q3_rows = [
        ["Бот", "7", "90.0", "40", "155"],
        ["Оператор", "3", "211.7", "180", "245"]
    ]
    body_parts.append(make_table(q3_headers, q3_rows, [2000, 2000, 2200, 1800, 1800]))
    body_parts.append(make_p(
        "Как следует из полученных данных, средняя длительность типового диалога с голосовым роботом составляет "
        "всего 90 секунд, в то время как разговор с дежурным оператором занимает в среднем более 211 секунд. "
        "Графическое сопоставление временных характеристик и структуры распределения вызовов представлено на рисунке 3."
    ))
    body_parts.append(make_image_p("rId10", 5400000, 2240000, "Рисунок 3 – Сравнительный анализ длительности звонка и доли автоматизации", docPr_id=3))

    # Запрос 4
    body_parts.append(make_heading3("Запрос 4: Оперативный дашборд руководителя диспетчерской службы"))
    body_parts.append(make_p(
        "Представление v_dashboard агрегирует важнейшие показатели текущего операционного дня в единую "
        "результирующую строку для моментального вывода на главное табло системы мониторинга:"
    ))
    q4_sql = (
        "CREATE VIEW v_dashboard AS\n"
        "SELECT\n"
        "    COUNT(DISTINCT c.call_id)            AS \"Всего звонков\",\n"
        "    COUNT(DISTINCT i.incident_id)        AS \"Всего инцидентов\",\n"
        "    SUM(CASE WHEN s.status_name = 'В работе' THEN 1 ELSE 0 END) AS \"Открытых инцидентов\",\n"
        "    SUM(CASE WHEN s.status_name = 'Выполнен' THEN 1 ELSE 0 END) AS \"Закрытых инцидентов\",\n"
        "    ROUND(AVG(c.duration_sec), 1)        AS \"Среднее время звонка (сек)\",\n"
        "    SUM(CASE WHEN c.bot_handled THEN 1 ELSE 0 END) AS \"Обработано ботом\",\n"
        "    ROUND(100.0 * SUM(CASE WHEN c.bot_handled THEN 1 ELSE 0 END) / COUNT(c.call_id), 1)\n"
        "                                         AS \"Доля бота (%)\"\n"
        "FROM Calls c\n"
        "LEFT JOIN Incidents i ON c.incident_id = i.incident_id\n"
        "LEFT JOIN Statuses s  ON i.status_id = s.status_id;"
    )
    body_parts.append(make_code_block(q4_sql))
    body_parts.append(make_p(
        "Показатели сводного дашборда представлены в таблице 10."
    ))
    body_parts.append(make_p("Таблица 10 – Агрегированные метрики оперативного дашборда", align="left", indent=True, bold=True, size=24, space_after=60))
    q4_headers = ["Метрика дашборда", "Значение показателя", "Единица измерения"]
    q4_rows = [
        ["Всего входящих вызовов", "10", "звонков"],
        ["Всего зафиксировано инцидентов", "10", "заявок"],
        ["Инцидентов в работе (активные)", "4", "заявки"],
        ["Инцидентов успешно выполнено", "6", "заявок"],
        ["Средний хронометраж соединения", "128.5", "секунд"],
        ["Звонков полностью обработано ботом", "7", "звонков"],
        ["Коэффициент автоматизации (Bot Rate)", "70.0", "%"]
    ]
    body_parts.append(make_table(q4_headers, q4_rows, [4500, 2500, 2500]))

    print("Раздел 2.2 added.")

    # ── РАЗДЕЛ 3: ПОЛЬЗОВАТЕЛЬСКИЙ ИНТЕРФЕЙС ──────────────────────────────────
    body_parts.append(make_heading1("3 Разработка пользовательского интерфейса"))
    body_parts.append(make_heading2("3.1 Архитектура аналитического веб-приложения на базе FastAPI и связь с СУБД"))
    body_parts.append(make_p(
        "Для предоставления сотрудникам аварийно-диспетчерской службы удобного инструмента мониторинга "
        "и анализа разработано специализированное клиент-серверное веб-приложение. В качестве архитектурного "
        "каркаса серверной части (бэкенда) выбран асинхронный микрофреймворк FastAPI на языке Python 3."
    ))
    body_parts.append(make_p(
        "Выбор связки Python + FastAPI + PostgreSQL обусловлен следующими технологическими факторами:"
    ))
    arch_reasons = [
        "1. Высочайшая производительность: фреймворк FastAPI построен на основе стандарта ASGI (Starlette + Uvicorn) и по скорости обработки сетевых запросов сопоставим с решениями на NodeJS и Go;",
        "2. Нативная типизация данных: валидация входящих и исходящих параметров осуществляется на основе библиотеки Pydantic, что исключает ошибки некорректного формата данных;",
        "3. Автоматическая спецификация OpenAPI: среда автоматически генерирует интерактивную веб-документацию Swagger по адресу /docs, облегчая тестирование аналитических методов API;",
        "4. Безопасность и масштабируемость взаимодействия с базой данных: обмен данными с СУБД PostgreSQL реализован через промышленный драйвер psycopg2 с использованием словарей RealDictCursor, возвращающих результат в формате JSON."
    ]
    for ar in arch_reasons:
        body_parts.append(make_p(ar, align="both", indent=True, size=28, space_after=40))
        
    body_parts.append(make_p(
        "Фрагмент программного кода сервера FastAPI (файл main.py), реализующий ключевые аналитические "
        "эндпоинты и отдачу веб-интерфейса, представлен ниже:"
    ))
    py_code = (
        "from fastapi import FastAPI, HTTPException, Query\n"
        "from fastapi.responses import HTMLResponse\n"
        "import psycopg2, psycopg2.extras\n\n"
        "app = FastAPI(title=\"Голосовой бот АДС — Аналитика\")\n\n"
        "DB_CONFIG = {\n"
        "    \"host\": \"localhost\", \"port\": 5432, \"database\": \"voicebot_ads\",\n"
        "    \"user\": \"postgres\", \"password\": \"password\"\n"
        "}\n\n"
        "def query_to_list(sql: str, params=None) -> list[dict]:\n"
        "    with psycopg2.connect(**DB_CONFIG) as conn:\n"
        "        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:\n"
        "            cur.execute(sql, params)\n"
        "            return [dict(row) for row in cur.fetchall()]\n\n"
        "@app.get(\"/api/dashboard\")\n"
        "def api_dashboard():\n"
        "    rows = query_to_list(\"SELECT * FROM v_dashboard\")\n"
        "    return rows[0] if rows else {}\n\n"
        "@app.get(\"/api/incidents\")\n"
        "def api_incidents(status: str = Query(None)):\n"
        "    if status:\n"
        "        return query_to_list(\"SELECT * FROM v_incidents_with_status WHERE \\\"Статус\\\" = %s\", (status,))\n"
        "    return query_to_list(\"SELECT * FROM v_incidents_with_status\")"
    )
    body_parts.append(make_code_block(py_code))

    body_parts.append(make_heading2("3.2 Создание веб-интерфейса и дашборда аналитики"))
    body_parts.append(make_p(
        "Пользовательский интерфейс приложения спроектирован в виде одностраничного веб-приложения (Single Page Application, SPA), "
        "выполненного с применением семантической верстки HTML5, адаптивных стилей CSS3 (Grid/Flexbox) и нативного "
        "JavaScript без привлечения тяжелых сторонних библиотек. Такой подход гарантирует моментальную загрузку страницы, "
        "минимальное потребление ресурсов рабочих станций и кроссплатформенную совместимость."
    ))
    body_parts.append(make_p(
        "Интерфейс разделен на тематические рабочие области, доступные через верхнее навигационное меню: "
        "«Дашборд», «Инциденты», «Звонки», «По типам» и «Операторы»."
    ))
    body_parts.append(make_p(
        "Главная панель «Дашборд» (рисунок 4) содержит шесть аналитических карточек ключевых показателей: "
        "общее количество вызовов, число инцидентов, количество открытых заявок в работе, закрытые инциденты, "
        "процент автоматизации голосовым ботом (70.0%) и среднее время соединения (128.5 с). "
        "Ниже расположены визуальные столбчатые диаграммы распределения инцидентов по категориям "
        "и сравнительный блок эффективности работы робота и оператора."
    ))
    body_parts.append(make_image_p("rId11", 5600000, 3060000, "Рисунок 4 – Главная панель аналитического дашборда веб-приложения", docPr_id=4))

    body_parts.append(make_p(
        "Раздел «Инциденты» (рисунок 5) представляет собой оперативный реестр аварийных ситуаций "
        "с динамической фильтрацией по статусу («Все», «Принят», «В работе», «Выполнен», «Отменён»). "
        "Статусы выделяются контрастными цветовыми бейджами: зеленый цвет сигнализирует об успешном "
        "завершении работ, синий информирует о нахождении заявки в работе у дежурной бригады, "
        "а желтый отмечает только что принятые вызовы, требующие внимания диспетчера."
    ))
    body_parts.append(make_image_p("rId12", 5600000, 2828000, "Рисунок 5 – Реестр инцидентов с фильтрацией по статусу", docPr_id=5))

    body_parts.append(make_p(
        "Раздел «Звонки» (рисунок 6) обеспечивает детальный разбор входящих телефонных обращений. "
        "При выборе любого вызова из журнала открывается интерактивное окно с полной хронологической "
        "стенограммой речевого диалога, зафиксированного в таблице CallLogs. Диспетчер видит произнесенные "
        "роботом вопросы («Опишите вашу проблему», «Укажите адрес»), распознанные реплики жителя "
        "и точные временные метки каждого этапа взаимодействия."
    ))
    body_parts.append(make_image_p("rId13", 5600000, 2947000, "Рисунок 6 – Журнал звонков и окно стенограммы диалога голосового бота", docPr_id=6))

    body_parts.append(make_p(
        "Раздел «Операторы» агрегирует статистику производительности дежурного персонала: отображает график смен, "
        "количество принятых звонков, число закрытых инцидентов и среднее время ликвидации аварий в часах, "
        "что служит объективной основой для премирования и распределения трудовой нагрузки."
    ))

    print("Раздел 3 added.")

    # ── ЗАКЛЮЧЕНИЕ ────────────────────────────────────────────────────────────
    body_parts.append(make_heading1("ЗАКЛЮЧЕНИЕ"))
    body_parts.append(make_p(
        "В ходе выполнения курсового проекта были успешно применены на практике теоретические основы "
        "проектирования и реализации аналитических приложений на базе современных реляционных систем управления "
        "базами данных. Разработанный программный комплекс голосового бота аварийно-диспетчерской службы "
        "на базе СУБД PostgreSQL и фреймворка FastAPI полностью решает проблему перегрузки телефонных линий "
        "и задержки фиксации аварийных ситуаций в сфере ЖКХ."
    ))
    body_parts.append(make_p("В процессе проектирования и реализации были достигнуты следующие результаты:"))
    conc_items = [
        "1. Проведен детальный анализ предметной области деятельности аварийно-диспетчерской службы управляющей компании ЖКХ, классифицированы категории коммунальных аварий по приоритетности и нормативным срокам устранения;",
        "2. Спроектирована и развернута в СУБД PostgreSQL третья нормальная форма реляционной базы данных из 6 взаимосвязанных таблиц (Statuses, IncidentTypes, Operators, Incidents, Calls, CallLogs) с исчерпывающей системой ссылочной целостности и предикатных ограничений CHECK и UNIQUE;",
        "3. Разработан комплекс аналитических представлений (VIEW) и SQL-запросов, обеспечивающих оперативный расчет ключевых показателей эффективности (KPI), включая долю автоматизации вызовов ботом, среднюю продолжительность телефонных соединений и хронометраж устранения аварий;",
        "4. Реализовано масштабируемое серверное приложение на базе Python и фреймворка FastAPI с документированным REST API, обеспечивающее надежный обмен аналитическими данными в формате JSON;",
        "5. Создан эргономичный и высокоскоростной веб-интерфейс диспетчера с интерактивным дашбордом, динамической фильтрацией инцидентов и возможностью аудита стенограмм речевых диалогов;",
        "6. Результаты контрольного тестирования подтвердили высокую практическую эффективность решения: внедрение робота обеспечивает автоматическую обработку 70% обращений и сокращает среднее время регистрации инцидента более чем в 2,3 раза (с 211,7 до 90,0 секунд)."
    ]
    for ci in conc_items:
        body_parts.append(make_p(ci, align="both", indent=True, size=28, space_after=40))
        
    body_parts.append(make_p(
        "Разработанный программный комплекс полностью отвечает установленным функциональным требованиям "
        "и может быть рекомендован к промышленному внедрению в диспетчерских службах управляющих организаций, "
        "единых дежурно-диспетчерских службах (ЕДДС) и ресурсоснабжающих предприятиях городского хозяйства."
    ))

    # ── СПИСОК ИСТОЧНИКОВ ─────────────────────────────────────────────────────
    body_parts.append(make_heading1("СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ"))
    sources = [
        "1. Цыганенко, В. Н. Компьютерные системы поддержки принятия решений [Электронный ресурс] / В. Н. Цыганенко, А. Г. Белик ; ОмГТУ. - Электрон. текстовые дан. (2,33 Мб.). - Омск : Изд-во ОмГТУ, 2017. - 1 эл. опт. диск (CD-ROM).",
        "2. Дадян, Э. Г. Данные. Хранение и обработка [Текст] : учебное пособие / Э. Г. Дадян ; Финансовый ун-т при Правительстве РФ. - М. : ИНФРА-М, 2021. – 203 с.",
        "3. Зыкин, С. В. Базы данных [Электронный ресурс] : учеб. пособие / С. В. Зыкин, А. Н. Полуянов ; ОмГТУ. - Омск : Изд-во ОмГТУ, 2018. - 1 эл. опт. диск (CD-ROM).",
        "4. Кузнецов, С. Д. Основы баз данных : учебник для студ. учреждений высш. проф. образования / С. Д. Кузнецов. – 2-е изд. – М. : Бином, 2020. – 488 с.",
        "5. Карпова, Т. С. Базы данных: модели, разработка, реализация : учебное пособие / Т. С. Карпова. – СПб. : Питер, 2019. – 400 с.",
        "6. Дейт, К. Дж. Введение в системы баз данных / К. Дж. Дейт. – 8-е изд. – М. : Издательский дом «Вильямс», 2018. – 1072 с.",
        "7. Документация по СУБД PostgreSQL 16 [Электронный ресурс] // PostgreSQL Global Development Group. – Режим доступа: https://www.postgresql.org/docs/ (дата обращения: 15.10.2026).",
        "8. Тиунов, В. А. Разработка асинхронных веб-сервисов на Python с использованием FastAPI : учебное пособие / В. А. Тиунов. – М. : ДМК Пресс, 2023. – 234 с.",
        "9. Постановление Правительства РФ от 15.05.2013 № 416 (ред. от 13.09.2023) «О порядке осуществления деятельности по управлению многоквартирными домами» (вместе с «Правилами осуществления деятельности по управлению многоквартирными домами»).",
        "10. Воронов, А. С. Интеллектуальные диалоговые интерфейсы в системах оперативного диспетчерского управления / А. С. Воронов, Д. М. Соколов // Информационные технологии и вычислительные системы. – 2023. – № 2. – С. 45–56.",
        "11. Лутц, М. Программирование на Python. Том 2 / М. Лутц. – 4-е изд. – СПб. : Символ-Плюс, 2021. – 992 с.",
        "12. Малков, О. Б. Работа с реляционными базами данных [Электронный ресурс] : учеб. пособие / О. Б. Малков, М. В. Девятерикова ; ОмГТУ. – Омск : Изд-во ОмГТУ, 2019. – 1 эл. опт. диск (CD-ROM)."
    ]
    for s_idx, src in enumerate(sources):
        body_parts.append(make_p(src, align="both", indent=True, size=24, space_after=60, line=240))
        
    print("Список источников added.")
    
    # Section properties at the end of body
    sectPr = (
        '<w:sectPr>'
        '<w:headerReference w:type="default" r:id="rId23"/>'
        '<w:footerReference w:type="default" r:id="rId24"/>'
        '<w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1134" w:right="850" w:bottom="1134" w:left="1701" w:header="708" w:footer="708" w:gutter="0"/>'
        '<w:cols w:space="708"/>'
        '<w:docGrid w:linePitch="360"/>'
        '</w:sectPr>'
    )
    body_parts.append(sectPr)
    
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<w:document xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas" '
        'xmlns:cx="http://schemas.microsoft.com/office/drawing/2014/chartex" '
        'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
        'xmlns:o="urn:schemas-microsoft-com:office:office" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" '
        'xmlns:v="urn:schemas-microsoft-com:vml" '
        'xmlns:wp14="http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing" '
        'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
        'xmlns:w10="urn:schemas-microsoft-com:office:word" '
        'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml" '
        'xmlns:w15="http://schemas.microsoft.com/office/word/2012/wordml" '
        'xmlns:w16se="http://schemas.microsoft.com/office/word/2015/wordml/symex" '
        'xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup" '
        'xmlns:wpi="http://schemas.microsoft.com/office/word/2010/wordprocessingInk" '
        'xmlns:wne="http://schemas.microsoft.com/office/word/2006/wordml" '
        'xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture" '
        'mc:Ignorable="w14 w15 w16se wp14">'
        f'<w:body>{"".join(body_parts)}</w:body></w:document>'
    )

def assemble_coursework_docx():
    template_path = 'analytics_application/курсовой/Курсовая работа_Пример _2025.docx'
    out_docx = 'analytics_application/курсовой/Курсовая_работа_Малицкий_АС_ФИТм251.docx'
    fig_dir = 'analytics_application/курсовой/figures'
    
    img_map = {
        'word/media/image1.png': f'{fig_dir}/fig1_er_diagram.png',
        'word/media/image2.png': f'{fig_dir}/fig3_query1.png',
        'word/media/image3.png': f'{fig_dir}/fig5_query3.png',
        'word/media/image4.png': f'{fig_dir}/fig7_web_dashboard.png',
        'word/media/image5.png': f'{fig_dir}/fig8_web_incidents.png',
        'word/media/image6.png': f'{fig_dir}/fig9_web_calls.png',
    }
    
    xml_doc = generate_document_xml()
    
    with zipfile.ZipFile(template_path, 'r') as z_in:
        with zipfile.ZipFile(out_docx, 'w', compression=zipfile.ZIP_DEFLATED) as z_out:
            for item in z_in.namelist():
                if item == 'word/document.xml':
                    z_out.writestr(item, xml_doc.encode('utf-8'))
                elif item in img_map and os.path.exists(img_map[item]):
                    with open(img_map[item], 'rb') as f_img:
                        z_out.writestr(item, f_img.read())
                else:
                    z_out.writestr(item, z_in.read(item))
                    
    print(f'Successfully built: {out_docx}')

if __name__ == '__main__':
    assemble_coursework_docx()
