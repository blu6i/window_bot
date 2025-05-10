from sql.add_info import (add_institutes, add_faculties,
                          add_specializations, add_departments)
from utils import logger

PATH_SUBJECTS = 'info_for_db/subjects.txt'
PATH_INST = 'info_for_db/institute.txt'
PATH_FAC = 'info_for_db/faculties.txt'
PATH_SPEC = 'info_for_db/spec.txt'
PATH_DEP = 'info_for_db/departament.txt'


def build_sql():
    add_institutes(PATH_INST)
    add_faculties(PATH_FAC)
    add_specializations(PATH_SPEC)
    add_departments(PATH_DEP)
    logger.info("Таблицы успешно созданы")
