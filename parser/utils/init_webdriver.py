from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from utils import logger


def setup_driver() -> WebDriver:
    """Настройка и инициализация веб-драйвера"""
    options = Options()
    options.add_argument("--disable-extensions")
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        logger.info(f'WebDriver инициализирован')
        return driver
    except Exception as e:
        logger.error(f"Ошибка инициализации WebDriver: {str(e)}")
        raise


def init_driver() -> tuple[WebDriver, WebDriverWait]:
    driver = setup_driver()
    wait = WebDriverWait(driver, 15)
    return driver, wait
