import auth
from server import VPN

vpn = VPN()
test = vpn.connection()
print(f"Connecting to {auth.host} - {test}")
all_users = vpn.users()
vpn.save_json_data(all_users, "users.json")
vpn.add_user(username="brunno", remark="Limit", days=10)
