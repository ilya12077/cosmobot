import json
import os
import time

import requests
from flask import Flask, request
from waitress import serve

import tools

app = Flask(__name__)

if os.environ.get('AM_I_IN_A_DOCKER_CONTAINER', False):
    path = '/etc/cosmobot/'
else:
    path = ''

# with open(f'{path}data/allowed_userids.txt', 'r', encoding='utf-8') as fl:
#     allowed_userids = fl.read().split()

pendingupdates_lastchecked = 0
pendingupdates_lastsent = 0


@app.route('/', methods=['GET', 'POST'])
def firewall():
    global pendingupdates_lastchecked, pendingupdates_lastsent
    if request.method == "GET":
        return 'I\'m working'
    r = request.get_json()
    with open(f'{path}data/quires.txt', 'a', encoding='utf-8') as f:
        f.write(str(r) + '\n')
    print(r)
    try:
        current_time = int(time.time())
        if current_time - pendingupdates_lastchecked > 60:
            pendingupdates_lastchecked = current_time
            response = requests.get(f'{tools.url}getWebhookInfo')
            if response.status_code == 200:
                pendingupdates_count = response.json().get("result", {}).get("pending_update_count", 0)
                if pendingupdates_count > 15:
                    if current_time - pendingupdates_lastsent > 60 * 5:  # 3600 секунд = 1 час
                        tools.send_message(647372660, f'⭕Я заметил, что pending updates сейчас: <b>{pendingupdates_count}</b>\n{tools.url}getWebhookInfo')
                        pendingupdates_lastsent = current_time
    except Exception as e:  # urllib3.exceptions.ConnectTimeoutError
        print(e)
    if 'message' in r:
        if r['message']['chat']['type'] == 'private':
            dm_handler(r)
            user_id = str(r['message']['from']['id'])
            if len(tools.ads) > 0 and user_id in tools.users and tools.users[user_id]['ad_countdown'] <= 0:
                keys = list(tools.ads.keys())
                try:
                    # Поиск индекса последнего использованного ключа
                    last_index = keys.index(tools.users[user_id]['last_ad_key'])
                    # Возвращаем ключ, следующий за last_ad_key, или первый ключ, если last_ad_key последний
                    ad_id = keys[last_index + 1] if last_index + 1 < len(keys) else keys[0]
                except ValueError:
                    # Возвращаем первый ключ, если last_ad_key не найден
                    ad_id = keys[0]
                # print(ad_id)
                tools.send_ad(user_id, ad_id)
                tools.users[user_id]['last_ad_key'] = str(ad_id)
                tools.users[user_id]['ad_countdown'] = tools.ad_countdown
            elif user_id in tools.users:
                tools.users[user_id]['ad_countdown'] = tools.users[user_id]['ad_countdown'] - 1
            with open(f'{path}data/users.json', 'w') as fl:
                json.dump(tools.users, fl, indent=4)
    return 'OK'


def create_account(r):
    user_id = str(r['message']['from']['id'])
    first_name = r['message']['from']['first_name']
    if 'username' in r['message']['from']:
        username = '@' + r['message']['from']['username']
    else:
        username = ''
    tools.users[user_id] = {'first_name': str(first_name), 'username': username, 'form': {'about': '', 'name': '', 'town': '', 'age': 0, 'sex': '', 'searching': '', 'picture': '', 'pic_type': ''}, 'was_liked_by': [], 'liked': [], 'disliked': [user_id], 'last_shown_form': '',
                            'waiting': {'is_waiting': False}, 'is_admin': False, 'is_banned': False, 'is_active': True, 'ad_countdown': tools.ad_countdown, 'last_ad_key': '0'}
    tools.send_message(user_id, 'Привет! Это бот для поиска друзей👫 и компании на концерты Космонавтов нет.')
    tools.send_message(user_id, 'Давай создадим тебе анкету, она будет видна другим пользователям. Как тебя зовут?', keyboard={'keyboard': [[{'text': first_name}]], 'resize_keyboard': True})
    tools.users[user_id]['waiting']['is_waiting'] = True
    tools.users[user_id]['waiting']['reason'] = 'name'
    with open(f'{path}data/users.json', 'w') as fl:
        json.dump(tools.users, fl, indent=4)


