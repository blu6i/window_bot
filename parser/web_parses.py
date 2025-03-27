from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from time import sleep
import re
from pdf_parser import pdf_to_csv


options = Options()
options.add_experimental_option("detach", True)

try:
    # Настройка браузера
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 10)

    # Открытие сайта
    driver.get("https://www.vyatsu.ru/studentu-1/spravochnaya-informatsiya/raspisanie-zanyatiy-dlya-studentov.html")

    # Поиск и прокликивание по факультетам
    fak_list = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "fak_name")))
    for fak in fak_list:
        fak.click()
        sleep(0.3)

    # Получение данных
    group_name_link = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'grpPeriod')))
    period_list = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'listPeriod')))

    # Получение даты актуального расписания
    # Требуется написать логику получения четного и нечетного семестра
    # Скорее всего использовать библиотеку time
    url = period_list[1].find_element(By.TAG_NAME, 'a').get_attribute("href")
    t = re.search(r'(\d{8}_\d{8})', url)
    dataRange = t.group(1)

    schedule_data = {}
    print(len(group_name_link))
    for i in range(0, len(group_name_link)):
        try:
            link = period_list[i].find_element(By.TAG_NAME, 'a').get_attribute("href")
            if dataRange in link.split('/')[-1]:
                name = group_name_link[i].text.strip()
                schedule_data[name] = link
        except NoSuchElementException:
            continue

    # 5. Вывод результатов
    if not schedule_data:
        print("Данные не найдены")
    else:
        for name, link in schedule_data.items():
            print(f"Группа: {name}\nСсылка: {link}\n{'=' * 50}")
            pdf_to_csv(link, name)
        print(dataRange)

except TimeoutException:
    print("Превышено время ожидания элементов")
except NoSuchElementException:
    print("Не удалось найти необходимые элементы")
except WebDriverException as e:
    print(f"Ошибка браузера: {str(e)}")
finally:
    driver.quit()
