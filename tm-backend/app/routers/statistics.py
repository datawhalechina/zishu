from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from typing import Optional, List
import os
import ast
import logging

logger = logging.getLogger(__name__)

from app.dependencies import check_jwt_token, get_db, require_admin
from app.core.schemas.users import TokenModel

router = APIRouter(prefix="/api/statistics", tags=["statistics"])


def read_user_file(filepath: str) -> List:
    """读取用户数据文件"""
    data = []
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f.readlines():
                    line = line.strip()
                    if line:
                        try:
                            data.append(ast.literal_eval(line))
                        except (ValueError, SyntaxError):
                            continue
        except Exception as e:
            logger.warning("读取文件失败 %s: %s", filepath, e)
    return data


# ============ 个人统计 API ============

@router.get("/personal/overview")
async def get_personal_overview(
    user: TokenModel = Depends(check_jwt_token),
    db: Session = Depends(get_db)
):
    """获取个人统计数据概览"""
    from app.core.models.users import Users

    user_data = db.query(Users).filter(Users.id == user.id).first()
    if not user_data:
        raise HTTPException(status_code=404, detail="用户不存在")

    userid_str = str(user.id)

    # 读取时间管理数据
    tm_file = f"static/tm/t{userid_str}.txt"
    fn_file = f"static/tm/f{userid_str}.txt"

    total_tasks = 0
    finished_tasks = 0
    total_hours = 0

    planned_tasks = read_user_file(tm_file)
    finished_task_list = read_user_file(fn_file)

    total_tasks = len(planned_tasks)
    finished_tasks = len(finished_task_list)

    for task in planned_tasks:
        if len(task) > 7 and task[7] and task[7] > 0:
            total_hours += task[7] / 60

    return {
        "code": 200,
        "data": {
            "shuzhi": round(user_data.shuzhi or 0, 1),
            "learn_hours": round(user_data.learn_hour or 0, 1),
            "create_hours": round(user_data.create_hour or 0, 1),
            "total_tasks": total_tasks,
            "finished_tasks": finished_tasks,
            "completion_rate": round(finished_tasks / total_tasks * 100, 1) if total_tasks > 0 else 0,
            "total_hours": round(total_hours, 1)
        }
    }


@router.get("/personal/trend")
async def get_personal_trend(
    days: int = 7,
    user: TokenModel = Depends(check_jwt_token),
    db: Session = Depends(get_db)
):
    """获取个人学习时长趋势"""
    from app.core.models.users import Users
    from datetime import datetime, timedelta

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # 按天统计学习时长
    daily_stats = []
    current = start_date
    while current <= end_date:
        date_str = current.strftime("%Y-%m-%d")
        daily_stats.append({
            "date": date_str,
            "value": 0
        })
        current += timedelta(days=1)

    # 从数据库获取学习记录
    records = db.query(Users).filter(
        Users.id == user.id
    ).first()

    # 返回模拟数据（实际项目中应该从study_time表获取）
    # 这里返回最近7天的模拟数据
    import random
    trend_data = []
    for i in range(days):
        date = (end_date - timedelta(days=days - i - 1)).strftime("%Y-%m-%d")
        trend_data.append({
            "date": date,
            "value": round(random.uniform(0.5, 4.0), 1)
        })

    return {"code": 200, "data": trend_data}


@router.get("/personal/shuzhi-history")
async def get_shuzhi_history(
    user: TokenModel = Depends(check_jwt_token)
):
    """获取塾值变化历史"""
    userid_str = str(user.id)
    file_path = f"static/shuzhi/s{userid_str}.txt"

    shuzhi_list = read_user_file(file_path)

    # 格式化返回数据
    formatted_list = []
    for item in shuzhi_list:
        if isinstance(item, dict) and len(item) >= 6:
            formatted_list.append({
                "target_type": item.get("target_type", ""),
                "target_title": item.get("target_title", ""),
                "amount": item.get("amount", 0),
                "balance": item.get("balance", 0),
                "comments": item.get("comments", ""),
                "create_time": item.get("create_time", "")
            })

    return {"code": 200, "data": list(reversed(formatted_list))}


