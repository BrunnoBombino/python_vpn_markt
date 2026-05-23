import os
import pickle
import time
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
        self._load_cookies()

    def _save_cookies(self):
        """Сохраняет куки сессии в файл"""
        try:
            with open(self.cookie_file, "wb") as f:
                pickle.dump(self.ses.cookies, f)
            print("💾 Сессия успешно сохранена в файл.")
        except Exception as e:
            print(f"⚠️ Не удалось сохранить куки: {e}")

    def _load_cookies(self):
        """Загружает куки сессии из файла, если он есть"""
        if os.path.exists(self.cookie_file):
            try:
                with open(self.cookie_file, "rb") as f:
                    self.ses.cookies.update(pickle.load(f))
                print("📂 Старая сессия загружена из файла.")
            except Exception as e:
                print(f"⚠️ Ошибка чтения файла сессии: {e}")

    def _is_connected(self) -> bool:
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
        if self._is_connected():
            print("🔄 Сессия активна, повторный вход не требуется.")
            return True

        print("0️⃣ Сессия пуста или устарела. Выполняю вход...")
        try:
            response = self.ses.post(f"{self.host}/login", data=self.login_data, timeout=5)
            if response.status_code == 200 and response.json().get("success"):
                print("🔓 Успешная авторизация!")
                self._save_cookies()  # Сохраняем новые куки после успешного входа
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

    def update_user(self, username, remark, new_username=None, new_uuid=None, add_days=None):
        """
                Обновляет данные клиента (Email, UUID, Время) строго внутри одного инбаунда.

                :param username: Текущее имя (email) клиента
                :param remark: Название инбаунда, в котором находится клиент
                :param new_username: (Опционально) Новое имя для замены
                :param new_uuid: (Опционально) Новый UUID для замены
                :param add_days: (Опционально) Количество дней, которое нужно ДОБАВИТЬ к подписке
        """

        if not self.connect():
            print("❌ Отмена операции: нет связи с API")
            return False

        # Получаем список инбаундов
        inbounds_data = self.users()
        if not inbounds_data.get("success"):
            print("❌ Не удалось получить список инбаундов")
            return False

        inbound_id = None
        client_data = None

        # Ищем инбаунд и текущие настройки клиента
        for inbound in inbounds_data.get("obj", []):
            if inbound.get("remark") == remark:
                inbound_id = inbound.get("id")
                try:
                    settings = json.loads(inbound.get("settings", "{}"))
                    for client in settings.get("clients", []):
                        if client.get("email") == username:
                            client_data = client.copy()  # Создаем копию для изменений
                            break
                except Exception as e:
                    print(f"⚠️ Ошибка чтения настроек инбаунда: {e}")
                break

        if inbound_id is None:
            print(f"❌ Инбаунд '{remark}' не найден!")
            return False
        if client_data is None:
            print(f"❌ Пользователь '{username}' не найден внутри '{remark}'!")
            return False

        # Сохраняем старый UUID, так как он нужен для URL-адреса запроса
        old_uuid = client_data["id"]

        # Применяем изменения, если они переданы
        if new_username:
            client_data["email"] = new_username
        if new_uuid:
            new_uuid = str(uuid.uuid1())
            client_data["id"] = new_uuid

        # Добавляем дни к текущему остатку
        if add_days is not None:
            current_expiry = client_data.get("expiryTime", 0)
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

            # Если аккаунт безлимитный (0) или подписка уже истекла, считаем от текущего момента
            if current_expiry <= now_ms:
                base_time = datetime.now(timezone.utc)
            else:
                base_time = datetime.fromtimestamp(current_expiry / 1000, tz=timezone.utc)

            new_expiry_date = base_time + timedelta(days=add_days)
            client_data["expiryTime"] = int(new_expiry_date.timestamp() * 1000)


        # Формируем payload для отправки
        # Панель ожидает структуру {"clients": [измененный_объект_клиента]}
        payload = {
            "id": inbound_id,
            "settings": json.dumps({"clients": [client_data]})
        }

        # Отправляем POST-запрос, указывая старый UUID в пути, чтобы панель нашла нужную запись
        url = f"{self.host}/panel/api/inbounds/updateClient/{old_uuid}"
        response = self.ses.post(url, json=payload)

        # 5. Проверяем результат
        if response.status_code == 200 and response.json().get("success"):
            print(f"✅ Данные пользователя '{username}' успешно обновлены.")
            if add_days:
                final_date = datetime.fromtimestamp(client_data["expiryTime"] / 1000, tz=timezone.utc)
                print(f"📅 Новая дата отключения: {final_date.strftime('%Y-%m-%d %H:%M:%S')} UTC")
            return client_data
        else:
            print(f"❌ Ошибка API при обновлении: {response.text}")
            return False

    def change_inbound(self, username, current_remark, new_remark):
        """
        Абсолютно безопасный перенос с учетом глобальной уникальности email в 3x-ui.
        Проверяет, что имя свободно во ВСЕЙ панели перед деструктивными действиями.
        """

        # Очищаем пробелы
        username = username.strip()
        current_remark = current_remark.strip()
        new_remark = new_remark.strip()

        if not self.connect():
            print("❌ Отмена операции: нет связи с API")
            return False

        inbounds_data = self.users()
        if not inbounds_data.get("success"):
            print("❌ Не удалось получить список инбаундов")
            return False

        client_data = None
        new_inbound_id = None

        # Переменная для отслеживания: занято ли имя КЕМ-ТО ЕЩЕ на сервере
        is_name_taken_elsewhere = False
        where_taken = ""

        # ГЛОБАЛЬНАЯ ПРОВЕРКА ВСЕЙ ПАНЕЛИ
        for inbound in inbounds_data.get("obj", []):
            remark_name = inbound.get("remark")

            # Сохраняем ID целевого инбаунда
            if remark_name == new_remark:
                new_inbound_id = inbound.get("id")

            try:
                settings = json.loads(inbound.get("settings", "{}"))
                for client in settings.get("clients", []):
                    if client.get("email") == username:
                        if remark_name == current_remark:
                            # Нашли нашего целевого клиента в исходной точке
                            client_data = client.copy()
                        else:
                            # Нашли тезку в ЛЮБОМ другом инбаунде (включая целевой)
                            is_name_taken_elsewhere = True
                            where_taken = remark_name
            except Exception as e:
                print(f"⚠️ Ошибка чтения настроек инбаунда '{remark_name}': {e}")

        # Проверки перед переносом
        if client_data is None:
            print(f"❌ Пользователь '{username}' не найден в стартовом инбаунде '{current_remark}'!")
            return False
        if new_inbound_id is None:
            print(f"❌ Целевой инбаунд '{new_remark}' не найден на сервере!")
            return False
        if current_remark == new_remark:
            print(f"ℹ️ Пользователь '{username}' уже находится в '{new_remark}'.")
            return True

        # 🛡️ КРИТИЧЕСКАЯ ЗАЩИТА: API 3x-ui запрещает одинаковые Email глобально.
        if is_name_taken_elsewhere:
            print(
                f"❌ ГЛОБАЛЬНЫЙ КОНФЛИКТ ИМЕН: Имя '{username}' уже используется на сервере в инбаунде '{where_taken}'!")
            print("🛡️ Операция отменена. Старый пользователь в безопасности и НЕ был удален.")
            return False

        # Если имя глобально чистое — запускаем процесс модификации (VIP)
        if new_remark.upper() == "VIP":
            print(f"⭐ Перенос в VIP. Сбрасываем лимиты для {username}...")
            client_data["expiryTime"] = 0
            client_data["totalGB"] = 0

        # Запись аварийного бэкапа
        backup_filename = "backup_lost_users.txt"
        backup_entry = f"=== BACKUP {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n" \
                       f"User: {username}\n" \
                       f"Target Inbound ID: {new_inbound_id}\n" \
                       f"Data: {json.dumps(client_data)}\n" \
                       f"=====================================\n\n"
        try:
            with open(backup_filename, "a", encoding="utf-8") as f:
                f.write(backup_entry)
        except Exception as e:
            print(f"⚠️ Ошибка бэкапа ({e}), но продолжаем...")

        # Удаление
        print(f"🗑️ Удаляем клиента из '{current_remark}'...")
        if not self.del_user(username, current_remark):
            print("❌ Ошибка удаления. Перенос прерван.")
            return False
        # Создание на новом месте
        payload = {
            "id": new_inbound_id,
            "settings": json.dumps({"clients": [client_data]})
        }

        try:
            response = self.ses.post(f"{self.host}/panel/api/inbounds/addClient", json=payload, timeout=10)
            success = response.status_code == 200 and response.json().get("success")
        except Exception as e:
            success = False
            print(f"💥 Сбой сети: {e}")

        if success:
            print(f"🚀 Пользователь '{username}' успешно перенесен в '{new_remark}'!")
            # Чистим бэкап
            try:
                if os.path.exists(backup_filename):
                    with open(backup_filename, "r", encoding="utf-8") as f:
                        content = f.read()
                    content = content.replace(backup_entry, "")
                    with open(backup_filename, "w", encoding="utf-8") as f:
                        f.write(content)
            except Exception as e:
                print(f"⚠️ Ошибка очистки бэкапа: {e}")
            return True
        else:
            print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: Не удалось создать пользователя на новом месте!")
            print(f"🚨 Восстановите его из файла '{backup_filename}'")
            return False

    def restore_lost_users(self, backup_filename="backup_lost_users.txt"):
        """
        Сканирует файл бэкапа и пытается автоматически восстановить
        всех пользователей, застрявших во время неудачного переноса.
        """
        if not os.path.exists(backup_filename) or os.path.getsize(backup_filename) == 0:
            print("📅 Файл бэкапа пуст или отсутствует. Восстановление не требуется.")
            return True

        if not self.connect():
            print("❌ Отмена операции: нет связи с API")
            return False

        print(f"🔍 Начинаю анализ файла бэкапа '{backup_filename}'...")

        # Будем собирать сюда блоки текста, которые НЕ удалось восстановить
        failed_blocks = []

        # Сначала прочитаем весь файл
        with open(backup_filename, "r", encoding="utf-8") as f:
            content = f.read()

        # Разделяем файл на отдельные бэкап-блоки
        blocks = content.split("=== BACKUP ")

        restored_count = 0
        skipped_count = 0

        for block in blocks:
            if not block.strip():
                continue

            # Восстанавливаем разделитель для лога, если этот блок не починится
            full_block_text = "=== BACKUP " + block

            # Извлекаем нужные строчки с помощью парсинга текста
            lines = block.split("\n")
            target_inbound_id = None
            client_data_json = None
            username = "Неизвестно"

            for line in lines:
                if line.startswith("User:"):
                    username = line.replace("User:", "").strip()
                elif line.startswith("Target Inbound ID:"):
                    target_inbound_id = line.replace("Target Inbound ID:", "").strip()
                elif line.startswith("Data:"):
                    client_data_json = line.replace("Data:", "").strip()

            # Если блок поврежден или это пустой кусок, просто сохраняем его
            if not target_inbound_id or not client_data_json:
                failed_blocks.append(full_block_text)
                continue

            print(f"⏳ Пробую восстановить пользователя '{username}' в инбаунд ID {target_inbound_id}...")

            # Формируем payload для API панели
            try:
                # client_data_json — это уже готовая JSON строка из файла,
                # превращаем её обратно в словарь, чтобы убедиться в корректности
                client_data = json.loads(client_data_json)

                payload = {
                    "id": int(target_inbound_id),
                    "settings": json.dumps({"clients": [client_data]})
                }

                # Шлем экстренный запрос на добавление
                response = self.ses.post(f"{self.host}/panel/api/inbounds/addClient", json=payload, timeout=10)

                if response.status_code == 200 and response.json().get("success"):
                    print(f"✅ Пользователь '{username}' успешно ВОССТАНОВЛЕН в панели!")
                    restored_count += 1
                else:
                    # Если панель ответила, что такой email уже есть, значит кто-то создал его вручную
                    if "already exists" in response.text:
                        print(
                            f"ℹ️ Пользователь '{username}' уже существует в целевом инбаунде. Запись удалена из бэкапа.")
                        skipped_count += 1
                    else:
                        print(f"❌ Панель отклонила запрос восстановления для '{username}': {response.text}")
                        failed_blocks.append(full_block_text)

            except Exception as e:
                print(f"💥 Ошибка при обработке записи '{username}': {e}")
                failed_blocks.append(full_block_text)

        # Перезаписываем файл бэкапа, оставляя только то, что НЕ удалось восстановить
        try:
            with open(backup_filename, "w", encoding="utf-8") as f:
                # Очищаем лишние переносы строк и собираем оставшиеся блоки
                new_content = "".join(failed_blocks).strip()
                if new_content:
                    f.write(new_content + "\n\n")

            print(
                f"📊 Итоги восстановления: Успешно: {restored_count}, Пропущено: {skipped_count}, Сбоев: {len(failed_blocks)}")
        except Exception as e:
            print(f"⚠️ Ошибка при обновлении файла бэкапа: {e}")

        return len(failed_blocks) == 0

    def check_user_by_username(self, username):
        pass

    def check_user_by_uuid(self, user_uuid):
        pass