def was_liked(user_id, msg):
    if msg == 'В другой раз':  # реакция на прошлую анкету
        tools.users[user_id]['waiting']['is_waiting'] = False
        del tools.users[user_id]['waiting']['reason']
        tools.show_next_form(user_id)
        return
    elif msg == '👍' and tools.users[user_id]['last_shown_form'] != '':
        liked_whom = tools.users[user_id]['last_shown_form']
        tools.users[user_id]['last_shown_form'] = ''
        tools.users[user_id]['liked'].append(liked_whom)
        if user_id in tools.users[liked_whom]['liked'] and 'is_active' in tools.users[liked_whom] and tools.users[liked_whom]['is_active']:
            tools.send_message(user_id, f'Взаимный лайк💖! Начинайте общаться {tools.users[liked_whom]["username"]}')
            tools.send_message(liked_whom, f'Взаимный лайк💖! Начинайте общаться {tools.users[user_id]["username"]}')
    elif msg == '👎' and tools.users[user_id]['last_shown_form'] != '':
        tools.users[user_id]['disliked'].append(tools.users[user_id]['last_shown_form'])
        tools.users[user_id]['last_shown_form'] = ''
    if len(tools.users[user_id]['was_liked_by']) != 0:  # показывание следующей
        tools.users[user_id]['last_shown_form'] = tools.users[user_id]['was_liked_by'][0]
        tools.send_form(user_id, tools.users[user_id]['was_liked_by'][0], is_was_liked=True)
        tools.users[user_id]['was_liked_by'].pop(0)
        with open(f'{path}data/users.json', 'w') as f:
            json.dump(tools.users, f, indent=4)
    else:
        tools.users[user_id]['waiting']['is_waiting'] = False
        del tools.users[user_id]['waiting']['reason']
        with open(f'{path}data/users.json', 'w') as fl:
            json.dump(tools.users, fl, indent=4)
        tools.show_next_form(user_id)


def case_picture(r):
    user_id = str(r['message']['from']['id'])
    if 'video' in r['message']:
        if int(r['message']['video']['duration']) <= 15:
            tools.users[user_id]['form']['picture'] = r['message']['video']['file_id']
            tools.users[user_id]['form']['pic_type'] = 'video'
            tools.users[user_id]['waiting']['is_waiting'] = False
            del tools.users[user_id]['waiting']['reason']
            with open(f'{path}data/users.json', 'w') as fl:
                json.dump(tools.users, fl, indent=4)
            tools.send_message(user_id, 'Твоя анкета готова!')
            tools.send_form(user_id, user_id)
            tools.send_message(user_id, 'Помни, что <b>в интернете люди могут выдавать себя не за того, кто они есть на самом деле</b>!')
            tools.send_message(user_id, 'Давай посмотрим кто тут есть🔍')
            tools.show_next_form(user_id)
        else:
            tools.send_message(user_id, 'Длительность видео должна быть меньше 15 сек.')
    elif 'photo' in r['message']:
        tools.users[user_id]['form']['picture'] = r['message']['photo'][-1]['file_id']
        tools.users[user_id]['form']['pic_type'] = 'photo'
        tools.users[user_id]['waiting']['is_waiting'] = False
        del tools.users[user_id]['waiting']['reason']
        with open(f'{path}data/users.json', 'w') as fl:
            json.dump(tools.users, fl, indent=4)
        tools.send_message(user_id, 'Твоя анкета готова!')
        tools.send_form(user_id, user_id)
        tools.send_message(user_id, 'Помни, что <b>в интернете люди могут выдавать себя не за того, кто они есть на самом деле</b>!')
        tools.send_message(user_id, 'Давай посмотрим кто тут есть🔍')
        tools.show_next_form(user_id)
    else:
        tools.send_message(user_id, 'Пришли фото или видео (до 15 сек.)')


