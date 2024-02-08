import string
import threading
from threading import Thread
from queue import Queue
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import spacy
from collections import Counter
import vk_api
from telethon.sync import TelegramClient
import asyncio
import tkinter as tk
#import ru_core_news_sm

# Импорт необходимых библиотек и модулей

vk_key = ''  # Токен для VK API
tg_id = ''  # ID Telegram API
tg_hash = ''  # Хеш для Telegram API

# Настройка ключей для API VK и Telegram

vk_session = vk_api.VkApi(token=vk_key)
vk_api_instance = vk_session.get_api()

nlp = spacy.load('ru_core_news_sm')


# Создание сессии для VK API и загрузка модели для обработки естественного языка

# Функция для получения user_id по имени пользователя в VK
def vk_get_user_id(username):
    try:
        response = vk_api_instance.users.get(user_ids=username)
        user_id = response[0]['id']
        return user_id
    except Exception as e:
        print(f"Ошибка1: {e}")
        return None


# Функция для получения сообщений со стены пользователя или группы в VK
def vk_get_wall(owner_id, count):
    try:
        response = vk_api_instance.wall.get(owner_id=owner_id, count=count)
        return response['items']
    except Exception as e:
        print(f"Ошибка2: {e}")
        return []


# Функция для скрапинга данных из VK и добавления в очередь
def scrape_vk(users, groups, data_queue):
    for username in users:
        user_id = vk_get_user_id(username)
        if user_id is not None:
            posts = vk_get_wall(user_id, 30)
            for post in posts:
                data_queue.put(post['text'])

    for group_id in groups:
        posts = vk_get_wall(group_id, 30)
        for post in posts:
            data_queue.put(post['text'])


# Функция для скрапинга данных из Telegram и добавления в очередь с использованием асинхронности
async def scrape_telegram(group_names, data_queue, num_messages):
    api_id = tg_id
    api_hash = tg_hash

    client = TelegramClient('session_name', api_id, api_hash, system_version='4.16.30-vxCUSTOM')
    await client.start()
    for group_name in group_names:
        group_entity = await client.get_input_entity(group_name)

        async for message in client.iter_messages(group_entity, limit=num_messages):
            data_queue.put(message.text)
    await client.disconnect()
    client.disconnect()


lock = threading.Lock()  # Блокировка для потоков


# Функция для предварительной обработки данных (удаление стоп-слов и токенизация)
def preprocess_data(data_queue, preprocessed_data, stop_words):
    while True:
        data = data_queue.get()
        if data is None:
            break

        data = data.lower()
        tokens = word_tokenize(data, language='russian')
        tokens = [word for word in tokens if word not in stop_words and not all(
            c in string.punctuation + '–«»—“”''utm_source=telegramoid=-67991642act=a_subscribe_boxhttps//vk.com/widget_community.phpstate=1|подпишись'
            for c in word)]

        with lock:
            preprocessed_data.extend(tokens)


# Функция для анализа текста и подсчета ключевых слов
def analyze(data, keyword_counts):
    doc = nlp(data)
    target_keywords = ["израиль"]
    for token in doc:
        if token.text in target_keywords:
            keyword_counts[token.text] += 1


def main():
    num_threads = 1  # Количество потоков
    vk_users = ['durov']  # Пользователи VK для скрапинга
    vk_groups = [-67991642, -15755094, -20169232, -40316705, -27532693]  # Группы VK для скрапинга
    telegram_groups = ['topor', 'arh_29ru', 'piterach', 'Cbpub', 'bazabazon']  # Группы Telegram для скрапинга

    # Очереди для хранения данных
    data_queue_vk = Queue()
    data_queue_telegram = Queue()

    # Списки для предварительно обработанных данных
    preprocessed_data_vk = []
    preprocessed_data_telegram = []

    # Счетчики для подсчета ключевых слов
    keyword_counts_vk = Counter()
    keyword_counts_telegram = Counter()

    stop_words = set(stopwords.words('russian'))  # Стоп-слова для русского языка

    # Потоки для скрапинга VK и Telegram
    vk_threads = [Thread(target=scrape_vk, args=(vk_users, vk_groups, data_queue_vk)) for _ in range(num_threads)]
    num_telegram_messages = 30

    # Поток для скрапинга Telegram с использованием асинхронности
    telegram_thread = Thread(
        target=lambda: asyncio.run(scrape_telegram(telegram_groups, data_queue_telegram, num_telegram_messages)))

    # Потоки для предварительной обработки данных
    preprocessing_threads = [Thread(target=preprocess_data, args=(data_queue_vk, preprocessed_data_vk, stop_words)),
                             Thread(target=preprocess_data,
                                    args=(data_queue_telegram, preprocessed_data_telegram, stop_words))]

    # Запуск потоков
    for thread in vk_threads:
        thread.start()

    telegram_thread.start()

    for thread in preprocessing_threads:
        thread.start()

    # Ожидание завершения работы потоков
    for thread in vk_threads:
        thread.join()

    telegram_thread.join()

    for _ in range(num_threads):
        data_queue_vk.put(None)
        data_queue_telegram.put(None)

    for thread in preprocessing_threads:
        thread.join()

    # Анализ данных
    for data_item in preprocessed_data_vk:
        analyze(data_item, keyword_counts_vk)

    for data_item in preprocessed_data_telegram:
        analyze(data_item, keyword_counts_telegram)

    # Нормализация результатов
    for keyword, count in keyword_counts_vk.items():
        keyword_counts_vk[keyword] = count // (num_threads + 1)

    for keyword, count in keyword_counts_telegram.items():
        keyword_counts_telegram[keyword] = count // (num_threads + 1)

    # Вывод результатов в GUI
    # (данный код взаимодействует с библиотекой tkinter для создания графического интерфейса)


# Инициализация графического интерфейса
root = tk.Tk()

# Создание виджетов (надписей, текстовых полей, кнопок) для отображения результатов
# и запуска анализа данных при нажатии кнопки

root.mainloop()  # Запуск основного цикла GUI
