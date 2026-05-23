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

    def save_cookies(self):
        """Сохраняет куки сессии в файл"""
        try:
            with open(self.cookie_file, "wb") as f:
                pickle.dump(self.ses.cookies, f)
            print("💾 Сессия успешно сохранена в файл.")
        except Exception as e:
            print(f"⚠️ Не удалось сохранить куки: {e}")

    def load_cookies(self):
        """Загружает куки сессии из файла, если он есть"""
        if os.path.exists(self.cookie_file):
            try:
                with open(self.cookie_file, "rb") as f:
                    self.ses.cookies.update(pickle.load(f))
                print("📂 Старая сессия загружена из файла.")
            except Exception as e:
                print(f"⚠️ Ошибка чтения файла сессии: {e}")

    def is_connected(self) -> bool:
        """Проверяет, жива ли текущая сессия API"""
        try:
            response = self.ses.get(f"{self.host}/panel/api/inbounds/list", timeout=5)
            if response.status_code != 200:
                return False
            return response.json().get("success") == True
        except (requests.RequestException, ValueError):
            return False

    def connect(self) -> bool:
        """Проверяет старую сессию и делает логин только при необходимости"""
        if self.is_connected():
            print("🔄 Сессия активна, повторный вход не требуется.")
            return True

        print("0️⃣ Сессия пуста или устарела. Выполняю вход...")
        try:
            response = self.ses.post(f"{self.host}/login", data=self.login_data, timeout=5)
            if response.status_code == 200 and response.json().get("success"):
                print("🔓 Успешная авторизация!")
                self.save_cookies()  # Сохраняем новые куки после успешного входа
                return True

            print(f"❌ Ошибка авторизации: {response.text}")
            return False
        except requests.RequestException as e:
            print(f"💥 Ошибка сети при подключении: {e}")
            return False

    @staticmethod
    def save_json_data(data, file_name):
        with open(file_name, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)

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
                print(f"remark: {inbound.get("remark")} - id: {inbound.get("id")}")
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