def waiting_user_handler(r):
    if 'text' in r['message']:
        msg = r['message']['text']
    else:
        msg = None
    user_id = str(r['message']['from']['id'])
    reason = tools.users[user_id]['waiting']['reason']
    match reason:
        case 'ad':
            if msg == 'Удалить':
                tools.send_message(user_id, 'Пришлите id рекламы для удаления')
                tools.users[user_id]['waiting']['reason'] = 'del_ad'
                with open(f'{path}data/users.json', 'w') as fl:
                    json.dump(tools.users, fl, indent=4)
            elif msg == 'Посмотреть все':
                for ad_id in tools.ads:
                    tools.send_message(user_id, f'Айди рекламы: {ad_id}')
                    tools.send_ad(user_id, ad_id)
                tools.users[user_id]['waiting']['is_waiting'] = False
                del tools.users[user_id]['waiting']['reason']
                with open(f'{path}data/users.json', 'w') as fl:
                    json.dump(tools.users, fl, indent=4)
            elif msg == 'Добавить':
                tools.send_message(user_id, 'Давай')
                tools.users[user_id]['waiting']['reason'] = 'add_ad'
                with open(f'{path}data/users.json', 'w') as fl:
                    json.dump(tools.users, fl, indent=4)
            elif msg == 'Главное меню':
                tools.send_message(user_id, 'Меню')
                tools.users[user_id]['waiting']['is_waiting'] = False
                del tools.users[user_id]['waiting']['reason']
                with open(f'{path}data/users.json', 'w') as fl:
                    json.dump(tools.users, fl, indent=4)
        case 'del_ad':
            if msg in tools.ads:
                ad_id = msg
                tools.send_ad(user_id, ad_id)
                del tools.ads[ad_id]
                with open(f'{path}data/ads.json', 'w') as fl:
                    json.dump(tools.ads, fl, indent=4)
                tools.send_message(user_id, "Удалил")
            else:
                tools.send_message(user_id, 'Такой нет')
            tools.users[user_id]['waiting']['is_waiting'] = False
            del tools.users[user_id]['waiting']['reason']
            with open(f'{path}data/users.json', 'w') as fl:
                json.dump(tools.users, fl, indent=4)
        case 'add_ad':
            if 'caption' in r['message']:
                caption = r['message']['caption']
            elif 'text' in r['message']:
                caption = r['message']['text']
            else:
                caption = None
            if 'photo' in r['message']:
                photo = r['message']['photo'][-1]['file_id']
            else:
                photo = None
            ad_id = tools.add_ad(photo, caption)
            if ad_id is not None:
                tools.send_message(user_id, f'Айди рекламы: {ad_id}')
                tools.send_ad(user_id, ad_id)
            else:
                tools.send_message(user_id, 'Ошибка')
            tools.users[user_id]['waiting']['is_waiting'] = False
            del tools.users[user_id]['waiting']['reason']
            with open(f'{path}data/users.json', 'w') as fl:
                json.dump(tools.users, fl, indent=4)
        case 'reset':
            if msg == 'сбросить':
                create_account(r)
            else:
                tools.users[user_id]['waiting']['is_waiting'] = False
                del tools.users[user_id]['waiting']['reason']
                with open(f'{path}data/users.json', 'w') as fl:
                    json.dump(tools.users, fl, indent=4)
                tools.show_next_form(user_id)
        case 'was_liked':
            was_liked(user_id, msg)
        case 'name':
            if msg is not None:
                if len(msg) <= 50:
                    tools.users[user_id]['form']['name'] = str(msg)
                    tools.users[user_id]['waiting']['reason'] = 'town'
                    with open(f'{path}data/users.json', 'w') as fl:
                        json.dump(tools.users, fl, indent=4)
                    tools.send_message(user_id, f'{str(msg)}, в каком городе ты хочешь просматривать анкеты?', keyboard={'keyboard': [[{'text': town} for town in inner_list] for inner_list in tools.towns], 'resize_keyboard': True, 'one_time_keyboard': True})
                else:
                    tools.send_message(user_id, 'Максимум 50 символов')
            else:
                tools.send_message(user_id, 'Как тебя зовут?')
        case 'town':
            if any(msg in sublist for sublist in tools.towns):
                tools.users[user_id]['form']['town'] = msg
                if tools.users[user_id]['form']['age'] == 0:  # если начальная анкета, а не изменение города
                    tools.users[user_id]['waiting']['reason'] = 'age'
                    tools.send_message(user_id, 'Сколько тебе лет?', keyboard={"remove_keyboard": True})
                else:
                    tools.send_message(user_id, 'Готово', keyboard={"remove_keyboard": True})
                    tools.users[user_id]['waiting']['is_waiting'] = False
                    del tools.users[user_id]['waiting']['reason']
                    tools.show_next_form(user_id)
                with open(f'{path}data/users.json', 'w') as fl:
                    json.dump(tools.users, fl, indent=4)
            else:
                tools.send_message(user_id, 'Выбери город из списка👇', keyboard={'keyboard': [[{'text': town} for town in inner_list] for inner_list in tools.towns], 'one_time_keyboard': True, 'resize_keyboard': True})
        case 'age':
            if msg is not None and msg.isdigit():
                msg = int(msg)
                if 14 <= msg <= 100:
                    tools.users[user_id]['form']['age'] = msg
                    tools.users[user_id]['waiting']['reason'] = 'sex'
                    with open(f'{path}data/users.json', 'w') as fl:
                        json.dump(tools.users, fl, indent=4)
                    tools.send_message(user_id, 'Укажи свой пол👇', keyboard={'keyboard': [[{'text': 'Я парень'}, {'text': 'Я девушка'}]], 'resize_keyboard': True})
                else:
                    tools.send_message(user_id, 'Возраст 14+')
            else:
                tools.send_message(user_id, 'Только цифры. Сколько тебе лет?')
        case 'sex':
            if msg in ['Я парень', 'Я девушка']:
                if msg == 'Я девушка':
                    tools.users[user_id]['form']['sex'] = 'female'
                else:
                    tools.users[user_id]['form']['sex'] = 'male'
                tools.users[user_id]['waiting']['reason'] = 'searching for sex'
                with open(f'{path}data/users.json', 'w') as fl:
                    json.dump(tools.users, fl, indent=4)
                tools.send_message(user_id, 'Кто тебе интересен?', keyboard={'keyboard': [[{'text': 'Парни'}, {'text': 'Девушки'}, {'text': 'Без разницы'}]], 'resize_keyboard': True})
            else:
                tools.send_message(user_id, 'Укажи свой пол👇')
        case 'searching for sex':
            if msg in ['Парни', 'Девушки', 'Без разницы']:
                if msg == 'Парни':
                    tools.users[user_id]['form']['searching'] = 'male'
                elif msg == 'Девушки':
                    tools.users[user_id]['form']['searching'] = 'female'
                else:
                    tools.users[user_id]['form']['searching'] = 'any'
                tools.users[user_id]['waiting']['reason'] = 'about'
                with open(f'{path}data/users.json', 'w') as fl:
                    json.dump(tools.users, fl, indent=4)
                tools.send_message(user_id, 'Расскажи что-нибудь о себе. Это будет отображаться с твоей анкетой.', keyboard={'keyboard': [[{'text': 'Пропустить'}]], 'one_time_keyboard': True, 'resize_keyboard': True})
            else:
                tools.send_message(user_id, 'Кто тебе интересен?')
        case 'about':
            if msg is not None and msg != 'Пропустить':
                if len(msg) <= 500:
                    tools.users[user_id]['form']['about'] = msg
                    if tools.users[user_id]['form']['picture'] == '':  # если начальная анкета, а не изменение about
                        tools.users[user_id]['waiting']['reason'] = 'picture'
                        tools.send_message(user_id, 'Последний шаг❗ Пришли свое фото или небольшое видео🎥 (до 15 сек.)', keyboard={"remove_keyboard": True})
                    else:
                        tools.send_message(user_id, 'Готово', keyboard={"remove_keyboard": True})
                        tools.users[user_id]['waiting']['is_waiting'] = False
                        del tools.users[user_id]['waiting']['reason']
                        tools.show_next_form(user_id)
                    with open(f'{path}data/users.json', 'w') as fl:
                        json.dump(tools.users, fl, indent=4)
                else:
                    tools.send_message(user_id, 'Ого, ты очень разноплановая личность. Но для анкеты нужно что-то покороче, максимум 500 символов', keyboard={'keyboard': [[{'text': 'Пропустить'}]], 'one_time_keyboard': True, 'resize_keyboard': True})
            else:
                tools.send_message(user_id, 'Пока пропустим этот вопрос.')  # about уже пустой при создании
                if tools.users[user_id]['form']['picture'] == '':  # если начальная анкета, а не изменение about
                    tools.users[user_id]['waiting']['reason'] = 'picture'
                    tools.send_message(user_id, 'Последний шаг❗ Пришли свое фото или небольшое видео🎥 (до 15 сек.)', keyboard={"remove_keyboard": True})
                else:
                    tools.users[user_id]['waiting']['is_waiting'] = False
                    del tools.users[user_id]['waiting']['reason']
                    tools.show_next_form(user_id)
                with open(f'{path}data/users.json', 'w') as fl:
                    json.dump(tools.users, fl, indent=4)
        case 'picture':
            case_picture(r)
        case 'change_picture':
            if msg == 'Отменить':
                tools.users[user_id]['waiting']['is_waiting'] = False
                del tools.users[user_id]['waiting']['reason']
                tools.send_message(user_id, 'Отменил', keyboard={'keyboard': [[{'text': 'Изменить "о себе"'}, {'text': 'Изменить фото'}, {'text': 'Изменить город'}], [{'text': 'Главное меню'}]], 'resize_keyboard': True})
                with open(f'{path}data/users.json', 'w') as fl:
                    json.dump(tools.users, fl, indent=4)
            else:
                case_picture(r)


