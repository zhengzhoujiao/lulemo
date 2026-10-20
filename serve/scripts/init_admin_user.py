"""
将指定账号设为管理员（role=1）。

用法：
    python scripts/init_admin_user.py admin              # 交互确认
    python scripts/init_admin_user.py admin --yes        # 跳过确认

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


def _has_pymongo() -> bool:
    try:
        __import__("pymongo")
        return True
    except ImportError:
        return False


def _mongosh(js: str) -> None:
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "ancestor=mongo:7", "--format", "{{.Names}}"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=5,
        )
    except FileNotFoundError:
        print("Error: docker not found. Install pymongo or run inside Docker host.")
        sys.exit(1)

    containers = [c for c in result.stdout.strip().split("\n") if c]
    if not containers:
        result2 = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=5,
        )
        containers = [c for c in result2.stdout.strip().split("\n") if c and "mongo" in c.lower()]

    if not containers:
        print("Error: no running MongoDB container found.")
        sys.exit(1)

    subprocess.run(["docker", "exec", containers[0], "mongosh", "--quiet", "--eval", js], check=True)


# ── 方式 1：pymongo ─────────────────────────────────────────────────────────

def set_admin_via_pymongo(account: str) -> None:
    from datetime import datetime, timezone
    from pymongo import MongoClient

    client = MongoClient(MONGODB_URL)
    db = client[MONGODB_DB]
    now = datetime.now(timezone.utc)

    result = db["users"].update_one(
        {"account": account},
        {"$set": {"role": 1, "updated_at": now}},
    )
    if result.matched_count == 0:
        print(f"Account not found: {account}")
        sys.exit(1)

    print(f"Set {account} as admin (role=1)")
    client.close()


# ── 方式 2：docker exec + mongosh ────────────────────────────────────────────

def set_admin_via_mongosh(account: str) -> None:
    db_name = MONGODB_DB
    js = (
        f'var r = db.getSiblingDB("{db_name}").users.updateOne('
        f'{{account: "{account}"}}, '
        f'{{$set: {{role: 1, updated_at: new Date()}}}}'
        f');'
        f'if (r.matchedCount === 0) {{ print("Account not found: {account}"); }}'
        f'else {{ print("Set {account} as admin (role=1)"); }}'
    )
    _mongosh(js)


# ── 主流程 ──────────────────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/init_admin_user.py <account> [--yes]")
        sys.exit(1)

    account = sys.argv[1].strip()
    if not account:
        print("Account cannot be empty")
        sys.exit(1)

    skip_confirm = "--yes" in sys.argv

    print("MongoDB URL: [loaded from local configuration]")
    print(f"Database:    {MONGODB_DB}")
    print(f"Account:     {account}")

    if not skip_confirm:
        answer = input(f"\nSet {account} as admin? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            print("Cancelled.")
            return

    if _has_pymongo():
        set_admin_via_pymongo(account)
    else:
        set_admin_via_mongosh(account)


if __name__ == "__main__":
    main()
