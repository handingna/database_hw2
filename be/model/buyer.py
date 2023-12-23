import uuid
import json
import logging

from sqlalchemy.exc import NoResultFound

from be.model.db_conn import DBConn
from be.model import error
from datetime import datetime
from be.model import store
from sqlalchemy import and_

class Buyer(DBConn):
    def __init__(self):
        DBConn.__init__(self)

    # 创建新订单方法
    def new_order(self, user_id: str, store_id: str, id_and_count: [(str, int)]) -> (int, str, str):
        order_id = ""
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id) + (order_id,)

            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id) + (order_id,)

            uid = "{}_{}_{}".format(user_id, store_id, str(uuid.uuid1()))

            for book_id, count in id_and_count:
                store_book = self.session.query(store.Store).filter_by(store_id=store_id, book_id=book_id).first()
                if store_book is None:
                    return error.error_non_exist_book_id(book_id) + (order_id,)

                stock_level = store_book.stock_level
                book_info = json.loads(store_book.book_info)
                price = book_info["price"]

                if stock_level < count:
                    return error.error_stock_level_low(book_id) + (order_id,)

                self.session.query(store.Store).filter_by(store_id=store_id, book_id=book_id).update(
                    {"stock_level": store_book.stock_level - count})
                self.session.commit()

                new_order_detail = store.NewOrderDetail(
                    order_id=uid,
                    book_id=book_id,
                    count=count,
                    price=price
                )
                self.session.add(new_order_detail)

            new_order = store.Orders(
                order_id=uid,
                user_id=user_id,
                store_id=store_id,
                status=1
            )
            self.session.add(new_order)
            self.session.commit()

            order_id = uid
        except Exception as e:
            logging.error(str(e))
            return 500, "Internal Server Error", order_id

        return 200, "ok", order_id

    def payment(self, user_id: str, password: str, order_id: str) -> (int, str):
        try:
            order_data = self.session.query(store.Orders).filter_by(order_id=order_id).first()
            if order_data is None:
                return error.error_invalid_order_id(order_id)

            buyer_id = order_data.user_id
            store_id = order_data.store_id
            status = order_data.status

            if status != 1:
                return 520, "error_invalid_order_status({})".format(order_id)

            if buyer_id != user_id:
                return error.error_authorization_fail()

            user_data = self.session.query(store.User).filter_by(user_id=buyer_id).first()
            if user_data is None:
                return error.error_non_exist_user_id(buyer_id)

            balance = user_data.balance
            if password != user_data.password:
                return error.error_authorization_fail()

            store_data = self.session.query(store.UserStore).filter_by(store_id=store_id).first()
            if store_data is None:
                return error.error_non_exist_store_id(store_id)

            seller_id = store_data.user_id

            if not self.user_id_exist(seller_id):
                return error.error_non_exist_user_id(seller_id)

            total_price = 0

            order_details = self.session.query(store.NewOrderDetail).filter_by(order_id=order_id)
            for detail in order_details:
                count = detail.count
                price = detail.price
                total_price += price * count

            if balance < total_price:
                return error.error_not_sufficient_funds(order_id)
            self.session.query(store.User).filter(store.User.user_id == buyer_id, store.User.balance >= total_price).update({store.User.balance: (store.User.balance - total_price)})
            self.session.query(store.User).filter_by(user_id=seller_id).update({"balance": user_data.balance + total_price})
            self.session.query(store.NewOrderDetail).filter_by(order_id=order_id).delete()
            self.session.query(store.Orders).filter_by(order_id=order_id).update({"status": 2})
            self.session.commit()
        except Exception as e:
            logging.info("Error: {}".format(str(e)))
            return 500, "Internal Server Error"

        return 200, "ok"
    # 用户充值方法
    def add_funds(self, user_id, password, add_value) -> (int, str):
        try:
            user_data = self.session.query(store.User).filter_by(user_id=user_id).first()
            if user_data is None:
                return error.error_authorization_fail()

            if user_data.password != password:
                return error.error_authorization_fail()

            self.session.query(store.User).filter_by(user_id=user_id).update({"balance": user_data.balance + add_value})
            self.session.commit()
        except Exception as e:
            logging.info("Error: {}".format(str(e)))
            return 500, "Internal Server Error"

        return 200, "ok"

    def receive_order(self, user_id, order_id):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id) + (order_id,)

            order = self.session.query(store.Orders).filter_by(order_id=order_id).first()
            if order is None:
                return error.error_invalid_order_id(order_id)

            status = order.status
            if status == 4:
                self.session.query(store.Orders).filter_by(order_id=order_id).update({"status": 4})
                self.session.commit()
            else:
                return 520, "error_invalid_order_status({})".format(order_id)
        except Exception as e:
            logging.info("Error: {}".format(str(e)))
            return 500, "Internal Server Error"

        return 200, "Order received successfully"

    def buyer_order_cancel(self, user_id: str, order_id: str) -> (int, str):
        store_id = ""
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)

            order = self.session.query(store.Orders).filter_by(order_id=order_id).first()
            if order is None:
                return error.error_invalid_order_id(order_id)

            if order.status == 1:
                if order.user_id != user_id:
                    return error.error_authorization_fail()

                self.session.query(store.Orders).filter_by(order_id=order_id).update({"status": 3})
                self.session.commit()
            elif order.status == 2:
                if order.user_id != user_id:
                    return error.error_authorization_fail()

                store_id = order.store_id
                price = order.price

                user_store = self.session.query(store.UserStore).filter_by(store_id=store_id).first()
                seller_id = user_store.user_id

                self.session.query(store.User).filter_by(user_id=seller_id).update({"balance": store.User.balance + price})
                self.session.query(store.User).filter_by(user_id=user_id).update({"balance": store.User.balance - price})
                self.session.query(store.NewOrderDetail).filter_by(order_id=order_id).delete()
                self.session.query(store.Orders).filter_by(order_id=order_id).update({"status": 3})
                self.session.commit()
            else:
                return error.error_authorization_fail()

            orders = self.session.query(store.NewOrderDetail).filter_by(order_id=order_id)
            for order in orders:
                book_id = order.book_id
                count = order.count

                self.session.query(store.Store).filter_by(store_id=store_id, book_id=book_id).update({"stock_level": store.Store.stock_level + count})

            self.session.commit()
        except Exception as e:
            logging.info("Error: {}".format(str(e)))
            return 500, "Internal Server Error"

        return 200, "ok"

    def history_order(self, user_id: str):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id), None

            orders = self.session.query(store.Orders).filter_by(user_id=user_id).all()

            result = []
            for order in orders:
                order_id = order.order_id
                order_details = self.session.query(store.NewOrderDetail).filter_by(order_id=order_id).all()
                for detail in order_details:
                    result.append(detail)
        except Exception as e:
            logging.info("Error: {}".format(str(e)))
            return 500, "Internal Server Error", None

        return 200, "ok", result

    def overtime_order_cancel(self):
        try:
            unpaid_orders = self.session.query(store.Orders).filter_by(status=1).all()
            current_time = datetime.now()
            print(current_time)
            for order in unpaid_orders:
                order_id = order.order_id
                # 获取 UUID 时间戳
                temp = order_id.split("_")
                l = len(temp)
                time_ = uuid.UUID(temp[l - 1])
                # print('1111111111111111')
                # print(temp)
                # print('1111111111111111')


                order_time = datetime.utcfromtimestamp(time_.time / 1e7)
                # 定义超时阈值
                timeout_threshold = 12 * 60

                if (current_time - order_time).total_seconds() > timeout_threshold:
                    self.buyer_order_cancel(order.user_id, order.order_id)
        except Exception as e:
            logging.info("Error: {}".format(str(e)))
            return 500, "Internal Server Error"


        return 200, "ok"