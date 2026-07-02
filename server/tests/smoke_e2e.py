"""全链路冒烟：lifespan 启动（调度器+admin 创建）→ 登录 → 下任务 → 轮询完成 → 校验流水线与审计。
运行：python tests/smoke_e2e.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
tmp = tempfile.mkdtemp()
os.environ["AAOS_DATA_DIR"] = tmp

from fastapi.testclient import TestClient  # noqa: E402

from app.config import config  # noqa: E402

config.data_dir = Path(tmp)
config.ensure_dirs()

from app.main import app  # noqa: E402


def main() -> int:
    with TestClient(app) as client:
        assert client.get("/healthz").json()["ok"]
        password = (Path(tmp) / "admin_password.txt").read_text().strip()

        r = client.post("/api/auth/login", json={"username": "admin", "password": password})
        assert r.status_code == 200, r.text
        print("① 登录成功:", r.json())

        r = client.post("/api/tasks", json={"type": "echo", "params": {"message": "AAOS 冒烟"}})
        assert r.status_code == 200, r.text
        task_id = r.json()["id"]
        print("② 任务已创建:", task_id)

        for _ in range(30):
            detail = client.get(f"/api/tasks/{task_id}").json()
            if detail["status"] in ("DONE", "FAILED"):
                break
            time.sleep(1)
        assert detail["status"] == "DONE", detail
        print("③ 任务完成，进度:", detail["progress"], "流水线:",
              [(s["name"], s["status"]) for s in detail["pipeline"]])
        assert len(detail["artifacts"]) == 2
        print("④ Artifacts:", [a["name"] for a in detail["artifacts"]])

        dash = client.get("/api/dashboard").json()
        print("⑤ 仪表盘:", dash)

        r = client.post("/api/keys", json={"raw_key": "  Bearer 'sk-ant-api03-testkey1234567890'  ",
                                           "skip_probe": True})
        assert r.status_code == 200 and r.json()["provider"] == "anthropic", r.text
        print("⑥ Key 归一化+识别:", r.json())

    print("\n[OK] 冒烟测试全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
