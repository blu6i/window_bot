import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


def get_log_dir():
    """Определяет путь к папке с логами (на 2 уровня выше от utils/)"""
    # Базовый путь - на 2 уровня выше от расположения logger.py
    base_path = Path(__file__).absolute().parent.parent
    log_dir = base_path / "logs"

    # Создаем папку, если не существует
    log_dir.mkdir(parents=True, exist_ok=True)

    return log_dir


def setup_logger():
    """Настройка логгера"""
    logger = logging.getLogger("window_bot")
    logger.setLevel(logging.INFO)  # Минимальный уровень логирования

    # Очищаем существующие обработчики
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Формат сообщений
    formatter = logging.Formatter(
        '%(asctime)s | %(filename)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    try:
        log_dir = get_log_dir()

        # Файловый обработчик с ротацией
        file_handler = TimedRotatingFileHandler(
            filename=log_dir / "application.log",
            when="midnight",
            interval=1,
            backupCount=7,
            encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)

    except Exception as e:
        sys.stderr.write(f"Ошибка настройки файлового логгера: {e}\n")

    # Консольный обработчик (дублирование в stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)

    return logger


# Инициализация глобального логгера
logger = setup_logger()

# Тестовое сообщение при инициализации
logger.info("Логгер успешно настроен, путь к логам: %s", get_log_dir())
