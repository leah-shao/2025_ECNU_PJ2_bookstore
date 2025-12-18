from fe import conf
from fe.access import seller, auth
import time


def register_new_seller(user_id, password) -> seller.Seller:
    a = auth.Auth(conf.URL)
    code = a.register(user_id, password)
    # allow already-existing user (512) to be treated as success for tests
    assert code == 200 or code == 512
    # Add delay to ensure registration is committed and visible to other connections
    time.sleep(0.5)
    s = seller.Seller(conf.URL, user_id, password)
    return s