def dm_handler(r):
    user_id = str(r['message']['from']['id'])
    if user_id in tools.users and tools.users[user_id]['is_banned'] and not tools.users[user_id]['is_admin']:
        tools.send_message(user_id, 'Сори, ты в бане ⛔')
        return
    if 'text' in r['message']:
        msg = r['message']['text']
    else:
        msg = None
    if user_id in tools.users and 'is_active' in tools.users[user_id] and not tools.users[user_id]['is_active'] and msg != 'Включить':
        tools.send_message(user_id, 'Анкета отключена', keyboard={'keyboard': [[{'text': 'Включить'}]], 'resize_keyboard': True})
        return
    if user_id in tools.users and tools.users[user_id]['waiting']['is_waiting']:
        waiting_user_handler(r)
        return
    match msg:
        case '/start':
            if 'username' not in r['message']['from']:
                tools.send_message(user_id, 'Привет! У тебя не установлен username в телеграме, поэтому при взаимном лайке тебе не смогут написать. Поставь его и обязательно начни заново на /start')
                return
            if user_id in tools.users:
                tools.send_message(user_id, 'Осторожно! Это действие полностью сбросит вашу статистику и анкету. Все лайки, предпочтения, вообще ВСЕ!', keyboard={'keyboard': [[{'text': 'сбросить'}, {'text': 'НЕ НАДО'}]], 'resize_keyboard': True})
                tools.users[user_id]['waiting']['is_waiting'] = True
                tools.users[user_id]['waiting']['reason'] = 'reset'
                with open(f'{path}data/users.json', 'w') as fl:
                    json.dump(tools.users, fl, indent=4)
            else:
                create_account(r)
        case 'Включить' if user_id in tools.users:
            if not tools.users[user_id]['is_active']:
                tools.users[user_id]['is_active'] = True
                with open(f'{path}data/users.json', 'w') as fl:
                    json.dump(tools.users, fl, indent=4)
            else:
                tools.send_message(user_id, 'Ваша анкета не отключена')
            tools.show_next_form(user_id)
        case 'Отключить анкету' if user_id in tools.users:
            if tools.users[user_id]['is_active']:
                tools.users[user_id]['is_active'] = False
                tools.send_message(user_id, 'Ваша анкета была отключена', keyboard={'keyboard': [[{'text': 'Включить'}]], 'resize_keyboard': True})
                with open(f'{path}data/users.json', 'w') as fl:
                    json.dump(tools.users, fl, indent=4)
            tools.show_next_form(user_id)
        case '👍' if user_id in tools.users and tools.users[user_id]['last_shown_form'] != '':
            liked_whom = tools.users[user_id]['last_shown_form']
            tools.users[user_id]['last_shown_form'] = ''
            tools.users[user_id]['liked'].append(liked_whom)

            if user_id in tools.users[liked_whom]['liked'] and 'is_active' in tools.users[liked_whom] and tools.users[liked_whom]['is_active']:
                tools.send_message(user_id, f'Взаимный лайк💖! Начинайте общаться {tools.users[liked_whom]["username"]}')
                tools.send_message(liked_whom, f'Взаимный лайк💖! Начинайте общаться {tools.users[user_id]["username"]}')
            else:
                tools.users[liked_whom]['was_liked_by'].append(user_id)
                if 'is_active' in tools.users[liked_whom] and tools.users[liked_whom]['is_active']:
                    tools.send_message(liked_whom, f'{len(tools.users[liked_whom]["was_liked_by"])} человек хотят пообщаться с тобой.', keyboard={'keyboard': [[{'text': 'Посмотреть их анкеты'}, {'text': 'В другой раз'}]], 'resize_keyboard': True})
                    tools.users[liked_whom]['waiting']['is_waiting'] = True
                    tools.users[liked_whom]['waiting']['reason'] = 'was_liked'
                # не сохраняется тут потому что сохраняется дальше
            tools.show_next_form(user_id)
        case '👎' if user_id in tools.users and tools.users[user_id]['last_shown_form'] != '':
            tools.users[user_id]['disliked'].append(tools.users[user_id]['last_shown_form'])
            tools.users[user_id]['last_shown_form'] = ''
            tools.show_next_form(user_id)
        case '👤' if user_id in tools.users:
            tools.send_message(user_id, 'Твоя анкета:', keyboard={'keyboard': [[{'text': 'Изменить анкету'}, {'text': 'Кто меня лайкнул?'}], [{'text': 'Главное меню'}]], 'resize_keyboard': True})
            tools.send_form(user_id, user_id, False)
        case 'Кто меня лайкнул?' if user_id in tools.users:
            if len(tools.users[user_id]['was_liked_by']) > 0:
                tools.users[user_id]['waiting']['is_waiting'] = True
                tools.users[user_id]['waiting']['reason'] = 'was_liked'
                was_liked(user_id, msg)
            else:
                tools.send_message(user_id, 'Пока никто:(')
        case 'Изменить анкету' if user_id in tools.users:
            tools.send_message(user_id, 'Что вы хотите изменить?', keyboard={'keyboard': [[{'text': 'Изменить "о себе"'}, {'text': 'Изменить фото'}, {'text': 'Изменить город'}, {'text': 'Отключить анкету'}], [{'text': 'Главное меню'}]], 'resize_keyboard': True})
        case 'Изменить "о себе"' if user_id in tools.users:
            tools.users[user_id]['waiting']['is_waiting'] = True
            tools.users[user_id]['waiting']['reason'] = 'about'
            with open(f'{path}data/users.json', 'w') as f:
                json.dump(tools.users, f, indent=4)
            tools.send_message(user_id, 'Расскажи что-нибудь о себе. Это будет отображаться с твоей анкетой.', keyboard={'keyboard': [[{'text': 'Пропустить'}]], 'one_time_keyboard': True, 'resize_keyboard': True})
        case 'Изменить фото' if user_id in tools.users:
            tools.users[user_id]['waiting']['is_waiting'] = True
            tools.users[user_id]['waiting']['reason'] = 'change_picture'
            tools.send_message(user_id, 'Пришли свое фото или небольшое видео🎥 (до 15 сек.)', keyboard={'keyboard': [[{'text': 'Отменить'}]], 'resize_keyboard': True})
            with open(f'{path}data/users.json', 'w') as f:
                json.dump(tools.users, f, indent=4)
        case 'Изменить город' if user_id in tools.users:
            tools.users[user_id]['waiting']['is_waiting'] = True
            tools.users[user_id]['waiting']['reason'] = 'town'
            with open(f'{path}data/users.json', 'w') as fl:
                json.dump(tools.users, fl, indent=4)
            tools.send_message(user_id, f'В каком городе ты хочешь просматривать анкеты?', keyboard={'keyboard': [[{'text': town} for town in inner_list] for inner_list in tools.towns], 'resize_keyboard': True, 'one_time_keyboard': True})
        case 'админка' if user_id in tools.users and tools.users[user_id]['is_admin']:
            tools.send_message(user_id, 'админка', keyboard={'keyboard': [[{'text': 'Бан/разбан'}, {'text': 'Применить script'}, {'text': 'Реклама'}], [{'text': 'Главное меню'}]], 'resize_keyboard': True, 'one_time_keyboard': True})
        case 'Бан/разбан' if user_id in tools.users and tools.users[user_id]['is_admin']:
            tools.send_message(user_id, 'Пока только через конфиг')
        case 'Применить script к базе' if user_id in tools.users and tools.users[user_id]['is_admin']:
            tools.use_script(user_id)
        case 'Применить script' if user_id in tools.users and tools.users[user_id]['is_admin']:
            tools.send_message(user_id, 'Напиши Применить sсript к базе')
        case 'Реклама' if user_id in tools.users and tools.users[user_id]['is_admin']:
            tools.users[user_id]['waiting']['is_waiting'] = True
            tools.users[user_id]['waiting']['reason'] = 'ad'
            tools.send_message(user_id, 'Реклама', keyboard={'keyboard': [[{'text': 'Удалить'}, {'text': 'Посмотреть все'}, {'text': 'Добавить'}], [{'text': 'Главное меню'}]], 'resize_keyboard': True, 'one_time_keyboard': True})
            with open(f'{path}data/users.json', 'w') as fl:
                json.dump(tools.users, fl, indent=4)
        case _:
            if user_id in tools.users:
                tools.show_next_form(user_id)
            else:
                tools.send_message(user_id, 'Я тебя не знаю, перезапусти /start')


if __name__ == '__main__':
    if os.environ.get('AM_I_IN_A_DOCKER_CONTAINER', False):
        serve(app, host='0.0.0.0', port=8881, url_scheme='http')
    else:
        app.run(host='192.168.1.10', port=8886)
        # serve(app, host='192.168.1.10', port=8886, url_scheme='http')
