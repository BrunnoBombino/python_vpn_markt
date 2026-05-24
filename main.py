from core.API import API

# vpn = API()
# vpn.add_user(username="Brunno", remark="VIP")
#time.sleep(20)
# new_data = vpn.update_user(username="Serge", remark="Limit", new_username="Lox", new_uuid=True, add_days=45)
# print(new_data)
# time.sleep(20)
# vpn.change_inbound(username="Lox", current_remark="Limit", new_remark="VIP")
# time.sleep(20)
# vpn.del_user(username="Lox", remark="VIP")

# vpn = API()
#
# Запрашиваем информацию о пользователе
# info = vpn.check_user("Brunno")
#
# if info:
#     print(f"\n===== ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ: {info['username']} =====")
#     print(f"📍 Подключение (Inbound): {info['inbound_remark']} (ID: {info['inbound_id']})")
#     print(f"🔑 Протокол и UUID: {info['protocol'].upper()} | {info['uuid']}")
#     print(f"🔗 SubID: {info['subId']}")
#     print(f"🟢 Статус в панели: {'АКТИВЕН' if info['is_enabled'] else 'ЗАБЛОКИРОВАН'}")
#     print(f"📅 Срок действия подписки: {info['expiry_date']}")
#     print(f"📊 Использовано трафика: {info['used_traffic_gb']} ГБ / {info['limit_traffic_gb']} ГБ")
#     print("==================================================\n")
# #
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

# api = API()
# users = api.users()
# api.save_json_data(users, 'users.json')
#api.add_user(username="Brunno", remark="VIP")
#Генерируем ссылку. Скрипт сам подставит IP вашего сервера 85.192.40.149 из настроек хоста


api = API()
(api.add_user(username="Brunno", remark="Limit", days=15))
username = "Brunno"
info = api.check_user(username)
sub_link = api.get_subscription_link(username)

if info:
    print(f"\n===== ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ: {info['username']} =====")
    print(f"📍 Подключение (Inbound): {info['inbound_remark']} (ID: {info['inbound_id']})")
    print(f"🔑 Протокол и UUID: {info['protocol'].upper()} | {info['uuid']}")

    if sub_link:
        print(f"🔄 Ссылка подписки: {sub_link}")  # Наш новый метод и эмодзи обновления

    print(f"🟢 Статус в панели: {'АКТИВЕН' if info['is_enabled'] else 'ЗАБЛОКИРОВАН'}")
    print(f"📅 Срок действия подписки: {info['expiry_date']}")
    print(f"📊 Использовано трафика: {info['used_traffic_gb']} ГБ / {info['limit_traffic_gb']} ГБ")
    print("==================================================\n")
config_link = api.get_client_link("Brunno")

if config_link:
    print("\n🔗 ССЫЛКА ДЛЯ НАСТРОЙКИ VPN:")
    print(config_link)
    print("===================================\n")