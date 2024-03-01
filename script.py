import html
import json


def escape_without_double_encoding(text):
    # Декодируем HTML-сущности в тексте, чтобы преобразовать их обратно в исходные символы
    decoded_text = html.unescape(text)
    # Затем экранируем текст, теперь без риска двойного экранирования
    escaped_text = html.escape(decoded_text)
    return escaped_text


def script(path: str) -> bool:
    try:
        with open(path, 'r') as f:
            users = json.load(f)
        for i in users:
            users[i]['form']['name'] = escape_without_double_encoding(users[i]['form']['name'])
            users[i]['form']['about'] = escape_without_double_encoding(users[i]['form']['about'])
        with open(path, 'w') as f:
            json.dump(users, f, indent=4)
        return True
    except Exception as e:
        print(e)
        return False
