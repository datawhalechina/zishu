from fastapi import APIRouter, Form, Depends, HTTPException, status, Request, UploadFile, File
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)
from app.dependencies import check_jwt_token, get_db, verify_password, get_password_hash, require_admin
from app.config import settings
from jose import jwt
import requests
import os
import json
import glob
import ast
import re  # 添加re模块用于正则表达式验证
from typing import Optional
from app.core.schemas.users import UserBase, TokenModel
from sqlalchemy.orm import Session
from sqlalchemy import func, desc 
from app.core.models.users import Base, Users, Register
from app.database import engine
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
# from app.core.config import settings

router = APIRouter(
    prefix="/api/users",
    tags=["users"],
    responses={404: {"description": "Not found"}},
)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """

    :param data: 需要进行JWT令牌加密的数据（解密的时候会用到）
    :param expires_delta: 令牌有效期
    :return: token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=15)
    # 添加失效时间
    to_encode.update({"exp": expire})
    # SECRET_KEY：密钥
    # ALGORITHM：JWT令牌签名算法
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def check_user(db: Session, phone, password):
    """
    :param username:
    :param password:
    :return:
    """
    # user = users_db.get(username)
    user = db.query(Users).filter(Users.phone== phone).first()
    if not user:
        return '用户不存在'
    # if not verify_password(password, user.get("password")):
    if not verify_password(password, user.password):
        return '密码错误'
    return user
def send_reset_password_email(email: str, reset_token: str):
    """
    发送密码重置邮件
    :param email: 用户邮箱
    :param reset_token: 重置密码的token
    """
    # 检查 SMTP 是否已配置
    smtp_user = settings.SMTP_USER or settings.SMTP_USERNAME
    if not smtp_user or not settings.SMTP_PASSWORD:
        raise HTTPException(
            status_code=500,
            detail="邮件服务未配置，请联系管理员配置 SMTP"
        )

    # 创建邮件内容
    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = email
    msg['Subject'] = '密码重置'

    # 邮件正文
    reset_link = f"{settings.HOST}:{settings.PORT}/reset-password?token={reset_token}"
    body = f"""
    您好,

    您请求重置密码。请点击以下链接重置密码:

    {reset_link}

    此链接24小时内有效。如果您没有请求重置密码,请忽略此邮件。

    祝好,
    系统管理员
    """
    msg.attach(MIMEText(body, 'plain'))

    # 发送邮件
    try:
        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
        server.starttls()
        server.login(smtp_user, settings.SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"发送邮件失败: {str(e)}"
        )

def generate_password_reset_token(user_id: int) -> str:
    """
    生成密码重置token
    """
    expires = datetime.now() + timedelta(hours=24)
    to_encode = {"exp": expires, "user_id": user_id}
    return create_access_token(data=to_encode)

@router.post("/forgot-password")
def forgot_password(phone: str, db: Session = Depends(get_db)):
    """
    忘记密码-发送重置邮件
    """
    user = db.query(Users).filter(Users.phone == phone).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="用户不存在"
        )
    
    if not user.email:
        raise HTTPException(
            status_code=400,
            detail="该用户未绑定邮箱"
        )
        
    reset_token = generate_password_reset_token(user.id)
    send_reset_password_email(user.email, reset_token)
    
    return {"message": "密码重置邮件已发送,请查收邮箱"}

@router.post("/reset-password")
def reset_password(
    token: str,
    new_password: str,
    db: Session = Depends(get_db)
):
    """
    重置密码
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=400,
                detail="无效的重置链接"
            )
    except jwt.JWTError:
        raise HTTPException(
            status_code=400,
            detail="无效的重置链接"
        )
        
    user = db.query(Users).filter(Users.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="用户不存在"
        )
        
    hashed_password = get_password_hash(new_password)
    user.password = hashed_password
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"密码重置失败: {str(e)}"
        )
    
    return {"message": "密码重置成功"}

