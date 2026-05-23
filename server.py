import requests
import json
import auth
from datetime import datetime, timezone, timedelta


class VPN:
    def __init__(self) -> None:
        login = auth.login
        password = auth.password
        self.host = auth.host
        self.header = []
        self.login_data = {"username": login, "password": password}
        self.ses = requests.Session()

    @staticmethod
    def save_json_data(data, file_name):
        with open(file_name, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)
            
    def test_connection(self):
        response = self.ses.post(f"{self.host}/login", data=self.login_data)
        if response.status_code == 200 and response.json().get("success"):
            return True
        raise Exception(f"Ошибка авторизации: {response.text}")

    def users(self):
        user_list = self.ses.get(f"{self.host}/panel/api/inbounds/list").json()
        return user_list

    def add_user(self, username, remark, days):
        now = datetime.now(timezone.utc) # Текущее время (UTC)
        expiry_date = now + timedelta(days=days) # Дата отключения (UTC)
        expiry_time_ms = int(expiry_date.timestamp() * 1000) # Значение для API

        inbound_list = self.ses.get(f"{self.host}/panel/api/inbounds/list").json()
        print(inbound_list)


    def del_user(self, user):
        pass

    def update_user(self, user):
        pass

    def check_user(self, user):
        pass



vpn = VPN()
vpn.test_connection()
vpn.add_user(username="brunno", remark="limit", days=10)


