import time

from server import VPN

vpn = VPN()
vpn.add_user(username="Serge", remark="Limit", days=10)
time.sleep(20)
new_data = vpn.update_user(username="Serge", remark="Limit", new_username="Lox", new_uuid=True, add_days=45)
print(new_data)
time.sleep(20)
vpn.change_inbound(username="Lox", current_remark="Limit", new_remark="Standart")
time.sleep(20)
vpn.change_inbound(username="Lox", current_remark="Standart", new_remark="VIP")
time.sleep(20)
vpn.del_user(username="Lox", remark="VIP")