# import httpx 
# async def login_flask(id,name,phone,role):
#     url = 'http://127.0.0.1:8008/v1/auth/login_api'
#     headers = {"content-type": "application/x-www-form-urlencoded"} 
#     data = {"id": id, "name": name, "phone":phone, "role":role}
#     async with httpx.AsyncClient() as client:  
#         res = await client.post(url, data=data, headers=headers)  
#     return res.text



# 使用表单格式参数需要安装模块：python-multipart
@router.post("/token", response_model=TokenModel)
async def login_for_access_token(phone: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = check_user(db, phone, password)
    if  isinstance(user, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=user,
            headers={"WWW-Authenticate": "Bearer"}, 
        )
    # access过期时间
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    # refresh过期时间
    refresh_token_expires = timedelta(minutes=10080)
    # 把id进行username加密，要使用str类型
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    refresh_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=refresh_token_expires
    )
    user.atoken = access_token
    user.rtoken = refresh_token
    #rtn = await login_flask(user.id,user.username,user.phone,user.role)
    #print(rtn)
    return user

@router.get("/refresh", response_model=TokenModel)
async def get_refresh_token(*, user: TokenModel = Depends(check_jwt_token)):
    # access过期时间
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    # refresh过期时间
    refresh_token_expires = timedelta(minutes=10080)
    # 把id进行username加密，要使用str类型
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    refresh_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=refresh_token_expires
    )
    user.atoken = access_token
    user.rtoken = refresh_token
    return user


@router.post("/register")
async def register(request: Request, name: str = Form(...), password: str = Form(...), email: str = Form(...), phone: str = Form(...), db: Session = Depends(get_db)):
    # 验证密码强度
    is_valid, error_msg = validate_password_strength(password)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=error_msg
        )
    
    logger.debug("用户注册: name=%s, email=%s", name, email)
    form_data = await request.form()
    logger.debug("注册手机号: %s", form_data.get("phone"))
    # 检查手机号是否已注册
    existing_user = db.query(Users).filter(Users.phone == phone).first()
    existing_register = db.query(Register).filter(Register.phone == phone).first()
    if existing_user or existing_register:
        raise HTTPException(
            status_code=400,
            detail="该手机号已被注册"
        )
    
    new_register = Register(
        name=name,
        password=get_password_hash(password),
        email=email,
        phone=phone,
        register_time=datetime.now()
    )
    db.add(new_register)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"注册失败: {str(e)}"
        )
    return {"code": 200, "message":"OK"}

@router.get("/fetch_registrations", dependencies=[Depends(check_jwt_token)])
async def fetch_registrations(user: TokenModel = Depends(require_admin), db: Session = Depends(get_db)):
    result_proxy = db.query(Register).all()
    all_q_registrations = [{"id":row.id, "name":row.name, "phone":row.phone, "email":row.email, "notes":row.notes, "register_time":row.register_time} for row in result_proxy]
    return all_q_registrations


@router.post("/handle_registrations")
async def handle_registrations(action: str = Form(...), id: int = Form(...), db: Session = Depends(get_db)):
    registeritem = db.query(Register).filter_by(id=id).first()
    if not registeritem:
        raise HTTPException(
            status_code=404,
            detail="注册记录不存在"
        )
    
    try:
        if action=="delete":
            db.delete(registeritem)
            db.commit()
        elif action=="activate":
            # 检查手机号是否已存在
            existing_user = db.query(Users).filter(Users.phone == registeritem.phone).first()
            if existing_user:
                raise HTTPException(
                    status_code=400,
                    detail="该手机号已被激活"
                )
            new_user = Users(
                username=registeritem.name,
                password=registeritem.password,
                email=registeritem.email,
                phone=registeritem.phone,
                register_time=registeritem.register_time
            )
            db.add(new_user)
            db.delete(registeritem)
            db.commit()
        else:
            raise HTTPException(
                status_code=400,
                detail="无效的操作类型"
            )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"操作失败: {str(e)}"
        )
    return {"code": 200, "message":"OK"}

