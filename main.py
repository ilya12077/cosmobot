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
    current_time = int(time.time())
    if current_time - pendingupdates_lastchecked > 60:
        pendingupdates_lastchecked = current_time
        response = requests.get(f'{tools.url}getWebhookInfo')
        if response.status_code == 200:
            pendingupdates_count = response.json().get("result", {}).get("pending_update_count", 0)
            if pendingupdates_count > 25:
                if current_time - pendingupdates_lastsent > 3600:  # 3600 секунд = 1 час
                    tools.send_message(647372660, f'⭕Я заметил, что pending updates сейчас: <b>{pendingupdates_count}</b>\n{tools.url}getWebhookInfo')
                    pendingupdates_lastsent = current_time
    if 'message' in r:
        if r['message']['chat']['type'] == 'private':
            dm_handler(r)
    return 'OK'


def create_account(r):
    user_id = str(r['message']['from']['id'])
    first_name = r['message']['from']['first_name']
    if 'username' in r['message']['from']:
        username = '@' + r['message']['from']['username']
    else:
        username = ''
    tools.users[user_id] = {'first_name': str(first_name), 'username': username, 'form': {'about': '', 'name': '', 'town': '', 'age': 0, 'sex': '', 'searching': '', 'picture': '', 'pic_type': ''}, 'was_liked_by': [], 'liked': [], 'disliked': [user_id], 'last_shown_form': '', 'waiting': {'is_waiting': False}, 'is_admin': False}
    tools.send_message(user_id, 'Привет! Это бот для поиска друзей👫 или пары💖 на концерты Космонавтов нет.')
    tools.send_message(user_id, 'Давай создадим тебе анкету, она будет видна другим пользователям. Как тебя зовут?', keyboard={'keyboard': [[{'text': first_name}]], 'resize_keyboard': True})
    tools.users[user_id]['waiting']['is_waiting'] = True
    tools.users[user_id]['waiting']['reason'] = 'name'
    with open(f'{path}data/users.json', 'w') as fl:
        json.dump(tools.users, fl, indent=4)


def waiting_user_handler(r):
    if 'text' in r['message']:
        msg = r['message']['text']
    else:
        msg = None
    user_id = str(r['message']['from']['id'])
    reason = tools.users[user_id]['waiting']['reason']
    match reason:
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
            if msg == 'В другой раз':
                tools.users[user_id]['waiting']['is_waiting'] = False
                del tools.users[user_id]['waiting']['reason']
                tools.show_next_form(user_id)
                return
            elif msg == '👍':
                liked_whom = tools.users[user_id]['last_shown_form']
                tools.users[user_id]['last_shown_form'] = ''
                tools.users[user_id]['liked'].append(liked_whom)
                if user_id in tools.users[liked_whom]['liked']:
                    tools.send_message(user_id, f'Взаимный лайк💖! Начинайте общаться {tools.users[liked_whom]["username"]}')
                    tools.send_message(liked_whom, f'Взаимный лайк💖! Начинайте общаться {tools.users[user_id]["username"]}')
            elif msg == '👎':
                tools.users[user_id]['disliked'].append(tools.users[user_id]['last_shown_form'])
                tools.users[user_id]['last_shown_form'] = ''
            if len(tools.users[user_id]['was_liked_by']) != 0:
                tools.send_form(user_id, tools.users[user_id]['was_liked_by'][0])
                tools.users[user_id]['last_shown_form'] = tools.users[user_id]['was_liked_by'][0]
                tools.users[user_id]['was_liked_by'].pop(0)
                with open(f'{path}data/users.json', 'w') as f:
                    json.dump(tools.users, f, indent=4)
            else:
                tools.users[user_id]['waiting']['is_waiting'] = False
                del tools.users[user_id]['waiting']['reason']
                with open(f'{path}data/users.json', 'w') as fl:
                    json.dump(tools.users, fl, indent=4)
                tools.show_next_form(user_id)
        case 'name':
            if msg is not None:
                if len(msg) <= 50:
                    tools.users[user_id]['form']['name'] = msg
                    tools.users[user_id]['waiting']['reason'] = 'town'
                    with open(f'{path}data/users.json', 'w') as fl:
                        json.dump(tools.users, fl, indent=4)
                    tools.send_message(user_id, f'{msg}, в каком городе ты хочешь просматривать анкеты?', keyboard={'keyboard': [[{'text': town} for town in tools.towns]], 'resize_keyboard': True, 'one_time_keyboard': True})
                else:
                    tools.send_message(user_id, 'Максимум 50 символов')
            else:
                tools.send_message(user_id, 'Как тебя зовут?')
        case 'town':
            if msg in tools.towns:
                tools.users[user_id]['form']['town'] = msg
                tools.users[user_id]['waiting']['reason'] = 'age'
                with open(f'{path}data/users.json', 'w') as fl:
                    json.dump(tools.users, fl, indent=4)
                tools.send_message(user_id, 'Сколько тебе лет?', keyboard={"remove_keyboard": True})
            else:
                tools.send_message(user_id, 'Выбери город из списка👇', keyboard={'keyboard': [[{'text': town} for town in tools.towns]], 'one_time_keyboard': True, 'resize_keyboard': True})
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
                    tools.users[user_id]['waiting']['reason'] = 'picture'
                    with open(f'{path}data/users.json', 'w') as fl:
                        json.dump(tools.users, fl, indent=4)
                    tools.send_message(user_id, 'Последний шаг❗. Пришли свое фото или небольшое видео🎥 (до 15 сек.)', keyboard={"remove_keyboard": True})
                else:
                    tools.send_message(user_id, 'Ого, ты очень разноплановая личность. Но для анкеты нужно что-то покороче, максимум 500 символов', keyboard={'keyboard': [[{'text': 'Пропустить'}]], 'one_time_keyboard': True, 'resize_keyboard': True})
            else:
                tools.users[user_id]['waiting']['reason'] = 'picture'
                with open(f'{path}data/users.json', 'w') as fl:
                    json.dump(tools.users, fl, indent=4)
                tools.send_message(user_id, 'Пока пропустим этот вопрос.')  # about уже пустой при создании
                tools.send_message(user_id, 'Последний шаг❗. Пришли свое фото или небольшое видео🎥 (до 15 сек.)', keyboard={"remove_keyboard": True})
        case 'picture':
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
                tools.send_message(user_id, 'Давай посмотрим кто тут есть🔍')
                tools.show_next_form(user_id)
            else:
                tools.send_message(user_id, 'Пришли фото или видео (до 15 сек.)')


