from fastapi import APIRouter, Form, Depends, HTTPException, status, Request
from datetime import datetime, timedelta
from app.dependencies import check_jwt_token, get_db
from sqlalchemy.orm import Session
from app.core.schemas.users import UserBase
from app.core.models.users import Users, Base
from app.database import engine
import json, os, ast
import logging

logger = logging.getLogger(__name__)


inno = APIRouter(
    prefix="/api/inno",
    tags=["inno"],
    responses={404: {"description": "Not found"}},
)


@inno.get('/get_tm/{user_id}')
async def get_tm(user_id:int):
    userid = str(user_id)
    pr = []
    fn = []
    if os.path.exists(f"static/tm/t{userid}.txt"):
        with open(f"static/tm/t{userid}.txt", "r", encoding="utf-8") as f:
            pr=f.readlines()
    pr = [ast.literal_eval(x) for x in pr]
    if os.path.exists(f"static/tm/f{userid}.txt"):
        with open(f"static/tm/f{userid}.txt", "r", encoding="utf-8") as f:
            fn=f.readlines()
    fn = [ast.literal_eval(x) for x in fn]
    fn.reverse()
    return {"pr":pr, "fn":fn}

@inno.get('/get_pr/{user_id}')
async def get_pr(user_id:int):
    userid = str(user_id)
    pr = []
    if os.path.exists(f"static/tm/t{userid}.txt"):
        with open(f"static/tm/t{userid}.txt", "r", encoding="utf-8") as f:
            pr=f.readlines()
    pr = [ast.literal_eval(x) for x in pr]
    return pr

@inno.put('/save_pr/{user_id}')
async def save_pr(request: Request, user_id:int):
    userid = str(user_id)
    form_data = await request.form()
    # 尝试多种参数格式
    taskinfo_str = form_data.get("params[taskinfo]") or form_data.get("taskinfo") or form_data.get("params")
    if taskinfo_str:
        tasklist = json.loads(taskinfo_str)
        with open(f"static/tm/t{userid}.txt", "w", encoding="utf-8") as f:
            for line in tasklist:
                f.write(str(line) + "\n")
    return {"code": "200"}

@inno.put('/finish_tm/{user_id}')
async def finish_tm(request: Request, user_id:int):
    userid = str(user_id)
    form_data = await request.form()
    # 尝试多种参数格式
    finishitem_str = form_data.get("params[finishitem]") or form_data.get("finishitem") or form_data.get("params")
    if finishitem_str:
        finishitem = json.loads(finishitem_str)
        finishitem.reverse()
        with open(f"static/tm/f{userid}.txt", "a", encoding="utf-8") as f:
            for line in finishitem:
                f.write(str(line) + "\n")
    return {"code": "200"}


@inno.post('/add_study_time/{user_id}')
async def add_study_time(request: Request, user_id:int):
    """添加学习时间到时间管理"""
    userid = str(user_id)
    try:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            data = await request.json()
            tasklist = data.get("taskinfo", [])
        else:
            # 支持表单格式
            form_data = await request.form()
            tasklist = form_data.getlist("taskinfo")

            # 如果 getlist 返回空，尝试从原始请求体解析
            if not tasklist:
                body = await request.body()
                try:
                    body_str = body.decode('utf-8')
                    # 解析 URL 编码的数据
                    import urllib.parse
                    parsed = urllib.parse.parse_qs(body_str)
                    # parse_qs 返回列表格式，需要提取第一个元素并解析 JSON
                    if 'taskinfo[]' in parsed:
                        tasklist_str = parsed['taskinfo[]'][0]
                        tasklist = json.loads(tasklist_str)
                    elif 'taskinfo' in parsed:
                        tasklist_str = parsed['taskinfo'][0]
                        tasklist = json.loads(tasklist_str)
                except Exception as parse_err:
                    logger.warning("URL解析错误: %s", parse_err)

        # 读取现有数据
        existing_pr = []
        if os.path.exists(f"static/tm/t{userid}.txt"):
            with open(f"static/tm/t{userid}.txt", "r", encoding="utf-8") as f:
                existing_pr = [ast.literal_eval(x) for x in f.readlines()]

        # 追加新的学习记录
        for line in tasklist:
            if isinstance(line, str):
                line = line.strip()
                if line:
                    try:
                        line = ast.literal_eval(line)
                    except (ValueError, SyntaxError):
                        continue
            existing_pr.append(line)

        # 保存
        with open(f"static/tm/t{userid}.txt", "w", encoding="utf-8") as f:
            for line in existing_pr:
                f.write(str(line) + "\n")

        return {"code": "200", "message": "添加成功"}
    except Exception as e:
        return {"code": "500", "message": str(e)}
