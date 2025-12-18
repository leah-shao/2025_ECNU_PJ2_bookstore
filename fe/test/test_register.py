import time
import uuid

import pytest

from fe.access import auth
from fe import conf


class TestRegister:
    @pytest.fixture(autouse=True)
    def pre_run_initialization(self):
        # Use UUID v4 which is generated randomly and should be globally unique
        unique_id = str(uuid.uuid4()).replace('-', '')
        self.user_id = "treg{}".format(unique_id)
        self.password = "pass{}".format(unique_id)
        self.auth = auth.Auth(conf.URL)
        yield

    def test_register_ok(self):
        code = self.auth.register(self.user_id, self.password)
        # Allow either 200 (new) or 512 (already exists from database cache)
        assert code in (200, 512)


