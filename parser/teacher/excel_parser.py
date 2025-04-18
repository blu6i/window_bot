import re
from datetime import datetime, timedelta
from io import BytesIO
from parser.utils.formating_str import format_class

import pandas as pd
import requests

from utils import logger

KEYWORDS = ['Практическое', 'Лекция', 'Лабораторная', 'Консультация', 'Экзамен', 'Зачет', 'Защита ВКР']
DAYS_OF_WEEK = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота']
FIRST_CLASS_TIME = '08:20-09:50'
TIME_PATTERN = re.compile(r'^\d{2}:\d{2}-\d{2}:\d{2}$')
GROUP_PATTERN = re.compile(
    r'\b[А-ЯЁа-яё]{1,6}'
    r'[а-яё]-'
    r'\d{4}-'
    r'\d{2}-\d{2}\b'
)


def parse_schedule_table(link: str, departament: str, faculty: str) -> pd.DataFrame:
    """
    Парсит Excel-файл с расписанием, обрабатывая данные по столбцам (по преподавателям).
    Args:
        link (str): Путь к файлу Excel
        departament (str): кафедра
        faculty (str): факультет
    Returns:
        pd.DataFrame: DataFrame в формате [teacher, date, day, time, schedule]
    """
    # Загружаем файл, пропуская первую строку (заголовок таблицы)
    response = requests.get(link, timeout=10)
    with BytesIO(response.content) as excel_data:
        df = pd.read_excel(excel_data, header=1, engine='xlrd')
    logger.info(f'Расписание {faculty} загружено')
    # Получаем список преподавателей (с 3-го столбца, индексы Pandas: 2 и далее)
    teachers = df.columns[2:].tolist()

    # Список для хранения данных
    result_data = []
    # Проходим по каждому преподавателю (столбцу)
    for teacher in teachers:
        try:
            # Проверка, что в столбце есть информация
            if not 'Unnamed' in teacher:
                # Проходим по строкам
                for idx, row in df.iterrows():
                    # Получаем время из 2-го столбца (индекс 1)
                    time = row.iloc[1]

                    # Получение расписания
                    schedule_list = process_schedule_info(row[teacher], teacher, time)
                    # Добавляем запись
                    for schedule in schedule_list:
                        result_data.append(schedule)
            logger.info(f'Расписание {teacher} добавлено')
        except Exception as e:
            t = input()
            logger.warning(f'Ошибка при добавлении расписания {teacher} | {str(e)}')

    # Создаем DataFrame
    result_df = add_dates_to_schedule(pd.DataFrame(result_data), link)
    # Добавляем факультет, кафедру
    result_df.insert(0, 'departament', departament)
    result_df.insert(0, 'faculty', faculty)
    logger.info(f'Расписание {departament} обработано успешно')
    return result_df


def process_schedule_info(schedule_info: str, teacher: str, time: str) -> list[dict[str, str | None]]:
    """
    Извлечения групп из расписания
    Args:
        schedule_info (str) - расписание
        teacher (str) - ФИО преподавателя
        time (str) - время
    Returns:
        Массив со словарями
    """
    groups_list = re.findall(GROUP_PATTERN, str(schedule_info))
    if schedule_info:
        clear_schedule = format_class(schedule_info)
    else:
        clear_schedule = ''
    teacher_schedule = []
    if not groups_list:
        teacher_schedule.append({
            'teacher': teacher,
            'time': time,
            'subject': None,
            'group': None
        })
    last_group = ''
    for group in groups_list:
        if group != last_group:
            teacher_schedule.append({
                'teacher': teacher,
                'time': time,
                'subject': clear_schedule,
                'group': group
            })
        last_group = group
    return teacher_schedule


def add_dates_to_schedule(df: pd.DataFrame, patch: str) -> pd.DataFrame:
    """
    Добавляет столбцы с датой и днём недели в DataFrame расписания.
    Args:
        df (dataframe) - dataframe с расписанием
        patch (str) - ссылка на расписание
    Returns:
        Обновленный dataframe с датой
    """
    date_match = re.search(r'(\d{8}_\d{8})', patch.split('/')[-1])
    if not date_match:
        raise ValueError("Не удалось извлечь дату из URL расписания")
    start_date = date_match.group(1).split('_')[0]
    FIRST_DATE = datetime.strptime(start_date, "%d%m%Y").date()

    last_name = ''
    day_index = 0
    date = FIRST_DATE
    # Списки для дат и дней
    date_column = []
    day_column = []
    # Переменная для хранения предыдущего времени
    last_time = None

    for _, row in df.iterrows():
        current_time = row["time"]
        name = row["teacher"]
        if name != last_name:
            day_index = 0
            date = FIRST_DATE
        # Проверяем, является ли текущее время первым занятием И отличается ли от предыдущего
        elif current_time == FIRST_CLASS_TIME and current_time != last_time:
            day_index = (day_index + 1) % len(DAYS_OF_WEEK)
            # Проверка на новую неделю
            if day_index == 0:
                date += timedelta(days=2)
            else:
                date += timedelta(days=1)

        date_column.append(date.strftime("%d.%m.%Y"))
        day_column.append(DAYS_OF_WEEK[day_index])
        # Обновляем предыдущее значение времени/имени
        last_time = current_time
        last_name = name
    # Добавляем дату и дни в dataframe
    df["day"] = day_column
    df["date"] = date_column
    return df


def main():
    parsed_schedule = parse_schedule_table("517_1_14042025_27042025.xls")
    parsed_schedule.to_excel("temp.xlsx", index=False)
    print(parsed_schedule.head())


if __name__ == "__main__":
    main()
