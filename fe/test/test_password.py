import time
import uuid

import pytest

from fe.access import auth
from fe import conf


class TestPassword:
    @pytest.fixture(autouse=True)
    def pre_run_initialization(self):
        self.auth = auth.Auth(conf.URL)
        unique_id = str(uuid.uuid4())
        self.user_id = f"tpwd_{unique_id}"
        self.old_password = f"old_{uuid.uuid4().hex}"
        self.new_password = f"new_{uuid.uuid4().hex}"
        self.terminal = f"term_{uuid.uuid4().hex}"

        code = self.auth.register(self.user_id, self.old_password)
        assert code == 200
        yield

    def test_ok(self):
        code = self.auth.password(self.user_id, self.old_password, self.new_password)
        assert code == 200

        code, new_token = self.auth.login(
            self.user_id, self.old_password, self.terminal
        )
        assert code != 200

        code, new_token = self.auth.login(
            self.user_id, self.new_password, self.terminal
        )
        assert code == 200

        code = self.auth.logout(self.user_id, new_token)
        assert code == 200
