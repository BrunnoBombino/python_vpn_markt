import requests
import json
import auth


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
        return response

    def users(self):
        user_list = self.ses.get(f"{self.host}/panel/api/inbounds/list").json()
        return user_list

    def add_user(self, username, remark):
        pass

    def del_user(self, user):
        pass

    def update_user(self, user):
        pass

    def check_user(self, user):
        pass


vpn = VPN()
test = vpn.test_connection()
all_users = vpn.users()
vpn.save_json_data(all_users, "users.json")



#vless://bfac5d50-3bbf-4b19-bd58-d0c53abe0957@85.192.40.149:20671?type=tcp&encryption=none&security=reality&pbk=WjNgpbCRz71oIQAy20CG_drYBKASzuszKsFKKuQJ3yc&fp=chrome&sni=www.icloud.com&sid=b28b7c3e68fc95&spx=%2F#test-t9mhlvqr
#vless://bfac5d50-3bbf-4b19-bd58-d0c53abe0957@85.192.40.149:20671?type=tcp&security=reality&pbk=WjNgpbCRz71oIQAy20CG_drYBKASzuszKsFKKuQJ3yc&fp=chrome&sni=www.icloud.com&sid=b28b7c3e68fc95&spx=%2F#test-t9mhlvqr
