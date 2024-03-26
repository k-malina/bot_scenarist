import telebot
from ya_gpt import create_promt, ask_gpt, count_tokens_in_dialogue
from config import MAX_USERS, MAX_SESSIONS, MAX_USER_TOKENS
import logging

from configconfig import token
bot = telebot.TeleBot(token)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="log_file.txt",
    filemode="w",
)

u_data = {}
exist_options = {
    'genres': ['комедия', 'детектив', 'фантастика'],
    'characters': ['Черная вдова (Наташа Романофф)', 'Рапунцель', 'Леонардо Ди Каприо', 'Танос'],
    'settings': ['Дубай', 'Айсберг', 'Межгалактический корабль']
}


def create_keyboard(options):
    buttons = []
    for option in options:
        buttons.append(telebot.types.KeyboardButton(text=option))

    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(*buttons)
    return keyboard


def bybye_text(user_id):
    bot.send_message(user_id, text='Лимит токенов исчерпан, сорри')

@bot.message_handler(commands=['start'])
def start(message):
    global u_data
    u_id = message.from_user.id

    if len(u_data) >= MAX_USERS:
        bybye_text(u_id)
        return

    bot.send_message(u_id, text='Привет, я бот-сценарист :) Основываясь на выбранном тобой жанре, персонаже, и локации,'
                                'я буду генерировать сценарий. Количество токенов и сессий на каждого польщователя ограниченно.'
                                '',
                     reply_markup=create_keyboard(['/new_story']))

    if u_id not in u_data:
        u_data[u_id] = {
            'session_id': 0,
            'genre': None,
            'character': None,
            'setting': None,
            'dop_info': None,
            'state': 'регистрация',
            'tokens' : 0,
            'test_mode': False
        }


@bot.message_handler(commands=['new_story'])
def new_story(message):
    global exist_options

    user_id = message.from_user.id

    if len(u_data) >= MAX_USERS:
        bybye_text(user_id)
        return

    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(telebot.types.InlineKeyboardButton("debug", callback_data="debug"))

    bot.send_message(user_id, text='Выбирай жанр своей истории',
                     reply_markup=create_keyboard(exist_options['genres']))

    bot.register_next_step_handler(message, handle_genre)

@bot.callback_query_handler(func=lambda call: True)
def answer(call):
    global u_data
    if call.data == 'debug':
        u_data[call.from_user.id]['test_mode'] = True
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text='Включен режим дебага')

def handle_genre(message):
    global u_data
    global exist_options

    genre = message.text
    user_id = message.from_user.id

    if genre not in exist_options['genres']:
        bot.send_message(user_id, text='Для начала выбери жанр',
                         reply_markup=create_keyboard(exist_options['genres']))
        bot.register_next_step_handler(message, handle_genre)

    logging.info(f"BOT: genre chosen: {genre}")

    u_data[user_id]['genre'] = genre
    bot.send_message(user_id, text='А теперь выбирай главного героя!)',
                     reply_markup=create_keyboard(exist_options['characters']))
    bot.register_next_step_handler(message, handle_character)


def handle_character(message):
    global u_data
    global exist_options

    character = message.text
    user_id = message.from_user.id

    if character not in exist_options['characters']:
        bot.send_message(user_id, text='Что то не то, с таким героем я не знаком.. нажми на одну из кнопочек пожалуйста.',
                         reply_markup=create_keyboard(exist_options['characters']))
        bot.register_next_step_handler(message, handle_character)
        return

    logging.info(f"BOT: character chosen: {character}")

    u_data[user_id]['character'] = character
    bot.send_message(user_id, text='Осталось выбрать лишь локацию!)',
                     reply_markup=create_keyboard(exist_options['settings']))
    bot.register_next_step_handler(message, handle_setting)


def handle_setting(message):
    global u_data
    global exist_options

    setting = message.text
    user_id = message.from_user.id

    if setting not in exist_options['settings']:
        bot.send_message(user_id, text='Осталось совсем чу чуть, выбери существующий сеттинг пожалуйста:)',
                         reply_markup=create_keyboard(exist_options['settings']))
        bot.register_next_step_handler(message, handle_setting)
        return

    if u_data[user_id]['test_mode']:
        bot.send_message(user_id, text=f'Выбран сеттинг "{setting}"')

    u_data[user_id]['setting'] = setting
    bot.send_message(user_id, text='Если хочешь чтобы дополнительные детали были учтены, то пиши их прямо сейчас.'
                                   'А если нет, то сразу жми /begin',
                     reply_markup=create_keyboard(['/begin']))
    bot.register_next_step_handler(message, begin)

@bot.message_handler(commands=['begin'])
def begin(message):
    global u_data

    user_id = message.from_user.id
    dop_info = message.text

    if len(u_data) >= MAX_USERS:
        bybye_text(user_id)
        return

    if user_id not in u_data:
        bot.send_message(user_id, text='Ты пока не регистрировался и не выбирал, '
                                       'из каких частей будет состоять твой сценарий. Нажми на /start',
                         reply_markup=create_keyboard(['/start']))
        return

    if u_data[user_id]['session_id'] > MAX_SESSIONS:
        bybye_text(user_id)
        return

    if dop_info != '/begin':
        u_data[user_id]['dop_info'] = dop_info
        bot.send_message(user_id, text='Жми /begin', reply_markup=create_keyboard(['/begin']))
        return

    promt = create_promt(u_data, user_id)

    logging.info(f"BOT: promt created: {promt}")

    bot.send_message(user_id, text='Генерирую...')


    collection = [
        {'role': 'system', 'text': promt}
    ]

    result, status = ask_gpt(collection)
    logging.info(f"BOT: ask_gpt() completed, results: {result,status}")
    if not status:
        bot.send_message(user_id, text='Произошла ошибка, попробуйте снова чуть позже',
                         reply_markup=create_keyboard(['/start']))
        if u_data[user_id]['debug']:
            bot.send_message(user_id, text=f'Произошла ошибка {result}')
        return

    collection.append({'role': 'assistant', 'text': result})
    tokens = count_tokens_in_dialogue(collection)
    u_data[user_id]['tokens'] += tokens

    if u_data[user_id]['tokens'] >= MAX_USER_TOKENS:
        bot.send_message(user_id, text=result)
        bot.send_message(user_id, text='Количество токенов в рамках текущей сессии закончилось. '
                                       'Началась следующая сессия. Хотел бы попробовать снова?',
                         reply_markup=create_keyboard(['/new_story']))
        u_data[user_id]['session_id'] += 1
        return

    bot.send_message(user_id, text=result)
    bot.send_message(user_id, text='Хотел бы попробовать снова? Нажми /new_story',
                     reply_markup=create_keyboard(['/new_story']))


bot.polling()

