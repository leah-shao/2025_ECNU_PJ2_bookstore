import pytest
import json
import time
import uuid
from be.model.buyer import Buyer
from be.model.seller import Seller
from be.model import store as model_store


def setup_function(fn):
    conn = model_store.get_db_conn()
    cursor = conn.execute('DELETE FROM new_order_detail;')
    cursor = conn.execute('DELETE FROM new_order;')
    cursor = conn.execute('DELETE FROM store;')
    cursor = conn.execute('DELETE FROM user_store;')
    cursor = conn.execute('DELETE FROM "user";')
    conn.commit()


class TestNewOrder:
    def test_new_order_success(self):
        conn = model_store.get_db_conn()
        
        # Create buyer and seller users
        conn.execute("INSERT INTO \"user\" (user_id, balance, password) VALUES (%s, %s, %s)", ("buyer1", 10000, "p"))
        conn.execute("INSERT INTO \"user\" (user_id, balance, password) VALUES (%s, %s, %s)", ("seller1", 0, "p"))
        conn.execute("INSERT INTO user_store (store_id, user_id) VALUES (%s, %s)", ("store1", "seller1"))
        
        # Add book to store
        book_info = {"title": "Python Book", "price": 100, "author": "John"}
        conn.execute(
            "INSERT INTO store (store_id, book_id, stock_level, book_info) VALUES (%s, %s, %s, %s)",
            ("store1", "book1", 10, json.dumps(book_info))
        )
        conn.commit()
        
        # Create order
        buyer = Buyer()
        code, msg, order_id = buyer.new_order("buyer1", "store1", [("book1", 2)])
        
        assert code == 200
        assert order_id != ""
    
    def test_new_order_non_existent_user(self):
        buyer = Buyer()
        code, msg, order_id = buyer.new_order("non_existent", "store1", [("book1", 1)])
        assert code == 511  # error_non_exist_user_id
    
    def test_new_order_non_existent_store(self):
        conn = model_store.get_db_conn()
        conn.execute("INSERT INTO \"user\" (user_id, balance, password) VALUES (%s, %s, %s)", ("buyer2", 1000, "p"))
        conn.commit()
        
        buyer = Buyer()
        code, msg, order_id = buyer.new_order("buyer2", "non_store", [("book1", 1)])
        assert code == 513  # error_non_exist_store_id
    
    def test_new_order_non_existent_book(self):
        conn = model_store.get_db_conn()
        conn.execute("INSERT INTO \"user\" (user_id, balance, password) VALUES (%s, %s, %s)", ("buyer3", 1000, "p"))
        conn.execute("INSERT INTO \"user\" (user_id, balance, password) VALUES (%s, %s, %s)", ("seller2", 0, "p"))
        conn.execute("INSERT INTO user_store (store_id, user_id) VALUES (%s, %s)", ("store2", "seller2"))
        conn.commit()
        
        buyer = Buyer()
        code, msg, order_id = buyer.new_order("buyer3", "store2", [("non_book", 1)])
        assert code == 515  # error_non_exist_book_id
    
    def test_new_order_insufficient_stock(self):
        conn = model_store.get_db_conn()
        conn.execute("INSERT INTO \"user\" (user_id, balance, password) VALUES (%s, %s, %s)", ("buyer4", 10000, "p"))
        conn.execute("INSERT INTO \"user\" (user_id, balance, password) VALUES (%s, %s, %s)", ("seller3", 0, "p"))
        conn.execute("INSERT INTO user_store (store_id, user_id) VALUES (%s, %s)", ("store3", "seller3"))
        
        book_info = {"title": "Rare Book", "price": 500, "author": "Jane"}
        conn.execute(
            "INSERT INTO store (store_id, book_id, stock_level, book_info) VALUES (%s, %s, %s, %s)",
            ("store3", "book_rare", 2, json.dumps(book_info))
        )
        conn.commit()
        
        buyer = Buyer()
        code, msg, order_id = buyer.new_order("buyer4", "store3", [("book_rare", 5)])
        assert code == 517  # error_stock_level_low
    
    def test_new_order_multiple_books(self):
        conn = model_store.get_db_conn()
        conn.execute("INSERT INTO \"user\" (user_id, balance, password) VALUES (%s, %s, %s)", ("buyer5", 5000, "p"))
        conn.execute("INSERT INTO \"user\" (user_id, balance, password) VALUES (%s, %s, %s)", ("seller4", 0, "p"))
        conn.execute("INSERT INTO user_store (store_id, user_id) VALUES (%s, %s)", ("store4", "seller4"))
        
        book1_info = {"title": "Book 1", "price": 100, "author": "A"}
        book2_info = {"title": "Book 2", "price": 200, "author": "B"}
        
        conn.execute(
            "INSERT INTO store (store_id, book_id, stock_level, book_info) VALUES (%s, %s, %s, %s)",
            ("store4", "book_a", 10, json.dumps(book1_info))
        )
        conn.execute(
            "INSERT INTO store (store_id, book_id, stock_level, book_info) VALUES (%s, %s, %s, %s)",
            ("store4", "book_b", 10, json.dumps(book2_info))
        )
        conn.commit()
        
        buyer = Buyer()
        code, msg, order_id = buyer.new_order("buyer5", "store4", [("book_a", 2), ("book_b", 3)])
        
        assert code == 200
        assert order_id != ""


