from datetime import datetime
from . import config
from .database import SessionLocal
from typing import Optional
from fastapi import Header, HTTPException, status, Depends
from jose import JWTError, jwt
from pydantic import ValidationError

from passlib.context import CryptContext

from sqlalchemy.orm import Session
from app.core.models import users
from .config import settings
# 使用的算法是Bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_password_hash(password):
    """
    哈希来自用户的密码
    :param password: 原密码
    :return: 哈希后的密码
    """
    return pwd_context.hash(password)
# 哈希后的密码
# $2b$12$sErK932BEaLyIisz30PubepN7w91RLwkISWbAFYgUgoIqh8goJLEW

def verify_password(plain_password, hashed_password):
    """
    校验接收的密码是否与存储的哈希值匹配
    :param plain_password: 原密码
    :param hashed_password: 哈希后的密码
    :return: 返回值为bool类型，校验成功返回True,反之False
    """
    return pwd_context.verify(plain_password, hashed_password)

def check_jwt_token(token: Optional[str] = Header(""), db: Session = Depends(get_db)):
    """
    验证token
    :param token:
    :return: 返回用户信息
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=settings.ALGORITHM)
        id: str = payload.get("sub")
        # 得到令牌过期时间
        expiration_timestamp = payload.get("exp")
        # 把令牌过期时间转化为人类可读时间信息
        # expiration_time = datetime.fromtimestamp(expiration_timestamp)
        # print(expiration_time)
        # 通过解析得到的username,获取用户信息,并返回
        # return users_db.get(username)
        user = db.query(users.Users).filter(users.Users.id== int(id)).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    'code': 5001,
                    'message': "User not found",
                    'data': "User not found",
                }
            )
        return user
    except (JWTError, ValidationError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                'code': 5000,
                'message': "Token Error",
                'data': "Token Error",
            }
        )


def require_admin(user: users.Users = Depends(check_jwt_token)):
    """
    检查用户是否为管理员
    :param user: 当前登录用户
    :return: 如果是管理员则返回用户，否则抛出异常
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                'code': 5003,
                'message': "Permission denied. Admin access required.",
                'data': None,
            }
        )
    return user
    
