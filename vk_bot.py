from random import choice

import vk_api as vk
from enum import Enum, auto
from environs import Env
from redis import Redis
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id

from bot_utils.questions import get_questions
from bot_utils.redis_db_connection import get_redis_db_connection

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
    question, answer = choice(
        list(questions.items())
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

    return States.ANSWER, keyboard, answer


def handle_solution_attempt(event, vk_api, keyboard, answer):
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
        

def show_answer(event, vk_api, answer):
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


def show_score(event, vk_api, state, keyboard):
    vk_api.messages.send(
        user_id=event.user_id,
        message='Счет пока не ведется',
        random_id=get_random_id(),
        keyboard=keyboard.get_keyboard(),
    )
    return state, keyboard


def callback_request_default(event, vk_api, state, keyboard):
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
    return state, keyboard


def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
    logger.info('Started')
    env = Env()
    env.read_env()

    vk_session = vk.VkApi(token=env.str('VK_BOT_TOKEN'))
    vk_api = vk_session.get_api()
    longpoll = VkLongPoll(vk_session)

    db_connection  = get_redis_db_connection()
    logger.info(f'db_connection_ping: {db_connection.ping()}')

    questions = get_questions()
    state = None
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            logger.debug(state)
            if not state:
                state, keyboard = start(event, vk_api)
            elif state == States.REQUEST:
                if event.message == 'Новый вопрос':
                    state, keyboard, answer = handle_new_question_request(event, vk_api, questions, db_connection)
                elif event.message == 'Мой счёт':
                    state, keyboard = show_score(event, vk_api, state, keyboard)
                else:
                    state, keyboard = callback_request_default(event, vk_api, state, keyboard)
            elif state == States.ANSWER:
                if event.message == 'Новый вопрос':
                    state, keyboard = handle_new_question_request(event, vk_api, questions, db_connection)
                elif event.message == 'Мой счёт':
                    state, keyboard = show_score(event, vk_api, state, keyboard)
                elif event.message == 'Сдаться':
                    state, keyboard = show_answer(event, vk_api, answer)
                else:
                    state, keyboard = handle_solution_attempt(event, vk_api, keyboard, answer)
            else:
                continue


if __name__ == '__main__':
    main()
