from enum import Enum, auto
from environs import Env
from redis import Redis
from random import choice
from time import sleep
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, RegexHandler

from bot_utils.questions import get_questions
from bot_utils.redis_db_connection import get_redis_db_connection

import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


class States(Enum):
    REQUEST = auto()
    ANSWER = auto()


def start(update, context):
    keyboard = [
        ['Новый вопрос'],
        ['Мой счёт'],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    update.message.reply_text(
        'Привет! Это викторина для определения твоей сообразительности. Начнем?',
        reply_markup=reply_markup,
    )

    return States.REQUEST


def handle_new_question_request(update, context):
    user_id = update.effective_user.id
    question, answer = choice(
        list(context.bot_data['questions'].items())
    )
    context.chat_data['current_answer'] = answer
    context.bot_data['db_connection'].set(user_id, question)
    keyboard = [
        ['Новый вопрос', 'Сдаться'],
        ['Мой счёт'],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    update.message.reply_text(question, reply_markup=reply_markup)

    return States.ANSWER


def handle_solution_attempt(update, context):
    text = update.message.text
    answer = context.chat_data['current_answer']
    short_answer = answer
    for sign in ('(', '.'):
        if sign in answer:
            short_answer = answer.split(sign)[0]
            break

    if short_answer.lower().strip() in text.lower().strip():
        keyboard = [
            ['Новый вопрос'],
            ['Мой счёт'],
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        update.message.reply_text(
            f'Правильно! Поздравляю!\nОтвет:\n{answer}\nДля следующего вопроса нажми «Новый вопрос».',
            reply_markup=reply_markup,
        )
        return States.REQUEST
    else:
        keyboard = [
            ['Новый вопрос', 'Сдаться'],
            ['Мой счёт'],
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        update.message.reply_text(
            'Неправильно… Попробуешь ещё раз?',
            reply_markup=reply_markup,
        )
        return States.ANSWER


def show_answer(update, context):
    answer = context.chat_data['current_answer']
    keyboard = [
        ['Новый вопрос'],
        ['Мой счёт'],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    update.message.reply_text(
        f'Ответ вот такой:\n{answer}\nДля нового вопроса нажми "Новый вопрос"',
        reply_markup=reply_markup,
    )
    
    return States.REQUEST


def show_score(update, context):
    update.message.reply_text('Счет пока не ведется')


def callback_request_default(update, context):
    text = choice(['Может начнем?',
                   'Нажми кнопку!',
                   'Кнопка внизу.',
                   'Не пиши, а нажми...',
                   'Как будешь готов - позови.',
                   'Зачем ты это делаешь?',
                   'Здесь вопросы задаю я!',
                   'Просто нажми эту кнопку!'])
    keyboard = [
        ['Новый вопрос'],
        ['Мой счёт'],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    update.message.reply_text(text, reply_markup=reply_markup)


def cancel(update, context):
    username = update.effective_user.first_name
    logger.info(f'User {username} canceled the conversation.')
    update.message.reply_text('До встречи!',
                              reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


def error(update, error):
    """Log Errors caused by Updates."""
    logger.warning(f'Update "{update}" caused error "{error}"')


def main():
    env = Env()
    env.read_env()
    
    db_connection = get_redis_db_connection()
    logger.info(f'db_connection_ping: {db_connection.ping()}')
    questions = get_questions()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            States.REQUEST: [
                MessageHandler(Filters.regex('^Новый вопрос$'), handle_new_question_request),
                MessageHandler(Filters.regex('^Мой счёт$'), show_score),
                MessageHandler(Filters.text, callback_request_default),
            ],
            States.ANSWER: [
                MessageHandler(Filters.regex('^Новый вопрос$'), handle_new_question_request),
                MessageHandler(Filters.regex('^Мой счёт$'), show_score),
                MessageHandler(Filters.regex('^Сдаться$'), show_answer),
                MessageHandler(Filters.text, handle_solution_attempt)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    while True:
        try:
            updater = Updater(token=env.str('TG_BOT_TOKEN'))
            dp = updater.dispatcher
            dp.add_handler(conv_handler)
            dp.add_error_handler(error)
            dp.bot_data = {
                'db_connection': db_connection,
                'questions': questions,
            }
            updater.start_polling()
            updater.idle()
        except Exception:
            logger.exception('Ошибка в devman-victorina-tgbot. Перезапуск через 15 секунд.')
            sleep(15)


if __name__ == '__main__':
    main()