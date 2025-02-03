import logging
import os
import sys
import time
from http import HTTPStatus

import requests
from dotenv import load_dotenv
from telebot import TeleBot

from exceptions import (InvalidHomeworkStatusError, PracticumAPIError,
                        TokenMissingError)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет наличие всех необходимых токенов."""
    required_tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    for token_name, token_value in required_tokens.items():
        if not token_value:
            logging.critical(
                f'Отсутствует обязательная переменная окружения: {token_name}'
            )
            raise TokenMissingError(token_name)
    return True


def send_message(bot, message):
    """Отправляет сообщение в Telegram-чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Бот отправил сообщение: {message}')
    except Exception as error:
        logging.error(f'Ошибка при отправке сообщения в Telegram: {error}')


def get_api_answer(timestamp):
    """Получает ответ от API."""
    try:
        response = requests.get(
            ENDPOINT, params={'from_date': timestamp}, headers=HEADERS
        )
    except requests.exceptions.RequestException as e:
        raise PracticumAPIError(f'Ошибка при запросе к API: {e}')

    if response.status_code != HTTPStatus.OK:
        raise PracticumAPIError(f'API вернул ошибку: {response.status_code}')

    return response.json()


def check_response(response):
    """Проверяет корректность ответа API."""
    if not isinstance(response, dict):
        raise TypeError(
            f'Ответ должен быть словарем, но получен: {type(response)}'
        )

    if 'homeworks' not in response:
        raise KeyError('Отсутствует ключ "homeworks" в ответе API')

    if not isinstance(response['homeworks'], list):
        raise TypeError('Ключ "homeworks" должен содержать список')

    return response['homeworks']


def parse_status(homework):
    """Извлекает статус домашней работы."""
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ "homework_name" в ответе API')

    if 'status' not in homework:
        raise KeyError('Отсутствует ключ "status" в ответе API')

    status = homework['status']
    homework_name = homework['homework_name']

    if status not in HOMEWORK_VERDICTS:
        raise InvalidHomeworkStatusError(status)

    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Отсутствует обязательная переменная окружения')
        raise TokenMissingError(
            'Отсутствует обязательная переменная окружения'
        )

    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_error = None

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)

            if homeworks:
                message = parse_status(homeworks[0])
                send_message(bot, message)
            else:
                logging.debug('Новых статусов нет')

            timestamp = response.get('current_date', timestamp)
        except PracticumAPIError as error:
            if str(error) != last_error:
                last_error = str(error)
                send_message(bot, f'Сбой в работе бота: {error}')
                logging.error(f'Сбой в работе бота: {error}')
        except Exception as error:
            logging.error(f'Необработанная ошибка: {error}')
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    main()
