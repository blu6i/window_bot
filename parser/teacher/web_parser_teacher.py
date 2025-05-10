import re
from datetime import date, timedelta
from time import sleep
from typing import Any

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from .excel_parser import parse_schedule_table
from utils import logger
from parser.utils.init_webdriver import init_driver

LINK = "https://www.vyatsu.ru/studentu-1/spravochnaya-informatsiya/teacher.html"

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


def get_current_semester_start(current_date: date) -> date:
    """Определяет начало текущего семестра (ближайший понедельник)."""
    year = current_date.year

    if 2 <= current_date.month <= 8:  # 2-й семестр (февраль–август)
        semester_start = date(year, 2, 1)
    else:  # 1-й семестр (сентябрь–январь)
        if current_date.month >= 9:
            semester_start = date(year, 9, 1)
        else:  # январь
            semester_start = date(year - 1, 9, 1)

    # Коррекция на понедельник (если начало семестра не понедельник)
    if semester_start.weekday() != 0:  # 0 = понедельник
        days_until_monday = (7 - semester_start.weekday()) % 7
        semester_start += timedelta(days=days_until_monday)

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
    current_start = semester_start + timedelta(days=block_number * 14)
    current_end = current_start + timedelta(days=13)

    # Следующий диапазон (14 дней)
    next_start = current_end + timedelta(days=1)
    next_end = next_start + timedelta(days=13)

    def format_date(d: date) -> str:
        return d.strftime("%d%m%Y")

    return [
        f"{format_date(current_start)}_{format_date(current_end)}",
        f"{format_date(next_start)}_{format_date(next_end)}"
    ]


def parse_schedule_teacher(link: str) -> list[dict[str, Any] | None]:
    try:
        driver, wait = init_driver()
        driver.get(link)
        logger.info('Сайт с расписанием преподавателей загружен')
        fak_list = wait.until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, 'fak_name'))
        )
        actual_date = get_actual_date()
        teachers = []
        for fak in fak_list:
            fak.click()
            sleep(0.5)
            fak_name = FACULTIES.get(fak.text)
            logger.debug(f'Обработка факультета  {fak_name}')
            fak_id = f'fak_id_{fak.get_attribute("data-fak_id")}'
            element = wait.until(
                EC.presence_of_element_located((By.ID, fak_id))
            )
            # Получение расписания
            period_list = element.find_elements(By.CLASS_NAME, 'listPeriod')
            # Название кафедр
            kaf_list = element.find_elements(By.CLASS_NAME, 'kafPeriod')
            for i in range(len(period_list)):
                link_list = period_list[i].find_elements(By.TAG_NAME, 'a')
                logger.debug(f'Обработка кафедры {kaf_list[i].text}')
                for link in link_list:
                    for year in actual_date:
                        url = link.get_attribute('href')
                        if year in url.split('/')[-1] and '.xls' in url.split('/')[-1]:
                            form = {'departament': kaf_list[i].text,
                                    'faculty': fak.text,
                                    'link': url}
                            logger.info(f'У кафедры {kaf_list[i].text} найдено расписание за {year}')
                            parse_schedule_table(link=form['link'],
                                                 departament=form['departament'],
                                                 faculty=form['faculty'])
                            #teachers.append(form)
        logger.info('Парсинг сайта завершен успешно')
        # return teachers
    except Exception as e:
        logger.info(f'Ошибка при парсинге расписания: {str(e)}')

    finally:
        driver.quit()


def main():
    link = parse_schedule_teacher(LINK)
    for i in link:
        print(f"{i}\n\n")


if __name__ == '__main__':
    main()
