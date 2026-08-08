"""
验证 /api/users/add_shuzhi 端点的鉴权修复

背景: 该端点此前完全无鉴权，仅需 user_id + balance 等 JSON 字段即可向任意账户
授予任意数量的"塾值"(shuzhi，平台内的虚拟积分货币)，属于经济类滥用漏洞。
本次修复强制 require_admin 校验。

检查项 (v1.59 6-check 模式):
1. 无 token -> 401
2. 普通用户 token -> 403 (非 admin)
3. admin token + 合法 JSON -> 通过鉴权层 (404 因 mock user 不存在)
4. AST 校验函数签名含 Depends(require_admin)
5. AST 校验函数体仍保留原有字段 (user_id/balance/target_type 等)
6. 父 commit (main HEAD) 应回滚到无鉴权状态，验证 fix 仅在本次 commit 起效
"""
import ast
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

# main.py 在 tm-backend 根目录；确保根目录在 sys.path 中以正确 import app.*
_BACKEND_ROOT = Path(__file__).resolve().parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


def load_add_shuzhi_node():
    """从 users.py AST 中提取 add_shuzhi 函数节点"""
    file_path = _BACKEND_ROOT / "app" / "routers" / "users.py"
    source = file_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "add_shuzhi":
            return node, source
    return None, source


def test_signature_has_require_admin():
    """检查项 4: 函数签名包含 Depends(require_admin)"""
    node, _ = load_add_shuzhi_node()
    assert node is not None, "未找到 add_shuzhi 函数"
    sig_src = ast.unparse(node.args)
    assert "Depends(require_admin)" in sig_src, (
        "add_shuzhi 函数签名缺少 Depends(require_admin) 鉴权依赖"
    )


def test_function_body_intact():
    """检查项 5: 函数体仍接受 user_id/balance/target_type 等字段"""
    node, _ = load_add_shuzhi_node()
    assert node is not None
    body_src = ast.unparse(node)
    for field in ("user_id", "balance", "target_type", "target_title"):
        assert field in body_src, f"add_shuzhi 函数体缺少 {field} 字段"


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
            "/api/users/add_shuzhi",
            json={
                "user_id": 1,
                "target_type": "study",
                "target_title": "test",
                "balance": 100,
            },
        )
        assert resp.status_code == 401, (
            f"无 token 应返回 401, 实际 {resp.status_code}: {resp.text}"
        )
    finally:
        app.dependency_overrides.clear()


def test_normal_user_token_returns_403():
    """检查项 2: 普通用户 (role != admin) token -> 403"""
    from fastapi.testclient import TestClient
    from jose import jwt
    from main import app
    from app.config import settings
    from app.dependencies import check_jwt_token, get_db

    class FakeUser:
        id = 2
        role = "user"

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
            "/api/users/add_shuzhi",
            json={
                "user_id": 1,
                "target_type": "study",
                "target_title": "test",
                "balance": 100,
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 403, (
            f"普通用户应返回 403, 实际 {resp.status_code}: {resp.text}"
        )
    finally:
        app.dependency_overrides.clear()


def test_admin_token_passes_auth():
    """检查项 3: admin token + 合法 JSON -> 通过鉴权层 (404 因 mock user 不存在)"""
    from fastapi.testclient import TestClient
    from jose import jwt
    from main import app
    from app.config import settings
    from app.dependencies import check_jwt_token, get_db

    class FakeAdmin:
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
        return FakeAdmin()

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
            "/api/users/add_shuzhi",
            json={
                "user_id": 999,
                "target_type": "study",
                "target_title": "test",
                "balance": 100,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code != 401, (
            f"admin 不应返回 401: {resp.text}"
        )
        assert resp.status_code != 403, (
            f"admin 不应返回 403: {resp.text}"
        )
        # 关键: 鉴权已通过。endpoint 在 useritem=None 时仍返回 200 (添加文件成功，
        # 但 DB 更新被跳过) 或 500。任一非 401/403 都证明鉴权 dep 正常工作。
        assert resp.status_code in (200, 500), (
            f"admin 通过鉴权后应进入正常路径, "
            f"实际 {resp.status_code}: {resp.text}"
        )
    finally:
        app.dependency_overrides.clear()


def test_parent_commit_lacks_auth():
    """检查项 6: 父 commit (main HEAD) 应回滚到无鉴权状态"""
    repo_root = _BACKEND_ROOT.parent
    result = subprocess.run(
        ["git", "show", "HEAD~1:tm-backend/app/routers/users.py"],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    assert result.returncode == 0, (
        f"无法读取父 commit 的 users.py: {result.stderr}"
    )
    tree = ast.parse(result.stdout)
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "add_shuzhi":
            sig_src = ast.unparse(node.args)
            assert "Depends(require_admin)" not in sig_src, (
                "父 commit 已经包含 require_admin, 无法证明本次 commit 引入修复"
            )
            return
    raise AssertionError("未在父 commit 中找到 add_shuzhi 函数")