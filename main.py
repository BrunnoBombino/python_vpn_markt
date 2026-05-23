import auth
from server import VPN

vpn = VPN()
vpn.connect()
all_users = vpn.users()
vpn.save_json_data(all_users, "users.json")
vpn.add_user(username="brunno", remark="Limit", days=10)
