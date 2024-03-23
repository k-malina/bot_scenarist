from database import (
    create_db,
    create_tbl,
    select_data,
    get_all_rows,
    is_value_in_table,
    add_record,
    get_dialogue_for_user,
    get_row_by_uid,
    get_size_of_sessions,
    is_limit_users,
    limit_users_sessions,
    get_session_number,
    limit_tokens_in_sessions,
    get_all_tokens,
    clean_tbl,
    get_user_session_id,
    execute_query,
    execute_selection_query,
    get_user_amount
)
import datetime
from ya_gpt import (
    count_tokens_in_dialogue,
    make_promt,
    new_token,
    ask_gpt
)
import telebot
from telebot import types
from telebot.types import KeyboardButton, ReplyKeyboardMarkup
from configconfig import token
import logging
import sqlite3
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="log_file.txt",
    filemode="w",
)


MAX_PROJECT_TOKENS = 15000
MAX_USER_TOKENS = 2000
MAX_USERS = 7
MAX_TOKENS_IN_SESSION = 700
MAX_SESSIONS = 3
DB_name = 'Promts'

bot = telebot.TeleBot(token=token)
users = {} #он толком не нужен, но при /start я его использую чтобы бот здоровался как будто это новый пользователь, или как старый
def new_user(user_name):
    if user_name not in users:
        users[user_name] = ''
        return True
    return False

u_data = {}
@bot.message_handler(commands=['start'])
def start(message):
    u_id = message.chat.id
    create_db()
    create_tbl()
    uname = message.from_user.first_name
    if new_user(uname):
        bot.send_message(u_id, text=f'Рад познакомиться, {uname}')
    else:
        bot.send_message(u_id, text=f'{uname}, снова привет')

    commands = ['/new_story', '/help']
    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    buttons = [types.KeyboardButton(command) for command in commands]
    keyboard.add(*buttons)
    bot.send_message(message.chat.id,
                     "Привеееет", reply_markup=keyboard)

    u_data[u_id] = {
        'session_id' : 0,
        'genre' : None,
        'character' : None,
        'setting' : None,
        'dop_info' : None,
        'state' : 'регистрация',
        'test_mode': False
    }

@bot.message_handler(commands=['all_tokens'])
def all_tokens(message):
    u_id = message.chat.id
    try:
        total_tokens = get_all_tokens(u_id)
        commands=['']
        keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        buttons = [types.KeyboardButton(command) for command in commands]
        keyboard.add(*buttons)
        bot.send_message(u_id,
                         f"Потрачено токенов за все время: {total_tokens}", reply_markup=keyboard)
    except Exception as e:
        bot.send_message(u_id, f'Сорри, не удалось подсчитать токены. Ошибка: {e}')

def is_tokens_limit(user_id, chat_id, bot): #применяем когда /continue
    # Если такого пользователя нет в таблице, ничего делать не будем
    if not is_value_in_table(DB_name, 'user_id', user_id):
        return

    # Берём из таблицы идентификатор сессии
    session_id = get_user_session_id(user_id)
    # Получаем из таблицы размер текущей сессии в токенах
    tokens_of_session = get_size_of_sessions(user_id, session_id)

    # В зависимости от полученного числа выводим сообщение
    if tokens_of_session >= MAX_TOKENS_IN_SESSION:
        bot.send_message(
            chat_id,
            f'Вы израсходовали все токены в этой сессии. Вы можете начать новую, введя help_with')

    elif tokens_of_session + 50 >= MAX_TOKENS_IN_SESSION:  # Если осталось меньше 50 токенов
        bot.send_message(
            chat_id,
            f'Вы приближаетесь к лимиту в {MAX_TOKENS_IN_SESSION} токенов в этой сессии. '
            f'Ваш запрос содержит суммарно {tokens_of_session} токенов.')

    elif tokens_of_session / 2 >= MAX_TOKENS_IN_SESSION:  # Если осталось меньше половины
        bot.send_message(
            chat_id,
            f'Вы использовали больше половины токенов в этой сессии. '
            f'Ваш запрос содержит суммарно {tokens_of_session} токенов.'
        )

def is_sessions_limit(user_id, chat_id, bot): #применяем когда новая сессия
    # Если такого пользователя нет в таблице, ничего делать не будем
    if not is_value_in_table(DB_name, 'user_id', user_id):
        return

    # Берём из таблицы идентификатор сессии
    session_id = get_user_session_id(user_id)
    # Получаем из таблицы размер текущей сессии в токенах
    tokens_of_session = get_size_of_sessions(user_id, session_id)
    session_number = get_session_number(session_id)

    # В зависимости от полученного числа выводим сообщение
    if session_number >= MAX_TOKENS_IN_SESSION:
        bot.send_message(
            chat_id,
            f'Вы израсходовали все токены в этой сессии. Вы можете начать новую, введя help_with')

    elif tokens_of_session + 50 >= MAX_TOKENS_IN_SESSION:  # Если осталось меньше 50 токенов
        bot.send_message(
            chat_id,
            f'Вы приближаетесь к лимиту в {MAX_TOKENS_IN_SESSION} токенов в этой сессии. '
            f'Ваш запрос содержит суммарно {tokens_of_session} токенов.')

    elif tokens_of_session / 2 >= MAX_TOKENS_IN_SESSION:  # Если осталось меньше половины
        bot.send_message(
            chat_id,
            f'Вы использовали больше половины токенов в этой сессии. '
            f'Ваш запрос содержит суммарно {tokens_of_session} токенов.'
        )

