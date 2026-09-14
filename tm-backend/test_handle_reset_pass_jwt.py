"""
验证 /api/users/handle_reset_pass 端点的鉴权修复

背景: 该端点此前完全无鉴权，只需 action + id 两个表单字段即可：
  - action="delete"  — 任意删除任意用户的重置密码申请
  - action="reset"   — 实际重置任意用户的密码为12位随机串（账户接管级别漏洞）

本次修复强制 require_admin 校验（先 check_jwt_token 401，再 role=="admin" 403）。

检查项:
1. 无 token -> 401
2. 普通用户 token -> 403（非 admin）
3. admin token + 合法表单 -> 路径正常执行（不抛鉴权异常）
4. AST 校验函数签名含 Depends(require_admin)
5. AST 校验函数体保留 action/id 字段
6. 父 commit (main HEAD) 应回滚到无鉴权状态，验证 fix 仅在本次 commit 起效
"""
import ast
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

# main.py 在 tm-backend 根目录；确保根目录在 sys.path 中以正确 import app.*
_BACKEND_ROOT = Path(__file__).resolve().parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


def _load_handle_reset_pass_node():
    """从源文件加载 handle_reset_pass 函数节点"""
    src_file = _BACKEND_ROOT / "app" / "routers" / "users.py"
    source = src_file.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "handle_reset_pass":
            return node, source
    raise AssertionError("未找到 handle_reset_pass 函数定义")


def test_signature_has_require_admin():
    """检查项 4: 函数签名包含 Depends(require_admin)"""
    node, _ = _load_handle_reset_pass_node()
    sig_src = ast.unparse(node.args)
    assert "Depends(require_admin)" in sig_src, (
        "handle_reset_pass 函数签名缺少 Depends(require_admin) 鉴权依赖"
    )


def test_function_body_preserves_action_and_id():
    """检查项 5: 函数体保留 action 与 id 表单字段（确保 fix 没有破坏功能）"""
    node, _ = _load_handle_reset_pass_node()
    args = node.args.args + node.args.kwonlyargs
    arg_names = [a.arg for a in args]
    assert "action" in arg_names, "handle_reset_pass 缺少 action 字段"
    assert "id" in arg_names, "handle_reset_pass 缺少 id 字段"
    # body 中至少应存在针对 action 的两个分支（delete / reset）
    # 注: ast.unparse 输出使用 Python repr，可能为单引号或双引号
    body_src = ast.unparse(node)
    has_delete = (
        "action == 'delete'" in body_src
        or 'action == "delete"' in body_src
        or "action=='delete'" in body_src
    )
    has_reset = (
        "action == 'reset'" in body_src
        or 'action == "reset"' in body_src
        or "action=='reset'" in body_src
    )
    assert has_delete, "handle_reset_pass 函数体缺少 action=='delete' 分支"
    assert has_reset, "handle_reset_pass 函数体缺少 action=='reset' 分支"


def test_no_token_returns_401():
    """检查项 1: 无 token -> 401"""
    from fastapi.testclient import TestClient
    from main import app
    from app.dependencies import get_db

    def override_get_db():
        db = object()
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app)
        resp = client.post(
            "/api/users/handle_reset_pass",
            data={"action": "delete", "id": 1},
        )
        assert resp.status_code == 401, f"无 token 应返回 401, 实际 {resp.status_code}: {resp.text}"
    finally:
        app.dependency_overrides.clear()


def test_normal_user_token_returns_403():
    """检查项 2: 普通用户 token (role != 'admin') -> 403"""
    from fastapi.testclient import TestClient
    from jose import jwt
    from main import app
    from app.config import settings
    from app.dependencies import get_db, check_jwt_token

    class FakeUser:
        id = 2
        role = "user"  # 非 admin

    def override_get_db():
        db = object()
        try:
            yield db
        finally:
            pass

    def override_check_jwt_token():
        return FakeUser()

    user_token = jwt.encode(
        {"sub": "2", "exp": datetime.utcnow() + timedelta(minutes=15)},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[check_jwt_token] = override_check_jwt_token
    try:
        client = TestClient(app)
        resp = client.post(
            "/api/users/handle_reset_pass",
            data={"action": "delete", "id": 1},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 403, (
            f"普通用户应返回 403, 实际 {resp.status_code}: {resp.text}"
        )
    finally:
        app.dependency_overrides.clear()


def test_admin_token_passes_auth():
    """检查项 3: admin token + 合法表单 -> 通过鉴权层"""
    from fastapi.testclient import TestClient
    from jose import jwt
    from main import app
    from app.config import settings
    from app.dependencies import get_db, check_jwt_token

    class FakeUser:
        id = 1
        role = "admin"

    class FakeQuery:
        def filter_by(self, **kwargs):
            return self

        def first(self):
            return None

    class FakeDB:
        def query(self, model):
            return FakeQuery()

    def override_get_db():
        db = FakeDB()
        try:
            yield db
        finally:
            pass

    def override_check_jwt_token():
        return FakeUser()

    admin_token = jwt.encode(
        {"sub": "1", "exp": datetime.utcnow() + timedelta(minutes=15)},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[check_jwt_token] = override_check_jwt_token
    try:
        client = TestClient(app)
        resp = client.post(
            "/api/users/handle_reset_pass",
            data={"action": "delete", "id": 1},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        # admin 通过鉴权后：mock 环境下 reset_list 为空，循环不进入任何分支，
        # 然后执行 file write 阶段（path 不存在但有 IOError 捕获），最终应返回 200
        # 或 500（mock 文件 IO 失败）—但绝对不能 401/403
        assert resp.status_code != 401, f"admin 不应返回 401: {resp.text}"
        assert resp.status_code != 403, f"admin 不应返回 403: {resp.text}"
    finally:
        app.dependency_overrides.clear()


def test_parent_commit_lacks_auth():
    """检查项 6: 父 commit (main HEAD) 应回滚到无鉴权状态"""
    repo_root = _BACKEND_ROOT.parent
    result = subprocess.run(
        ["git", "show", "HEAD~1:tm-backend/app/routers/users.py"],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
    )
    assert result.returncode == 0, f"git show 失败: {result.stderr}"
    tree = ast.parse(result.stdout)
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "handle_reset_pass":
            sig_src = ast.unparse(node.args)
            assert "Depends(require_admin)" not in sig_src, (
                "父 commit 已经包含 require_admin 鉴权，无法证明本次 commit 引入修复"
            )
            return
    raise AssertionError("未在父 commit 中找到 handle_reset_pass 函数")
