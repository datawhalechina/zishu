import os
import time
import glob
from datetime import datetime
from functools import lru_cache
from fastapi import APIRouter, HTTPException, Form
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

# 教程基础目录 - 使用项目根目录的 tutorial 文件夹
# 从当前文件位置向上查找 project_root 目录
current_dir = os.path.dirname(os.path.abspath(__file__))  # .../tm-backend/app/routers
# 向上3级: routers -> app -> tm-backend -> wow-fullstack
for _ in range(3):
    current_dir = os.path.dirname(current_dir)
TUTORIAL_BASE_DIR = os.path.join(current_dir, "tutorial")

# 教程结构缓存（5分钟有效期）
_cached_courses = None
_cache_timestamp = 0.0
_CACHE_TTL = 300  # 缓存有效期：5分钟


class TutorialFile(BaseModel):
    path: str
    title: str
    category: str
    chapter: str
    duration: Optional[int] = None  # 预计学习时间（分钟）


class CourseInfo(BaseModel):
    name: str
    path: str
    total_lessons: int
    total_duration: int  # 总时长（分钟）
    chapters: List[dict]


def parse_tutorial_structure():
    """解析教程目录结构（带5分钟缓存）"""
    global _cached_courses, _cache_timestamp

    now = time.time()
    if _cached_courses is not None and (now - _cache_timestamp) < _CACHE_TTL:
        return _cached_courses

    courses = []

    if not os.path.exists(TUTORIAL_BASE_DIR):
        return courses

    for course_name in sorted(os.listdir(TUTORIAL_BASE_DIR)):
        course_path = os.path.join(TUTORIAL_BASE_DIR, course_name)
        if not os.path.isdir(course_path):
            continue

        chapters = {}
        total_lessons = 0
        total_duration = 0

        # 遍历课程下的所有文件和文件夹
        for root, dirs, files in os.walk(course_path):
            # 按目录名排序
            dirs.sort()
            files.sort()

            for file in files:
                if file.endswith('.md'):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, TUTORIAL_BASE_DIR)

                    # 解析章节名称
                    dir_name = os.path.basename(root)
                    chapter_name = dir_name

                    if chapter_name not in chapters:
                        chapters[chapter_name] = {
                            'name': chapter_name,
                            'lessons': []
                        }

                    # 解析课时信息
                    title = file.replace('.md', '')
                    duration = 30  # 默认30分钟

                    # 尝试从文件名提取时长
                    if '第' in title and '课' in title:
                        try:
                            num = int(''.join(filter(str.isdigit, title.split('课')[0].split('节')[-1])))
                            duration = num * 5  # 简单估算：每个数字5分钟
                            duration = min(max(duration, 15), 60)  # 限制在15-60分钟
                        except (ValueError, TypeError):
                            pass

                    chapters[chapter_name]['lessons'].append({
                        'title': title,
                        'path': rel_path,
                        'duration': duration
                    })

                    total_lessons += 1
                    total_duration += duration

        if chapters:
            courses.append({
                'name': course_name,
                'path': course_name,
                'total_lessons': total_lessons,
                'total_duration': total_duration,
                'chapters': list(chapters.values())
            })

    _cached_courses = courses
    _cache_timestamp = time.time()
    return courses


def read_tutorial_file(file_path: str) -> str:
    """读取教程文件内容"""
    full_path = os.path.realpath(os.path.join(TUTORIAL_BASE_DIR, file_path))

    if not full_path.startswith(os.path.realpath(TUTORIAL_BASE_DIR)):
        raise HTTPException(status_code=400, detail="无效的文件路径")

    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="教程文件不存在")

    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取文件失败: {str(e)}")


@router.get("/courses")
async def get_courses():
    """获取所有课程列表"""
    courses = parse_tutorial_structure()
    return {"code": 200, "data": courses}


@router.get("/course/{course_name}")
async def get_course_detail(course_name: str):
    """获取指定课程详情"""
    courses = parse_tutorial_structure()
    for course in courses:
        if course['path'] == course_name:
            return {"code": 200, "data": course}
    raise HTTPException(status_code=404, detail="课程不存在")


@router.get("/content")
async def get_tutorial_content(path: str):
    """获取教程文件内容"""
    content = read_tutorial_file(path)
    return {"code": 200, "data": {"content": content}}


class ReportStudyTime(BaseModel):
    user_id: int
    course_name: str
    lesson_title: str
    duration: int  # 学习时长（分钟）
    description: Optional[str] = None


@router.post("/report-study-time")
async def report_study_time(
    user_id: int = Form(...),
    course_name: str = Form(...),
    lesson_title: str = Form(...),
    duration: int = Form(...)
):
    """申报学习时间，同步到时间管理"""
    # 生成时间记录
    now = datetime.now()
    date_string = now.strftime("%Y/%m/%d")

    # 构建时间管理记录格式
    study_record = [
        "",  # 编号
        f"学习-{course_name}",  # 主题
        duration,  # 目标用时（分钟）
        lesson_title,  # 分拆事项
        duration,  # 计划用时（分钟）
        "",  # 开始时间
        "",  # 结束时间
        duration,  # 实际用时（分钟）
        date_string  # 日期
    ]

    return {
        "code": 200,
        "message": "申报成功",
        "data": {
            "user_id": user_id,
            "course_name": course_name,
            "lesson_title": lesson_title,
            "duration": duration,
            "record": study_record
        }
    }


class SyncStudyTime(BaseModel):
    user_id: int
    course_name: str
    lesson_title: str
    duration: int  # 学习时长（分钟）
    date: str  # 日期


@router.post("/sync-study-time")
async def sync_study_time(
    user_id: int = Form(...),
    course_name: str = Form(...),
    lesson_title: str = Form(...),
    duration: int = Form(...),
    date: str = Form(...)
):
    """同步学习时间到时间管理系统"""
    return {
        "code": 200,
        "message": "同步成功",
        "data": {
            "taskinfo": [[
                "",  # 编号
                f"学习-{course_name}",  # 主题
                duration,  # 目标用时
                lesson_title,  # 分拆事项
                duration,  # 计划用时
                "",  # 开始时间
                "",  # 结束时间
                duration,  # 实际用时
                date  # 日期
            ]]
        }
    }
