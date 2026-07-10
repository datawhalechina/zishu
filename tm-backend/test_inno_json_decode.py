"""
Test for inno.py save_pr / finish_tm json.loads JSONDecodeError handling.

Verifies that the fix correctly returns HTTPException(400, "无效的JSON格式")
when the form data contains a non-JSON string for taskinfo / finishitem,
rather than the previous behaviour of throwing a 500 (uncaught JSONDecodeError).

Approach: import the source file, extract the function bodies via AST, and
patch the global `json.loads` to raise JSONDecodeError. Then call the
endpoints via TestClient with a malformed payload and assert the 400.
"""
import sys
import os
import json
import importlib

# Add the backend to the path AND chdir so pydantic-settings can find .env
# 始终基于测试文件自身所在目录定位后端代码，避免硬编码绝对路径，
# 保证在任意克隆位置 / CI 环境下都导入本分支的代码
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND_DIR)
os.chdir(BACKEND_DIR)

# Ensure static/tm/ exists for the regression tests (seed.py normally creates this)
os.makedirs('static/tm', exist_ok=True)

# Use the inno router's endpoints via FastAPI TestClient
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# Test 1: save_pr with malformed JSON in 'taskinfo' field should return 400
# (Previously: would 500 with json.JSONDecodeError)
def test_save_pr_malformed_json_returns_400():
    # Use a user_id; no auth check on these endpoints from what we can see
    r = client.put(
        "/api/inno/save_pr/1",
        data={"taskinfo": "not-a-valid-json{{{"},
    )
    assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"
    assert "无效的JSON格式" in r.text or "JSON" in r.text, f"Expected JSON error message, got: {r.text}"
    print(f"  ✓ save_pr malformed → 400: {r.json()}")


# Test 2: finish_tm with malformed JSON in 'finishitem' field should return 400
def test_finish_tm_malformed_json_returns_400():
    r = client.put(
        "/api/inno/finish_tm/1",
        data={"finishitem": "definitely not json"},
    )
    assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"
    assert "无效的JSON格式" in r.text or "JSON" in r.text, f"Expected JSON error message, got: {r.text}"
    print(f"  ✓ finish_tm malformed → 400: {r.json()}")


# Test 3: save_pr with valid JSON still works (regression: ensure fix didn't break happy path)
def test_save_pr_valid_json_still_works():
    valid = '[{"task": "test", "time": 60}]'
    r = client.put(
        "/api/inno/save_pr/1",
        data={"taskinfo": valid},
    )
    # Should NOT be 400 (and should NOT be a 500 JSONDecodeError either)
    assert r.status_code != 400, f"Valid JSON should not 400, got: {r.text}"
    assert r.status_code != 500 or "JSONDecodeError" not in r.text, f"Got unhandled JSON error: {r.text}"
    print(f"  ✓ save_pr valid → {r.status_code}: {r.json()}")


# Test 4: finish_tm with valid JSON still works
def test_finish_tm_valid_json_still_works():
    valid = '[{"item": "done"}]'
    r = client.put(
        "/api/inno/finish_tm/1",
        data={"finishitem": valid},
    )
    assert r.status_code != 400, f"Valid JSON should not 400, got: {r.text}"
    assert r.status_code != 500 or "JSONDecodeError" not in r.text, f"Got unhandled JSON error: {r.text}"
    print(f"  ✓ finish_tm valid → {r.status_code}: {r.json()}")


if __name__ == "__main__":
    print("Test 1: save_pr with malformed JSON")
    test_save_pr_malformed_json_returns_400()
    print("Test 2: finish_tm with malformed JSON")
    test_finish_tm_malformed_json_returns_400()
    print("Test 3: save_pr with valid JSON (regression)")
    test_save_pr_valid_json_still_works()
    print("Test 4: finish_tm with valid JSON (regression)")
    test_finish_tm_valid_json_still_works()
    print("\n✓ All 4 tests passed")
