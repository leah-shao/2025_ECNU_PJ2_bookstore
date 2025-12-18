import time
import uuid

import pytest

from fe.access import auth
from fe import conf


class TestLogin:
    @pytest.fixture(autouse=True)
    def pre_run_initialization(self):
        self.auth = auth.Auth(conf.URL)
        unique_id = str(uuid.uuid4())
        self.user_id = f"tlog_{unique_id}"
        self.password = f"pass_{uuid.uuid4().hex}"
        self.terminal = f"term_{uuid.uuid4().hex}"
        code = self.auth.register(self.user_id, self.password)
        assert code == 200
        yield

    def test_ok(self):
        code, token = self.auth.login(self.user_id, self.password, self.terminal)
        assert code == 200

        code = self.auth.logout(self.user_id, token)
        assert code == 200


