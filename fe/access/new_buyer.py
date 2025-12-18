from fe import conf
from fe.access import buyer, auth
import time


def register_new_buyer(user_id, password) -> buyer.Buyer:
    a = auth.Auth(conf.URL)
    code = a.register(user_id, password)
    assert code == 200 or code == 512
    time.sleep(0.5)
    s = buyer.Buyer(conf.URL, user_id, password)
    return s