class TestPayment:
    
    def _setup_order(self, buyer_id="buyer_pay", seller_id="seller_pay", store_id="store_pay", book_id="book_pay"):
        """Helper to setup a paid order scenario"""
        conn = model_store.get_db_conn()
        
        # Create users and store
        conn.execute("INSERT INTO \"user\" (user_id, balance, password) VALUES (%s, %s, %s)", 
                    (buyer_id, 10000, "pass"))
        conn.execute("INSERT INTO \"user\" (user_id, balance, password) VALUES (%s, %s, %s)", 
                    (seller_id, 0, "pass"))
        conn.execute("INSERT INTO user_store (store_id, user_id) VALUES (%s, %s)", 
                    (store_id, seller_id))
        
        # Add book
        book_info = {"title": "Test Book", "price": 100, "author": "Test"}
        conn.execute(
            "INSERT INTO store (store_id, book_id, stock_level, book_info) VALUES (%s, %s, %s, %s)",
            (store_id, book_id, 100, json.dumps(book_info))
        )
        conn.commit()
        
        # Create order
        buyer = Buyer()
        code, msg, order_id = buyer.new_order(buyer_id, store_id, [(book_id, 1)])
        assert code == 200
        
        return order_id, buyer_id, seller_id, store_id
    
    def test_payment_success(self):
        order_id, buyer_id, seller_id, store_id = self._setup_order()
        
        buyer = Buyer()
        code, msg = buyer.payment(buyer_id, "pass", order_id)
        
        assert code == 200
        
        # Verify order status changed to 'paid'
        conn = model_store.get_db_conn()
        cursor = conn.execute("SELECT status FROM new_order WHERE order_id = %s", (order_id,))
        row = cursor.fetchone()
        assert row[0] == "paid"
    
    def test_payment_invalid_order(self):
        buyer = Buyer()
        code, msg = buyer.payment("buyer_x", "pass", "invalid_order")
        assert code == 518  # error_invalid_order_id
    
    def test_payment_wrong_password(self):
        order_id, buyer_id, seller_id, store_id = self._setup_order()
        
        buyer = Buyer()
        code, msg = buyer.payment(buyer_id, "wrong_pass", order_id)
        assert code == 401  # error_authorization_fail
    
    def test_payment_insufficient_balance(self):
        conn = model_store.get_db_conn()
        
        # Create buyer with low balance
        conn.execute("INSERT INTO \"user\" (user_id, balance, password) VALUES (%s, %s, %s)", 
                    ("buyer_poor", 10, "pass"))
        conn.execute("INSERT INTO \"user\" (user_id, balance, password) VALUES (%s, %s, %s)", 
                    ("seller_rich", 0, "pass"))
        conn.execute("INSERT INTO user_store (store_id, user_id) VALUES (%s, %s)", 
                    ("store_rich", "seller_rich"))
        
        # Add expensive book
        book_info = {"title": "Expensive", "price": 1000, "author": "Test"}
        conn.execute(
            "INSERT INTO store (store_id, book_id, stock_level, book_info) VALUES (%s, %s, %s, %s)",
            ("store_rich", "expensive_book", 100, json.dumps(book_info))
        )
        conn.commit()
        
        # Create order
        buyer = Buyer()
        code, msg, order_id = buyer.new_order("buyer_poor", "store_rich", [("expensive_book", 1)])
        assert code == 200
        
        # Try to pay
        code, msg = buyer.payment("buyer_poor", "pass", order_id)
        assert code == 519  # error_not_sufficient_funds
    
    def test_payment_authorization_fail_wrong_user(self):
        order_id, buyer_id, seller_id, store_id = self._setup_order()
        
        buyer = Buyer()
        code, msg = buyer.payment("wrong_buyer", "pass", order_id)
        assert code == 401  # error_authorization_fail


