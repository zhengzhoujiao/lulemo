"""
清空数据库所有测试数据。

用法：
    python scripts/clear_db.py              # 交互确认后清空
    python scripts/clear_db.py --yes        # 跳过确认直接清空

环境要求：
    - 本地开发：需要 pymongo 已安装
    - 生产服务器：自动使用 docker exec + mongosh 直接操作容器内 MongoDB
"""

import os
import re
import subprocess
import sys

# ── 读取 .env 中的配置 ──────────────────────────────────────────────────────

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_SERVE_DIR = os.path.dirname(_SCRIPT_DIR)
_ENV_FILE = os.path.join(_SERVE_DIR, ".env")

MONGODB_URL = "mongodb://localhost:27017"
MONGODB_DB = "lulemo"

if os.path.isfile(_ENV_FILE):
    with open(_ENV_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = re.match(r"^(\w+)\s*=\s*(.+)$", line)
            if not m:
                continue
            key, val = m.group(1), m.group(2).strip().strip('"').strip("'")
            if key == "MONGODB_URL":
                MONGODB_URL = val
            elif key == "MONGODB_DB":
                MONGODB_DB = val

ALL_COLLECTIONS = [
    "users", "records", "check_ins",
    "teams", "team_members", "team_messages", "team_chat_reads", "team_join_requests",
    "posts", "comments",
    "work_orders", "work_order_replies",
    "counters",
]


def _has_pymongo() -> bool:
    try:
        __import__("pymongo")
        return True
    except ImportError:
        return False


# ── 方式 1：pymongo ─────────────────────────────────────────────────────────

def clear_via_pymongo() -> None:
    from pymongo import MongoClient

    client = MongoClient(MONGODB_URL)
    db = client[MONGODB_DB]
    for name in ALL_COLLECTIONS:
        result = db[name].delete_many({})
        print(f"  {name}: deleted {result.deleted_count}")
    client.close()


# ── 方式 2：docker exec + mongosh ────────────────────────────────────────────

def _mongosh(js: str) -> None:
    """在 MongoDB 容器中执行一段 JavaScript。"""
    # 先找到运行中的 mongo 容器
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "ancestor=mongo:7", "--format", "{{.Names}}"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=5,
        )
    except FileNotFoundError:
        print("错误：未找到 docker 命令，请安装 pymongo 后重试")
        sys.exit(1)

    containers = [c for c in result.stdout.strip().split("\n") if c]
    if not containers:
        # 尝试更宽松的匹配
        try:
            result2 = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=5,
            )
        except Exception:
            print("错误：未找到运行中的 MongoDB 容器，请确认 Docker 服务已启动")
            sys.exit(1)
        # 找包含 mongo 名字的容器
        containers = [c for c in result2.stdout.strip().split("\n") if c and "mongo" in c.lower()]

    if not containers:
        print("错误：未找到运行中的 MongoDB 容器")
        sys.exit(1)

    container = containers[0]
    cmd = ["docker", "exec", container, "mongosh", "--quiet", "--eval", js]
    subprocess.run(cmd, check=True)


def clear_via_mongosh() -> None:
    db = MONGODB_DB
    for name in ALL_COLLECTIONS:
        js = f'db.getSiblingDB("{db}").{name}.deleteMany({{}})'
        _mongosh(js)
        print(f"  {name}: done")


# ── 主流程 ──────────────────────────────────────────────────────────────────

def main() -> None:
    skip_confirm = "--yes" in sys.argv

    print(f"MongoDB URL: {MONGODB_URL}")
    print(f"Database:    {MONGODB_DB}")
    print(f"\nCollections to clear: {', '.join(ALL_COLLECTIONS)}")

    if not skip_confirm:
        answer = input("\nProceed? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            print("Cancelled.")
            return

    if _has_pymongo():
        print("\nUsing pymongo...")
        clear_via_pymongo()
    else:
        print("\npymongo not found, using docker exec + mongosh...")
        clear_via_mongosh()

    print("\nDone.")


if __name__ == "__main__":
    main()
