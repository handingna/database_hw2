import pytest
from fe.access.new_seller import register_new_seller
from fe.access import book
from fe.access import auth

import uuid
from fe import conf

class TestSearchBooks:
    @pytest.fixture(autouse=True)
    def pre_run_initialization(self):
        # 初始化测试环境
        self.seller_id = "test_search_books_seller_{}".format(str(uuid.uuid1()))
        self.password = self.seller_id
        self.seller = register_new_seller(self.seller_id, self.password)
        self.store_id = "test_search_books_store_{}".format(str(uuid.uuid1()))
        self.user_id = "test_search_books_user_{}".format(str(uuid.uuid1()))
        self.user = auth.Auth(conf.URL)
        # 创建虚拟书本数据
        code = self.seller.create_store(self.store_id)
        assert code == 200
        book_db = book.BookDB(conf.Use_Large_DB)
        self.books = book_db.get_book_info(0, 5)
        for bk in self.books:
            code = self.seller.add_book(self.store_id, 0, bk)
            assert code == 200
        yield

    def test_search_books_by_title(self):
        # 测试根据书籍标题搜索，预期应该能找到
        for b in self.books:
            book_title = b.title
            code = self.user.search_books(book_title, "title", self.store_id)
            assert code == 200

    def test_search_books_by_tag(self):
        # 测试根据书籍标签搜索，预期应该能找到
        for b in self.books:
            book_tags = b.tags
            code = self.user.search_books(book_tags[0], "tag",self.store_id)
            assert code == 200

    def test_search_books_by_content(self):
        # 测试根据书籍目录搜索，预期应该能找到
        for b in self.books:
            book_content = b.content
            code = self.user.search_books(book_content[0:10], "content",self.store_id)
            assert code == 200

    def test_search_books_by_book_intro(self):
        # 测试根据书籍内容搜索，预期应该能找到
        for b in self.books:
            book_intro = b.book_intro
            code = self.user.search_books(book_intro[0:10], "book_intro",self.store_id)
            assert code == 200

    def test_search_books_invalid_scope(self):
        # 测试使用无效的搜索范围，预期应该返回错误
        for b in self.books:
            book_title = b.title
            code = self.user.search_books(book_title, "invalid_scope",self.store_id)
            assert code != 200

    def test_search_books_no_result(self):
        # 测试一个不存在的查询，预期应该返回一个空的结果
        non_exist_query = "non_existing_book_title"
        code = self.user.search_books(non_exist_query, "title",self.store_id)
        assert code == 200

    def test_search_books_invalid_store_id(self):
        # 测试使用不存在的店铺 ID 进行搜索，预期应该返回错误
        non_exist_store_id = "non_existing_store_id"
        code = self.user.search_books("query", "title", non_exist_store_id)
        assert code != 200

