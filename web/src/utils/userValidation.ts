const ALNUM_CN = /^[a-zA-Z0-9\u4e00-\u9fff]+$/;
const HAS_CN = /[\u4e00-\u9fff]/;

export function validateAccount(v: string): string | null {
  const s = v.trim();
  if (s.length < 3) return "账号至少 3 个字符";
  if (!ALNUM_CN.test(s)) return "账号只允许字母、数字或中文";
  return null;
}

export function validateNickname(v: string): string | null {
  const s = v.trim();
  if (!s) return "请填写昵称";
  if (!ALNUM_CN.test(s)) return "昵称只允许字母、数字或中文";
  return null;
}

export function validatePassword(v: string): string | null {
  if (v.length < 8) return "密码至少 8 位";
  if (HAS_CN.test(v)) return "密码不支持中文";
  return null;
}