class TestQueryOrders:
    
    def test_query_empty_orders(self):
        buyer = Buyer()
        code, msg, orders = buyer.query_orders("user_no_orders")
        
        assert code == 200
        assert orders == []
    
    def test_query_single_order(self):
        conn = model_store.get_db_conn()
        
        # Setup user and order
        conn.execute("INSERT INTO \"user\" (user_id, balance, password) VALUES (%s, %s, %s)", 
                    ("query_buyer", 1000, "p"))
        conn.execute("INSERT INTO new_order (order_id, store_id, user_id, status, create_time) VALUES (%s, %s, %s, %s, %s)",
                    ("order_1", "store_q", "query_buyer", "created", 123456))
        conn.execute("INSERT INTO new_order_detail (order_id, book_id, count, price) VALUES (%s, %s, %s, %s)",
                    ("order_1", "book_q", 2, 50))
        conn.commit()
        
        buyer = Buyer()
        code, msg, orders = buyer.query_orders("query_buyer")
        
        assert code == 200
        assert len(orders) == 1
        assert orders[0]["order_id"] == "order_1"
        assert orders[0]["status"] == "created"
        assert len(orders[0]["details"]) == 1
    
    def test_query_multiple_orders(self):
        conn = model_store.get_db_conn()
        
        conn.execute("INSERT INTO \"user\" (user_id, balance, password) VALUES (%s, %s, %s)", 
                    ("multi_buyer", 1000, "p"))
        
        for i in range(3):
            conn.execute("INSERT INTO new_order (order_id, store_id, user_id, status, create_time) VALUES (%s, %s, %s, %s, %s)",
                        (f"order_{i}", f"store_{i}", "multi_buyer", "created", 100000 + i))
            conn.execute("INSERT INTO new_order_detail (order_id, book_id, count, price) VALUES (%s, %s, %s, %s)",
                        (f"order_{i}", f"book_{i}", 1, 100))
        
        conn.commit()
        
        buyer = Buyer()
        code, msg, orders = buyer.query_orders("multi_buyer")
        
        assert code == 200
        assert len(orders) == 3


