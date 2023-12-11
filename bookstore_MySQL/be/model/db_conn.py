from be.model import store

class DBConn:
    def __init__(self):
        self.db = store.get_db_conn()

        # self.db = Store("mongodb://127.0.0.1:27017")

    def user_id_exist(self, user_id):
        # 在MongoDB中查找用户
        user = self.db.db.user.find_one({"user_id": user_id})
        return user is not None

    def book_id_exist(self, store_id, book_id):
        # 在MongoDB中查找书本
        book = self.db.db.store.find_one({"store_id": store_id, "book_id": book_id})
        return book is not None

    def store_id_exist(self, store_id):
        # 在MongoDB中查找商店
        store = self.db.db.user_store.find_one({"store_id": store_id})
        return store is not None