def dm_handler(r):
    user_id = str(r['message']['from']['id'])
    # tools.send_form(user_id, user_id)
    # print(tools.send_photo(user_id, tools.users[user_id]['form']['picture']).json())
    if 'text' in r['message']:
        msg = r['message']['text']
    else:
        msg = None
    if user_id in tools.users and tools.users[user_id]['waiting']['is_waiting']:
        waiting_user_handler(r)
        return
    match msg:
        case '/start':
            if 'username' not in r['message']['from']:
                tools.send_message(user_id, 'Привет! У тебя не установлен username в телеграме, поэтому при взаимном лайке тебе не смогут написать. Поставь его и обязательно начни заново на /start')
                tools.users[user_id] = {'first_name': "", 'username': "", 'form': {'about': '', 'name': '', 'town': '', 'age': 0, 'sex': '', 'searching': '', 'picture': '', 'pic_type': ''}, 'was_liked_by': [], 'liked': [], 'disliked': [user_id], 'last_shown_form': '', 'waiting': {'is_waiting': False}, 'is_admin': False}
                with open(f'{path}data/users.json', 'w') as fl:
                    json.dump(tools.users, fl, indent=4)
                return
            if user_id in tools.users:
                tools.send_message(user_id, 'Осторожно! Это действие полностью сбросит вашу статистику и анкету. Все лайки, предпочтения, вообще ВСЕ!', keyboard={'keyboard': [[{'text': 'сбросить'}, {'text': 'Я ПЕРЕДУМАЛ'}]], 'resize_keyboard': True})
                tools.users[user_id]['waiting']['is_waiting'] = True
                tools.users[user_id]['waiting']['reason'] = 'reset'
                with open(f'{path}data/users.json', 'w') as fl:
                    json.dump(tools.users, fl, indent=4)
            else:
                create_account(r)
        case '👍' if tools.users[user_id]['last_shown_form'] != '':
            liked_whom = tools.users[user_id]['last_shown_form']
            tools.users[user_id]['last_shown_form'] = ''
            tools.users[user_id]['liked'].append(liked_whom)

            if user_id in tools.users[liked_whom]['liked']:
                tools.send_message(user_id, f'Взаимный лайк💖! Начинайте общаться {tools.users[liked_whom]["username"]}')
                tools.send_message(liked_whom, f'Взаимный лайк💖! Начинайте общаться {tools.users[user_id]["username"]}')
            else:
                tools.users[liked_whom]['was_liked_by'].append(user_id)
                tools.send_message(liked_whom, f'{len(tools.users[liked_whom]["was_liked_by"])} человек хотят пообщаться с тобой.', keyboard={'keyboard': [[{'text': 'Посмотреть их анкеты'}, {'text': 'В другой раз'}]], 'resize_keyboard': True})
                tools.users[liked_whom]['waiting']['is_waiting'] = True
                tools.users[liked_whom]['waiting']['reason'] = 'was_liked'
            tools.show_next_form(user_id)
        case '👎' if tools.users[user_id]['last_shown_form'] != '':
            tools.users[user_id]['disliked'].append(tools.users[user_id]['last_shown_form'])
            tools.users[user_id]['last_shown_form'] = ''
            tools.show_next_form(user_id)
        case '💤':
            pass
        case _:
            tools.show_next_form(user_id)


if __name__ == '__main__':
    if os.environ.get('AM_I_IN_A_DOCKER_CONTAINER', False):
        serve(app, host='0.0.0.0', port=8881, url_scheme='http')
    else:
        app.run(host='192.168.1.10', port=8886)
        # app.run(host='192.168.1.21', port=8881)