class TestCancelOrder:
    
    def test_cancel_order_success(self):
        conn = model_store.get_db_conn()
        
        # Setup - must create seller user first for foreign key
        conn.execute("INSERT INTO \"user\" (user_id, balance, password) VALUES (%s, %s, %s)", 
                    ("seller_cancel", 0, "p"))
        conn.execute("INSERT INTO \"user\" (user_id, balance, password) VALUES (%s, %s, %s)", 
                    ("cancel_buyer", 1000, "p"))
        conn.execute("INSERT INTO user_store (store_id, user_id) VALUES (%s, %s)", ("cancel_store", "seller_cancel"))
        
        book_info = {"title": "Cancel Book", "price": 100, "author": "Test"}
        conn.execute(
            "INSERT INTO store (store_id, book_id, stock_level, book_info) VALUES (%s, %s, %s, %s)",
            ("cancel_store", "cancel_book", 5, json.dumps(book_info))
        )
        conn.commit()
        
        # Create order
        buyer = Buyer()
        code, msg, order_id = buyer.new_order("cancel_buyer", "cancel_store", [("cancel_book", 2)])
        assert code == 200
        
        # Cancel order
        code, msg = buyer.cancel_order("cancel_buyer", order_id)
        assert code == 200
        
        # Verify order is deleted
        conn = model_store.get_db_conn()
        cursor = conn.execute("SELECT order_id FROM new_order WHERE order_id = %s", (order_id,))
        assert cursor.fetchone() is None
    
    def test_cancel_order_invalid_order(self):
        buyer = Buyer()
        code, msg = buyer.cancel_order("user_c", "invalid_order_id")
        assert code == 518  # error_invalid_order_id
    
    def test_cancel_order_authorization_fail(self):
        conn = model_store.get_db_conn()
        
        conn.execute("INSERT INTO \"user\" (user_id, balance, password) VALUES (%s, %s, %s)", 
                    ("buyer_auth", 1000, "p"))
        conn.execute("INSERT INTO new_order (order_id, store_id, user_id, status, create_time) VALUES (%s, %s, %s, %s, %s)",
                    ("order_auth", "store_a", "buyer_auth", "created", 123))
        conn.commit()
        
        buyer = Buyer()
        code, msg = buyer.cancel_order("different_user", "order_auth")
        assert code == 401  # error_authorization_fail
    
    def test_cancel_paid_order_fail(self):
        conn = model_store.get_db_conn()
        
        conn.execute("INSERT INTO \"user\" (user_id, balance, password) VALUES (%s, %s, %s)", 
                    ("buyer_paid", 1000, "p"))
        conn.execute("INSERT INTO new_order (order_id, store_id, user_id, status, create_time) VALUES (%s, %s, %s, %s, %s)",
                    ("order_paid", "store_p", "buyer_paid", "paid", 123))
        conn.commit()
        
        buyer = Buyer()
        code, msg = buyer.cancel_order("buyer_paid", "order_paid")
        assert code == 530  # Cannot cancel paid order


class TestReceiveOrder:
    
    def test_receive_order_success(self):
        conn = model_store.get_db_conn()
        
        conn.execute("INSERT INTO \"user\" (user_id, balance, password) VALUES (%s, %s, %s)", 
                    ("receive_buyer", 1000, "p"))
        conn.execute("INSERT INTO new_order (order_id, store_id, user_id, status, create_time) VALUES (%s, %s, %s, %s, %s)",
                    ("order_shipped", "store_s", "receive_buyer", "shipped", 123))
        conn.commit()
        
        buyer = Buyer()
        code, msg = buyer.receive_order("receive_buyer", "order_shipped")
        assert code == 200
        
        # Verify status changed to 'received'
        cursor = conn.execute("SELECT status FROM new_order WHERE order_id = %s", ("order_shipped",))
        assert cursor.fetchone()[0] == "received"
    
    def test_receive_invalid_order(self):
        buyer = Buyer()
        code, msg = buyer.receive_order("user_r", "invalid_ship_order")
        assert code == 518  # error_invalid_order_id
    
    def test_receive_order_not_shipped(self):
        conn = model_store.get_db_conn()
        
        conn.execute("INSERT INTO \"user\" (user_id, balance, password) VALUES (%s, %s, %s)", 
                    ("receive_buyer2", 1000, "p"))
        conn.execute("INSERT INTO new_order (order_id, store_id, user_id, status, create_time) VALUES (%s, %s, %s, %s, %s)",
                    ("order_created", "store_c", "receive_buyer2", "created", 123))
        conn.commit()
        
        buyer = Buyer()
        code, msg = buyer.receive_order("receive_buyer2", "order_created")
        assert code == 530  # order not in shipped status


