"""账号、昵称、密码格式校验。"""

import re

ALNUM_CN_RE = re.compile(r"^[a-zA-Z0-9\u4e00-\u9fff]+$")
CN_RE = re.compile(r"[\u4e00-\u9fff]")


def validate_account(v: str) -> str:
    s = v.strip()
    if not ALNUM_CN_RE.match(s):
        raise ValueError("账号只允许字母、数字或中文")
    return s


def validate_nickname(v: str) -> str:
    s = v.strip()
    if not s or not ALNUM_CN_RE.match(s):
        raise ValueError("昵称只允许字母、数字或中文")
    return s


def validate_password(v: str) -> str:
    if len(v) < 8:
        raise ValueError("密码至少 8 位")
    if CN_RE.search(v):
        raise ValueError("密码不支持中文")
    return v
