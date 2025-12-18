from flask import Blueprint, request, jsonify
from be.model import db_conn
from be.model import store as model_store

bp_debug = Blueprint("debug", __name__, url_prefix="/debug")


@bp_debug.route("/user_balance", methods=["GET"])
def user_balance():
    """Return the integer balance for a given user_id (for test debugging).

    Query param: user_id
    Returns JSON: {"balance": <int>} or an error message.
    """
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"message": "user_id required"}), 400
    # sqlite connection used by the app is created in be.model.store.get_db_conn()
    conn = model_store.get_db_conn()
    cursor = conn.execute('SELECT balance FROM "user" WHERE user_id = %s', (user_id,))
    row = cursor.fetchone()
    if row is None:
        return jsonify({"message": "user not found"}), 404
    return jsonify({"balance": row[0]}), 200
