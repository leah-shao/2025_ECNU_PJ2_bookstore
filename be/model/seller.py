from be.model import error
from be.model import db_conn
import threading
import logging

# 全局店铺创建锁，防止并发创建相同店铺导致的竞态条件
_store_locks = {}
_store_locks_lock = threading.Lock()


def _get_store_lock(store_id: str) -> threading.RLock:
    """获取店铺特定的锁，用于防止并发创建同一店铺"""
    with _store_locks_lock:
        if store_id not in _store_locks:
            _store_locks[store_id] = threading.RLock()
        return _store_locks[store_id]



class Seller(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)

    def add_book(
        self,
        user_id: str,
        store_id: str,
        book_id: str,
        book_json_str: str,
        stock_level: int,
    ):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            if self.book_id_exist(store_id, book_id):
                return error.error_exist_book_id(book_id)

            self.conn.execute(
                "INSERT into store(store_id, book_id, book_info, stock_level)"
                "VALUES (%s, %s, %s, %s)",
                (store_id, book_id, book_json_str, stock_level),
            )
            self.conn.commit()
        except Exception as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    def add_stock_level(
        self, user_id: str, store_id: str, book_id: str, add_stock_level: int
    ):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            if not self.book_id_exist(store_id, book_id):
                return error.error_non_exist_book_id(book_id)

            self.conn.execute(
                "UPDATE store SET stock_level = stock_level + %s "
                "WHERE store_id = %s AND book_id = %s",
                (add_stock_level, store_id, book_id),
            )
            self.conn.commit()
        except Exception as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    def create_store(self, user_id: str, store_id: str) -> (int, str):
        # 使用店铺特定的锁，防止并发创建同一店铺
        store_lock = _get_store_lock(store_id)
        with store_lock:
            # 在锁内，再检查一次店铺是否已存在（double-check pattern）
            if self.store_id_exist(store_id):
                return error.error_exist_store_id(store_id)
            
            try:
                if not self.user_id_exist(user_id):
                    return error.error_non_exist_user_id(user_id)
                
                self.conn.execute(
                    "INSERT into user_store(store_id, user_id)" "VALUES (%s, %s)",
                    (store_id, user_id),
                )
                self.conn.commit()
            except Exception as e:
                logging.error(f"Create store failed for store {store_id}: {e}")
                return 528, "{}".format(str(e))
            except BaseException as e:
                logging.error(f"Create store failed (BaseException) for store {store_id}: {e}")
                return 530, "{}".format(str(e))
            return 200, "ok"

    def ship_order(self, user_id: str, order_id: str) -> (int, str):
        try:
            # check order exists
            cursor = self.conn.execute(
                "SELECT order_id, store_id, status FROM new_order WHERE order_id = %s",
                (order_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return error.error_invalid_order_id(order_id)
            store_id = row[1]
            status = row[2]

            # check seller owns the store
            cursor = self.conn.execute(
                "SELECT user_id FROM user_store WHERE store_id = %s;",
                (store_id,),
            )
            r = cursor.fetchone()
            if r is None:
                return error.error_non_exist_store_id(store_id)
            seller_id = r[0]
            if seller_id != user_id:
                return error.error_authorization_fail()

            if status != "paid":
                return error.error_and_message(530, "order not paid or already shipped")

            ship_time = int(__import__("time").time())
            cursor = self.conn.execute(
                "UPDATE new_order SET status = %s, ship_time = %s WHERE order_id = %s",
                ("shipped", ship_time, order_id),
            )
            if cursor.rowcount == 0:
                return error.error_invalid_order_id(order_id)
            self.conn.commit()
            return 200, "ok"
        except Exception as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
