import sqlite3
import requests
import logging
MAX_PROJECT_TOKENS = 15000
MAX_USER_TOKENS = 2000
MAX_USERS = 7
MAX_TOKENS_IN_SESSION = 700
MAX_SESSIONS = 3
DB_dir = ''
DB_name = 'Promts'

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="log_file.txt",
    filemode="w",
)

def create_db():
    try:
        con = sqlite3.connect('db.sqlite')
        cur = con.cursor()
    except sqlite3.Error as e:
        print("Ошибка при работе с sqlite:", e)
    finally:
        con.close()

def create_tbl(table_columns):
    sql_query = f'CREATE TABLE IF NOT EXISTS {DB_name}'
    sql_query += '('
    columns = []
    for data_name, data_type in table_columns.items():
        columns.append(f'{data_name} {data_type}')
    sql_query += ', '.join(columns) + ')'
    execute_query(sql_query)

#создает & подключается к БД --- подгатавливает БД
def prepare_db():
    create_db()
    table_columns = {
        'id': 'INTEGER PRIMARY KEY',
        'user_id': 'INTEGER',
        'role': 'TEXT',
        'content': 'TEXT',
        'date': 'DATETIME',
        'tokens': 'INTEGER',
        'session_id': 'INTEGER'
    }
    create_tbl(table_columns)

#функция выполняет любой sql запрос где надо что то удалить/добавить
def execute_query(sql_query, data=None, db_path=f'{DB_name}'):
    try:
        logging.info(f"DB: выполняется скьюл запрос : {sql_query}")
        with sqlite3.connect(db_path) as connection:
            connection = sqlite3.connect(db_path)
            cursor = connection.cursor()
            if data:
                cursor.execute(sql_query, data)
            else:
                cursor.execute(sql_query)
                connection.commit()
                connection.close()
    except Exception as e:
        logging.error(f"DB error: {e}")

#эта функция выполняет любые sql запросы которые что то возвращают
def execute_selection_query(sql_query, data=None, database_path = f'{DB_dir}/{DB_name}'):
    try:
        logging.info(f"DB: выполняется sql запрос: {sql_query}")
        with sqlite3.connect(database_path) as connection:
            connection.row_factory = sqlite3.Row
            con = sqlite3.connect('db.sqlite')
            cur = con.cursor()

            if data:
                cur.execute(sql_query, data)
            else:
                cur.execute(sql_query)
            rows = cur.fetchall()
        return rows
    except Exception as e:
        logging.error(f"DB error: {e}")

def select_data(u_id, session_id, promt_type):
    con = sqlite3.connect('db.sqlite')
    cur = con.cursor()
    cur.execute(f'''
    SELECT content 
    FROM prompts WHERE user_id = {u_id} 
    AND session_id = {session_id} 
    AND role = {promt_type}
    LIMIT 1;''')
    con.commit()
    con.close()

#проверка БД -- выводит всю таблицу
def get_all_rows():
    sql_query = f'''SELECT * FROM {DB_name} 
                    ORDER BY date desc'''
    rows = execute_selection_query(sql_query)
    for row in rows:
        print(row)

#проверяет есть ли элемент в указанном столбце
def is_value_in_table(tbl_name, column_name, value):
    sql_query = f'''SELECT {column_name}
                    FROM {tbl_name}
                    WHERE {column_name} = ?
                    order by date desc'''
    rows = execute_selection_query(sql_query, [value])
    return rows
#def get_user_session_id(user_id):

# записывает историю запросов в таблицу
def add_record(user_id, role, content, date, tokens, session_id):
    insert_row([user_id, role, content, date, tokens, session_id],
               columns = ['user_id', 'role', 'content', 'date', 'tokens', 'session_id'])

#вставляет новую строку в таблицу, принимая список значений для каждой колонки и ее названия
def insert_row(values, columns=''): #нужна для add_record
    if columns != '':
        holders = ', '.join(['?'] * len(values))
        columns = ', '.join(columns)
        sql_query = (f'''INSERT INTO Promts ({columns})
                 VALUES ({holders});''')
        execute_query(sql_query, values)

