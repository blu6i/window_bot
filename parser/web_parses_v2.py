import logging
import re
from dataclasses import dataclass
from datetime import datetime, date
from time import sleep
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)
LINK = "https://www.vyatsu.ru/studentu-1/spravochnaya-informatsiya/raspisanie-zanyatiy-dlya-studentov.html"

FACULTIES = {
    "Дирекция ОП Пединститута (ОРУ)": "ФПП",
    "Институт биологии и биотехнологии (факультет)(ОРУ)": "ИББТ",
    "Институт химии и экологии (факультет) (ОРУ)": "ИнХимЭк",
    "Факультет автоматики и вычислительной техники (ОРУ)": "ФАВТ",
    "Факультет истории, политических наук и культурологии (ОРУ)": "ФИПНК",
    "Факультет компьютерных и физико-математических наук (ОРУ)": "ФКиФМН",
    "Факультет лингвистики (ОРУ)": "ФЛ",
    "Факультет международного образования (ОРУ)": "ФМО",
    "Факультет менеджмента и сервиса (ОРУ)": "ФМиС",
    "Факультет педагогики и психологии (ОРУ)": "ФПП",
    "Факультет строительства и архитектуры (ОРУ)": "ФСА",
    "Факультет технологий, инжиниринга и дизайна (ОРУ)": "ФТИД",
    "Факультет физической культуры и спорта (ОРУ)": "ФФКС",
    "Факультет филологии и медиакоммуникаций (ОРУ)": "ФФМ",
    "Факультет экономики и финансов (ОРУ)": "ФЭиФ",
    "Электротехнический факультет (ОРУ)": "ЭТФ",
    "Юридический институт (факультет) (ОРУ)": "ЮИ"
}


def setup_driver():
    """Настройка и инициализация веб-драйвера"""
    options = Options()
    options.add_argument("--disable-extensions")
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except Exception as e:
        logging.error(f"Ошибка инициализации WebDriver: {str(e)}")
        raise


@dataclass(frozen=True)
class GroupScheduleDTO:
    """Неизменяемый DTO для расписания группы."""
    institute: str  # Код института (1 цифра)
    faculty: str  # Название факультета (из Selenium)
    direction: str  # Направление (1-6 букв)
    education_level: str  # Уровень образования (буква)
    education_form: str  # Форма обучения (2 цифры)
    schedule_url: str  # Ссылка на расписание

    def __post_init__(self):
        """Валидация данных при создании DTO."""
        if not re.match(r'^[0-9]$', self.institute):
            raise ValueError(f"Некорректный код института: {self.institute}")
        if not re.match(r'^[а-яё]$', self.education_level.lower()):
            raise ValueError(f"Некорректный уровень образования: {self.education_level}")
        if not re.match(r'^[0-9]{2}$', self.education_form):
            raise ValueError(f"Некорректная форма обучения: {self.education_form}")


def parse_group_name(
        group_name: str,
        faculty: str,
        schedule_url: str,
) -> Optional[GroupScheduleDTO]:
    """Заполняет информацию об группе и возвращает DTO.

    Args:
        group_name: Название группы (формат: AAAb-CDEE-FF-GG).
        faculty: Название факультета (из Selenium).
        schedule_url: Ссылка на расписание.

    Returns:
        GroupScheduleDTO или None (если название невалидно).
    """
    pattern = (
        r'^(?P<direction>[А-ЯЁа-яё]{1,6})'
        r'(?P<education_level>[а-яё])-'
        r'(?P<course>[0-9])'
        r'(?P<institute>[0-9])'
        r'(?P<group_num>[0-9]{2})-'
        r'(?P<profile>[0-9]{2})-'
        r'(?P<education_form>[0-9]{2})$'
    )

    if not (match := re.fullmatch(pattern, group_name)):
        logger.error(f"Неверный формат группы: {group_name}")
        return None

    try:
        return GroupScheduleDTO(
            institute=match.group("institute"),
            faculty=faculty,
            direction=match.group("direction"),
            education_level=match.group("education_level"),
            education_form=match.group("education_form"),
            schedule_url=schedule_url,
        )
    except ValueError as e:
        logger.error(f"Ошибка валидации: {e}")
        return None


def get_current_semester():
    """Определяет текущий семестр (1 или 2)"""
    today = datetime.now()

    # Определяем год начала учебного года (если сейчас январь, учебный год начался в прошлом году)
    year = today.year if today.month >= 9 else today.year - 1

    # Даты начала семестров
    first_semester_start = datetime(year, 9, 1)  # 1 сентября
    second_semester_start = datetime(year + 1, 2, 1)  # 1 февраля следующего года

    if first_semester_start <= today < second_semester_start:
        return 0  # Первый семестр
    else:
        return 1  # Второй семестр


