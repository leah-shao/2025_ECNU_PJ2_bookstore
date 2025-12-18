import time
from be.model import buyer as buyer_mod
from be.model import store as model_store


def setup_function(fn):
    conn = model_store.get_db_conn()
    cursor = conn.execute("DELETE FROM new_order_detail;")
    cursor = conn.execute("DELETE FROM new_order;")
    cursor = conn.execute("DELETE FROM store;")
    conn.commit()


def test_auto_cancel_unpaid_restores_stock():
    conn = model_store.get_db_conn()
    # First, insert users
    cursor = conn.execute("INSERT INTO \"user\" (user_id, balance, password) VALUES (%s, %s, %s)", ("u_timeout", 0, "p"))
    cursor = conn.execute("INSERT INTO \"user\" (user_id, balance, password) VALUES (%s, %s, %s)", ("u1", 0, "p"))
    cursor = conn.execute("INSERT INTO \"user\" (user_id, balance, password) VALUES (%s, %s, %s)", ("u2", 0, "p"))
    # Insert user_store mapping
    cursor = conn.execute("INSERT INTO user_store (store_id, user_id) VALUES (%s, %s)", ("s_timeout", "u_timeout"))
    cursor = conn.execute(
        "INSERT INTO store(store_id, book_id, book_info, stock_level) VALUES (%s, %s, %s, %s)",
        ("s_timeout", "b1", '{"price":10}', 5),
    )

    now = int(time.time())
    old_order_id = "o_old"
    new_order_id = "o_new"

    # old order: created 2 hours ago
    cursor = conn.execute(
        "INSERT INTO new_order(order_id, store_id, user_id, status, create_time) VALUES (%s, %s, %s, %s, %s)",
        (old_order_id, "s_timeout", "u1", "created", now - 7200),
    )
    cursor = conn.execute(
        "INSERT INTO new_order_detail(order_id, book_id, count, price) VALUES (%s, %s, %s, %s)",
        (old_order_id, "b1", 2, 10),
    )

    # new order: created now
    cursor = conn.execute(
        "INSERT INTO new_order(order_id, store_id, user_id, status, create_time) VALUES (%s, %s, %s, %s, %s)",
        (new_order_id, "s_timeout", "u2", "created", now),
    )
    cursor = conn.execute(
        "INSERT INTO new_order_detail(order_id, book_id, count, price) VALUES (%s, %s, %s, %s)",
        (new_order_id, "b1", 1, 10),
    )

    # decrement stock to reflect orders reserved (simulate previous reservation)
    cursor = conn.execute("UPDATE store SET stock_level = stock_level - %s WHERE store_id = %s AND book_id = %s", (3, "s_timeout", "b1"))
    conn.commit()

    b = buyer_mod.Buyer()
    code, msg, cancelled = b.auto_cancel_unpaid(3600)
    assert code == 200
    assert cancelled == 1

    # old order should be removed
    cursor = conn.execute("SELECT COUNT(1) FROM new_order WHERE order_id = %s", (old_order_id,))
    assert cursor.fetchone()[0] == 0

    # new order should remain
    cursor = conn.execute("SELECT COUNT(1) FROM new_order WHERE order_id = %s", (new_order_id,))
    assert cursor.fetchone()[0] == 1

    # stock should have been restored by 2 (old order had count 2). original 5 -3 =2 then +2 => 4
    cursor = conn.execute("SELECT stock_level FROM store WHERE store_id = %s AND book_id = %s", ("s_timeout", "b1"))
    stock = cursor.fetchone()[0]
    assert stock == 4

