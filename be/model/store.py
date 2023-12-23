import logging
from sqlalchemy import create_engine, Column, String, Integer, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


# 定义 User 表，用于存储用户信息
class User(Base):
    __tablename__ = 'user'

    user_id = Column(String(255), primary_key=True, unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    balance = Column(Integer, nullable=False)
    token = Column(String(511))
    terminal = Column(String(255))

# 定义 UserStore 表，用于关联用户和商店的关系
class UserStore(Base):
    __tablename__ = 'user_store'

    user_id = Column(String(255), ForeignKey('user.user_id'), primary_key=True)
    store_id = Column(String(255), primary_key=True)  # 添加索引

# 定义 Store 表，用于存储商店信息和图书信息
class Store(Base):
    __tablename__ = 'store'

    store_id = Column(String(255), primary_key=True, nullable=False)
    book_id = Column(String(255), primary_key=True, nullable=False)  # 确保添加了索引
    book_info = Column(Text)
    stock_level = Column(Integer)
    detail_book = Column(Text)

# 定义 Orders 表，用于存储订单信息
class Orders(Base):
    __tablename__ = 'orders'

    order_id = Column(String(255), primary_key=True, nullable=False)
    user_id = Column(String(255), ForeignKey('user.user_id'), index=True)
    store_id = Column(String(255), index=True)
    status = Column(Integer, index=True)

# 定义 NewOrderDetail 表，用于存储订单详细信息
class NewOrderDetail(Base):
    __tablename__ = 'new_order_detail'

    order_id = Column(String(255), primary_key=True, nullable=False)
    book_id = Column(String(255), primary_key=True, nullable=False)
    count = Column(Integer)
    price = Column(Integer)

class StoreORM:
    def __init__(self, db_config):
        self.session = None
        self.engine = create_engine(
            f"mysql+mysqlconnector://{db_config['user']}:{db_config['password']}@{db_config['host']}/{db_config['database']}",
            echo=True
        )

        self.init_tables()

    def init_tables(self):
        try:
            Base.metadata.create_all(self.engine)

        except Exception as e:
            logging.error(e)

    def get_db_conn(self):
        DbSession = sessionmaker(bind=self.engine)
        self.session = DbSession()
        return self.session


database_instance: StoreORM = None


def init_database(db_config):
    global database_instance
    database_instance = StoreORM(db_config)


def get_db_conn():
    global database_instance
    return database_instance.get_db_conn()