@router.post("/handle_changepass")
async def handle_changepass(newpass: str = Form(...), name: str = Form(...), user: TokenModel = Depends(check_jwt_token), db: Session = Depends(get_db)):
    # 验证密码强度
    is_valid, error_msg = validate_password_strength(newpass)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=error_msg
        )
    
    useritem = db.query(Users).filter_by(id=user.id).first()
    if not useritem:
        raise HTTPException(
            status_code=404,
            detail="用户不存在"
        )
    
    useritem.password = get_password_hash(newpass)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"修改密码失败: {str(e)}"
        )
    return {"code": 200, "message":"OK"}

@router.post("/reset_pass")
async def reset_pass(phone: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    # 验证密码强度
    is_valid, error_msg = validate_password_strength(password)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=error_msg
        )
    
    useritem = db.query(Users).filter_by(phone=phone).first()
    if not useritem:
        raise HTTPException(
            status_code=404,
            detail="用户不存在"
        )
    
    # 关键修复: 实际更新用户密码（必须先哈希）
    useritem.password = get_password_hash(password)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"重置密码失败: {str(e)}"
        )
    
    reset_list = []
    times = 0
    found = 0
    reset_file_path = "static/am/reset_pass.txt"
    
    try:
        if not os.path.exists("static/am/"):
            os.makedirs("static/am/")
        
        if os.path.exists(reset_file_path):
            try:
                with open(reset_file_path, "r", encoding="utf-8") as f:
                    reset_list = f.readlines()
            except (IOError, OSError) as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"读取重置记录文件失败: {str(e)}"
                )
        
        # 安全解析文件内容
        parsed_list = []
        for line in reset_list:
            line = line.strip()
            if not line:
                continue
            try:
                parsed_list.append(ast.literal_eval(line))
            except (ValueError, SyntaxError):
                # 跳过无效的行
                continue
        
        reset_list = parsed_list
        
        for item in reset_list:
            if item.get("id") == useritem.id:
                item["times"] = item.get("times", 0) + 1
                times = item["times"]
                found = 1
                item["update_time"] = datetime.now().strftime('%Y-%m-%d')
                break
        
        if found == 0:
            tmp = {
                "id": useritem.id,
                "username": useritem.username,
                "phone": useritem.phone,
                "times": 1,
                "create_time": datetime.now().strftime('%Y-%m-%d'),
                "update_time": datetime.now().strftime('%Y-%m-%d')
            }
            times = 1
            reset_list.append(tmp)
        
        # 写入文件
        try:
            with open(reset_file_path, "w", encoding="utf-8") as f:
                for line in reset_list:
                    f.write(str(line) + "\n")
        except (IOError, OSError) as e:
            raise HTTPException(
                status_code=500,
                detail=f"写入重置记录文件失败: {str(e)}"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"处理重置密码请求失败: {str(e)}"
        )
    
    return {"code": 200, "times": times}

@router.get("/reset_list", dependencies=[Depends(check_jwt_token)])
async def reset_list():
    reset_list = []
    reset_file_path = "static/am/reset_pass.txt"
    
    if os.path.exists(reset_file_path):
        try:
            with open(reset_file_path, "r", encoding="utf-8") as f:
                reset_list = f.readlines()
        except (IOError, OSError) as e:
            raise HTTPException(
                status_code=500,
                detail=f"读取重置记录文件失败: {str(e)}"
            )
    
    # 安全解析文件内容
    parsed_list = []
    for line in reset_list:
        line = line.strip()
        if not line:
            continue
        try:
            parsed_list.append(ast.literal_eval(line))
        except (ValueError, SyntaxError):
            # 跳过无效的行
            continue
    
    return parsed_list

