from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from datetime import datetime

from app.dependencies import check_jwt_token, get_db, require_admin
from app.core.schemas.users import TokenModel
from app.core.models.config import SystemConfig
from app.core.models.users import Users

router = APIRouter(prefix="/api/config", tags=["config"])


# 默认配置
DEFAULT_CONFIGS = {
    "inactive_days_threshold": {"value": "7", "description": "不活跃天数阈值"},
    "enable_email_notification": {"value": "false", "description": "是否启用邮件通知"},
    "notification_user_ids": {"value": "", "description": "需要通知的管理员ID列表（逗号分隔）"},
}


@router.get("/get")
async def get_configs(
    user: TokenModel = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """获取系统配置"""
    # 从数据库获取配置
    db_configs = db.query(SystemConfig).all()
    config_dict = {cfg.key: cfg.value for cfg in db_configs}

    # 填充缺失的默认配置
    result = {}
    for key, default in DEFAULT_CONFIGS.items():
        if key in config_dict:
            result[key] = config_dict[key]
        else:
            result[key] = default["value"]

    return {
        "code": 200,
        "data": result
    }


@router.post("/save")
async def save_configs(
    request_data: Dict[str, str],
    user: TokenModel = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """保存系统配置"""
    try:
        for key, value in request_data.items():
            if key not in DEFAULT_CONFIGS:
                continue

            # 查找现有配置
            config = db.query(SystemConfig).filter(SystemConfig.key == key).first()

            if config:
                config.value = value
                config.updated_at = datetime.now()
            else:
                config = SystemConfig(
                    key=key,
                    value=value,
                    description=DEFAULT_CONFIGS[key]["description"]
                )
                db.add(config)

        db.commit()

        return {
            "code": 200,
            "message": "配置保存成功"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}") from e


@router.get("/check-inactive")
async def check_inactive_users(
    user: TokenModel = Depends(check_jwt_token),
    db: Session = Depends(get_db)
):
    """检查不活跃用户（管理员专用）"""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="权限不足")

    # 获取配置
    db_configs = db.query(SystemConfig).all()
    config_dict = {cfg.key: cfg.value for cfg in db_configs}

    inactive_threshold = int(config_dict.get("inactive_days_threshold", "7"))

    # 获取所有用户
    users = db.query(Users).all()

    from datetime import timedelta
    threshold_date = datetime.now() - timedelta(days=inactive_threshold)

    inactive_users = []
    for u in users:
        last_study = u.last_study_time or u.last_login_time
        if last_study and last_study < threshold_date:
            days_inactive = (datetime.now() - last_study).days
            inactive_users.append({
                "id": u.id,
                "username": u.username,
                "last_study_time": last_study.strftime("%Y-%m-%d") if last_study else None,
                "days_inactive": days_inactive
            })

    return {
        "code": 200,
        "data": {
            "threshold": inactive_threshold,
            "inactive_count": len(inactive_users),
            "inactive_users": inactive_users
        }
    }
