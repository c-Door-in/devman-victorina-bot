from random import choice

import vk_api as vk
from enum import Enum, auto
from environs import Env
from redis import Redis
from time import sleep
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id

from bot_utils.questions import get_questions

import logging


logger = logging.getLogger(__name__)


class States(Enum):
    REQUEST = auto()
    ANSWER = auto()


def start(event, vk_api):
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button('Новый вопрос', color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button('Мой счёт', color=VkKeyboardColor.SECONDARY)
    vk_api.messages.send(
        user_id=event.user_id,
        message='Привет! Это викторина для определения твоей сообразительности. Начнем?',
        random_id=get_random_id(),
        keyboard=keyboard.get_keyboard(),
    )
    return States.REQUEST, keyboard


def handle_new_question_request(event, vk_api, questions, db_connection):
    question = choice(
        list(questions.keys())
    )
    db_connection.set(event.user_id, question)
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button('Новый вопрос', color=VkKeyboardColor.SECONDARY)
    keyboard.add_button('Сдаться', color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button('Мой счёт', color=VkKeyboardColor.SECONDARY)
    vk_api.messages.send(
        user_id=event.user_id,
        message=question,
        random_id=get_random_id(),
        keyboard=keyboard.get_keyboard(),
    )

    return States.ANSWER, keyboard


def handle_solution_attempt(event, vk_api, keyboard, questions, db_connection):
    answer = questions[db_connection.get(event.user_id)]
    short_answer = answer
    for simbol in ('(', '.'):
        if simbol in answer:
            short_answer = answer.split(simbol)[0]
            break
    
    if not short_answer.lower().strip() in event.message.lower().strip():
        vk_api.messages.send(
            user_id=event.user_id,
            message='Неправильно… Попробуешь ещё раз?',
            random_id=get_random_id(),
            keyboard=keyboard.get_keyboard(),
        )
        return States.ANSWER, keyboard

    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button('Новый вопрос', color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button('Мой счёт', color=VkKeyboardColor.SECONDARY)
    vk_api.messages.send(
        user_id=event.user_id,
        message=f'Правильно! Поздравляю!\nОтвет:\n{answer}\nДля следующего вопроса нажми «Новый вопрос».',
        random_id=get_random_id(),
        keyboard=keyboard.get_keyboard(),
    )
    return States.REQUEST, keyboard
        

def show_answer(event, vk_api, questions, db_connection):
    answer = questions[db_connection.get(event.user_id)]
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button('Новый вопрос', color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button('Мой счёт', color=VkKeyboardColor.SECONDARY)
    vk_api.messages.send(
        user_id=event.user_id,
        message=f'Ответ вот такой:\n{answer}\nДля нового вопроса нажми "Новый вопрос"',
        random_id=get_random_id(),
        keyboard=keyboard.get_keyboard(),
    )
    return States.REQUEST, keyboard


def show_score(event, vk_api, keyboard):
    vk_api.messages.send(
        user_id=event.user_id,
        message='Счет пока не ведется',
        random_id=get_random_id(),
        keyboard=keyboard.get_keyboard(),
    )
    return keyboard


def callback_request_default(event, vk_api, keyboard):
    vk_api.messages.send(
        user_id=event.user_id,
        message=choice(['Может начнем?',
                        'Нажми кнопку!',
                        'Кнопка внизу.',
                        'Не пиши, а нажми...',
                        'Как будешь готов - позови.',
                        'Зачем ты это делаешь?',
                        'Здесь вопросы задаю я!',
                        'Просто нажми эту кнопку!']),
        random_id=get_random_id(),
        keyboard=keyboard.get_keyboard(),
    )
    return keyboard


def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.DEBUG)
    logger.info('Started')
    env = Env()
    env.read_env()

    db_connection  = Redis(
        host=env.str('REDIS_HOST'),
        port=env.str('REDIS_PORT'),
        username=env.str('REDIS_USERNAME', default='default'),
        password=env.str('REDIS_PASSWORD'),
        decode_responses=True,
    )
    logger.info(f'db_connection_ping: {db_connection.ping()}')
    questions = get_questions()

    vk_session = vk.VkApi(token=env.str('VK_BOT_TOKEN'))
    while True:
        try:
            vk_api = vk_session.get_api()
            longpoll = VkLongPoll(vk_session)
            states = {}
            for event in longpoll.listen():
                logger.debug(f'Event_type is NEW_MESSAGE?: {event.type == VkEventType.MESSAGE_NEW}, to me?: {event.to_me}')
                if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                    user_id = event.user_id
                    if not user_id in states:
                        logger.debug(f'User state is None')
                        states[user_id], keyboard = start(event, vk_api)
                    elif states[user_id] == States.REQUEST:
                        if event.message == 'Новый вопрос':
                            states[user_id], keyboard = handle_new_question_request(event, vk_api, questions, db_connection)
                        elif event.message == 'Мой счёт':
                            keyboard = show_score(event, vk_api, keyboard)
                        else:
                            keyboard = callback_request_default(event, vk_api, keyboard)
                    elif states[user_id] == States.ANSWER:
                        if event.message == 'Новый вопрос':
                            states[user_id], keyboard = handle_new_question_request(event, vk_api, questions, db_connection)
                        elif event.message == 'Мой счёт':
                            keyboard = show_score(event, vk_api, keyboard)
                        elif event.message == 'Сдаться':
                            states[user_id], keyboard = show_answer(event, vk_api, questions, db_connection)
                        else:
                            states[user_id], keyboard = handle_solution_attempt(event, vk_api, keyboard, questions, db_connection)
        except Exception:
            logger.exception('Ошибка в devman-victorina-vkbot. Перезапуск через 15 секунд.')
            sleep(15)


if __name__ == '__main__':
    main()
