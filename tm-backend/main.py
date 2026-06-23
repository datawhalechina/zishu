import uvicorn
import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware

from app.routers import users
from app.routers import inno
from app.routers import tutorial
from app.routers import statistics
from app.routers import code_execution
from app.routers import config

from app.config import settings
from app.core.models.users import Base
from app.database import engine

# 初始化数据库表结构
Base.metadata.create_all(bind=engine)

# 配置日志格式
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

app = FastAPI()
app.mount("/api/static", StaticFiles(directory="static"), name="static")
app.add_middleware(
    CORSMiddleware,
    # 允许跨域的源列表，例如 ["http://www.example.org"] 等等，["*"] 表示允许任何源
    allow_origins=["*"],
    # 跨域请求是否支持 cookie，默认是 False，如果为 True，allow_origins 必须为具体的源，不可以是 ["*"]
    allow_credentials=False,
    # 允许跨域请求的 HTTP 方法列表，默认是 ["GET"]
    allow_methods=["*"],
    # 允许跨域请求的 HTTP 请求头列表，默认是 []，可以使用 ["*"] 表示允许所有的请求头
    # 当然 Accept、Accept-Language、Content-Language 以及 Content-Type 总之被允许的
    allow_headers=["*"],
    # 可以被浏览器访问的响应头, 默认是 []，一般很少指定
    expose_headers=["*"]
    # 设定浏览器缓存 CORS 响应的最长时间，单位是秒。默认为 600，一般也很少指定
    # max_age=1000
)

app.include_router(users.router)
app.include_router(inno.inno)
app.include_router(tutorial.router, prefix="/api/tutorial")
app.include_router(statistics.router)
app.include_router(code_execution.router, prefix="/api/code")
app.include_router(config.router)

@app.get("/")
def read_root():
    return {"Hello": "World"}


if __name__ == '__main__':
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
