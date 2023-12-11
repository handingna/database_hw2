import json

from be.model import error
from be.model import db_conn
from jieba import cut  # 用于中文分词
import re


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

        ###########为search做准备 start
        book_json = json.loads(book_json_str)
        print(book_json)
        title = book_json.get('title', [])
        tags = book_json.get('tags', [])
        content = book_json.get('content', [])
        book_intro = book_json.get('book_intro', [])

        # 执行分词操作
        tags_tokens = " ".join(tags)
        content_tokens = " ".join(cut(content))  # 对内容进行分词
        book_intro_tokens = " ".join(cut(book_intro))  # 对书籍介绍进行分词

        detail_book = str(title) + ' ' + str(tags_tokens) + ' ' + str(content_tokens) + ' ' + str(book_intro_tokens)
        ###########为search做准备  end
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            if self.book_id_exist(store_id, book_id):
                return error.error_exist_book_id(book_id)

            # 在MongoDB中插入书本信息
            book_info = {
                "store_id": store_id,
                "book_id": book_id,
                "book_info": book_json_str,
                "stock_level": stock_level,
                "detail_book": detail_book,
            }
            self.db.db.store.insert_one(book_info)

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

            # 更新MongoDB中书本的库存
            filter = {"store_id": store_id, "book_id": book_id}
            update = {"$inc": {"stock_level": add_stock_level}}
            self.db.db.store.update_one(filter, update)
        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    def create_store(self, user_id: str, store_id: str) -> (int, str):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if self.store_id_exist(store_id):
                return error.error_exist_store_id(store_id)

            # 在MongoDB中插入商店信息
            store_info = {"store_id": store_id, "user_id": user_id}
            self.db.db.user_store.insert_one(store_info)
        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"


    def ship_order(self, user_id: str, store_id: str, order_id: str):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)

            # 在MongoDB中查询订单信息
            order_info = self.db.db.orders.find_one({"order_id": order_id, "store_id": store_id})

            if not order_info:
                return error.error_invalid_order_id(order_id)

            # 获取订单状态
            current_status = order_info.get("status", 1)

            if current_status == 2:
            # 更新订单状态为4（已发货未收货）
                self.db.db.orders.update_one({"order_id": order_id}, {"$set": {"status": 4}})
            else:            # 如果订单状态不为2（已付款未发货）
                return 520,"error_invalid_order_status({})".format(order_id)
        except BaseException as e:
            return 530, "{}".format(str(e))

        return 200, "ok"

