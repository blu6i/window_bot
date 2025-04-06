from parser import parse_schedule, parser_pdf
from utils import logger

LINK = "https://www.vyatsu.ru/studentu-1/spravochnaya-informatsiya/raspisanie-zanyatiy-dlya-studentov.html"


def main():
    groups = parse_schedule(LINK)
    for group_data in groups:
        group = parser_pdf(group_data)
        filename = f"data/{group_data['group']}.csv"
        group.to_csv(filename, index=False, encoding='utf-8')
        logger.info(f'Данные сохранены в {filename}')


if __name__ == '__main__':
    main()