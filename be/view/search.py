from flask import Blueprint, request, jsonify
from be.model.search import search_books

bp_search = Blueprint("search", __name__, url_prefix="/search")


@bp_search.route("/", methods=["GET"])
def search():
    q = request.args.get("q", "")
    fields = request.args.get("fields")
    if fields:
        fields = [f.strip() for f in fields.split(",") if f.strip()]
    store_id = request.args.get("store_id")
    try:
        page = int(request.args.get("page", 1))
    except Exception:
        page = 1
    try:
        page_size = int(request.args.get("page_size", 10))
    except Exception:
        page_size = 10

    code, message, results, total = search_books(q, fields=fields, store_id=store_id, page=page, page_size=page_size)
    return jsonify({"message": message, "results": results, "total": total, "page": page, "page_size": page_size}), code
