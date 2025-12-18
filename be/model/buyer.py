import uuid
import json
import logging
import time
from be.model import db_conn
from be.model import error


class Buyer(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)

    def new_order(
        self, user_id: str, store_id: str, id_and_count: [(str, int)]
    ) -> (int, str, str):
        order_id = ""
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id) + (order_id,)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id) + (order_id,)
            uid = "{}_{}_{}".format(user_id, store_id, str(uuid.uuid1()))

            # Collect all book details first
            book_details = []
            for book_id, count in id_and_count:
                cursor = self.conn.execute(
                    "SELECT book_id, stock_level, book_info FROM store "
                    "WHERE store_id = %s AND book_id = %s;",
                    (store_id, book_id),
                )
                row = cursor.fetchone()
                if row is None:
                    return error.error_non_exist_book_id(book_id) + (order_id,)

                stock_level = row[1]
                book_info = row[2]
                # PostgreSQL JSONB 类型会自动返回字典，如果是字符串则需要转换
                if isinstance(book_info, str):
                    book_info_json = json.loads(book_info)
                else:
                    book_info_json = book_info
                price = book_info_json.get("price")

                if stock_level < count:
                    return error.error_stock_level_low(book_id) + (order_id,)

                cursor = self.conn.execute(
                    "UPDATE store set stock_level = stock_level - %s "
                    "WHERE store_id = %s and book_id = %s and stock_level >= %s; ",
                    (count, store_id, book_id, count),
                )
                if cursor.rowcount == 0:
                    return error.error_stock_level_low(book_id) + (order_id,)

                # Store book details for later insertion
                book_details.append((book_id, count, price))

            # Insert order record 
            create_time = int(time.time())
            self.conn.execute(
                "INSERT INTO new_order(order_id, store_id, user_id, status, create_time) "
                "VALUES(%s, %s, %s, %s, %s);",
                (uid, store_id, user_id, "created", create_time),
            )

            for book_id, count, price in book_details:
                self.conn.execute(
                    "INSERT INTO new_order_detail(order_id, book_id, count, price) "
                    "VALUES(%s, %s, %s, %s);",
                    (uid, book_id, count, price),
                )

            self.conn.commit()
            order_id = uid
        except Exception as e:
            logging.info("528, {}".format(str(e)))
            return 528, "{}".format(str(e)), ""
        except BaseException as e:
            logging.info("530, {}".format(str(e)))
            return 530, "{}".format(str(e)), ""

        return 200, "ok", order_id

    def payment(self, user_id: str, password: str, order_id: str) -> (int, str):
        conn = self.conn
        try:
            cursor = conn.execute(
                "SELECT order_id, user_id, store_id FROM new_order WHERE order_id = %s",
                (order_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return error.error_invalid_order_id(order_id)

            order_id = row[0]
            buyer_id = row[1]
            store_id = row[2]

            if buyer_id != user_id:
                return error.error_authorization_fail()

            cursor = conn.execute(
                'SELECT balance, password FROM "user" WHERE user_id = %s;', (buyer_id,)
            )
            row = cursor.fetchone()
            if row is None:
                return error.error_non_exist_user_id(buyer_id)
            balance = row[0]
            if password != row[1]:
                return error.error_authorization_fail()

            cursor = conn.execute(
                "SELECT store_id, user_id FROM user_store WHERE store_id = %s;",
                (store_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return error.error_non_exist_store_id(store_id)

            seller_id = row[1]

            if not self.user_id_exist(seller_id):
                return error.error_non_exist_user_id(seller_id)

            cursor = conn.execute(
                "SELECT book_id, count, price FROM new_order_detail WHERE order_id = %s;",
                (order_id,),
            )
            total_price = 0
            for row in cursor:
                count = row[1]
                price = row[2]
                total_price = total_price + price * count

            if balance < total_price:
                return error.error_not_sufficient_funds(order_id)

            cursor = conn.execute(
                'UPDATE "user" set balance = balance - %s '
                'WHERE user_id = %s AND balance >= %s',
                (total_price, buyer_id, total_price),
            )
            if cursor.rowcount == 0:
                return error.error_not_sufficient_funds(order_id)

            cursor = conn.execute(
                'UPDATE "user" set balance = balance + %s '
                'WHERE user_id = %s',
                (total_price, seller_id),
            )

            if cursor.rowcount == 0:
                return error.error_non_exist_user_id(seller_id)

            # mark order as paid
            pay_time = int(time.time())
            cursor = conn.execute(
                "UPDATE new_order SET status = %s, pay_time = %s WHERE order_id = %s",
                ("paid", pay_time, order_id),
            )
            if cursor.rowcount == 0:
                return error.error_invalid_order_id(order_id)
            conn.commit()

        except Exception as e:
            return 528, "{}".format(str(e))

        except BaseException as e:
            return 530, "{}".format(str(e))

        return 200, "ok"

    def query_orders(self, user_id: str):
        try:
            cursor = self.conn.execute(
                "SELECT order_id, store_id, status, create_time, pay_time, ship_time, receive_time FROM new_order WHERE user_id = %s",
                (user_id,),
            )
            orders = []
            for row in cursor:
                order_id = row[0]
                details_cursor = self.conn.execute(
                    "SELECT book_id, count, price FROM new_order_detail WHERE order_id = %s",
                    (order_id,),
                )
                details = [dict(book_id=r[0], count=r[1], price=r[2]) for r in details_cursor]
                orders.append(
                    {
                        "order_id": order_id,
                        "store_id": row[1],
                        "status": row[2],
                        "create_time": row[3],
                        "pay_time": row[4],
                        "ship_time": row[5],
                        "receive_time": row[6],
                        "details": details,
                    }
                )
            return 200, "ok", orders
        except Exception as e:
            return 528, "{}".format(str(e)), []

    def cancel_order(self, user_id: str, order_id: str) -> (int, str):
        try:
            cursor = self.conn.execute(
                "SELECT order_id, user_id, store_id, status FROM new_order WHERE order_id = %s",
                (order_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return error.error_invalid_order_id(order_id)
            if row[1] != user_id:
                return error.error_authorization_fail()
            status = row[3]
            if status != "created":
                # only allow cancel before payment
                return error.error_and_message(530, "order cannot be canceled in status {}".format(status))

            # restore stock levels
            cursor = self.conn.execute(
                "SELECT book_id, count FROM new_order_detail WHERE order_id = %s",
                (order_id,),
            )
            for r in cursor:
                book_id = r[0]
                count = r[1]
                self.conn.execute(
                    "UPDATE store SET stock_level = stock_level + %s WHERE book_id = %s AND store_id = %s",
                    (count, book_id, row[2]),
                )

            self.conn.execute("DELETE FROM new_order_detail WHERE order_id = %s", (order_id,))
            self.conn.execute("DELETE FROM new_order WHERE order_id = %s", (order_id,))
            self.conn.commit()
            return 200, "ok"
        except Exception as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))

    def receive_order(self, user_id: str, order_id: str) -> (int, str):
        try:
            cursor = self.conn.execute(
                "SELECT order_id, user_id, status FROM new_order WHERE order_id = %s",
                (order_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return error.error_invalid_order_id(order_id)
            if row[1] != user_id:
                return error.error_authorization_fail()
            status = row[2]
            if status != "shipped":
                return error.error_and_message(530, "order not in shipped status")
            receive_time = int(time.time())
            self.conn.execute(
                "UPDATE new_order SET status = %s, receive_time = %s WHERE order_id = %s",
                ("received", receive_time, order_id),
            )
            self.conn.commit()
            return 200, "ok"
        except Exception as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))

    def add_funds(self, user_id, password, add_value) -> (int, str):
        try:
            cursor = self.conn.execute(
                'SELECT password  FROM "user" where user_id=%s', (user_id,)
            )
            row = cursor.fetchone()
            if row is None:
                return error.error_authorization_fail()

            if row[0] != password:
                return error.error_authorization_fail()

            cursor = self.conn.execute(
                'UPDATE "user" SET balance = balance + %s WHERE user_id = %s',
                (add_value, user_id),
            )
            if cursor.rowcount == 0:
                return error.error_non_exist_user_id(user_id)

            self.conn.commit()
        except Exception as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))

        return 200, "ok"

    def auto_cancel_unpaid(self, timeout_seconds: int) -> (int, str, int):
        try:
            now = int(time.time())
            cutoff = now - int(timeout_seconds)
            cursor = self.conn.execute(
                "SELECT order_id, store_id FROM new_order WHERE status = %s AND create_time <= %s",
                ("created", cutoff),
            )
            orders = [(r[0], r[1]) for r in cursor]
            cancelled = 0
            for order_id, store_id in orders:
                # restore stock
                details_cursor = self.conn.execute(
                    "SELECT book_id, count FROM new_order_detail WHERE order_id = %s",
                    (order_id,),
                )
                for r in details_cursor:
                    book_id = r[0]
                    count = r[1]
                    self.conn.execute(
                        "UPDATE store SET stock_level = stock_level + %s WHERE book_id = %s AND store_id = %s",
                        (count, book_id, store_id),
                    )

                self.conn.execute("DELETE FROM new_order_detail WHERE order_id = %s", (order_id,))
                self.conn.execute("DELETE FROM new_order WHERE order_id = %s", (order_id,))
                cancelled += 1

            if cancelled > 0:
                self.conn.commit()

            return 200, "ok", cancelled
        except Exception as e:
            return 528, "{}".format(str(e)), 0
        except BaseException as e:
            return 530, "{}".format(str(e)), 0