@bot.message_handler(commands=['/begin'])
def begin(message):
    u_id = message.chat.id
    if not u_data.get(u_id):
        bot.send_message(u_id, "Не знаю как так получилось, но тебя нет в списке зарегестрированных пользователй"
                         "Жми /start чтобы зарегестрироваться")
        return
    if u_data.get(u_id) == 'Регистрация':
        bot.send_message(u_id, "Жми /new_story чтобы скорее начать писать новую историю!")
    u_data[u_id]['state'] = 'В истории'

    get_story(message)

@bot.message_handler(commands=['end'])
def end_story(message):
    u_id = message.chat.id
    if not is_value_in_table('Promts', 'user_id', u_id):
        keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        buttons = ['begin']
        keyboard.add(*buttons)
        bot.send_message(u_id,
                         "Не уверен как так получилось, но вроде как ты еще не начал[а] историю.."
                               "Скорее жми /begin для того чтобы написать свой шедевр!)")

        story_handler(message)

        commands = ['/whole_story', '/new_story', '/all_tokens', '/debug']
        keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        buttons = [types.KeyboardButton(command) for command in commands]
        keyboard.add(*buttons)
        bot.send_message(u_id,
                         f"С тобой весело писать историю, что делаем дальше?", reply_markup=keyboard)

@bot.message_handler(commands=['whole_story']):
def get_whole_story(message):
    u_id = message.chat.id
    session_id = None
    if is_value_in_table('Promts,', 'user_id', u_id)
        row: sqlite3.Row = get_value_from_table('session_id', u_id)
        session_id = row['session_id']
    if not session_id:
        bot.send_message(u_id, "Не уверен как так получилось, но вроде как ты еще не начал[а] историю.."
                               "Скорее жми /begin для того чтобы написать свой шедевр!)")
        return
    collection: sqlite3.Row = get_dialogue_for_user(u_id, session_id)
    whole_story = ''
    for row in collection:
        whole_story += row['content']
    sql_query = (f'''
    SELECT content from {DB_name} 
    WHERE user_id = ? and role = ?''')
    promt = execute_selection_query(sql_query, u_id, 'system')
    whole_story = whole_story.replace(promt[0]['content'], ' ')
    bot.send_message(u_id, f'История которая у нас получается:\n'
                           f'{whole_story}')

@bot.message_handler(commands=['new_story'])
def registration(message): #изменение статуса пользователя на 'в истории'
    user_quantity = get_user_amount()
    if user_quantity >= MAX_USERS:
        bot.send_message(message.chat.id, "Упс, кажется уже слишком много пользователей зарегестрировалось")
        return
    genres = ['', '', '',]
    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    buttons = [types.KeyboardButton(genre) for genre in genres]
    keyboard.add(*buttons)
    bot.send_message(message.chat.id,
                     f"Выбирай жанр своей истории:", reply_markup=keyboard)
    bot.register_next_step_handler(message, handle_genre)
def handle_genre(message):
    u_id = message.chat.id
    genre = message.text
    if genre not in ['', '', '']:
        genres = ['', '', '', ]
        keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        buttons = [types.KeyboardButton(genre) for genre in genres]
        keyboard.add(*buttons)
        bot.send_message(message.chat.id,
                         f"Для начала надо выбрать жанр своей истории", reply_markup=keyboard)
        bot.register_next_step_handler(message, handle_genre)
        return
    u_data[u_id]['genre'] = genre
    u_data[u_id]['state'] = 'в истории'

    characters = ['', '', '', ]
    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    buttons = [types.KeyboardButton(character) for character in characters]
    keyboard.add(*buttons)
    bot.send_message(u_id,
                     f"А теперь выбирай персонажа:", reply_markup=keyboard)
    bot.register_next_step_handler(message, handle_character)
def handle_character(message):
    u_id = message.chat.id
    character = message.text
    settings = {
        '': '',
        '': '',
        '': '',
        '': '',
        '': '',
        '': ''
    }
    if character not in ['','','']:
        characters = ['', '', '', ]
        keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        buttons = [types.KeyboardButton(character) for character in characters]
        keyboard.add(*buttons)
        bot.send_message(u_id,
                         f"Чтобы продолжить, надо все таки выбрать персонажа:", reply_markup=keyboard)
        bot.register_next_step_handler(message, handle_character)

    u_data[u_id]['character'] = character
    setting_string = "\n".join([f"{name}:{description}" for name, description in settings.items()])
    setting_options = ['', '', '', ]
    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    buttons = [types.KeyboardButton(setting) for setting in setting_options]
    keyboard.add(*buttons)
    bot.send_message(u_id,
                     f"Выбирай локацию:\n" + setting_string, reply_markup=keyboard)
    bot.register_next_step_handler(message, handle_setting)

