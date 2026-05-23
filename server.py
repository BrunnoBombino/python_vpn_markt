import os
import pickle
import uuid
import requests
import json
import auth
from datetime import datetime, timezone, timedelta


class VPN:
    def __init__(self, cookie_file="session_cookies.pkl") -> None:
        self.host = auth.host
        self.login_data = {"username": auth.login, "password": auth.password}
        self.cookie_file = cookie_file

        # Создаем сессию
        self.ses = requests.Session()

        # Автоматически загружаем старые куки, если файл существует
        self.load_cookies()

    @staticmethod
    def save_json_data(data, file_name):
        with open(file_name, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)
            
    def connection(self):
        response = self.ses.post(f"{self.host}/login", data=self.login_data)
        if response.status_code == 200 and response.json().get("success"):
            return True
        raise Exception(f"Ошибка авторизации: {response.text}")

    def users(self):
        user_list = self.ses.get(f"{self.host}/panel/api/inbounds/list").json()
        return user_list

    def find_inbound_id_by_remark(self, remark):
        """Поиск ID инбаунда по его названию (remark)"""
        response = self.ses.get(f"{self.host}/panel/api/inbounds/list")
        if response.status_code != 200:
            raise Exception(f"Не удалось получить список инбаундов: {response.text}")

        inbounds = response.json().get("obj", [])
        for inbound in inbounds:
            if inbound.get("remark") == remark:
                return inbound.get("id")
        return None

    def add_user(self, username, remark, days):
        now = datetime.now(timezone.utc) # Текущее время (UTC)
        expiry_date = now + timedelta(days=days) # Дата отключения (UTC)
        expiry_time_ms = int(expiry_date.timestamp() * 1000) # Значение для API

        inbound_id = self.find_inbound_id_by_remark(remark) # Находим ID нужного inbound


    def del_user(self, user):
        pass

    def update_user(self, user):
        pass

    def check_user(self, user):
        pass



vpn = VPN()
vpn.test_connection()
#vpn.add_user(username="brunno", remark="Limit", days=10)