@router.post("/handle_reset_pass")
async def handle_reset_pass(action: str = Form(...), id: int = Form(...), db: Session = Depends(get_db)):
    reset_file_path = "static/am/reset_pass.txt"
    reset_list = []
    
    if os.path.exists(reset_file_path):
        try:
            with open(reset_file_path, "r", encoding="utf-8") as f:
                reset_list = f.readlines()
        except (IOError, OSError) as e:
            raise HTTPException(
                status_code=500,
                detail=f"读取重置记录文件失败: {str(e)}"
            )
    
    # 安全解析文件内容
    parsed_list = []
    for line in reset_list:
        line = line.strip()
        if not line:
            continue
        try:
            parsed_list.append(ast.literal_eval(line))
        except (ValueError, SyntaxError):
            # 跳过无效的行
            continue
    
    reset_list = parsed_list
    k = -1
    
    for i, item in enumerate(reset_list):
        if item.get("id") == id:
            k = i
            break
    
    try:
        if k > -1:
            if action == "delete":
                reset_list.pop(k)
            elif action == "reset":
                reset_list.pop(k)
                useritem = db.query(Users).filter_by(id=id).first()
                if not useritem:
                    raise HTTPException(
                        status_code=404,
                        detail="用户不存在"
                    )
                # 安全修复: 生成随机密码而不是硬编码
                import secrets
                import string
                # 生成12位随机密码
                alphabet = string.ascii_letters + string.digits
                random_password = ''.join(secrets.choice(alphabet) for _ in range(12))
                useritem.password = get_password_hash(random_password)
                try:
                    db.commit()
                except Exception as e:
                    db.rollback()
                    raise HTTPException(
                        status_code=500,
                        detail=f"重置密码失败: {str(e)}"
                    )
            else:
                raise HTTPException(
                    status_code=400,
                    detail="无效的操作类型"
                )
        
        # 写入文件
        try:
            with open(reset_file_path, "w", encoding="utf-8") as f:
                for line in reset_list:
                    f.write(str(line) + "\n")
        except (IOError, OSError) as e:
            raise HTTPException(
                status_code=500,
                detail=f"写入重置记录文件失败: {str(e)}"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"处理重置密码请求失败: {str(e)}"
        )
    
    return {"code": 200, "message":"OK"}

@router.post("/save_profile")
async def save_profile(request: Request, user: TokenModel = Depends(check_jwt_token)):
    """
    保存用户头像文件
    安全修复: 添加文件类型和大小验证
    """
    form = await request.form()
    file = form.get('file')
    
    if not file or not hasattr(file, 'read'):
        raise HTTPException(
            status_code=400,
            detail="未提供文件"
        )
    
    # 验证文件大小 (限制为5MB)
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="文件大小超过限制(5MB)"
        )
    
    # 验证文件类型 (只允许图片)
    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif'}
    file_extension = os.path.splitext(file.filename or '')[1].lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="不支持的文件类型，只允许图片文件"
        )
    
    save_base_dir = "static/uploads/profiles/"
    try:
        if not os.path.exists(save_base_dir):
            os.makedirs(save_base_dir)
        
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        user_id = form.get("id") or str(user.id)
        serial = 4
        for i in range(0, 5):
            pattern = str(user_id) + "_" + str(i) + "*.jpg"
            if not glob.glob(os.path.join(save_base_dir, pattern)):
                serial = i
                break
        
        filename = str(user_id) + "_" + str(serial) + "_" + timestamp + ".jpg"
        file_path = os.path.join(save_base_dir, filename)
        
        # 使用上下文管理器确保文件正确关闭
        with open(file_path, 'wb') as fout:
            fout.write(contents)
        
        return {"code": 200, "message":"OK"}
    except OSError as e:
        raise HTTPException(
            status_code=500,
            detail=f"保存文件失败: {str(e)}"
        )

@router.get("/get_profile/{user_id}", dependencies=[Depends(check_jwt_token)])
async def get_profile(*, user_id: int, user: TokenModel = Depends(check_jwt_token), db: Session = Depends(get_db)):
    """
    获取用户资料
    安全修复: 只有用户本人或管理员可以查看用户资料
    """
    # 检查权限：只有用户本人或管理员可以查看
    if user.id != user_id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此用户资料"
        )
    useritem = db.query(Users).filter_by(id=user_id).first()
    if not useritem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    rtn = {}
    rtn['name']=useritem.username or ''
    rtn['gender']=useritem.gender or ''
    rtn['location']=useritem.location or ''
    rtn['desc']=useritem.desc or ''
    save_base_dir = "static/uploads/profiles/"
    if not os.path.exists(save_base_dir):
        os.makedirs(save_base_dir)
    tmplist = []
    for i in range(0,5):
        pattern = str(user_id)+"_"+str(i)+"*.jpg"
        findfile = glob.glob(os.path.join(save_base_dir, pattern))
        if findfile:
            tmpdict = {
                "name":'api/'+ findfile[0],
                "url":'api/'+ findfile[0]
                }
            tmplist.append(tmpdict)
    rtn["profiles"]=tmplist
    return rtn