def handle_setting(message):
    u_id = message.chat.id
    u_setting = message.text
    if u_setting not in ['','','']:
        setting_options = ['', '', '', ]
        keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        buttons = [types.KeyboardButton(setting) for setting in setting_options]
        keyboard.add(*buttons)
        bot.send_message(u_id,
                         f"Уже совсем скоро начнём писать историю, осталось выбрать лишь локацию!)", reply_markup=keyboard)
        bot.register_next_step_handler(message, handle_setting)
        return

    u_data[u_id]['setting'] = u_setting
    u_data[u_id]['state'] = 'в истории'

    setting_options = ['/begin']
    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    buttons = [types.KeyboardButton(setting) for setting in setting_options]
    keyboard.add(*buttons)
    bot.send_message(u_id,
                     f"Если хочешь чтобы нейросеть учла что либо ещё, то пиши в следующем сообщение"
                     f"Если же ты уже готов[а], то жми /begin", reply_markup=keyboard)
    bot.register_next_step_handler(message, handle_dop_info)
def handle_dop_info(message):
    u_id = message.text.id
    dop_info = message.text
    if dop_info == '/begin':
        begin_story(message)
    else:
        u_data[u_id]['dop_info'] = dop_info
        setting_options = ['/begin']
        keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        buttons = [types.KeyboardButton(setting) for setting in setting_options]
        keyboard.add(*buttons)
        bot.send_message(u_id,
                         f"Классная добавка к твоей истории, жми /begin чтобы начать писать историю!", reply_markup=keyboard)
        bot.register_next_step_handler(message, handle_dop_info)

@bot.message_handler(content_types=['text'])
def story_handler(message: types.Message, mode = 'continue')
    u_id: int = message.from_user.id
    u_answer: str = message.txt

    if mode == 'end':
        u_answer : END_STORY

    row : sqlite3.Row = get_value_from_table('session_id', u_id)
    collection : sqlite3.Row = get_dialogue_for_user(u_id, row['session_id'])
    collection.append({'role':'user', 'content' : u_answer})

    tokens : int = count_tokens_in_dialogue(collection)

    if is_tokens_limit(message, tokens, bot):
        return

    add_record(
        u_id,
        'user',
        u_answer,
        datetime.now(),
        tokens,
        row['session_id']
    )

    if is_tokens_limit(message, tokens, bot):
        return

    gpt_text, result_for_test = ask_gpt(collection, mode)

    collection: sqlite3.Row = get_dialogue_for_user(u_id, row['session_id'])
    collection.append({'role': 'assistant', 'content': gpt_text})
    tokens : int = count_tokens_in_dialogue(collection)

    add_record(
        u_id,
        'assistant',
        gpt_text,
        datetime.now(),
        tokens,
        row['session_id']
    )

    if not u_data[u_id]['test_mode']:
        end_option = ['/end']
        keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        buttons = [types.KeyboardButton(option) for option in end_option]
        keyboard.add(*buttons)
        bot.send_message(u_id, gpt_text, reply_markup=keyboard)
    else:
        end_option = ['/end']
        keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        buttons = [types.KeyboardButton(option) for option in end_option]
        keyboard.add(*buttons)
        bot.send_message(u_id, result_for_test, reply_markup=keyboard)

@bot.message_handler(content_types=['text'])
def get_story(message: types.Message):
    u_id : int = message.from_user.id
    if is_sessions_limit(message, bot):
        return
    session_id = 1
    if is_value_in_table('user_id', u_id)
        row : sqlite3.Row = get_value_from_table('session_id', u_id)
        session_id = row['session_id'] + 1

    u_story = make_promt(u_data, u_id)

    collection: sqlite3.Row = get_dialogue_for_user(u_id, session_id)
    collection.append({'role': 'system', 'content': u_story})
    tokens: int = count_tokens_in_dialogue(collection)

    bot.send_message(u_id, "История генерируется ")

    add_record(
        u_id,
        'system',
        u_story,
        datetime.now(),
        tokens,
        session_id
    )

    collection : sqlite3.Row = get_dialogue_for_user(u_id, session_id)
    gpt_text, result_for_test = ask_gpt(collection)
    collection.append({'role' : 'assistant', 'content' : gpt_text})

    tokens: int = count_tokens_in_dialogue(collection)
    if is_tokens_limit(message, tokens, bot):
        return
    add_record(
        u_id,

    )


@bot.message_handler(commands=['debug'])
def logs_debug(message):
    with open("log_file.txt", "rb") as f:
        bot.send_document(message.chat.id, f)

@bot.message_handler(commands=['debug_off'])
def debug_off(message):
    u_id = message.chat.id
    if u_data.get(u_id):
        u_data[u_id]['test_mode'] = False
        bot.send_message(u_id, "Тестовый режим успешно выключен")

@bot.message_handler(commands=['debug_on'])
def debug_on(message):
    u_id = message.chat.id
    if u_data.get(u_id):
        u_data[u_id]['test_mode'] = True
        bot.send_message(u_id, "Тестовый режим успешно включен ")