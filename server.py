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
        # 1. Проверяем/восстанавливаем сессию подключения
        if not self.connect():
            print("❌ Отмена операции: нет связи с API")
            return False

        if remark != "VIP":
            now = datetime.now(timezone.utc) # Текущее время (UTC)
            expiry_date = now + timedelta(days=days) # Дата отключения (UTC)
            expiry_time_ms = int(expiry_date.timestamp() * 1000) # Значение для API
        else:
            expiry_time_ms = 0

        inbound_id = self.find_inbound_id_by_remark(remark) # Находим ID нужного inbound

        client_uuid = str(uuid.uuid1())

        # Формируем структуру настроек
        client_settings = {
            "clients": [{
                "id": client_uuid,
                "alterId": 0,
                "email": username,
                "totalGB": 0,
                "expiryTime": expiry_time_ms,
                "enable": True,
                "tgId": "",
                "subId": "",
                "limitIp": 0
            }]
        }
        payload = {
            "id": inbound_id,
            "settings": json.dumps(client_settings)  # Используем стандартный json из вашего импорта
        }

        # Отправляем запрос в API
        url = f"{self.host}/panel/api/inbounds/addClient"
        response = self.ses.post(url, json=payload)

        if response.status_code == 200 and response.json().get("success"):
            print(f"✅ Пользователь {username} добавлен на {days} дней.")
            print(f"UUID: {client_uuid}")
            return response.json()
        else:
            print(f"❌ Ошибка API: {response.json().get('msg')}")
            return None

    def del_user(self, username, remark):
        # Проверяем/восстанавливаем сессию подключения
        if not self.connect():
            print("❌ Отмена операции: нет связи с API")
            return False

        # Получаем актуальный список инбаундов
        inbounds_data = self.users()
        if not inbounds_data.get("success"):
            print("❌ Не удалось получить список инбаундов")
            return False

        inbound_id = None
        client_uuid = None

        # Ищем инбаунд по названию и парсим его клиентов в поиске нужного UUID
        for inbound in inbounds_data.get("obj", []):
            if inbound.get("remark") == remark:
                inbound_id = inbound.get("id")
                try:
                    settings = json.loads(inbound.get("settings", "{}"))
                    for client in settings.get("clients", []):
                        if client.get("email") == username:
                            client_uuid = client.get("id")
                            break
                except Exception as e:
                    print(f"⚠️ Ошибка чтения настроек инбаунда: {e}")
                break

        # Проверяем, нашли ли мы всё необходимое
        if inbound_id is None:
            print(f"❌ Подключение (inbound) с названием '{remark}' не найдено!")
            return False

        if client_uuid is None:
            print(f"❌ Пользователь '{username}' не найден внутри инбаунда '{remark}'!")
            return False

        # Отправляем POST-запрос на эндпоинт удаления
        url = f"{self.host}/panel/api/inbounds/{inbound_id}/delClient/{client_uuid}"

        response = self.ses.post(url)

        if response.status_code == 200 and response.json().get("success"):
            print(f"🗑️ Пользователь {username} (UUID: {client_uuid}) успешно удален из '{remark}'.")
            return True
        else:
            print(response)
            print(f"❌ Ошибка API при удалении: {response.text}")
            return False

    def update_user(self, user):
        pass

    def check_user(self, user):
        pass