@router.post("/delete_profile", dependencies=[Depends(check_jwt_token)])
async def delete_profile(filename: str = Form(...), user: TokenModel = Depends(check_jwt_token)):
    """
    删除用户头像文件
    安全修复: 验证文件路径，防止路径遍历攻击
    """
    save_base_dir = "static/uploads/profiles/"
    # 验证文件路径，防止路径遍历攻击
    if ".." in filename or "/" in filename.replace("\\", "/") or "\\" in filename:
        raise HTTPException(
            status_code=400,
            detail="无效的文件路径"
        )
    # 确保文件在允许的目录内
    file_path = os.path.join(save_base_dir, os.path.basename(filename))
    # 进一步验证：确保文件路径在允许的目录内
    if not os.path.abspath(file_path).startswith(os.path.abspath(save_base_dir)):
        raise HTTPException(
            status_code=400,
            detail="文件路径不在允许的目录内"
        )
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
        return {"code": 200, "message":"OK"}
    except OSError as e:
        raise HTTPException(
            status_code=500,
            detail=f"删除文件失败: {str(e)}"
        )

@router.post("/submit_profile")
async def submit_profile(info: str = Form(...), 
                user: UserBase = Depends(check_jwt_token), 
                db: Session = Depends(get_db)):
    try:
        userinfo = json.loads(info)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="无效的JSON格式"
        )
    
    useritem = db.query(Users).filter_by(id=user.id).first()
    if not useritem:
        raise HTTPException(
            status_code=404,
            detail="用户不存在"
        )
    
    useritem.username = userinfo.get("name", useritem.username)
    useritem.gender = userinfo.get("gender", useritem.gender)
    useritem.location = userinfo.get("region", useritem.location)
    useritem.desc = userinfo.get("desc", useritem.desc)
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"更新资料失败: {str(e)}"
        )
    return {"code": 200, "message":"OK"}


