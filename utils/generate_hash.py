import hashlib
import os

from dotenv import load_dotenv

load_dotenv('../../../config/.env')
TOKEN = os.getenv('HASH_TOKEN')


def generate_hash(fullname: str) -> str:
    """
    Генерирует хэш на основе полного имени преподавателя и секретного ключа из .env
    """
    data_to_hash = TOKEN + fullname.strip()
    return hashlib.sha256(data_to_hash.encode('utf-8')).hexdigest()


if __name__ == '__main__':
    print(generate_hash('iditudasudaobratnoandeiwwdfnf@@@@'))
