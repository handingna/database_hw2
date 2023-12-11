import logging
from pymongo import MongoClient

class Store:
    client: MongoClient
    db: str

    def __init__(self, db_uri):
        self.client = MongoClient(db_uri)
        self.db = self.client.get_database("be")
        self.init_collections()

    def init_collections(self):
        try:
            # 创建用户表
            self.db.create_collection("user")
            self.db.user.create_index("user_id", unique=True)

            # 创建用户商店关联表
            self.db.create_collection("user_store")
            self.db.user_store.create_index([("user_id", 1), ("store_id", 1)], unique=True)

            # 创建商店表
            self.db.create_collection("store")
            self.db.store.create_index([("store_id", 1), ("book_id", 1)], unique=True)

            # 创建新订单表
            self.db.create_collection("orders")
            self.db.orders.create_index("order_id", unique=True)

            # 创建新订单详情表
            self.db.create_collection("new_order_detail")
            self.db.new_order_detail.create_index([("order_id", 1), ("book_id", 1)], unique=True)

        except Exception as e:
            logging.error(e)

    def get_db_conn(self):
        return self

database_instance: Store = None

def init_database(db_uri):
    global database_instance
    database_instance = Store(db_uri)

def get_db_conn():
    global database_instance
    return database_instance.get_db_conn()

