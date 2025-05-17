import logging
from logging import handlers
from logging.handlers import TimedRotatingFileHandler
import queue
import sys
from pathlib import Path


def get_log_dir():
    base_path = Path(__file__).absolute().parent.parent
    log_dir = base_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def setup_logger():
    logger = logging.getLogger("window_bot")
    logger.setLevel(logging.INFO)

    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    formatter = logging.Formatter(
        '%(asctime)s | %(filename)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Очередь логов
    log_queue = queue.Queue(-1)
    queue_handler = logging.handlers.QueueHandler(log_queue)
    logger.addHandler(queue_handler)

    # настройка логгера
    file_handler = TimedRotatingFileHandler(
        filename=get_log_dir() / "application.log",
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG)

    listener = logging.handlers.QueueListener(
        log_queue,
        file_handler,
        console_handler,
        respect_handler_level=True
    )
    listener.start()

    return logger


logger = setup_logger()
logger.info("Нам IIZ6a!")
