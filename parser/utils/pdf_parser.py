import re
from datetime import datetime, timedelta
from io import BytesIO

import pandas as pd
import pdfplumber
import requests
from pandas import DataFrame

from utils import logger

DAYS_OF_WEEK = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
FIRST_CLASS_TIME = "08:20-09:50"
TIME_PATTERN = re.compile(r'^\d{2}:\d{2}-\d{2}:\d{2}$')


def is_time(cell: str) -> bool:
    # Строго HH:MM-HH:MM
    """Проверяет формат времени HH:MM-HH:MM."""
    if not isinstance(cell, str) or not cell.strip():
        return False
    return bool(TIME_PATTERN.match(cell.strip()))


def parse_pdf_to_dataframe(pdf_content: bytes) -> pd.DataFrame:
    """
    Парсит PDF файл и возвращает DataFrame с временем и расписанием.
    Адаптированная версия вашей функции parse_pdf_to_excel для работы в памяти.
    """

    with pdfplumber.open(BytesIO(pdf_content)) as pdf:
        tables = []
        for page in pdf.pages:
            tables.extend(page.extract_tables())

        if not tables:
            raise ValueError("В PDF не найдено таблиц")

    processed_data = []
    current_time = None

    for table in tables:
        for row in table:
            cells = [str(cell).strip() if cell is not None else "" for cell in row]

            # Ищем время в первых двух столбцах
            time_in_columns = [i for i, cell in enumerate(cells[:2]) if is_time(cell)]

            if time_in_columns:
                current_time = cells[time_in_columns[0]]
            elif current_time is None:
                continue

            # Собираем части расписания
            schedule_parts = []
            start_index = time_in_columns[0] + 1 if time_in_columns else 0
            for cell in cells[start_index:]:
                if cell and not is_time(cell):
                    schedule_parts.append(cell)

            if schedule_parts or time_in_columns:
                schedule = " ".join(schedule_parts) if schedule_parts else ""
                processed_data.append((current_time, schedule))

    if not processed_data:
        raise ValueError("Не найдено данных для сохранения")

    return pd.DataFrame(processed_data, columns=["Time", "Subject"])


def add_date_of_week(dataframe: pd.DataFrame, str_date: str) -> pd.DataFrame:
    """Добавляет столбцы с датой и днём недели в DataFrame расписания."""
    day_index = -1
    date = datetime.strptime(str_date, "%d%m%Y").date()
    date -= timedelta(days=1)

    date_column = []
    day_column = []

    last_time = None  # Инициализируем переменную для хранения предыдущего времени

    for _, row in dataframe.iterrows():
        current_time = row["Time"]

        # Проверяем, является ли текущее время первым занятием И отличается ли от предыдущего
        if current_time == FIRST_CLASS_TIME and current_time != last_time:
            day_index = (day_index + 1) % len(DAYS_OF_WEEK)
            date += timedelta(days=1)

        date_column.append(date.strftime("%d.%m.%Y"))
        day_column.append(DAYS_OF_WEEK[day_index])

        last_time = current_time  # Обновляем предыдущее значение времени

    dataframe.insert(0, "Day", day_column)
    dataframe.insert(0, "Date", date_column)
    return dataframe


def parser_pdf(group_data: dict) -> DataFrame:
    """
    Обрабатывает расписание для одной группы с использованием улучшенного парсера PDF.
    """
    try:
        # Загрузка PDF
        response = requests.get(group_data['schedule_url'], timeout=10)
        response.raise_for_status()

        # Используем новую функцию парсинга
        df = parse_pdf_to_dataframe(response.content)

        # Извлекаем дату из URL
        date_match = re.search(r'(\d{8}_\d{8})', group_data['schedule_url'])
        if not date_match:
            raise ValueError("Не удалось извлечь дату из URL расписания")
        start_date = date_match.group(1).split('_')[0]

        # Добавляем даты
        df = add_date_of_week(df, start_date)

        # Добавляем информацию о группе
        group_pattern = (
            r'^(?P<direction>[А-ЯЁа-яё]{1,6})'
            r'(?P<education_level>[а-яё])-'
            r'(?P<course>[0-9])'
            r'(?P<institute>[0-9])'
            r'(?P<group_num>[0-9]{2})-'
            r'(?P<profile>[0-9]{2})-'
            r'(?P<education_form>[0-9]{2})$'
        )

        group_match = re.fullmatch(group_pattern, group_data['group'])
        if not group_match:
            raise ValueError(f"Неверный формат группы: {group_data['group']}")

        df.insert(0, 'EducationForm', group_match.group('education_form'))
        df.insert(0, 'Institute', group_match.group('institute'))
        df.insert(0, 'EducationLevel', group_match.group('education_level'))
        df.insert(0, 'Specilizations', group_match.group('direction'))
        df.insert(0, 'Group', group_data['group'])
        df.insert(0, 'Faculty', group_data['faculty'])

        # Сохранение в CSV
        # filename = f"{clean_filename(group_data['group'])}.csv"
        # df.to_csv(filename, index=False, encoding='utf-8')

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
        'schedule_url': 'https://www.vyatsu.ru/reports/schedule/Group/24257_2_31032025_13042025.pdf'
    }
    try:
        filename = parser_pdf(group_data)
        print(f"Файл сохранен: {filename}")
    except Exception as e:
        print(f"Ошибка: {str(e)}")


if __name__ == '__main__':
    main()