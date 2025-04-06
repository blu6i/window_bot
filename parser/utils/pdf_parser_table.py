import pdfplumber
import pandas as pd
import re

from pandas import DataFrame


def parse_pdf_to_excel(pdf_file: str) -> DataFrame:
    """
    Парсит PDF таблицу, извлекает только время и расписание,
    игнорируя столбец с днем недели.
    """
    TIME_PATTERN = re.compile(r'^\d{2}:\d{2}-\d{2}:\d{2}$')  # Строго HH:MM-HH:MM

    def is_time(cell: str) -> bool:
        """Проверяет формат времени HH:MM-HH:MM."""
        if not isinstance(cell, str) or not cell.strip():
            return False
        return bool(TIME_PATTERN.match(cell.strip()))

    # Извлекаем данные из PDF
    with pdfplumber.open(pdf_file) as pdf:
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

            # Обновляем текущее время если найдено
            if time_in_columns:
                current_time = cells[time_in_columns[0]]
            elif current_time is None:
                continue  # Пропускаем если нет времени и current_time не установлен

            # Собираем части расписания
            schedule_parts = []
            start_index = time_in_columns[0] + 1 if time_in_columns else 0
            for cell in cells[start_index:]:
                if cell and not is_time(cell):
                    schedule_parts.append(cell)

            if schedule_parts or time_in_columns:
                schedule = " ".join(schedule_parts) if schedule_parts else ""
                processed_data.append((current_time, schedule))  # Только время и расписание

    if not processed_data:
        raise ValueError("Не найдено данных для сохранения")

    # Создаем DataFrame только с нужными столбцами
    df = pd.DataFrame(
        processed_data,
        columns=["Время", "Расписание"]
    )

    return df


if __name__ == "__main__":
    df = parse_pdf_to_excel("input.pdf")
    df.to_excel('output.xlsx', index=False, engine="openpyxl")