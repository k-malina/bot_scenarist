import os.path
import time
import requests
import sqlite3
import logging
import json
from transformers import AutoTokenizer
import transformers
MAX_PROJECT_TOKENS = 15000
MAX_USER_TOKENS = 2000
MAX_USERS = 7
MAX_TOKENS_IN_SESSION = 700
MAX_SESSIONS = 3

token_path = 'creds/gpt_token.json'
folderIDpath = 'creds/gpt_folder_id.txt'

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="log_file.txt",
    filemode="w",
)

temp = 1.2
max_tokens = 60
url = 'http://localhost:1234/v1/chat/completions'
MAX_tokens = 2000
assistant_content = 'Давай короткие'
iam_TOKEN = "t1.9euelZqdjpCXyM-TzZ2Ux5WJzInJyu3rnpWajpOMnpOWj4uJnsePlpDJm53l8_deAS9Q-e8hW00P_t3z9x4wLFD57yFbTQ_-zef1656VmozMns7HmpOKyZ2dnouaxo2b7_zF656VmozMns7HmpOKyZ2dnouaxo2bveuelZqUi57NjsfNnp2Qi8eUi53Ml7XehpzRnJCSj4qLmtGLmdKckJKPioua0pKai56bnoue0oye.paqT3iO7QKbqYnW9uKlBLv9MunuA0BYFxQwH2Ktn7rGVoOR19E4QoSYANmI4MN7yp8Z76o__o_QVWTWO7y9yDg"
FOLDER_id = 'b1goevfjrs5m3rb7tlpu'  # Folder_id для доступа к YandexGPT
machine_address = '158.160.132.17'
API_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
END_STORY = "Напиши завершение истории c неожиданной развязкой. Не пиши никакой пояснительный текст от себя"
CONTINUE_STORY = "Продолжи сюжет в 1-3 предложения и оставь интригу. Не пиши никакой пояснительный текст от себя"

SYSTEM_PROMPT = (
    "Ты пишешь историю вместе с человеком. "
    "Историю вы пишете по очереди. Начинает человек, а ты продолжаешь. "
    "Если это уместно, ты можешь добавлять в историю диалог между персонажами. "
    "Диалоги пиши с новой строки и отделяй тире. "
    "Не пиши никакого пояснительного текста в начале, а просто логично продолжай историю."
)

def count_tokens_in_dialogue(messages: sqlite3.Row) -> int:
    headers = {
        'Authorization': f'Bearer {iam_TOKEN}',
        'Content-Type': 'application/json'
    }
    data = {
        "modelUri": f"gpt://{FOLDER_id}/yandexgpt/latest",
        "maxTokens": MAX_MODEL_TOKENS,
        "messages": []
    }

    # Проходимся по всем сообщениям и добавляем их в список
    for row in messages:
        data["messages"].append(
            {
                "role": row["role"],
                "text": row["content"]
            }
        )

    return len(
        requests.post(
            "https://llm.api.cloud.yandex.net/foundationModels/v1/tokenizeCompletion",
            json=data,
            headers=headers
        ).json()["tokens"]
    )


def make_promt(user_data, user_id):
    # Начальный текст для нашей истории - это типа вводная часть
    prompt = SYSTEM_PROMPT

    # Добавляем в начало истории инфу о жанре и главном герое, которых выбрал пользователь
    prompt += (f"\nНапиши начало истории в стиле {user_data[user_id]['genre']} "
              f"с главным героем {user_data[user_id]['character']}. "
              f"Вот начальный сеттинг: \n{user_data[user_id]['setting']}. \n"
              "Начало должно быть коротким, 1-3 предложения.\n")

    # Если пользователь указал что-то еще в "дополнительной информации", добавляем это тоже
    if user_data[user_id]['additional_info']:
        prompt += (f"Также пользователь попросил учесть "
                   f"следующую дополнительную информацию: {user_data[user_id]['additional_info']} ")

    # Добавляем к prompt напоминание не давать пользователю лишних подсказок
    prompt += 'Не пиши никакие подсказки пользователю, что делать дальше. Он сам знает'

    logging.info(f"GPT: сформирован промт: {prompt}")
    # Возвращаем сформированный текст истории
    return prompt


def get_creds():
    """Получение токена u folder_id uз yandex cloud command line interface"""
    try:
        with open(TOKEN_PATH, 'r') as f:
            d = json.load(f)
            expiration = d['expires_at']

        if expiration < time.time():
            create_new_token()
    except:
        create_new_token()

    with open(TOKEN_PATH, 'r') as f:
        d = json.load(f)
        token = d["access_token"]

    with open(FOLDER_ID_PATH, 'r') as f:
        folder_id = f.read().strip()

    return token, folder_id

def create_new_token():
    metadata_url = f'http://{machine_address}/computeMetadata/v1/instance/service-accounts/default/token'
    headers = {"Metadata-Flavor": "Google"}
    token_dir = os.path.dirname(TOKEN_PATH)
    if not os.path.exists(token_dir):
        os.makedirs(token_dir)

    try:
        response = requests.get(metadata_url, headers = headers)
        if response.status_code == 200:
            token_data= response.json()
            token_data['expires_at'] = time.time() + token_data['expires_in']
            with open(TOKEN_PATH, "w") as token_file:
                json.dump(token_data, token_file)
            logging.info("создан токен")
        else:
            logging.error(f"Не удалось получить токен, код ошибки: {response.status_code}")
    except Exception as e:
        logging.error(f"Ошибка при получении токена: {e}")

def ask_gpt(collection, mode='continue'):
    """Запрос к YandexGPT"""
    token = '<iam-токен>'
    folder_id = '<folder_id>'

    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    data = {
        "modelUri": f"gpt://{folder_id}/yandexgpt/latest",
        "completionOptions": {"stream": False, "temperature": 0.6, "maxTokens": 200},
        "messages": []
    }

    for row in collection:
        content = row['content']
        if mode == 'continue' and row['role'] == 'user':
            content += '\n' + CONTINUE_STORY
        elif mode == 'end' and row['role'] == 'user':
            content += '\n' + END_STORY
        data["messages"].append({"role": row["role"], "text": content})

    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code != 200:
            return f"Status code {response.status_code}."

        logging.info(f"GPT: получен ответ от нейросети: {response.json()['result']['alternatives'][0]['message']['text']}")

        return response.json()['result']['alternatives'][0]['message']['text']
    except Exception as e:
        logging.error(f"GPT: Ошибка при работе с gpt : {e}")
        return "Произошла непредвиденная ошибка."


