import uuid
import json
import logging
from be.model import db_conn
from be.model import error
from datetime import datetime


class Buyer(db_conn.DBConn):
    def __init__(self):
        super().__init__()  # 初始化Buyer类，继承了数据库连接类DBConn

    # 创建新订单方法
    def new_order(self, user_id: str, store_id: str, id_and_count: [(str, int)]) -> (int, str, str):
        order_id = ""  # 初始化订单ID为空字符串
        try:
            # 检查用户ID是否存在
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id) + (order_id,)  # 返回用户ID不存在的错误信息

            # 检查商店ID是否存在
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id) + (order_id,)  # 返回商店ID不存在的错误信息

            uid = "{}_{}_{}".format(user_id, store_id, str(uuid.uuid1()))  # 生成订单ID，使用UUID
            # 遍历传入的图书ID和购买数量
            for book_id, count in id_and_count:
                # 查询图书库存和信息
                store_data = self.db.db.store.find_one(
                    {"store_id": store_id, "book_id": book_id}
                )
                if store_data is None:
                    return error.error_non_exist_book_id(book_id) + (order_id,)  # 返回图书ID不存在的错误信息

                stock_level = store_data["stock_level"]
                book_info = store_data['book_info']
                book_info = json.loads(book_info)
                price = book_info["price"]

                # 检查库存是否足够
                if stock_level < count:
                    return error.error_stock_level_low(book_id) + (order_id,)  # 返回库存不足的错误信息
                # 更新图书库存
                self.db.db.store.update_one(
                    {"store_id": store_id, "books.book_id": book_id},
                    {"$inc": {"books.$.stock_level": -count}},
                )

                # 插入新订单的详细信息
                self.db.db.new_order_detail.insert_one(
                    {"order_id": uid, "book_id": book_id, "count": count, "price": price}
                )

            # 插入新订单

            self.db.db.orders.insert_one(
                {"order_id": uid, "store_id": store_id, "user_id": user_id, "status": 1}
            )

            order_id = uid  # 更新订单ID
        except Exception as e:
            logging.info("Error: {}".format(str(e)))
            return 500, "Internal Server Error", ""

        return 200, "ok", order_id  # 返回成功状态码、消息和订单ID

    # 支付订单方法
    def payment(self, user_id: str, password: str, order_id: str) -> (int, str):
        try:
            # 查询订单信息
            order_data = self.db.db.orders.find_one({"order_id": order_id})
            if order_data is None:
                return error.error_invalid_order_id(order_id)  # 返回无效订单ID的错误信息

            buyer_id = order_data["user_id"]
            store_id = order_data["store_id"]
            status = order_data["status"]

            # 检查订单状态
            if status != 1:
                return 520,"error_invalid_order_status({})".format(order_id)


            # 检查用户权限
            if buyer_id != user_id:
                return error.error_authorization_fail()  # 返回权限验证失败的错误信息

            # 查询用户余额和密码
            user_data = self.db.db.user.find_one({"user_id": buyer_id})
            if user_data is None:
                return error.error_non_exist_user_id(buyer_id)  # 返回用户ID不存在的错误信息

            balance = user_data["balance"]
            if password != user_data["password"]:
                return error.error_authorization_fail()  # 返回权限验证失败的错误信息

            # 查询商店信息
            store_data = self.db.db.user_store.find_one({"store_id": store_id})
            if store_data is None:
                return error.error_non_exist_store_id(store_id)  # 返回商店ID不存在的错误信息

            seller_id = store_data["user_id"]

            # 检查卖家ID是否存在
            if not self.user_id_exist(seller_id):
                return error.error_non_exist_user_id(seller_id)  # 返回卖家ID不存在的错误信息

            total_price = 0

            # 查询订单详细信息并计算总价
            order_details = self.db.db.new_order_detail.find({"order_id": order_id})
            for detail in order_details:
                count = detail["count"]
                price = detail["price"]
                total_price += price * count  # 计算订单总价

            # 检查用户余额是否足够支付订单
            if balance < total_price:
                return error.error_not_sufficient_funds(order_id)  # 返回余额不足的错误信息

            # 更新买家余额
            self.db.db.user.update_one(
                {"user_id": buyer_id, "balance": {"$gte": total_price}},
                {"$inc": {"status": -total_price}},
            )

            # 更新卖家余额
            self.db.db.user.update_one(
                {"user_id": seller_id},
                {"$inc": {"balance": total_price}},
            )

            # 删除订单和订单详细信息
            self.db.db.new_order_detail.delete_many({"order_id": order_id})
            self.db.db.orders.update_one(
                {"order_id": order_id},
                {"$set": {"status": 2}},
            )
        except Exception as e:
            logging.info("Error: {}".format(str(e)))
            return 500, "Internal Server Error"

        return 200, "ok"  # 返回成功状态码和消息

    # 用户充值方法
    def add_funds(self, user_id, password, add_value) -> (int, str):
        try:

            user_data = self.db.db.user.find_one({"user_id": user_id})
            if user_data is None:
                return error.error_authorization_fail()  # 返回权限验证失败的错误信息

            # 检查用户密码是否匹配
            if user_data["password"] != password:
                return error.error_authorization_fail()  # 返回权限验证失败的错误信息

            # 更新用户余额
            self.db.db.user.update_one(
                {"user_id": user_id},
                {"$inc": {"balance": add_value}},
            )
        except Exception as e:
            logging.info("Error: {}".format(str(e)))
            return 500, "Internal Server Error"

        return 200, "ok"  # 返回成功状态码和消息

    def receive_order(self, user_id, order_id):
        try:
            # 检查买家用户ID是否存在
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id) + (order_id,)  # 返回用户ID不存在的错误信息

            # 查询订单信息
            order = self.db.db.orders.find_one({"order_id": order_id})
            if order is None:
                return error.error_invalid_order_id(order_id)  # 返回无效订单ID的错误信息

            # 提取订单信息中的相关字段
            status = order["status"]

            # 验证订单状态
            if status == 4:
                self.db.db.orders.update_one({"order_id": order_id}, {"$set": {"status": 4}})
            else:
                return 520,"error_invalid_order_status({})".format(order_id)

        except Exception as e:
            logging.info("Error: {}".format(str(e)))
            return 500, "Internal Server Error"

        return 200, "Order received successfully"

    def buyer_order_cancel(self, user_id: str, order_id: str) -> (int, str):
        store_id = ""
        try:
            # 检查用户ID是否存在
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)

            order = self.db.db.orders.find_one({"order_id": order_id})
            if order is None:
                return error.error_invalid_order_id(order_id)  # 返回无效订单ID的错误信息

            if order["status"] == 1:
                buyer_id = order["user_id"]
                if buyer_id != user_id:
                    return error.error_authorization_fail()
                self.db.db.orders.update_one({"order_id": order_id}, {"$set": {"status": 3}})

            # 如果已经支付的话需要取消订单以后减少商家余额，增加用户余额
            elif order["status"] == 2:
                buyer_id = order["user_id"]

                if buyer_id != user_id:
                    return error.error_authorization_fail()
                # 找到对应商店和价格
                store_id = order["store_id"]
                price = order["price"]

                # 根据商店找到卖家
                user_store = self.db.db.user_store.find_one({"store_id": store_id})

                seller_id = user_store["user_id"]

                # 减少卖家余额
                condition = {"$inc": {"balance": -price}}
                seller = {"user_id": seller_id}
                self.db.db.user.update_one(seller, condition)

                # 增加买家余额
                buyer = {"user_id": buyer_id}
                condition = {"$inc": {"balance": price}}
                self.db.db.user.update_one(buyer, condition)
            else:
                return error.error_authorization_fail()
            # 取消订单
            self.db.db.orders.update_one({"order_id": order_id}, {"$set": {"status": 3}})

            # 增加书籍库存
            orders = self.db.db.new_order_detail.find({"order_id": order_id})
            for order in orders:
                book_id = order["book_id"]
                count = order["count"]
                store_book = {"store_id": store_id, "book_id": book_id}
                condition = {"$inc": {"stock_level": count}}
                self.db.db.store.update_one(store_book, condition)
        except Exception as e:
            logging.info("Error: {}".format(str(e)))
            return 500, "Internal Server Error"

        return 200, "ok"