def get_user_session_id(): #######
    sql_query = ''

def get_dialogue_for_user(user_id, session_id):
    con = sqlite3.connect('db.sqlite')
    cur = con.cursor()
    try:
        cur.execute(f'''
            ''')
        con.commit()
    except sqlite3.Error as e:
        print(f"An error occurred: {e.args[0]}")
    finally:
        con.close()

def get_row_by_uid():
    con = sqlite3.connect('db.sqlite')
    cur = con.cursor()
    try:
        cur.execute(f'''''')
        con.commit()
    except sqlite3.Error as e:
        print(f"An error occurred: {e.args[0]}")
    finally:
        con.close()

def get_size_of_sessions(u_id, session_id):
    con = sqlite3.connect('db.sqlite')
    cur = con.cursor()
    try:
        cur.execute(f'''
        SELECT tokens 
        FROM prompts 
        WHERE user_id = {u_id} 
        AND session_id = {session_id}
        ORDER BY date DESC LIMIT 1;
                ''')
        con.commit()
    except sqlite3.Error as e:
        print(f"An error occurred: {e.args[0]}")
    finally:
        con.close()

def is_limit_users():
    connection = sqlite3.connect('sqlite3.db')
    cursor = connection.cursor()
    result = cursor.execute('SELECT DISTINCT user_id '
                            'FROM table_name;')
    count = 0  # количество пользователей
    for i in result:  # считаем количество полученных строк
        count += 1  # одна строка == один пользователь
    connection.close()
    return count >= MAX_USERS

def limit_users_sessions():
    connection = sqlite3.connect('sqlite3.db')
    cursor = connection.cursor()
    result = cursor.execute('SELECT DISTINCT sessions_id'
                            'FROM table_name;')
    count = 0  # количество сессий
    for i in result:  # считаем количество полученных строк
        count += 1  # одна строка == один пользователь
    connection.close()
    if count < MAX_SESSIONS:
        response = 'У вас ещё есть сессии, смело продолжайте создавать вашу историю!)'
        return response
    elif count >= MAX_USERS:
        response = 'Лимит сессий исчерпан, приходите попозже:)'
        return response

def get_session_number(session_id):
    connection = sqlite3.connect('sqlite3.db')
    cursor = connection.cursor()
    result = cursor.execute(f'''SELECT DISTINCT {session_id}'
                            FROM table_name;''')
    count = 0  # количество сессий
    for i in result:  # считаем количество полученных строк
        count += 1  # одна строка == один пользователь

def limit_tokens_in_sessions():
    data = execute_selection_query(f'''SELECT DISTINCT sessions_id'
                            FROM {DB_name};''')
    count = 0  # количество сессий
    for i in data:  # считаем количество полученных строк
        count += 1  # одна строка == один пользователь
    if count < MAX_SESSIONS:
        response = 'Вы можете начать новую сессию'
        return response
    elif count >= MAX_USERS:
        response = 'Лимит сессий исчерпан'
        return response

def get_all_tokens(user_id):
    # Подключение к базе данных SQLite
    con = sqlite3.connect('db.sqlite')
    cur = con.cursor()

    try:
        # Получаем список уникальных session_id
        cur.execute(f'''
            SELECT DISTINCT session_id
            FROM prompts
            WHERE user_id = {user_id};
        ''')
        session_ids = cur.fetchall()

        total_tokens = 0

        # Для каждой сессии получаем размер
        for session_id in session_ids:
            size = get_size_of_sessions(user_id, session_id[0])
            total_tokens += size
        return total_tokens

    except sqlite3.Error as e:
        print(f"An error occurred: {e.args[0]}")
    finally:
        con.close()

def clean_tbl(tbl_name):
    sql_query = f'''DELETE FROM {tbl_name}'''
    execute_query(sql_query)

def get_user_amount():

