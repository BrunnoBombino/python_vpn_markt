import auth
from server import VPN

vpn = VPN()
test = vpn.test_connection()
print(f"Connecting to {auth.host} - {test}")
all_users = vpn.users()
vpn.save_json_data(all_users, "users.json")

response = vpn.ses.get(f"{auth.host}/panel/api/inbounds/list")
if response.status_code != 200:
    raise Exception(f"Не удалось получить Inbound list {response.text}")
inbounds = response.json().get("obj", [])
for inbound in inbounds:
    print(f"inbound - {inbound.get("remark")}, id - {inbound.get("id")}")