@router.get("/fetch_all_users", dependencies=[Depends(check_jwt_token)])
async def fetch_all_users(user: TokenModel = Depends(require_admin), db: Session = Depends(get_db)):
    """
    获取所有用户列表
    安全修复: 仅管理员可访问，且过滤敏感字段
    """
    users = db.query(Users).order_by(desc(Users.id)).all()
    rtn = []
    for user in users:
        # 过滤敏感字段，只返回必要的用户信息
        user_dict = {
            "id": user.id,
            "username": user.username,
            "phone": user.phone,
            "email": user.email,
            "role": user.role,
            "register_time": user.register_time,
        }
        rtn.append(user_dict)
    return rtn


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    验证密码强度
    返回: (是否通过, 错误信息)
    """
    if len(password) < 8:
        return False, "密码长度至少8位"
    
    if not re.search(r"[A-Z]", password):
        return False, "密码必须包含大写字母"
    
    if not re.search(r"[a-z]", password):
        return False, "密码必须包含小写字母"
    
    if not re.search(r"[0-9]", password):
        return False, "密码必须包含数字"
    
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", password):
        return False, "密码必须包含特殊字符(!@#$%^&*等)"
    
    return True, ""


def validate_password_format(password: str) -> bool:
    """
    简单验证密码格式（用于已有函数兼容）
    至少8位，包含数字和字母
    """
    if len(password) < 8:
        return False
    if not re.search(r"[0-9]", password):
        return False
    if not re.search(r"[A-Za-z]", password):
        return False
    return True


@router.get("/fetch_shuzhi")
async def fetch_shuzhi(userid: int):
    """获取用户塾值记录"""
    userid_str = str(userid)
    shuzhi_list = []
    file_path = f"static/shuzhi/s{userid_str}.txt"

    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            for line in lines:
                line = line.strip()
                if line:
                    try:
                        shuzhi_list.append(ast.literal_eval(line))
                    except (ValueError, SyntaxError):
                        continue
        except (IOError, OSError):
            pass

    return shuzhi_list


@router.post("/add_shuzhi")
async def add_shuzhi(request: Request, db: Session = Depends(get_db)):
    """添加塾值记录"""
    try:
        data = await request.json()
        user_id = data.get("user_id")
        target_type = data.get("target_type")
        target_title = data.get("target_title")
        amount = data.get("amount", 0)
        balance = data.get("balance", 0)
        comments = data.get("comments", "")
        create_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 保存到文件
        userid_str = str(user_id)
        os.makedirs("static/shuzhi/", exist_ok=True)

        record = {
            "target_type": target_type,
            "target_title": target_title,
            "amount": amount,
            "balance": balance,
            "comments": comments,
            "create_time": create_time
        }

        with open(f"static/shuzhi/s{userid_str}.txt", "a", encoding="utf-8") as f:
            f.write(str(record) + "\n")

        # 更新用户表中的塾值
        useritem = db.query(Users).filter_by(id=user_id).first()
        if useritem:
            useritem.shuzhi = (useritem.shuzhi or 0) + balance
            db.commit()

        return {"code": 200, "message": "添加成功"}
    except Exception as e:
        return {"code": 500, "message": str(e)}


@router.post("/update_user_role")
async def update_user_role(request: Request, user: TokenModel = Depends(require_admin), db: Session = Depends(get_db)):
    """更新用户角色"""
    try:
        data = await request.json()
        target_user_id = data.get("user_id")
        new_role = data.get("role")

        if target_user_id == user.id:
            return {"code": 400, "message": "不能修改自己的角色"}

        useritem = db.query(Users).filter_by(id=target_user_id).first()
        if not useritem:
            return {"code": 404, "message": "用户不存在"}

        useritem.role = new_role
        db.commit()

        return {"code": 200, "message": "角色更新成功"}
    except Exception as e:
        db.rollback()
        return {"code": 500, "message": str(e)}


@router.get("/fetch_permissions")
async def fetch_permissions(user: TokenModel = Depends(require_admin)):
    """获取权限配置"""
    file_path = "static/am/permissions.txt"
    permissions = []

    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            for line in lines:
                line = line.strip()
                if line:
                    try:
                        permissions.append(ast.literal_eval(line))
                    except (ValueError, SyntaxError):
                        continue
        except (IOError, OSError):
            pass

    # 如果没有配置，返回默认配置
    if not permissions:
        permissions = [
            {"id": "courses", "name": "课程学习", "enabled": True},
            {"id": "manager", "name": "时间管理", "enabled": True},
            {"id": "shuzhi", "name": "塾值记录", "enabled": True},
            {"id": "agents", "name": "智能体", "enabled": True},
            {"id": "profile", "name": "个人资料", "enabled": True},
            {"id": "registers", "name": "注册审核", "enabled": False},
            {"id": "all_users", "name": "全塾用户", "enabled": False},
            {"id": "reset_pass", "name": "重置密码", "enabled": False},
            {"id": "admin", "name": "系统管理", "enabled": False}
        ]

    return permissions


@router.post("/save_permissions")
async def save_permissions(request: Request, user: TokenModel = Depends(require_admin)):
    """保存权限配置"""
    try:
        data = await request.json()
        permissions = data.get("permissions", [])

        os.makedirs("static/am/", exist_ok=True)

        with open("static/am/permissions.txt", "w", encoding="utf-8") as f:
            for perm in permissions:
                f.write(str(perm) + "\n")

        return {"code": 200, "message": "权限配置已保存"}
    except Exception as e:
        return {"code": 500, "message": str(e)}