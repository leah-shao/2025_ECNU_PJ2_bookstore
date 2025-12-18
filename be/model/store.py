# be/model/store.py
import os
import threading
import psycopg2
from psycopg2 import sql
from contextlib import contextmanager
import logging

init_completed_event = threading.Event()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PostgreSQLConnection:
    
    def __init__(self, db_host="localhost", db_port=5432, db_user="postgres", 
                 db_password="postgres", db_name="bookstore"):
        
        self.db_host = os.environ.get('DB_HOST', db_host)
        self.db_port = int(os.environ.get('DB_PORT', db_port))
        self.db_user = os.environ.get('DB_USER', db_user)
        self.db_password = os.environ.get('DB_PASSWORD', db_password)
        self.db_name = os.environ.get('DB_NAME', db_name)
        self.conn_pool = {}
        self.pool_lock = threading.Lock()
        # self._init_database() # Defer initialization
    
    def _get_connection(self):
        thread_id = threading.get_ident()
        if thread_id not in self.conn_pool:
            try:
                conn = psycopg2.connect(
                    host=self.db_host,
                    port=self.db_port,
                    user=self.db_user,
                    password=self.db_password,
                    database=self.db_name
                )
                # 设置自动提交为 False，需要手动 commit
                conn.autocommit = False
                self.conn_pool[thread_id] = conn
                logger.info(f"Created new connection for thread {thread_id}")
            except psycopg2.Error as e:
                logger.error(f"Failed to connect to database: {e}")
                raise
        return self.conn_pool[thread_id]
    
    @contextmanager
    def get_cursor(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            cursor.close()
    
    def execute(self, query, params=None):
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            conn.commit()
            return cursor
        except Exception as e:
            conn.rollback()
            logger.error(f"Query failed: {query}, params: {params}, error: {e}")
            raise
    
    def _init_database(self):
        try:
            conn = psycopg2.connect(
                host=self.db_host,
                port=self.db_port,
                user=self.db_user,
                password=self.db_password,
                database="postgres"  # 连接到默认数据库
            )
            conn.autocommit = True
            cursor = conn.cursor()
            
            # 检查数据库是否存在，如果不存在则创建
            cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{self.db_name}'")
            if cursor.fetchone() is None:
                cursor.execute(sql.SQL("CREATE DATABASE {}").format(
                    sql.Identifier(self.db_name)
                ))
                logger.info(f"Created database {self.db_name}")
            
            cursor.close()
            conn.close()
            
            # 连接到实际的数据库并创建表
            actual_conn = psycopg2.connect(
                host=self.db_host,
                port=self.db_port,
                user=self.db_user,
                password=self.db_password,
                database=self.db_name
            )
            actual_conn.autocommit = True
            cursor = actual_conn.cursor()
            
            # 创建用户表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS "user" (
                    user_id TEXT PRIMARY KEY,
                    password TEXT NOT NULL,
                    balance INTEGER DEFAULT 0,
                    token TEXT,
                    terminal TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # 创建用户店铺表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_store (
                    store_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES "user"(user_id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # 创建店铺表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS store (
                    store_id TEXT NOT NULL REFERENCES user_store(store_id),
                    book_id TEXT NOT NULL,
                    book_info JSONB NOT NULL,
                    stock_level INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(store_id, book_id)
                );
            """)
            
            # 创建订单表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS new_order (
                    order_id TEXT PRIMARY KEY,
                    store_id TEXT NOT NULL,
                    user_id TEXT NOT NULL REFERENCES "user"(user_id),
                    status TEXT DEFAULT 'created',
                    create_time INTEGER,
                    pay_time INTEGER,
                    ship_time INTEGER,
                    receive_time INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # 创建订单详情表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS new_order_detail (
                    order_id TEXT NOT NULL REFERENCES new_order(order_id),
                    book_id TEXT NOT NULL,
                    count INTEGER NOT NULL,
                    price INTEGER NOT NULL,
                    PRIMARY KEY(order_id, book_id)
                );
            """)
            
            # 创建索引以提高查询性能
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_store_user_id ON user_store(user_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_store_store_id ON store(store_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_new_order_user_id ON new_order(user_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_new_order_store_id ON new_order(store_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_new_order_detail_order_id ON new_order_detail(order_id);")
            
            cursor.close()
            actual_conn.close()
            logger.info("Database schema initialized successfully.")

            # 发送初始化完成信号
            init_completed_event.set()

        except psycopg2.Error as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    def commit(self):
        conn = self._get_connection()
        conn.commit()
    
    def rollback(self):
        conn = self._get_connection()
        conn.rollback()
    
    def close_all(self):
        with self.pool_lock:
            for conn in self.conn_pool.values():
                try:
                    conn.close()
                except:
                    pass
            self.conn_pool.clear()


# 全局数据库连接实例
db_conn = None

# 单例锁
db_conn_lock = threading.Lock()

def init_db_connection():
    global db_conn
    with db_conn_lock:
        if db_conn is None:
            db_conn = PostgreSQLConnection()
            db_conn._init_database()
            logger.info("Database connection initialized.")

def get_db_conn():
    return db_conn
