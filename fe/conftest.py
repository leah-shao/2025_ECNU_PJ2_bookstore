import requests
import threading
import time
import psycopg2
import uuid
import pytest
from urllib.parse import urljoin
from be import serve
from be.model import store, db_conn
from fe import conf

thread: threading.Thread = None

# Global lock for database cleanup before tests - serializes all test execution
_test_execution_lock = threading.RLock()

# Sequence counter for unique IDs in concurrent tests
_id_counter = 0
_id_lock = threading.Lock()


def get_unique_id():
    global _id_counter
    with _id_lock:
        _id_counter += 1
        return _id_counter


def get_unique_id_prefix():
    # Use thread ID + unique counter for maximum uniqueness
    thread_id = threading.get_ident()
    unique_num = get_unique_id()
    return f"{thread_id}_{unique_num}"


@pytest.fixture(autouse=True)
def test_execution_lock():
    global _test_execution_lock
    _test_execution_lock.acquire()
    try:
        yield
    finally:
        _test_execution_lock.release()



def run_backend():
    serve.run_backend()


def pytest_configure(config):
    global thread
    print("frontend begin test")
    thread = threading.Thread(target=run_backend, daemon=True)
    thread.start()
    store.init_completed_event.wait()
    
    # Initialize database: clean all tables
    _init_database()


def pytest_unconfigure(config):
    url = urljoin(conf.URL, "shutdown")
    try:
        requests.get(url, timeout=5)
    except:
        pass
    thread.join(timeout=5)
    print("frontend end test")


def _init_database():
    conn = store.get_db_conn()
    try:
        tables_to_clean = [
            'new_order_detail',
            'new_order', 
            'user_store',
            'store',
            '"user"'
        ]
        
        for table in tables_to_clean:
            try:
                conn.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;")
            except Exception:
                try:
                    conn.execute(f"DELETE FROM {table};")
                except:
                    pass
        
        conn.commit()
    except Exception as e:
        print(f"Database init warning: {str(e)}")
        try:
            conn.rollback()
        except:
            pass


def _force_reset_backend_connections():
    try:
        # Clear all connections from the backend's connection pool
        if hasattr(store.db_conn, 'conn_pool'):
            for thread_id in list(store.db_conn.conn_pool.keys()):
                try:
                    conn = store.db_conn.conn_pool[thread_id]
                    conn.close()
                except:
                    pass
            store.db_conn.conn_pool.clear()
    except Exception:
        pass


def pytest_runtest_setup(item):
    global _test_execution_lock
    
    # Force backend to reset its connection pool so it gets fresh connections
    _force_reset_backend_connections()
    
    # Use lock (acquired by fixture) for database operations
    with _test_execution_lock:
        conn = store.get_db_conn()
        
        try:
            tables_to_clean = [
                'new_order_detail',
                'new_order', 
                'user_store',
                'store',
                '"user"'
            ]
            
            # Truncate in correct dependency order
            for table in tables_to_clean:
                try:
                    sql = f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;"
                    conn.execute(sql)
                except Exception as e:
                    # Fallback to DELETE if TRUNCATE fails
                    try:
                        conn.execute(f"DELETE FROM {table};")
                        try:
                            table_name = table.strip('"')
                            conn.execute(f"ALTER SEQUENCE {table_name}_id_seq RESTART WITH 1;")
                        except:
                            pass
                    except Exception:
                        pass
            
            conn.commit()
        except Exception as e:
            try:
                conn.rollback()
            except:
                pass
        
        time.sleep(0.001)


def pytest_runtest_teardown(item, nextitem):
    global _test_execution_lock
    
    with _test_execution_lock:
        conn = store.get_db_conn()
        try:
            conn.rollback()
        except:
            pass



