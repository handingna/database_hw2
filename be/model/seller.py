import json
from be.model import store

from be.model import error
from be.model.db_conn import DBConn
from jieba import cut  # 用于中文分词
import re
from sqlalchemy.orm import aliased


class Seller(DBConn):
    def __init__(self):
        DBConn.__init__(self)

    def add_book(
            self, user_id: str, store_id: str, book_id: str, book_json_str: str, stock_level: int
    ):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            if self.book_id_exist(store_id, book_id):
                return error.error_exist_book_id(book_id)

            book_json = json.loads(book_json_str)

            # 为search做准备
            title = book_json.get("title", [])
            tags = book_json.get("tags", [])
            content = book_json.get("content", [])
            book_intro = book_json.get("book_intro", [])

            # 执行分词操作
            tags_tokens = " ".join(tags)
            content_tokens = " ".join(cut(content))
            book_intro_tokens = " ".join(cut(book_intro))
            detail_book = str(title) + " " + str(tags_tokens) + " " + str(content_tokens) + " " + str(book_intro_tokens)

            # 在MySQL中插入书本信息
            new_book = store.Store(
                store_id=store_id,
                book_id=book_id,
                book_info=book_json_str,
                stock_level=stock_level,
                detail_book=detail_book,
            )
            self.session.add(new_book)
            self.session.commit()

        except Exception as e:
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

            # 更新MySQL中书本的库存
            self.session.query(store.Store).filter_by(store_id=store_id, book_id=book_id).update(
                {"stock_level": store.Store.stock_level + add_stock_level}
            )
            self.session.commit()

        except Exception as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    def create_store(self, user_id: str, store_id: str) -> (int, str):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if self.store_id_exist(store_id):
                return error.error_exist_store_id(store_id)

            # 在MySQL中插入商店信息
            new_store = store.UserStore(user_id=user_id, store_id=store_id)
            self.session.add(new_store)
            self.session.commit()

        except Exception as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    def ship_order(self, user_id: str, store_id: str, order_id: str):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)

            # 在MySQL中查询订单信息
            order_info = (
                self.session.query(store.Orders)
                .filter_by(order_id=order_id, store_id=store_id)
                .first()
            )

            if not order_info:
                return error.error_invalid_order_id(order_id)

            # 获取订单状态
            current_status = order_info.status

            if current_status == 2:
                # 更新订单状态为4（已发货未收货）
                self.session.query(store.Orders).filter_by(order_id=order_id).update(
                    {"status": 4}
                )
                self.session.commit()
            else:
                # 如果订单状态不为2（已付款未发货）
                return 520, "error_invalid_order_status({})".format(order_id)

        except Exception as e:
            return 530, "{}".format(str(e))

        return 200, "ok"


