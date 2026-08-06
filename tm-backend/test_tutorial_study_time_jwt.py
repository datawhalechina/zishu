"""
端到端验证：/api/tutorial/report-study-time 与 /api/tutorial/sync-study-time
两个端点在本次修复前后都应满足

  1. 必须带有效 JWT（无 token -> 401）
  2. token 中的 user.id 必须与表单 user_id 一致（不一致 -> 403）
  3. 自身用户调用应正常（200）

不依赖 pytest，不依赖 seed 数据。
通过 FastAPI app.dependency_overrides 直接 mock 掉 check_jwt_token，
避免触碰 bcrypt 4.x 与本地 sqlite schema 漂移。
"""

import sys
import ast
from pathlib import Path

from fastapi.testclient import TestClient
from main import app  # noqa: E402

client = TestClient(app)


ENDPOINTS = [
    ("/api/tutorial/report-study-time", {
        "user_id": 1,
        "course_name": "Vue3",
        "lesson_title": "L1",
        "duration": 30,
    }),
    ("/api/tutorial/sync-study-time", {
        "user_id": 1,
        "course_name": "Vue3",
        "lesson_title": "L1",
        "duration": 30,
        "date": "2026/08/07",
    }),
]


class _FakeUser:
    """最小可用的 TokenModel 替身，只提供端点用到的 .id 字段。"""
    def __init__(self, user_id: int) -> None:
        self.id = user_id


def _override_auth_as(user_id: int):
    """覆盖 check_jwt_token 直接返回 _FakeUser(user_id)，跳过数据库。"""
    from app.dependencies import check_jwt_token

    def _fake_check_jwt_token():
        return _FakeUser(user_id)

    app.dependency_overrides[check_jwt_token] = _fake_check_jwt_token


def _clear_auth_override():
    app.dependency_overrides.clear()


def test_no_token_rejected():
    """未带 token 时两个端点都应返回 401。"""
    _clear_auth_override()
    for url, form in ENDPOINTS:
        r = client.post(url, data=form)
        assert r.status_code == 401, f"{url} without token should be 401, got {r.status_code} {r.text}"
        print(f"  [OK] {url} no-token -> 401")


def test_token_userid_mismatch_rejected():
    """token 解析出的 user.id 与表单 user_id 不一致时应返回 403。"""
    _override_auth_as(user_id=1)
    try:
        for url, form in ENDPOINTS:
            body = dict(form)
            body["user_id"] = 999
            r = client.post(url, data=body)
            assert r.status_code == 403, f"{url} mismatch should be 403, got {r.status_code} {r.text}"
            assert "无权" in r.text, f"{url} detail should mention 无权, got {r.text}"
            print(f"  [OK] {url} mismatch(user_id=999, token=1) -> 403 ({r.json()['detail']!r})")
    finally:
        _clear_auth_override()


def test_self_user_succeeds():
    """token 中的 user.id 与表单 user_id 一致时应返回 200。"""
    _override_auth_as(user_id=1)
    try:
        for url, form in ENDPOINTS:
            body = dict(form)
            body["user_id"] = 1
            r = client.post(url, data=body)
            assert r.status_code == 200, f"{url} self should be 200, got {r.status_code} {r.text}"
            data = r.json()
            assert data.get("code") == 200, f"{url} body.code expected 200, got {data!r}"
            print(f"  [OK] {url} self(user_id=1) -> 200 (code={data['code']})")
    finally:
        _clear_auth_override()


def test_source_has_jwt_dep():
    """源码层验证：两个端点的签名都包含 Depends(check_jwt_token)。"""
    src = Path("app/routers/tutorial.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    saw_report = False
    saw_sync = False
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name in ("report_study_time", "sync_study_time"):
                args = [a.arg for a in node.args.args]
                defaults = node.args.defaults
                has_jwt = any(
                    isinstance(d, ast.Call)
                    and isinstance(d.func, ast.Name)
                    and d.func.id == "Depends"
                    and d.args
                    and isinstance(d.args[0], ast.Name)
                    and d.args[0].id == "check_jwt_token"
                    for d in defaults
                )
                if not has_jwt:
                    raise AssertionError(
                        f"{node.name}() missing Depends(check_jwt_token) in signature"
                    )
                assert "user" in args, f"{node.name}() missing `user` parameter"
                if node.name == "report_study_time":
                    saw_report = True
                else:
                    saw_sync = True
    assert saw_report and saw_sync, "AST check missed one of the two endpoints"
    print("  [OK] AST: report_study_time & sync_study_time both have Depends(check_jwt_token)")


def test_source_user_id_check():
    """源码层验证：两个端点内部都有 `if user.id != user_id: raise 403`。"""
    src = Path("app/routers/tutorial.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name in ("report_study_time", "sync_study_time"):
                body_src = ast.unparse(node)
                assert "user.id != user_id" in body_src, (
                    f"{node.name}() body missing `if user.id != user_id` check"
                )
                assert "403" in body_src, f"{node.name}() body missing 403 status"
    print("  [OK] AST: both endpoints have `if user.id != user_id: raise 403` guard")


def main():
    print("== test_no_token_rejected ==")
    test_no_token_rejected()
    print("== test_token_userid_mismatch_rejected ==")
    test_token_userid_mismatch_rejected()
    print("== test_self_user_succeeds ==")
    test_self_user_succeeds()
    print("== test_source_has_jwt_dep ==")
    test_source_has_jwt_dep()
    print("== test_source_user_id_check ==")
    test_source_user_id_check()
    print("\nAll checks passed.")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print(f"FAILED: {e}")
        sys.exit(1)
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: {e!r}")
        sys.exit(2)
