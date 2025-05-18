from datetime import datetime


def get_rus_date(date_str: str) -> list[str]:
    """
    Преобразует строку с датой в формате 'YYYY-MM-DD' в формат 'DD.MM.YYYY (День недели)'
    """
    weekdays = {
        0: "Понедельник",
        1: "Вторник",
        2: "Среда",
        3: "Четверг",
        4: "Пятница",
        5: "Суббота",
        6: "Воскресенье"
    }

    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")

        weekday_num = date_obj.weekday()
        weekday = weekdays[weekday_num]

        formatted_date = date_obj.strftime("%d.%m.%Y")

        return [formatted_date, weekday]  #f"{formatted_date} ({weekday})"

    except ValueError as e:
        raise ValueError(f"Некорректный формат даты: {e}")


def date_format_db(text: str) -> str:
    """Преобразование строки вида DD, DD.MM, DD.MM.YY(YY) в YYYY-MM-DD с учетом перехода на следующий месяц"""
    try:
        today = datetime.now()
        parts = list(map(int, text.split(".")))

        if len(parts) == 1:
            day = parts[0]
            month = today.month
            year = today.year
            try:
                temp_date = datetime(year, month, day)
                if temp_date.date() < today.date():
                    # День уже прошел в этом месяце -> следующий месяц
                    if month == 12:
                        month = 1
                        year += 1
                    else:
                        month += 1
            except ValueError:
                # День не существует в этом месяце, пробуем следующий месяц
                if month == 12:
                    month = 1
                    year += 1
                else:
                    month += 1

        elif len(parts) == 2:
            day, month = parts
            year = today.year

        elif len(parts) == 3:
            day, month, year = parts
            # Преобразуем двухзначный год в четырехзначный
            if year < 100:
                current_century = (today.year // 100) * 100
                if year <= today.year % 100 + 20:
                    year = current_century + year
                else:
                    year = current_century - 100 + year

        date_obj = datetime(year, month, day)
        return date_obj.strftime("%Y-%m-%d")

    except Exception as e:
        raise