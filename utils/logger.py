import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


def get_log_dir():
    """Определяет путь к папке с логами (на 2 уровня выше от utils/)"""
    try:
        # Базовый путь - на 2 уровня выше от расположения logger.py
        base_path = Path(__file__).absolute().parent.parent
        log_dir = base_path / "logs"  # Используем 'logs' вместо 'log' как более стандартный вариант

        # Создаем папку, если не существует
        log_dir.mkdir(parents=True, exist_ok=True)

        # Проверяем доступность папки для записи
        test_file = log_dir / ".write_test"
        try:
            test_file.touch()
            test_file.unlink()
        except (PermissionError, OSError) as e:
            raise RuntimeError(f"Нет прав на запись в {log_dir}: {e}")

        return log_dir

    except Exception as e:
        # Фолбэк на временную папку, если не удалось использовать основной путь
        temp_log_dir = Path("/tmp") / "myapp_logs"
        temp_log_dir.mkdir(exist_ok=True)
        return temp_log_dir


def setup_logger():
    """Настройка логгера с ротацией логов"""
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
