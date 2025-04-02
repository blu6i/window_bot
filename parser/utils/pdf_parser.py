import re
import pdfplumber
import pandas as pd
import requests
from io import BytesIO
from datetime import datetime, timedelta


def clean_filename(filename):
    """Очищает имя файла, удаляя недопустимые символы и лишние пробелы.

    Аргументы:
        filename (str): Исходное имя файла

    Возвращает:
        str: Очищенное имя файла, безопасное для файловой системы
    """
    filename = filename.strip()
    filename = re.sub(r'[\\/:*?"<>|]', '', filename)
    return filename


DAYS_OF_WEEK = [
    "Понедельник",
    "Вторник",
    "Среда",
    "Четверг",
    "Пятница",
    "Суббота",
    "Воскресенье"
]

# Время первой пары
FIRST_CLASS_TIME = "08:20-09:50"


def add_date_of_week(dataframe, str_date):
    """Добавляет столбцы с датой и днём недели в DataFrame расписания.

    Аргументы:
        dataframe (pd.DataFrame): Исходный DataFrame с расписанием
        str_date (str): Начальная дата в формате ДДММГГГГ

    Возвращает:
        pd.DataFrame: DataFrame с добавленными столбцами даты и дня недели
    """

    day_index = -1  # Начинаем перед понедельником (индекс 0)
    date = datetime.strptime(str_date, "%d%m%Y").date()
    date -= timedelta(days=1)  # Начинаем с предыдущего дня

    date_column = []
    day_column = []

    for _, row in dataframe.iterrows():
        current_time = row["Время"]

        # Если это первая пара дня, переходим на следующий день
        if current_time == FIRST_CLASS_TIME:
            day_index = (day_index + 1) % len(DAYS_OF_WEEK)
            date += timedelta(days=1)

        date_column.append(date.strftime("%d.%m.%Y"))
        day_column.append(DAYS_OF_WEEK[day_index])

    # Вставляем новые столбцы в начало
    dataframe.insert(0, "День недели", day_column)
    dataframe.insert(0, "Дата", date_column)

    return dataframe


def add_info_group(dataframe, name: str):
    """Добавляет данные об группе в таблицу

    Шифр группы
    AAAb-CDEE-FF-GG
    AAA - Направление (1-6 буквы)
    b - уровень образования
    C - курс
    D - код института
    EE - номер группы
    FF - номер профиля
    GG - форма обучения
    :param dataframe:
    :param name:
    :return pd.DataFrame:
    """
    # Регулярное выражение
    pattern = (r'^(?P<direction>[А-ЯЁа-яё]{1,6})(?P<education_level>[а-яё])-(?P<course>[0-9]{1})(?P<institute>[0-9]{'
               r'1})(?P<num_group>[0-9]{2})-(?P<profile>[0-9]{2})-(?P<form>[0-9]{2})$')
    group_name = re.fullmatch(pattern, name)
    # Вставляем каждый столбец на нужную позицию (0 - начало)
    dataframe.insert(0, 'форма_обучения', group_name.group('form'))
    dataframe.insert(0, 'институт', group_name.group('institute'))
    dataframe.insert(0, 'уровень_образования', group_name.group('education_level'))
    dataframe.insert(0, 'направление', group_name.group('direction'))
    '''dataframe = dataframe.assign(
        направление=group_name.group('direction'),
        уровень_образования=group_name.group('education_level'),
        институт=group_name.group('institute'),
        форма_обучения=group_name.group('form')
    )'''
    return dataframe


def save_to_csv(dataframe, csv_path):
    """Сохраняет DataFrame в CSV файл.

    Аргументы:
        dataframe (pd.DataFrame): Данные для сохранения
        csv_path (str): Путь к результирующему CSV файлу
    """
    dataframe.to_csv(csv_path, index=False, encoding='utf-8')


def pdf_to_csv(pdf_url, name_file, date):
    """Конвертирует PDF с расписанием в CSV с добавлением информации о дате.

    Аргументы:
        pdf_url (str): URL PDF файла
        name_file (str): Базовое имя выходного файла
        date (str): Начальная дата в формате ДДММГГГГ

    Возвращает:
        str: Путь к созданному CSV файлу

    Исключения:
        ValueError: Если PDF не может быть загружен или распарсен
    """
    try:
        response = requests.get(pdf_url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        raise ValueError(f"Ошибка загрузки PDF: {str(e)}")

    try:
        with pdfplumber.open(BytesIO(response.content)) as pdf:
            tables = []
            for page in pdf.pages:
                tables.extend(page.extract_tables())

            if not tables:
                raise ValueError("В PDF не найдено таблиц")

            # Обрабатываем таблицы (пропускаем заголовок в первой таблице)
            data = []
            for table_idx, table in enumerate(tables):
                rows = table[1:] if table_idx == 0 else table
                data.extend([row[1:] for row in rows])  # Пропускаем первый столбец

    except Exception as e:
        raise ValueError(f"Ошибка парсинга PDF: {str(e)}")

    # Создаём DataFrame со столбцами времени и пар
    df = pd.DataFrame(data, columns=["Время", "Пара"])
    df = add_date_of_week(df, date)
    df = add_info_group(df, name_file)

    # Сохраняем в CSV
    csv_filename = f"{clean_filename(name_file)}.csv"
    save_to_csv(df, csv_filename)

    #print(f"Данные сохранены в {csv_filename}")
    return csv_filename
