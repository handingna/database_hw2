from sqlalchemy.orm.exc import NoResultFound
from be.model import error
from be.model.db_conn import DBConn
import jwt
import time
import logging
from be.model import store


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
    token_lifetime: int = 3600  # 3600 seconds

    def __init__(self):
        DBConn.__init__(self)

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

    def register(self, user_id: str, password: str):
        try:
            if self.user_id_exist(user_id):
                return error.error_exist_user_id(user_id)
            terminal = "terminal_{}".format(str(time.time()))
            token = jwt_encode(user_id, terminal)

            new_user = store.User(
                user_id=user_id,
                password=password,
                balance=0,
                token=token,
                terminal=terminal
            )

            self.session.add(new_user)
            self.session.commit()
        except Exception as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    def check_token(self, user_id: str, token: str) -> (int, str):
        try:
            user = self.session.query(store.User).filter_by(user_id=user_id).one()
            db_token = user.token
            if not self.__check_token(user_id, db_token, token):
                return error.error_authorization_fail()
            return 200, "ok"
        except NoResultFound:
            return error.error_authorization_fail()

    def check_password(self, user_id: str, password: str) -> (int, str):
        try:
            user = self.session.query(store.User).filter_by(user_id=user_id).one()
            db_password = user.password
            if password != db_password:
                return error.error_authorization_fail()
            return 200, "ok"
        except NoResultFound:
            return error.error_authorization_fail()

    def login(self, user_id: str, password: str, terminal: str) -> (int, str, str):
        token = ""
        try:
            code, message = self.check_password(user_id, password)
            if code != 200:
                return code, message, ""

            token = jwt_encode(user_id, terminal)
            # user = self.session.query(store.User).filter_by(user_id=user_id).one()
            # user.token = token
            # user.terminal = terminal

            self.session.query(store.User).filter_by(user_id=user_id).update(
                {"token": token,"terminal":terminal})

            self.session.commit()
        except NoResultFound:
            return error.error_authorization_fail() + ("",)
        except Exception as e:
            return 530, "{}".format(str(e)), ""
        return 200, "ok", token

    def logout(self, user_id: str, token: str) -> bool:
        try:
            code, message = self.check_token(user_id, token)
            if code != 200:
                return code, message

            terminal = "terminal_{}".format(str(time.time()))
            dummy_token = jwt_encode(user_id, terminal)
            #
            # user = self.session.query(store.User).filter_by(user_id=user_id).one()
            # user.token = dummy_token
            # user.terminal = terminal

            self.session.query(store.User).filter_by(user_id=user_id).update(
                {"token": dummy_token,"terminal":terminal})

            self.session.commit()
        except NoResultFound:
            return error.error_authorization_fail()
        except Exception as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    def unregister(self, user_id: str, password: str) -> (int, str):
        try:
            code, message = self.check_password(user_id, password)
            if code != 200:
                return code, message

            self.session.query(store.User).filter_by(user_id=user_id).delete()
            self.session.commit()

            return 200, "ok"
        except NoResultFound:
            return error.error_authorization_fail()
        except Exception as e:
            return 530, "{}".format(str(e))
        return error.error_authorization_fail()

    def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        try:
            code, message = self.check_password(user_id, old_password)
            if code != 200:
                return code, message

            terminal = "terminal_{}".format(str(time.time()))
            token = jwt_encode(user_id, terminal)

            self.session.query(store.User).filter_by(user_id=user_id).update(
                {"password":new_password,"token": token,"terminal":terminal})

            self.session.commit()
        except NoResultFound:
            return error.error_authorization_fail()
        except Exception as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    def search_books(self, query: str, search_scope: str, store_id=None):
        try:
            search_scope_mapping = {
                "title": "book_info",
                "tag": "book_info",
                "content": "book_info",
                "book_intro": "book_info"
            }
            page = 1
            page_size = 10
            search_filter = {}

            if store_id:
                if not self.store_id_exist(store_id):
                    return error.error_non_exist_store_id(store_id)
                search_filter["store_id"] = store_id

            if search_scope in search_scope_mapping:
                field_name = search_scope_mapping[search_scope]

                # 使用类似 SQLAlchemy ORM 的方式进行查询
                query = (
                    self.session.query(store.Store)
                    .filter(getattr(store.Store, field_name).ilike(f"%{query}%"))
                    .limit(page_size)
                    .offset((page - 1) * page_size)
                )

                books = [
                    {
                        "store_id": book.store_id,
                        "book_id": book.book_id,
                        "book_info": book.book_info,
                        "stock_level": book.stock_level
                    }
                    for book in query
                ]

                return 200, "Search successful", books
            else:
                return error.error_and_message(400, "Invalid search scope"), None
        except Exception as e:
            return error.error_and_message(500, f"Error: {str(e)}"), None

