import re
from datetime import datetime, timedelta

import fitz
import pandas as pd
import requests
from pandas import DataFrame

from parser.utils.formating_str import format_class
from sql import add_groups, add_schedule
from utils import logger

DAYS_OF_WEEK = ['понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота', 'воскресенье']
FIRST_CLASS_TIME = "08:20-09:50"
TIME_PATTERN = re.compile(r'\d{2}:\d{2}-\d{2}:\d{2}')
DATE_PATTER = re.compile(r'\b\d{2}\.\d{2}\.\d{2}\b')
GROUP_PATTERN = re.compile(
    r'^(?P<direction>[А-ЯЁа-яё]{1,6})'
    r'(?P<education_level>[а-яё])-'
    r'(?P<course>[0-9])'
    r'(?P<institute>[0-9])'
    r'(?P<group_num>[0-9]{2})-'
    r'(?P<profile>[0-9]{2})-'
    r'(?P<education_form>[0-9]{2})$'
)


def is_time(cell: str) -> bool:
    # Строго HH:MM-HH:MM
    """Проверяет формат времени HH:MM-HH:MM."""
    if not isinstance(cell, str) or not cell.strip():
        return False
    return bool(TIME_PATTERN.match(cell.strip()))


def parse_pdf_to_dataframe(pdf_content: bytes) -> pd.DataFrame:
    """
    Парсит PDF файл и возвращает DataFrame с временем и расписанием.
    Args:
        pdf_content: byte файл с расписанием
    Returns:
        pd: dataframe с расписанием
    """
    # Открываем pdf
    pdf = fitz.open("pdf", pdf_content)
    all_tables = []  # Постраничная обработка pdf
    for page in pdf:
        tables = page.find_tables()
        # Проверка на присутсвие таблиц на странице
        if not tables.tables:
            continue
        table = tables[0].extract()
        all_tables.append(table)

    # Обработка данных таблицы
    processed_data = []
    current_time = None
    current_subject = None
    current_date = None
    current_day = None
    last_time = None
    list_subject = []
    count = 0
    for table in all_tables:
        for row in table:
            count += 1
            cells = [str(cell).strip() if cell is not None else "" for cell in row]

            # Проверяем только первый столбец на наличие времени
            if len(cells) > 0:
                current_time = cells[1] if is_time(cells[1]) else current_time  # Время всегда в первой ячейке
                current_subject = format_class(cells[2]) if len(cells) > 1 and cells[2] else ""
            elif current_time is None:
                continue

            if cells[0]:
                t = cells[0].split()
                if len(t) == 2:
                    current_day = t[0]
                    date = t[1].split('.')
                    current_date = f'20{date[2]}-{date[1]}-{date[0]}'
                elif len(t) > 2:
                    for day in DAYS_OF_WEEK:
                        if day in cells[0]:
                            current_day = day
                        m = re.search(DATE_PATTER, cells[0])
                        if m:
                            date = m.group(0).split('.')
                            current_date = f'20{date[2]}-{date[1]}-{date[0]}'

            # Проверка что найденно расписание или время
            if current_subject or current_time:
                if current_time != last_time:
                    list_subject.clear()
                    list_subject = []
                    last_time = current_time
                # Проверяем, что текущая пара не дублирует предыдущие
                if not (current_subject in list_subject):
                    processed_data.append((current_date, current_day, current_time, current_subject))
                    last_time = current_time
                    list_subject.append(current_subject)

    if not processed_data:
        raise ValueError("Не найдено данных для сохранения")

    return pd.DataFrame(processed_data, columns=["date", "day", "time", "subject"])


def add_date_of_week(dataframe: pd.DataFrame, str_date: str) -> pd.DataFrame:
    """
    Добавляет столбцы с датой и днём недели в DataFrame расписания.

    Args:
        dataframe: dataframe с распианием
        str_date: диапазон дат

    Returns:
        dataframe: dataframe с добавленным датами/днями
    """
    # Инициализация 1 дня расписания
    day_index = -1
    date = datetime.strptime(str_date, "%d%m%Y").date()
    date -= timedelta(days=1)

    date_column = []
    day_column = []

    last_time = None

    for _, row in dataframe.iterrows():
        current_time = row["time"]

        # Проверяем, является ли текущее время первым занятием И отличается ли от предыдущего
        if current_time == FIRST_CLASS_TIME and current_time != last_time:
            day_index = (day_index + 1) % len(DAYS_OF_WEEK)
            date += timedelta(days=1)

        date_column.append(date.strftime("%d.%m.%Y"))
        day_column.append(DAYS_OF_WEEK[day_index])
        # Обновляем предыдущее значение времени
        last_time = current_time

    # Добавление столбцов с датой и днем
    dataframe.insert(0, "day", day_column)
    dataframe.insert(0, "date", date_column)
    return dataframe


def parser_pdf(group_data: dict) -> DataFrame:
    """
    Обрабатывает расписание для одной группы.

    Args:
        group_data: словарь с информацией об группе (Группа, факультет, ссылка на расписание)

    Results:
        df: результат парсинга (Информация об группе + расписание)
    """
    try:
        # Загрузка PDF
        response = requests.get(group_data['schedule_url'], timeout=10)
        response.raise_for_status()

        # Парсинг
        df = parse_pdf_to_dataframe(response.content)

        # Извлекаем дату из URL
        # date_match = re.search(r'(\d{8}_\d{8})', group_data['schedule_url'])
        # if not date_match:
        #    raise ValueError("Не удалось извлечь дату из URL расписания")
        # start_date = date_match.group(1).split('_')[0]

        # Добавляем даты
        # df = add_date_of_week(df, start_date)

        # Добавляем информацию о группе
        group_match = re.fullmatch(GROUP_PATTERN, group_data['group'])
        if not group_match:
            raise ValueError(f"Неверный формат группы: {group_data['group']}")
        df = df[df['day'] != 'воскресенье']
        df.insert(0, 'course', group_match.group('course'))
        df.insert(0, 'institute', group_match.group('institute'))
        df.insert(0, 'education_level', group_match.group('education_level'))
        df.insert(0, 'specilizations', group_match.group('direction'))
        df.insert(0, 'group', group_data['group'])
        df.insert(0, 'faculty', group_data['faculty'])
        add_groups(df)
        add_schedule(df)
        return df

    except requests.RequestException as e:
        logger.error(f"Ошибка загрузки PDF: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Ошибка обработки данных: {str(e)}")
        raise


def main():
    # Пример использования
    group_data = {
        'group': 'ИВТб-1303-05-00',
        'faculty': 'ФАВТ',
        'schedule_url': 'https://www.vyatsu.ru/reports/schedule/Group/24257_2_14042025_27042025.pdf'
    }
    # conn = create_connection()
    # cursor = conn.cursor()
    try:
        filename = parser_pdf(group_data)
        # filename.to_excel('fall.xlsx', index=False)
    except Exception as e:
        logger.info(f"Ошибка: {str(e)}")


if __name__ == '__main__':
    main()