def get_date_range(link):
    url = link.split('/')[-1]
    res = re.search(r'(\d{8}_\d{8})', url)
    return res.group(1)


'''def get_actual_date(period_date):
    """Требуется поменять логику для отбора расписания
    Расписание на 4-ую неделю не сразу появляется,
    а следовательно там будут окна"""
    periods = period_date.find_elements(By.TAG_NAME, 'a')
    date_range = []
    if len(periods) >= 2:
        date_range.append(get_date_range(periods[0].get_attribute('href')))
        date_range.append(get_date_range(periods[1].get_attribute('href')))
    else:
        date_range.append(get_date_range(periods[0].get_attribute('href')))
    return date_range'''


def get_current_semester_start(current_date: datetime.date) -> datetime.date:
    """Определяет начало текущего семестра (ближайший понедельник)."""
    year = current_date.year

    if 2 <= current_date.month <= 8:  # 2-й семестр (февраль–август)
        semester_start = datetime.date(year, 2, 1)
    else:  # 1-й семестр (сентябрь–январь)
        if current_date.month >= 9:
            semester_start = datetime.date(year, 9, 1)
        else:  # январь
            semester_start = datetime.date(year - 1, 9, 1)

    # Коррекция на понедельник (если начало семестра не понедельник)
    if semester_start.weekday() != 0:  # 0 = понедельник
        days_until_monday = (7 - semester_start.weekday()) % 7
        semester_start += datetime.timedelta(days=days_until_monday)

    return semester_start


def get_actual_date() -> list[str]:
    """
    Возвращает массив из двух строк с датами:
    - Текущий двухнедельный диапазон
    - Следующий двухнедельный диапазон
    Формат каждой строки: "DDMMYYYY_DDMMYYYY"
    """
    current_date = date.today()

    semester_start = get_current_semester_start(current_date)

    if current_date < semester_start:
        raise ValueError("Текущая дата раньше начала семестра!")

    delta_days = (current_date - semester_start).days
    block_number = delta_days // 14

    # Текущий диапазон (14 дней)
    current_start = semester_start + datetime.timedelta(days=block_number * 14)
    current_end = current_start + datetime.timedelta(days=13)

    # Следующий диапазон (14 дней)
    next_start = current_end + datetime.timedelta(days=1)
    next_end = next_start + datetime.timedelta(days=13)

    def format_date(date: datetime.date) -> str:
        return date.strftime("%d%m%Y")

    return [
        f"{format_date(current_start)}_{format_date(current_end)}",  # Текущий
        f"{format_date(next_start)}_{format_date(next_end)}"  # Следующий
    ]


def parse_schedule(driver, wait):
    """Основная логика парсинга расписания"""
    try:
        # Открытие сайта
        driver.get(LINK)
        logging.info("Сайт успешно загружен")
        # Получение факультетов
        fak_list = wait.until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "fak_name"))
        )
        actual_date = get_actual_date()
        print(len(actual_date))
        # Обход всех факультетов
        for fak in fak_list:
            fak.click()
            sleep(0.5)
            # Получение сокращенного имени факультета
            fak_name = FACULTIES.get(fak.text)
            # Получение элемента факультета с расписанием групп
            fak_id = f'fak_id_{fak.get_attribute("data-fak_id")}'
            element = wait.until(
                EC.presence_of_element_located((By.ID, fak_id))
            )
            # Получение расписания
            period_list = element.find_elements(By.CLASS_NAME, 'listPeriod')
            # Имена групп
            group_list = element.find_elements(By.CLASS_NAME, 'grpPeriod')
            print(f'Групп: {len(group_list)} - расписаний: {len(period_list)}')
            # Получения семестра
            #semestr = get_current_semester()
            # Получение актуальной даты для расписания


            for i in range(len(period_list)):
                link_list = period_list[i].find_elements(By.TAG_NAME, 'a')
                for link in link_list:
                    for date in actual_date:
                        url = link.get_attribute("href")
                        #link = wait.until(
                        #    period_list[i].presence_of_element_located(
                        #        (By.CSS_SELECTOR, f"div.listPeriod>a[href*='{date}']"))
                        #).get_attribute('href')
                        #link = period.find_element(By.CSS_SELECTOR, f"div.listPeriod>a[href*='{date}']").get_attribute('href')
                        if date in url.split('/')[-1]:
                            name_group = group_list[i]
                            print('----------')
                            print(name_group.text)
                            print(url)
                            print('----------')

    except Exception as e:
        logging.error(f"Ошибка при парсинге расписания: {str(e)}")
        return None


def main():
    """Основная функция"""
    driver = setup_driver()
    wait = WebDriverWait(driver, 15)  # Увеличенное время ожидания
    parse_schedule(driver, wait)
    driver.quit()


if __name__ == "__main__":
    main()
