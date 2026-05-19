import requests
import json


class VPN:
    def __init__(self) -> None:
        login = 'Galas'
        password = 'Galakhov23418'
        self.host = 'https://85.192.40.149:19045/6QIM0PTGPA5RjE2oKi'
        self.header = []
        self.login_data = {"username": login, "password": password}
        self.ses = requests.Session()

    @staticmethod
    def save_json_data(data, file_name):
        with open(file_name, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)
            
    def test_connection(self):
        response = self.ses.post(f"{self.host}/login", data=self.login_data)
        return response

    def users(self):
        user_list = self.ses.get(f"{self.host}/panel/api/inbounds/list").json()
        return user_list


vpn = VPN()
test = vpn.test_connection()
all_users = vpn.users()
vpn.save_json_data(all_users, "users.json")
