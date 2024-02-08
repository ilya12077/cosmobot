import html
import json
import os

import requests
from dotenv import load_dotenv, find_dotenv
from flask import Response

load_dotenv(find_dotenv())
url = os.environ.get('URL')

if os.environ.get('AM_I_IN_A_DOCKER_CONTAINER', False):
    path = '/etc/cosmobot/'
else:
    path = ''

for filename in ['users.json']:
    if not os.path.isfile(f'{path}data/{filename}'):
        # Создаем файл, если он не существует
        with open(f'{path}data/{filename}', 'w', encoding='utf-8') as fl:
            fl.write('{}')

with open(f'{path}data/users.json', 'r') as fl:
    users = json.load(fl)
towns = ['Москва']


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
    r = requests.post(url + 'sendMessage', json=send_body)
    # print(r.content)
    if r.status_code == 400:
        send_message(chat_id, html.escape(message), keyboard, spoiler)
    else:
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
    r = requests.post(url + 'sendVideo', json=send_body)
    return r


def send_form(send_to_user_id: int | str, whos_form_user_id: str) -> None | Response:
    caption = str(', '.join([str(users[whos_form_user_id]['form']['name']), str(users[whos_form_user_id]['form']['age']), str(users[whos_form_user_id]['form']['about'])]))
    if users[whos_form_user_id]['form']['pic_type'] == 'video':
        return send_video(send_to_user_id, users[whos_form_user_id]['form']['picture'], caption, {'keyboard': [[{'text': '👍'}, {'text': '👎'}, {'text': '💤'}]], 'resize_keyboard': True}).json()
    elif users[whos_form_user_id]['form']['pic_type'] == 'photo':
        return send_photo(send_to_user_id, users[whos_form_user_id]['form']['picture'], caption, {'keyboard': [[{'text': '👍'}, {'text': '👎'}, {'text': '💤'}]], 'resize_keyboard': True})


def show_next_form(show_to_user_id: int | str) -> None:
    flag = False
    for userid in users:
        if userid not in users[show_to_user_id]['disliked'] and userid not in users[show_to_user_id]['liked'] and show_to_user_id not in users[userid]['disliked'] and\
                (users[userid]['form']['searching'] == users[show_to_user_id]['form']['sex'] or users[userid]['form']['searching'] == 'any') and (users[show_to_user_id]['form']['searching'] == users[userid]['form']['sex'] or users[show_to_user_id]['form']['searching'] == 'any')\
                and users[userid]['form']['town'] == users[show_to_user_id]['form']['town']:
            flag = True
            send_form(show_to_user_id, userid)
            users[show_to_user_id]['last_shown_form'] = userid
            break
    if not flag:
        send_message(show_to_user_id, 'К сожалению новые анкеты кончились. Возвращайся позже!', keyboard={"remove_keyboard": True})
    with open(f'{path}data/users.json', 'w') as f:
        json.dump(users, f, indent=4)