# 查询历史订单
    def history_order(self, user_id: str):
        # 最后返回一个订单详情
        # his_order_detail = []
        try:
            # 检查用户ID是否存在
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id) ,None

            # 查询历史订单分为：取消的订单和未取消的订单

            user = {"user_id": user_id}
            orders = self.db.db.orders.find(user)

            result = []
            # 取消的订单
            if(orders["status"==3]):
                for order in orders:
                   result.append(order)
            # 未取消的订单
            else:
                for order in orders:
                    order_id = order["order_id"]
                    order = {"order_id": order_id}
                    order_details = self.db.db.new_order_details.find(order)
                    for detail in order_details:
                        result.append(detail)
        except Exception as e:
            logging.info("Error: {}".format(str(e)))
            return 500, "Internal Server Error",None
        return 200, "ok", result

    def overtime_order_cancel(self):
        try:
        # 查询未支付订单
            unpaid_orders = self.db.db.orders.find({"status": '1'})
            current_time = datetime.now()

            for order in unpaid_orders:
                order_id = order["order_id"]
                # 获取 UUID 时间戳
                temp = order_id.split("_")
                time_ = temp[2]
                # 转换 UUID 时间戳为可读的时间格式
                order_time = datetime.fromtimestamp(uuid.UUID(time_).time)
                # 定义超时阈值
                timeout_threshold = 12 * 60

                if (current_time - order_time) > timeout_threshold:
                    # 取消订单
                    self.buyer_order_cancel(order["user_id"], order_id)

        except Exception as e:
            logging.info("Error: {}".format(str(e)))
            return 500, "Internal Server Error"

        return 200, "ok"