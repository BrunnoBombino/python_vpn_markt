import time

from API import API

# vpn = VPN()
# vpn.add_user(username="Serge", remark="Limit", days=10)
# time.sleep(20)
# new_data = vpn.update_user(username="Serge", remark="Limit", new_username="Lox", new_uuid=True, add_days=45)
# print(new_data)
# time.sleep(20)
# vpn.change_inbound(username="Lox", current_remark="Limit", new_remark="VIP")
# time.sleep(20)
# vpn.del_user(username="Lox", remark="VIP")

# vpn = VPN()
#
# # Запрашиваем информацию о пользователе
# info = vpn.check_user("a-02")
#
# if info:
#     print(f"\n===== ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ: {info['username']} =====")
#     print(f"📍 Подключение (Inbound): {info['inbound_remark']} (ID: {info['inbound_id']})")
#     print(f"🔑 Протокол и UUID: {info['protocol'].upper()} | {info['uuid']}")
#     print(f"🟢 Статус в панели: {'АКТИВЕН' if info['is_enabled'] else 'ЗАБЛОКИРОВАН'}")
#     print(f"📅 Срок действия подписки: {info['expiry_date']}")
#     print(f"📊 Использовано трафика: {info['used_traffic_gb']} ГБ / {info['limit_traffic_gb']} ГБ")
#     print("==================================================\n")
#
# # Обнуляем трафик для вашего пользователя
# vpn.reset_traffic("a-02")
#
# # Проверяем результат, чтобы убедиться, что там теперь 0.0 ГБ
# info = vpn.check_user("a-02")
#
#
# if info:
#     print(f"\n===== ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ: {info['username']} =====")
#     print(f"📍 Подключение (Inbound): {info['inbound_remark']} (ID: {info['inbound_id']})")
#     print(f"🔑 Протокол и UUID: {info['protocol'].upper()} | {info['uuid']}")
#     print(f"🟢 Статус в панели: {'АКТИВЕН' if info['is_enabled'] else 'ЗАБЛОКИРОВАН'}")
#     print(f"📅 Срок действия подписки: {info['expiry_date']}")
#     print(f"📊 Использовано трафика: {info['used_traffic_gb']} ГБ / {info['limit_traffic_gb']} ГБ")
#     print("==================================================\n")

api = API()
api.add_user(username="Brunno", remark="VIP")
# Генерируем ссылку. Скрипт сам подставит IP вашего сервера 85.192.40.149 из настроек хоста
config_link = api.get_client_link("Brunno")

if config_link:
    print("\n🔗 ССЫЛКА ДЛЯ НАСТРОЙКИ VPN:")
    print(config_link)
    print("===================================\n")