class TestAddFunds:
    
    def test_add_funds_success(self):
        conn = model_store.get_db_conn()
        
        conn.execute("INSERT INTO \"user\" (user_id, balance, password) VALUES (%s, %s, %s)", 
                    ("funds_buyer", 100, "fund_pass"))
        conn.commit()
        
        buyer = Buyer()
        code, msg = buyer.add_funds("funds_buyer", "fund_pass", 500)
        assert code == 200
        
        # Verify balance updated
        cursor = conn.execute("SELECT balance FROM \"user\" WHERE user_id = %s", ("funds_buyer",))
        assert cursor.fetchone()[0] == 600
    
    def test_add_funds_wrong_password(self):
        conn = model_store.get_db_conn()
        
        conn.execute("INSERT INTO \"user\" (user_id, balance, password) VALUES (%s, %s, %s)", 
                    ("funds_buyer2", 100, "correct_pass"))
        conn.commit()
        
        buyer = Buyer()
        code, msg = buyer.add_funds("funds_buyer2", "wrong_pass", 500)
        assert code == 401  # error_authorization_fail
    
    def test_add_funds_non_existent_user(self):
        buyer = Buyer()
        code, msg = buyer.add_funds("non_existent_user", "pass", 500)
        assert code == 401  # error_authorization_fail


class TestAutoCancelUnpaid:
    
    def test_auto_cancel_no_expired_orders(self):
        conn = model_store.get_db_conn()
        
        # Create a recent order
        current_time = int(time.time())
        conn.execute("INSERT INTO \"user\" (user_id, balance, password) VALUES (%s, %s, %s)", 
                    ("auto_buyer", 1000, "p"))
        conn.execute("INSERT INTO new_order (order_id, store_id, user_id, status, create_time) VALUES (%s, %s, %s, %s, %s)",
                    ("recent_order", "store_auto", "auto_buyer", "created", current_time))
        conn.commit()
        
        buyer = Buyer()
        code, msg, cancelled = buyer.auto_cancel_unpaid(3600)  # 1 hour timeout
        
        assert code == 200
        assert cancelled == 0
    
    def test_auto_cancel_expired_orders(self):
        conn = model_store.get_db_conn()
        
        current_time = int(time.time())
        old_time = current_time - 7200  # 2 hours ago
        
        # Create seller first for foreign key
        conn.execute("INSERT INTO \"user\" (user_id, balance, password) VALUES (%s, %s, %s)", 
                    ("seller_auto", 0, "p"))
        conn.execute("INSERT INTO \"user\" (user_id, balance, password) VALUES (%s, %s, %s)", 
                    ("auto_buyer2", 1000, "p"))
        conn.execute("INSERT INTO user_store (store_id, user_id) VALUES (%s, %s)", ("store_auto2", "seller_auto"))
        
        # Add book
        book_info = {"title": "Auto Book", "price": 100, "author": "Test"}
        conn.execute(
            "INSERT INTO store (store_id, book_id, stock_level, book_info) VALUES (%s, %s, %s, %s)",
            ("store_auto2", "book_auto", 10, json.dumps(book_info))
        )
        
        # Create old order
        conn.execute("INSERT INTO new_order (order_id, store_id, user_id, status, create_time) VALUES (%s, %s, %s, %s, %s)",
                    ("old_order", "store_auto2", "auto_buyer2", "created", old_time))
        conn.execute("INSERT INTO new_order_detail (order_id, book_id, count, price) VALUES (%s, %s, %s, %s)",
                    ("old_order", "book_auto", 1, 100))
        conn.commit()
        
        buyer = Buyer()
        code, msg, cancelled = buyer.auto_cancel_unpaid(3600)  # 1 hour timeout
        
        assert code == 200
        assert cancelled == 1
        
        # Verify order was deleted
        cursor = conn.execute("SELECT order_id FROM new_order WHERE order_id = %s", ("old_order",))
        assert cursor.fetchone() is None
