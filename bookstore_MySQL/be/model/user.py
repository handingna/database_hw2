from be.model import error
from be.model.db_conn import DBConn
import jwt
import time
import logging


# encode a json string like:
#   {
#       "user_id": [user name],
#       "terminal": [terminal code],
#       "timestamp": [ts]} to a JWT
#   }
def jwt_encode(user_id: str, terminal: str) -> str:
    encoded = jwt.encode(
        {"user_id": user_id, "terminal": terminal, "timestamp": time.time()},
        key=user_id,
        algorithm="HS256",
    )
    return encoded.encode("utf-8").decode("utf-8")


# decode a JWT to a json string like:
#   {
#       "user_id": [user name],
#       "terminal": [terminal code],
#       "timestamp": [ts]} to a JWT
#   }
def jwt_decode(encoded_token, user_id: str) -> str:
    decoded = jwt.decode(encoded_token, key=user_id, algorithms="HS256")
    return decoded


class User(DBConn):
    token_lifetime: int = 3600  # 3600 second

    def __init__(self):
        DBConn.__init__(self)

    # 检查用户 token
    def __check_token(self, user_id, db_token, token) -> bool:
        try:
            if db_token != token:
                return False
            jwt_text = jwt_decode(encoded_token=token, user_id=user_id)
            ts = jwt_text["timestamp"]
            if ts is not None:
                now = time.time()
                if self.token_lifetime > now - ts >= 0:
                    return True
        except jwt.exceptions.InvalidSignatureError as e:
            logging.error(str(e))
            return False

    # 注册用户
    def register(self, user_id: str, password: str):
        # 检查用户是否已存在
        if self.db.db.user.find_one({"user_id": user_id}):
            return 512, "exist user id {}".format(user_id)

        try:
            # 用户不存在，继续注册逻辑
            terminal = "terminal_{}".format(str(time.time()))
            token = jwt_encode(user_id, terminal)

            user_data = {
                "user_id": user_id,
                "password": password,
                "balance": 0,
                "token": token,
                "terminal": terminal
            }
            self.db.db.user.insert_one(user_data)
        except Exception as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    # 检查用户 token
    def check_token(self, user_id: str, token: str) -> (int, str):
        user = self.db.db.user.find_one({"user_id": user_id})
        if user is None:
            return error.error_authorization_fail()

        db_token = user.get("token", "")
        if not self.__check_token(user_id, db_token, token):
            return error.error_authorization_fail()
        return 200, "ok"

    # 检查用户密码
    def check_password(self, user_id: str, password: str) -> (int, str):
        user = self.db.db.user.find_one({"user_id": user_id})
        if user is None:
            return error.error_authorization_fail()

        db_password = user.get("password", "")
        if password != db_password:
            return error.error_authorization_fail()

        return 200, "ok"

    # 用户登录
    def login(self, user_id: str, password: str, terminal: str) -> (int, str, str):
        try:
            code, message = self.check_password(user_id, password)
            if code != 200:
                return code, message, ""

            # 更新用户的 token
            token = jwt_encode(user_id, terminal)
            self.db.db.user.update_one({"user_id": user_id}, {"$set": {"token": token, "terminal": terminal}})
        except Exception as e:
            return 530, "{}".format(str(e)), ""
        return 200, "ok", token

    # 用户登出
    def logout(self, user_id: str, token: str) -> bool:
        try:
            code, message = self.check_token(user_id, token)
            if code != 200:
                return code, message

            # 生成新的 token
            terminal = "terminal_{}".format(str(time.time()))
            dummy_token = jwt_encode(user_id, terminal)

            # 更新用户的 token
            self.db.db.user.update_one({"user_id": user_id}, {"$set": {"token": dummy_token, "terminal": terminal}})
        except Exception as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    # 注销用户
    def unregister(self, user_id: str, password: str) -> (int, str):
        try:
            code, message = self.check_password(user_id, password)
            if code != 200:
                return code, message

            # 删除用户数据
            result = self.db.db.user.delete_one({"user_id": user_id})
            if result.deleted_count == 1:
                return 200, "ok"
        except Exception as e:
            return 530, "{}".format(str(e))
        return error.error_authorization_fail()

    # 修改密码
    def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        try:
            code, message = self.check_password(user_id, old_password)
            if code != 200:
                return code, message

            # 更新密码和 token
            terminal = "terminal_{}".format(str(time.time()))
            token = jwt_encode(user_id, terminal)
            self.db.db.user.update_one({"user_id": user_id},
                                       {"$set": {"password": new_password, "token": token, "terminal": terminal}})
        except Exception as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    def search_books(self, query: str, search_scope: str, store_id=None):
        try:
            search_scope_mapping = {
                "title",
                "tag",
                "content",
                "book_intro"
            }
            page = 1
            page_size = 10
            search_filter = {}

            if store_id:
                # If store_id is provided, limit the search to the specific store
                if not self.store_id_exist(store_id):
                    return error.error_non_exist_store_id(store_id)
                search_filter["store_id"] = store_id

            if search_scope in search_scope_mapping:
                # Create a full-text search index if not already created
                self.db.db.store.create_index(
                    [("detail_book", "text")]
                )
                # Build the query based on store_id and search_scope
                query_filter = search_filter
                query_filter["$text"] = {"$search": query}

                skip = (page - 1) * page_size

                results = self.db.db.store.find(
                    query_filter,
                    {"store_id": 1, "book_id": 1, "book_info": 1, "stock_level": 1},
                ).sort([("score", {"$meta": "textScore"})]).skip(skip).limit(page_size)
                books = []
                for book in results:
                    books.append(book)

                # Convert ObjectId to strings
                for book in books:
                    book['_id'] = str(book['_id'])

                return 200, "Search successful", books
            else:
                return error.error_and_message(400, "Invalid search scope"), None
        except Exception as e:
            return error.error_and_message(500, f"Error: {str(e)}"), None
