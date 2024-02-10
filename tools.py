import html
import json
import os

import requests
from dotenv import load_dotenv, find_dotenv
from flask import Response

from script import script

load_dotenv(find_dotenv())
url = os.environ.get('URL')

if os.environ.get('AM_I_IN_A_DOCKER_CONTAINER', False):
    path = '/etc/cosmobot/'
else:
    path = ''

for filename in ['users.json', 'ads.json']:
    if not os.path.isfile(f'{path}data/{filename}'):
        # Создаем файл, если он не существует
        with open(f'{path}data/{filename}', 'w', encoding='utf-8') as fl:
            fl.write('{}')

with open(f'{path}data/users.json', 'r') as fl:
    users = json.load(fl)
with open(f'{path}data/ads.json', 'r') as fl:
    ads = json.load(fl)
towns = [['Москва', 'Санкт-Петербург', 'Екатеринбург', 'Омск'], ['Ростов-на-Дону', 'Челябинск', 'Красноярск', 'Воронеж', 'Краснодар'], ['Владимир', 'Тюмень', 'Ярославль', 'Абакан', 'Новосибирск']]


def send_message(chat_id: int | str, message, keyboard: dict = None, spoiler=False, reply_to_message_id: int = None) -> None | Response:
    # print(switch_safe_mode, switch_authorize_all, switch_entire_authorization, switch_message_deletion)
    if spoiler:
        message = f'<tg-spoiler>{message}</tg-spoiler>'
    if keyboard is None:
        send_body = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
    else:
        send_body = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML',
            'reply_markup': keyboard
        }
    if reply_to_message_id is not None:
        send_body['reply_to_message_id'] = reply_to_message_id
    try:
        r = requests.post(url + 'sendMessage', json=send_body)
        # print(r.content)
        if r.status_code == 400:
            send_body['text'] = html.escape(message)
            r = requests.post(url + 'sendMessage', json=send_body)
    except requests.exceptions.ConnectTimeout:
        r = requests.post(url + 'sendMessage', json=send_body)
        # print(r.content)
        if r.status_code == 400:
            send_body['text'] = html.escape(message)
            r = requests.post(url + 'sendMessage', json=send_body)
    return r


def send_photo(chat_id: int | str, file_id: str, caption: None | str = None, keyboard: dict = None) -> None | Response:
    send_body = {
        'chat_id': chat_id,
        'photo': file_id,
        'parse_mode': 'HTML'
    }
    if caption is not None:
        send_body['caption'] = caption
    if keyboard is not None:
        send_body['reply_markup'] = keyboard
    try:
        r = requests.post(url + 'sendPhoto', json=send_body)
    except requests.exceptions.ConnectTimeout:
        r = requests.post(url + 'sendPhoto', json=send_body)
    return r


def send_video(chat_id: int | str, file_id: str, caption: None | str = None, keyboard: dict = None) -> None | Response:
    send_body = {
        'chat_id': chat_id,
        'video': file_id,
        'parse_mode': 'HTML'
    }
    if caption is not None:
        send_body['caption'] = caption
    if keyboard is not None:
        send_body['reply_markup'] = keyboard
    try:
        r = requests.post(url + 'sendVideo', json=send_body)
    except requests.exceptions.ConnectTimeout:
        r = requests.post(url + 'sendVideo', json=send_body)
    return r


def send_form(send_to_user_id: int | str, whos_form_user_id: str, keyboard: bool = True) -> None | Response:
    if keyboard:
        keyboard = {'keyboard': [[{'text': '👍'}, {'text': '👎'}, {'text': '👤'}]], 'resize_keyboard': True}
    else:
        keyboard = None
    caption = str(', '.join([str(users[whos_form_user_id]['form']['name']), str(users[whos_form_user_id]['form']['age']), str(users[whos_form_user_id]['form']['about'])]))
    if users[whos_form_user_id]['form']['pic_type'] == 'video':
        return send_video(send_to_user_id, users[whos_form_user_id]['form']['picture'], caption, keyboard).json()
    elif users[whos_form_user_id]['form']['pic_type'] == 'photo':
        return send_photo(send_to_user_id, users[whos_form_user_id]['form']['picture'], caption, keyboard)


