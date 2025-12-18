import time
import pytest

from fe.access.new_seller import register_new_seller
import uuid


class TestCreateStore:
    @pytest.fixture(autouse=True)
    def pre_run_initialization(self):
        # Use timestamp + uuid for absolute uniqueness
        ts = str(int(time.time() * 1000000))
        self.user_id = "tcs{}".format(ts)
        self.store_id = "tcs_st{}".format(ts)
        self.password = self.user_id
        yield

    def test_ok(self):
        self.seller = register_new_seller(self.user_id, self.password)
        code = self.seller.create_store(self.store_id)
        assert code == 200

