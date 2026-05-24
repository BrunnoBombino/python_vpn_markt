import json

from core.init_api import api

with open("users.json", "w", encoding="utf-8") as file:
    json.dump(api.users(), file, indent=4, ensure_ascii=False)