def show_next_form(show_to_user_id: int | str) -> None:
    flag = False
    for userid in users:
        if userid not in users[show_to_user_id]['disliked'] and userid not in users[show_to_user_id]['liked'] and show_to_user_id not in users[userid]['disliked'] and \
                (users[userid]['form']['searching'] == users[show_to_user_id]['form']['sex'] or users[userid]['form']['searching'] == 'any') and (users[show_to_user_id]['form']['searching'] == users[userid]['form']['sex'] or users[show_to_user_id]['form']['searching'] == 'any') \
                and users[userid]['form']['town'] == users[show_to_user_id]['form']['town'] and not users[show_to_user_id]['is_banned']:
            if users[show_to_user_id]['form']['picture'] != '':
                flag = True
                send_form(show_to_user_id, userid)
                users[show_to_user_id]['last_shown_form'] = userid
                break
    if not flag:
        send_message(show_to_user_id, 'К сожалению новые анкеты кончились. Возвращайся позже!', keyboard={'keyboard': [[{'text': '👍'}, {'text': '👎'}, {'text': '👤'}]], 'resize_keyboard': True})
    with open(f'{path}data/users.json', 'w') as f:
        json.dump(users, f, indent=4)


def use_script(issued_user_id: str):
    global users
    send_message(issued_user_id, 'применяю...')
    with open(f'{path}data/users.json', 'r', encoding='utf-8') as source:
        content = source.read()
    with open(f'{path}data/users_new.json', 'w', encoding='utf-8') as target:
        target.write(content)

    file_path = f'{path}data/users_bak.json'
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            send_message(issued_user_id, f"Файл {file_path} успешно удален.")
        except Exception as e:
            send_message(issued_user_id, f"Произошла ошибка при удалении файла {file_path}: {e}")
            return

    res = script(f'{path}data/users_new.json')

    if res:
        try:
            os.rename(f'{path}data/users.json', f'{path}data/users_bak.json')
            os.rename(f'{path}data/users_new.json', f'{path}data/users.json')
            send_message(issued_user_id, 'Успешно переименовано')
        except Exception as e:
            send_message(issued_user_id, f"Ошибка операционной системы: {e}")
            return
        with open(f'{path}data/users.json', 'r') as f:
            users = json.load(f)
        send_message(issued_user_id, 'Успех')
    else:
        send_message(issued_user_id, 'Script прошел с ошибкой')
        file_path = f'{path}data/users_new.json'
        try:
            os.remove(file_path)
            send_message(issued_user_id, f"Файл {file_path} успешно удален.")
        except Exception as e:
            send_message(issued_user_id, f"Произошла ошибка при удалении файла {file_path}: {e}")


def send_ad(user_id, ad_id: str, keyboard: dict = None):
    photo = ads[ad_id]['photo'] if 'photo' in ads[ad_id] else None
    caption = ads[ad_id]['caption'] if 'caption' in ads[ad_id] else None
    if ad_id in ads:
        if photo is not None:
            send_photo(user_id, photo, caption)
        else:
            send_message(user_id, caption)


def add_ad(photo: str | None = None, caption: str | None = None) -> str | None:
    if any([photo, caption]):
        for i in range(1, 100):  # можно просто увеличить
            if str(i) not in ads:
                ads[str(i)] = {}
                if caption is not None:
                    ads[str(i)]['caption'] = caption
                if photo is not None:
                    ads[str(i)]['photo'] = photo
                with open(f'{path}data/ads.json', 'w') as f:
                    json.dump(ads, f, indent=4)
                return str(i)
    return None
