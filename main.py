import time

from server import VPN

vpn = VPN()
vpn.add_user(username="Serge", remark="VIP", days=0)
time.sleep(20)
vpn.del_user(username="Serge", remark="VIP")