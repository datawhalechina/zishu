from sqlalchemy import Column, Integer, Float, VARCHAR, Sequence, DateTime, Index
from app.database import Base

class Users(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(VARCHAR(200), nullable=False)
    email = Column(VARCHAR(200), nullable=False)
    password = Column(VARCHAR(500), nullable=True)
    phone = Column(VARCHAR(80), index=True)
    gender = Column(VARCHAR(32))
    location = Column(VARCHAR(32))
    bumen = Column(VARCHAR(32))
    role = Column(VARCHAR(32), index=True)
    shuzhi = Column(Float, default=0.0)
    learn_hour = Column(Float, default=0.0)
    create_hour = Column(Float, default=0.0)
    avantar = Column(VARCHAR(256))
    desc = Column(VARCHAR(1000))
    register_time = Column(DateTime, index=True)
    last_login_time = Column(DateTime)
    last_study_time = Column(DateTime)  # 最后学习时间

class Register(Base):
    __tablename__ = 'register'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(VARCHAR(200), nullable=False)
    email = Column(VARCHAR(200), nullable=False)
    password = Column(VARCHAR(500), nullable=True)
    phone = Column(VARCHAR(80))
    notes = Column(VARCHAR(500))
    register_time = Column(DateTime)

