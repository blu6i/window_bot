import re

KEYWORDS = ['Практическое', 'Лекция', 'Лабораторная', 'Консультация', 'Экзамен', 'Зачет', 'Защита ВКР']
TIME_PATTERN = re.compile(r'^\d{2}:\d{2}-\d{2}:\d{2}$')
GROUP_PATTERN = re.compile(
    r'\b[А-ЯЁа-яё]{1,6}'
    r'[а-яё]-'
    r'\d{4}-'
    r'\d{2}-\d{2}\b'
)
# Формат аудитории
CLASS_PATTERN = re.compile(r'\b\d{1,2}\s*-\s*\d{3}[А-ЯЁа-яё_]?[А-ЯЁа-яё_]?\b')
# Формат цифр в скокбах
NUM_PATTERN = re.compile(r'\(\d+ \d+\)')
# Формат ФИО
FIO_PATTERN = re.compile(r'[А-ЯЁ][а-яё]+\s[А-ЯЁ]\.[А-ЯЁ]\.')


def fix_line_breaks(text: str) -> str:
    """
    Убирает переносы строк
    """
    if not isinstance(text, str):
        text = str(text)

    # Обрабатываем переносы, но защищаем URL и специальные последовательности
    text = re.sub(r'(?<!\w)\n(?!\w)', ' ', text)  # Одиночные переносы
    text = re.sub(r'(\S)\n(\S)', r'\1 \2', text)  # Переносы между словами
    return text.strip()


def format_class(study: str) -> str:
    """
    Форматирует строку с названием занятия:
    1. Удаляет название группы, если оно есть
    2. Удаляет номера аудиторий
    3. Обрезает до первого типа занятия

    Args:
        study: Исходная строка с названием занятия

    Returns:
        Отформатированная строка или пустая строка, если нет занятия
    """
    if str(study) == 'nan':
        return ''
    study = fix_line_breaks(study)
    # Удаляем название группы, если оно есть
    cleaned_text = re.sub(GROUP_PATTERN, "", str(study)).rstrip('.').strip()

    # Удаляем номера аудиторий формата "8-310А"
    cleaned_text = re.sub(CLASS_PATTERN, '', cleaned_text)

    # Удаляем цифры в скобках
    cleaned_text = re.sub(NUM_PATTERN, '', cleaned_text)

    # Удаляем фамилии (Опционально для расписания студентов)
    cleaned_text = re.sub(FIO_PATTERN, '', cleaned_text)
    # Проверка, что после чистки строка не стала пустой или цифрой
    if not cleaned_text or cleaned_text.isnumeric():
        return ''

    # Ищем заглавные буквы
    uppercase_in_text = None
    for s in cleaned_text:
        if s.isupper():
            uppercase_in_text = s
            break

    # Определяем позиции ключевых слов
    positions = None
    for keyword in KEYWORDS:
        pos = cleaned_text.find(keyword)
        if pos != -1:
            positions = pos
            break

    # Если нашли ключевые слова - обрезаем до первого из них
    if positions:
        start = cleaned_text.find(uppercase_in_text)
        return cleaned_text[start:positions].strip()

    # Если ключевых слов нет, возвращаем текст от первой заглавной буквы
    start = cleaned_text.find(uppercase_in_text)
    format_text = cleaned_text.split(',')[0]
    return format_text[start:].strip()
