import logging
import os
import time
from sys import stdout
from typing import Dict, List

import requests
from dotenv import load_dotenv
from telegram import Bot

import exceptions


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(stream=stdout)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


def send_message(bot, message):
    """Функция отправляет сообщение в Telegram чат, определяемый
    переменной окружения TELEGRAM_CHAT_ID. Принимает на вход два параметра:
    экземпляр класса Bot и строку с текстом сообщения.
    """

    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        logger.error(f'Сбой при отправлении сообщения: {error}')
    else:
        logger.info('Отправлено сообщение в чат')


def get_api_answer(current_timestamp):
    """Функция делает запрос к единственному эндпоинту API-сервиса.
    В качестве параметра функция получает временную метку.
    В случае успешного запроса возвращает ответ API, преобразованный
    из формата JSON к типам данных Python.
    """

    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    homework_status = requests.get(
        ENDPOINT,
        headers=HEADERS,
        params=params
    )
    if homework_status.status_code != 200:
        raise Exception(
            'API возвращает код, отличный от 200')
    return homework_status.json()


def check_response(response):
    """Функция проверяет ответ API на корректность. В качестве параметра
    функция получает ответ API, приведенный к типам данных Python.
    """

    if not isinstance(response, Dict):
        raise TypeError(
            'Ошибка ответа API: Ответ не является словарём!')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, List):
        raise TypeError(
            'Ошибка ответа API: Домашки не являются списком!')
    if homeworks is None:
        raise exceptions.NoHWStatusChangeError('Статус домашки не поменялся.')
    return homeworks


def parse_status(homework):
    """Функция извлекает из информации о конкретной домашней работе
    статус этой работы. В качестве параметра функция получает только
    один элемент из списка домашних работ. В случае успеха, функция
    возвращает подготовленную для отправки в Telegram строку, содержащую
    один из вердиктов словаря HOMEWORK_STATUSES.
    """

    try:
        homework_name = homework.get('homework_name')
        homework_status = homework.get('status')
        if homework_status not in HOMEWORK_STATUSES:
            raise ValueError('Недокументированный статус домашней работы!')
    except ValueError as error:
        logger.error(error)
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Функция проверяет доступность переменных окружения, которые
    необходимы для работы программы. Если отсутствует хотя бы одна
    переменная окружения — функция должна вернуть False, иначе — True.
    """

    try:
        if not all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)):
            return False
    except NameError:
        return False
    except KeyError:
        return False
    return True


def error_log_and_message(bot, error, exc_info=False):
    """Функция логирует ошибку и отправляет сообщение в Телеграм-чат."""

    logger.error(error, exc_info=exc_info)
    bot.send_message(TELEGRAM_CHAT_ID, error)


def main():
    """Основная логика работы бота."""

    if not check_tokens():
        logger.critical('Отсутствуют обязательные переменные окружения')
        raise exceptions.TokenError('Необходимо определить токены и чат-ID!')

    bot = Bot(token=TELEGRAM_TOKEN)
    try:
        current_timestamp = int(time.time())
        if current_timestamp < 1637092500:
            raise exceptions.CurrentTimeError(
                'Текущее время определено неправильно')
    except exceptions.CurrentTimeError as error:
        error_log_and_message(bot, error)
    except Exception as error:
        message = f'Сбой в определении текущего времени: {error}'
        error_log_and_message(bot, message)

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            current_timestamp = int(response.get('current_date'))
        except TypeError as error:
            error_log_and_message(bot, error)
        except exceptions.NoHWStatusChangeError as error:
            logger.debug(error)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            error_log_and_message(bot, message, exc_info=True)
        else:
            for hw in homeworks:
                message = parse_status(hw)
                send_message(bot, message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