@router.get("/personal/time-distribution")
async def get_time_distribution(
    user: TokenModel = Depends(check_jwt_token),
    db: Session = Depends(get_db)
):
    """获取时间分配"""
    from app.core.models.users import Users

    user_data = db.query(Users).filter(Users.id == user.id).first()

    # 返回时间分配数据
    return {
        "code": 200,
        "data": [
            {"name": "学习", "value": user_data.learn_hour or 0},
            {"name": "创作", "value": user_data.create_hour or 0},
            {"name": "其他", "value": 20}  # 模拟数据
        ]
    }


# ============ 全局统计 API (仅管理员) ============

@router.get("/global/overview")
async def get_global_overview(
    user: TokenModel = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """获取全局统计数据"""
    from app.core.models.users import Users

    users = db.query(Users).all()

    total_users = len(users)
    total_shuzhi = sum(u.shuzhi or 0 for u in users)
    total_learn_hours = sum(u.learn_hour or 0 for u in users)
    total_create_hours = sum(u.create_hour or 0 for u in users)

    # 按角色统计
    role_stats = {}
    for u in users:
        role = u.role or 'user'
        if role not in role_stats:
            role_stats[role] = {"count": 0, "shuzhi": 0}
        role_stats[role]["count"] += 1
        role_stats[role]["shuzhi"] += u.shuzhi or 0

    # 按地区统计
    location_stats = {}
    for u in users:
        location = u.location or '未知'
        if location not in location_stats:
            location_stats[location] = 0
        location_stats[location] += 1

    return {
        "code": 200,
        "data": {
            "total_users": total_users,
            "total_shuzhi": round(total_shuzhi, 1),
            "total_learn_hours": round(total_learn_hours, 1),
            "total_create_hours": round(total_create_hours, 1),
            "role_stats": role_stats,
            "location_stats": location_stats
        }
    }


@router.get("/global/ranking")
async def get_global_ranking(
    type: str = "shuzhi",
    limit: int = 10,
    user: TokenModel = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """获取排行榜"""
    from app.core.models.users import Users

    valid_types = ["shuzhi", "learn_hour", "create_hour"]
    if type not in valid_types:
        type = "shuzhi"

    column = getattr(Users, type, Users.shuzhi)
    top_users = (
        db.query(Users)
        .order_by(desc(column))
        .limit(min(limit, 100))
        .all()
    )

    ranking_data = []
    for i, u in enumerate(top_users):
        value = getattr(u, type, 0) or 0
        ranking_data.append({
            "index": i + 1,
            "id": u.id,
            "username": u.username,
            "location": u.location or '-',
            "bumen": u.bumen or '-',
            "value": round(value, 1)
        })

    return {"code": 200, "data": ranking_data}


@router.get("/global/growth-trend")
async def get_growth_trend(
    days: int = 30,
    user: TokenModel = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """获取用户增长趋势"""
    from app.core.models.users import Users
    from datetime import datetime, timedelta
    from sqlalchemy import func, cast, Date

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # 按天统计注册用户数（单次查询）
    results = db.query(
        func.date(Users.register_time).label('register_date'),
        func.count().label('count')
    ).filter(
        Users.register_time >= start_date
    ).group_by(
        func.date(Users.register_time)
    ).all()

    # 转为字典便于查找
    count_map = {str(row.register_date): row.count for row in results}

    # 补全日期范围内的每一天
    daily_stats = []
    current = start_date
    while current <= end_date:
        date_str = current.strftime("%Y-%m-%d")
        daily_stats.append({
            "date": date_str,
            "count": count_map.get(date_str, 0)
        })
        current += timedelta(days=1)

    return {"code": 200, "data": daily_stats}


@router.get("/global/course-stats")
async def get_course_stats(
    user: TokenModel = Depends(require_admin)
):
    """获取课程统计（模拟数据）"""
    # 模拟课程热度数据
    course_data = [
        {"name": "Vue3入门", "views": 1200, "duration": 45},
        {"name": "FastAPI实战", "views": 980, "duration": 60},
        {"name": "TypeScript精讲", "views": 850, "duration": 40},
        {"name": "Element Plus教程", "views": 720, "duration": 35},
        {"name": "Excel自动化", "views": 680, "duration": 50}
    ]

    return {"code": 200, "data": course_data}


# ============ 新增：全局用户学习情况 API ============

@router.get("/global/users-list")
async def get_users_learning_list(
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "learn_hour",
    sort_order: str = "desc",
    location: Optional[str] = None,
    bumen: Optional[str] = None,
    user: TokenModel = Depends(check_jwt_token),
    db: Session = Depends(get_db)
):
    """获取所有用户学习情况列表（所有认证用户可见）"""
    from app.core.models.users import Users
    from app.core.models.config import SystemConfig
    from sqlalchemy import or_

    # 获取不活跃阈值配置
    config = db.query(SystemConfig).filter(SystemConfig.key == "inactive_days_threshold").first()
    inactive_threshold = int(config.value) if config else 7
    threshold_date = datetime.now() - timedelta(days=inactive_threshold)

    # 构建查询
    query = db.query(Users)

    # 筛选条件
    if location:
        query = query.filter(Users.location == location)
    if bumen:
        query = query.filter(Users.bumen == bumen)

    # 排序
    sort_column = getattr(Users, sort_by, Users.learn_hour)
    if sort_order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(sort_column)

    # 分页
    total = query.count()
    users = query.offset((page - 1) * page_size).limit(page_size).all()

    # 获取每个用户的课程进度
    users_data = []
    for u in users:
        userid_str = str(u.id)

        # 读取已完成任务获取课程学习记录
        fn_file = f"static/tm/f{userid_str}.txt"
        finished_tasks = read_user_file(fn_file)

        # 统计学习相关课程
        courses_completed = 0
        courses_in_progress = set()

        for task in finished_tasks:
            if len(task) > 1 and isinstance(task[1], str) and task[1].startswith("学习-"):
                courses_completed += 1
                # 提取课程名称
                course_name = task[1].replace("学习-", "", 1).split("/")[0]
                courses_in_progress.add(course_name)

        # 判断是否不活跃
        last_study = u.last_study_time or u.last_login_time
        is_inactive = last_study and last_study < threshold_date

        users_data.append({
            "id": u.id,
            "username": u.username,
            "location": u.location or '-',
            "bumen": u.bumen or '-',
            "role": u.role or 'user',
            "learn_hour": round(u.learn_hour or 0, 1),
            "create_hour": round(u.create_hour or 0, 1),
            "shuzhi": round(u.shuzhi or 0, 1),
            "last_study_time": last_study.strftime("%Y-%m-%d") if last_study else None,
            "last_login_time": u.last_login_time.strftime("%Y-%m-%d") if u.last_login_time else None,
            "is_inactive": is_inactive,
            "days_inactive": (datetime.now() - last_study).days if last_study else None,
            "courses_completed": courses_completed,
            "courses_in_progress": len(courses_in_progress)
        })

    # 统计概览数据
    all_users = db.query(Users).all()
    active_count = sum(1 for u in all_users if (u.last_study_time or u.last_login_time) and (u.last_study_time or u.last_login_time) >= threshold_date)
    total_learn = sum(u.learn_hour or 0 for u in all_users)

    return {
        "code": 200,
        "data": {
            "total": total,
            "active_users": active_count,
            "inactive_users": len(all_users) - active_count,
            "avg_learn_hours": round(total_learn / len(all_users), 1) if all_users else 0,
            "users": users_data,
            "inactive_threshold": inactive_threshold
        }
    }


@router.get("/global/inactive-users")
async def get_inactive_users(
    user: TokenModel = Depends(check_jwt_token),
    db: Session = Depends(get_db)
):
    """获取不活跃用户列表"""
    from app.core.models.users import Users
    from app.core.models.config import SystemConfig

    # 获取不活跃阈值配置
    config = db.query(SystemConfig).filter(SystemConfig.key == "inactive_days_threshold").first()
    inactive_threshold = int(config.value) if config else 7
    threshold_date = datetime.now() - timedelta(days=inactive_threshold)

    # 获取所有用户
    users = db.query(Users).all()

    inactive_users = []
    for u in users:
        last_study = u.last_study_time or u.last_login_time
        if last_study and last_study < threshold_date:
            days_inactive = (datetime.now() - last_study).days
            inactive_users.append({
                "id": u.id,
                "username": u.username,
                "location": u.location or '-',
                "bumen": u.bumen or '-',
                "last_study_time": last_study.strftime("%Y-%m-%d"),
                "last_login_time": u.last_login_time.strftime("%Y-%m-%d") if u.last_login_time else None,
                "days_inactive": days_inactive,
                "learn_hour": round(u.learn_hour or 0, 1),
                "shuzhi": round(u.shuzhi or 0, 1)
            })

    # 按不活跃天数排序
    inactive_users.sort(key=lambda x: x["days_inactive"], reverse=True)

    return {
        "code": 200,
        "data": {
            "threshold": inactive_threshold,
            "count": len(inactive_users),
            "users": inactive_users
        }
    }


@router.get("/global/locations")
async def get_locations(
    user: TokenModel = Depends(check_jwt_token),
    db: Session = Depends(get_db)
):
    """获取所有地区选项（用于筛选）"""
    from app.core.models.users import Users

    locations = db.query(Users.location).distinct().all()
    location_list = [loc[0] for loc in locations if loc[0]]

    return {
        "code": 200,
        "data": location_list
    }


@router.get("/global/departments")
async def get_departments(
    user: TokenModel = Depends(check_jwt_token),
    db: Session = Depends(get_db)
):
    """获取所有部门选项（用于筛选）"""
    from app.core.models.users import Users

    departments = db.query(Users.bumen).distinct().all()
    dept_list = [dept[0] for dept in departments if dept[0]]

    return {
        "code": 200,
        "data": dept_list
    }


# ============ 新增：个人深度统计分析 API ============

@router.get("/personal/detail/{user_id}")
async def get_user_detail_analysis(
    user_id: int,
    user: TokenModel = Depends(check_jwt_token),
    db: Session = Depends(get_db)
):
    """获取用户详细统计分析（管理员或本人）"""
    from app.core.models.users import Users

    # 权限检查
    if user.id != user_id and user.role != "admin":
        raise HTTPException(status_code=403, detail="无权访问此用户数据")

    user_data = db.query(Users).filter(Users.id == user_id).first()
    if not user_data:
        raise HTTPException(status_code=404, detail="用户不存在")

    userid_str = str(user_id)

    # 读取时间管理数据
    tm_file = f"static/tm/t{userid_str}.txt"
    fn_file = f"static/tm/f{userid_str}.txt"

    planned_tasks = read_user_file(tm_file)
    finished_tasks = read_user_file(fn_file)

    # 统计各类任务
    study_tasks = []
    create_tasks = []
    other_tasks = []

    for task in finished_tasks:
        if len(task) > 1:
            theme = task[1] if isinstance(task[1], str) else ""
            if theme.startswith("学习-"):
                study_tasks.append(task)
            elif theme.startswith("创作-"):
                create_tasks.append(task)
            else:
                other_tasks.append(task)

    # 计算平均完成时间
    planned_hours = sum(len(t) > 4 and t[4] or 0 for t in planned_tasks if isinstance(t[4], (int, float))) / 60
    actual_hours = sum(len(t) > 7 and t[7] or 0 for t in finished_tasks if isinstance(t[7], (int, float))) / 60

    return {
        "code": 200,
        "data": {
            "user": {
                "id": user_data.id,
                "username": user_data.username,
                "location": user_data.location,
                "bumen": user_data.bumen,
                "shuzhi": round(user_data.shuzhi or 0, 1),
                "learn_hour": round(user_data.learn_hour or 0, 1),
                "create_hour": round(user_data.create_hour or 0, 1),
                "register_time": user_data.register_time.strftime("%Y-%m-%d") if user_data.register_time else None,
                "last_login_time": user_data.last_login_time.strftime("%Y-%m-%d") if user_data.last_login_time else None,
                "last_study_time": user_data.last_study_time.strftime("%Y-%m-%d") if user_data.last_study_time else None
            },
            "tasks": {
                "total_planned": len(planned_tasks),
                "total_finished": len(finished_tasks),
                "study_count": len(study_tasks),
                "create_count": len(create_tasks),
                "other_count": len(other_tasks),
                "planned_hours": round(planned_hours, 1),
                "actual_hours": round(actual_hours, 1)
            },
            "recent_tasks": finished_tasks[:10] if finished_tasks else []
        }
    }


@router.get("/personal/study-calendar/{user_id}")
async def get_study_calendar(
    user_id: int,
    days: int = 365,
    user: TokenModel = Depends(check_jwt_token),
    db: Session = Depends(get_db)
):
    """获取学习日历热力图数据"""
    from app.core.models.users import Users

    # 权限检查
    if user.id != user_id and user.role != "admin":
        raise HTTPException(status_code=403, detail="无权访问此用户数据")

    userid_str = str(user_id)
    fn_file = f"static/tm/f{userid_str}.txt"

    finished_tasks = read_user_file(fn_file)

    # 按日期统计学习时长
    daily_data = {}
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    for task in finished_tasks:
        if len(task) > 8:
            date_str = task[8] if isinstance(task[8], str) else ""
            duration = task[7] if len(task) > 7 and isinstance(task[7], (int, float)) else 0

            if date_str:
                if date_str not in daily_data:
                    daily_data[date_str] = 0
                daily_data[date_str] += duration / 60  # 转换为小时

    # 格式化为日历热力图数据
    calendar_data = []
    for date, hours in daily_data.items():
        try:
            calendar_data.append({
                "date": date,
                "value": round(hours, 1),
                "level": min(4, int(hours / 2))  # 0-4级热力
            })
        except (ValueError, SyntaxError):
            continue

    return {
        "code": 200,
        "data": calendar_data
    }


@router.get("/personal/course-progress/{user_id}")
async def get_course_progress(
    user_id: int,
    user: TokenModel = Depends(check_jwt_token),
    db: Session = Depends(get_db)
):
    """获取课程学习进度"""
    from app.core.models.users import Users

    # 权限检查
    if user.id != user_id and user.role != "admin":
        raise HTTPException(status_code=403, detail="无权访问此用户数据")

    userid_str = str(user_id)
    fn_file = f"static/tm/f{userid_str}.txt"

    finished_tasks = read_user_file(fn_file)

    # 统计课程学习记录
    course_progress = {}
    for task in finished_tasks:
        if len(task) > 1:
            theme = task[1] if isinstance(task[1], str) else ""
            if theme.startswith("学习-"):
                # 提取课程和课时
                parts = theme.replace("学习-", "", 1).split("/")
                course_name = parts[0] if parts else "未知课程"
                lesson_name = task[3] if len(task) > 3 and isinstance(task[3], str) else ""

                if course_name not in course_progress:
                    course_progress[course_name] = {
                        "course_name": course_name,
                        "lessons": [],
                        "total_hours": 0
                    }

                duration = task[7] if len(task) > 7 and isinstance(task[7], (int, float)) else 0
                course_progress[course_name]["lessons"].append({
                    "title": lesson_name,
                    "duration": round(duration / 60, 1)  # 分钟转小时
                })
                course_progress[course_name]["total_hours"] += duration / 60

    # 转换为列表并计算进度
    progress_list = []
    for course, data in course_progress.items():
        progress_list.append({
            "course_name": data["course_name"],
            "lessons_count": len(data["lessons"]),
            "total_hours": round(data["total_hours"], 1),
            "recent_lessons": data["lessons"][-5:]  # 最近5个课时
        })

    # 按学习时长排序
    progress_list.sort(key=lambda x: x["total_hours"], reverse=True)

    return {
        "code": 200,
        "data": progress_list
    }


@router.get("/personal/time-analysis/{user_id}")
async def get_time_analysis(
    user_id: int,
    days: int = 30,
    user: TokenModel = Depends(check_jwt_token),
    db: Session = Depends(get_db)
):
    """获取时间管理分析"""
    from app.core.models.users import Users

    # 权限检查
    if user.id != user_id and user.role != "admin":
        raise HTTPException(status_code=403, detail="无权访问此用户数据")

    userid_str = str(user_id)
    tm_file = f"static/tm/t{userid_str}.txt"
    fn_file = f"static/tm/f{userid_str}.txt"

    planned_tasks = read_user_file(tm_file)
    finished_tasks = read_user_file(fn_file)

    # 计算计划vs实际
    total_planned = sum(len(t) > 4 and isinstance(t[4], (int, float)) and t[4] or 0 for t in planned_tasks) / 60
    total_actual = sum(len(t) > 7 and isinstance(t[7], (int, float)) and t[7] or 0 for t in finished_tasks) / 60

    # 按日期统计最近N天的完成情况
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    daily_completion = {}
    for task in finished_tasks:
        if len(task) > 8:
            date_str = task[8] if isinstance(task[8], str) else ""
            duration = task[7] if len(task) > 7 and isinstance(task[7], (int, float)) else 0

            try:
                task_date = datetime.strptime(date_str, "%Y/%m/%d")
                if start_date <= task_date <= end_date:
                    if date_str not in daily_completion:
                        daily_completion[date_str] = 0
                    daily_completion[date_str] += duration / 60
            except (ValueError, SyntaxError):
                continue

    # 按天统计
    trend_data = []
    current = start_date
    while current <= end_date:
        date_str = current.strftime("%Y/%m/%d")
        trend_data.append({
            "date": current.strftime("%Y-%m-%d"),
            "value": round(daily_completion.get(date_str, 0), 1)
        })
        current += timedelta(days=1)

    # 时间分布统计
    time_distribution = {
        "学习": 0,
        "创作": 0,
        "其他": 0
    }

    for task in finished_tasks:
        if len(task) > 1:
            theme = task[1] if isinstance(task[1], str) else ""
            duration = task[7] if len(task) > 7 and isinstance(task[7], (int, float)) else 0

            if theme.startswith("学习-"):
                time_distribution["学习"] += duration / 60
            elif theme.startswith("创作-"):
                time_distribution["创作"] += duration / 60
            else:
                time_distribution["其他"] += duration / 60

    distribution_data = [
        {"name": k, "value": round(v, 1)}
        for k, v in time_distribution.items()
    ]

    return {
        "code": 200,
        "data": {
            "planned_hours": round(total_planned, 1),
            "actual_hours": round(total_actual, 1),
            "completion_rate": round(total_actual / total_planned * 100, 1) if total_planned > 0 else 0,
            "trend": trend_data,
            "distribution": distribution_data
        }
    }


@router.get("/personal/trend")
async def get_personal_trend_fixed(
    days: int = 7,
    user: TokenModel = Depends(check_jwt_token),
    db: Session = Depends(get_db)
):
    """获取个人学习时长趋势（修复版，从真实文件读取）"""
    userid_str = str(user.id)
    fn_file = f"static/tm/f{userid_str}.txt"

    finished_tasks = read_user_file(fn_file)

    # 按日期统计
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    daily_data = {}
    for task in finished_tasks:
        if len(task) > 8:
            date_str = task[8] if isinstance(task[8], str) else ""
            duration = task[7] if len(task) > 7 and isinstance(task[7], (int, float)) else 0

            try:
                task_date = datetime.strptime(date_str, "%Y/%m/%d")
                if start_date <= task_date <= end_date:
                    if date_str not in daily_data:
                        daily_data[date_str] = 0
                    daily_data[date_str] += duration / 60
            except (ValueError, SyntaxError):
                continue

    # 生成完整的日期序列
    trend_data = []
    current = start_date
    while current <= end_date:
        date_str = current.strftime("%Y/%m/%d")
        trend_data.append({
            "date": current.strftime("%Y-%m-%d"),
            "value": round(daily_data.get(date_str, 0), 1)
        })
        current += timedelta(days=1)

    return {"code": 200, "data": trend_data}
