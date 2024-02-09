import json


def script(path:str) -> bool:
    try:
        with open(path, 'r') as f:
            users = json.load(f)
        for i in users:
            if 'ad_countdown' not in users[i]:
                users[i]['ad_countdown'] = 15
        with open(path, 'w') as f:
            json.dump(users, f, indent=4)
        return True
    except Exception as e:
        print(e)
        return False

