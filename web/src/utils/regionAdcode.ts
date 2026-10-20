/** 将 element-china-area-data 的 value 转为民政部 6 位 adcode（右侧补 0） */
export function toSixDigitAdcode(code: string): string {
  const digits = code.replace(/\D/g, "");
  if (digits.length >= 6) return digits.slice(0, 6);
  return digits.padEnd(6, "0");
}
