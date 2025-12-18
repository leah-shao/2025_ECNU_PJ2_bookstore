import logging
import os
from flask import Flask
from flask import Blueprint
from flask import request
from be.view import auth
from be.view import seller
from be.view import buyer
from be.view import search
from be.model.store import init_db_connection, init_completed_event

bp_shutdown = Blueprint("shutdown", __name__)


def shutdown_server():
    func = request.environ.get("werkzeug.server.shutdown")
    if func is None:
        raise RuntimeError("Not running with the Werkzeug Server")
    func()


@bp_shutdown.route("/shutdown")
def shutdown():
    shutdown_server()
    return "Server shutting down..."


def run_backend():
    init_db_connection()
    app.run()


app = Flask(__name__)
app.register_blueprint(bp_shutdown)
app.register_blueprint(auth.bp_auth)
app.register_blueprint(seller.bp_seller)
app.register_blueprint(buyer.bp_buyer)
app.register_blueprint(search.bp_search)

logging.basicConfig(level=logging.ERROR)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s"
)
handler.setFormatter(formatter)
logging.getLogger().addHandler(handler)

if __name__ == "__main__":
    run_backend()
