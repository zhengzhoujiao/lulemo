<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAuth, type UserRegionPayload } from "../stores/auth";
import { ApiError } from "../api/client";
import { regionData } from "element-china-area-data";
import RegionPicker from "../components/RegionPicker.vue";
import { toSixDigitAdcode } from "../utils/regionAdcode";
import { validateAccount, validateNickname, validatePassword } from "../utils/userValidation";

type Mode = "login" | "register";

interface AreaItem {
  value: string;
  label: string;
  children?: AreaItem[];
}

const provinces = regionData as unknown as AreaItem[];

const router = useRouter();
const { login, register } = useAuth();

const mode = ref<Mode>("login");
const account = ref("");
const nickname = ref("");
const password = ref("");
const confirmPassword = ref("");
const errorMsg = ref("");
const loading = ref(false);

const provinceCode = ref("");
const cityCode = ref("");
const districtCode = ref("");

function buildRegionPayload(): UserRegionPayload | null {
  const pItem = provinces.find((x) => x.value === provinceCode.value);
  const cItem = pItem?.children?.find((x) => x.value === cityCode.value);
  const dItem = cItem?.children?.find((x) => x.value === districtCode.value);
  if (!pItem || !cItem || !dItem) return null;
  return {
    province_code: toSixDigitAdcode(pItem.value),
    city_code: toSixDigitAdcode(cItem.value),
    district_code: toSixDigitAdcode(dItem.value),
    province_name: pItem.label,
    city_name: cItem.label,
    district_name: dItem.label,
  };
}

function switchMode(m: Mode) {
  mode.value = m;
  errorMsg.value = "";
  password.value = "";
  confirmPassword.value = "";
  nickname.value = "";
  provinceCode.value = "";
  cityCode.value = "";
  districtCode.value = "";
}

async function submit() {
  errorMsg.value = "";

  if (!account.value.trim() || !password.value) {
    errorMsg.value = "请填写账号和密码";
    return;
  }

  if (mode.value === "register") {
    const accountErr = validateAccount(account.value);
    if (accountErr) {
      errorMsg.value = accountErr;
      return;
    }
    const nicknameErr = validateNickname(nickname.value);
    if (nicknameErr) {
      errorMsg.value = nicknameErr;
      return;
    }
    const passwordErr = validatePassword(password.value);
    if (passwordErr) {
      errorMsg.value = passwordErr;
      return;
    }
    if (password.value !== confirmPassword.value) {
      errorMsg.value = "两次密码不一致";
      return;
    }
    const reg = buildRegionPayload();
    if (!reg) {
      errorMsg.value = "请选择完整的省·市·区";
      return;
    }
  } else {
    if (account.value.trim().length < 1) {
      errorMsg.value = "请填写账号";
      return;
    }
  }

  loading.value = true;
  try {
    if (mode.value === "login") {
      await login(account.value.trim(), password.value);
    } else {
      const reg = buildRegionPayload();
      if (!reg) throw new Error("请选择省市区");
      await register(account.value.trim(), nickname.value.trim(), password.value, reg);
    }
    router.replace("/");
  } catch (e) {
    if (e instanceof ApiError) {
      if (e.status === 401) errorMsg.value = "账号或密码错误";
      else if (e.status === 409) errorMsg.value = "账号已被占用，换一个试试";
      else if (e.status === 422)
        errorMsg.value =
          e.detail?.length ? String(e.detail) : "信息格式有误，请检查账号、昵称、密码与地区";
      else errorMsg.value = e.detail || "请求失败，请稍后重试";
    } else {
      errorMsg.value = "网络异常，请检查连接后重试";
    }
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="auth-page">
    <div class="auth-card">
      <!-- Logo / 标题 -->
      <div class="brand">
        <h1 class="brand-name">噜了么</h1>
        <p class="brand-sub">男性健康自我管理工具</p>
      </div>

      <!-- 切换 Tab -->
      <div class="tabs" role="tablist">
        <button
          type="button"
          role="tab"
          class="tab"
          :class="{ active: mode === 'login' }"
          @click="switchMode('login')"
        >
          登录
        </button>
        <button
          type="button"
          role="tab"
          class="tab"
          :class="{ active: mode === 'register' }"
          @click="switchMode('register')"
        >
          注册
        </button>
      </div>

      <!-- 表单 -->
      <form class="form" autocomplete="off" @submit.prevent="submit">
        <div class="field">
          <label class="label" for="auth-account">账号</label>
          <input
            id="auth-account"
            name="lulemo-account"
            v-model="account"
            type="text"
            class="input"
            placeholder="3~20 位，字母/数字/中文"
            autocomplete="off"
            autocapitalize="off"
            autocorrect="off"
            spellcheck="false"
            :disabled="loading"
            maxlength="20"
          />
        </div>

        <transition name="slide-down">
          <div v-if="mode === 'register'" class="field">
            <label class="label" for="auth-nickname">昵称</label>
            <input
              id="auth-nickname"
              name="lulemo-nickname"
              v-model="nickname"
              type="text"
              class="input"
              placeholder="1~24 位，字母/数字/中文"
              autocomplete="off"
              :disabled="loading"
              maxlength="24"
            />
          </div>
        </transition>

        <div class="field">
          <label class="label" for="auth-password">密码</label>
          <input
            id="auth-password"
            name="lulemo-password"
            v-model="password"
            type="password"
            class="input"
            placeholder="至少 8 位"
            autocomplete="off"
            :disabled="loading"
            maxlength="64"
          />
        </div>

        <transition name="slide-down">
          <div v-if="mode === 'register'" class="field">
            <label class="label" for="auth-confirm">确认密码</label>
            <input
              id="auth-confirm"
              name="lulemo-password-confirm"
              v-model="confirmPassword"
              type="password"
              class="input"
              placeholder="再次输入密码"
              autocomplete="off"
              :disabled="loading"
              maxlength="64"
            />
          </div>
        </transition>

        <transition name="slide-down">
          <div v-if="mode === 'register'" class="region-block">
            <p class="region-label">所在地区（必选）</p>
            <RegionPicker
              v-model:province-code="provinceCode"
              v-model:city-code="cityCode"
              v-model:district-code="districtCode"
              :disabled="loading"
            />
          </div>
        </transition>

        <!-- 错误提示 -->
        <transition name="fade">
          <p v-if="errorMsg" class="error-msg" role="alert">{{ errorMsg }}</p>
        </transition>

        <button type="submit" class="submit-btn" :disabled="loading">
          <span v-if="loading" class="spinner" aria-hidden="true" />
          {{ loading ? "请稍候…" : mode === "login" ? "登录" : "注册并登录" }}
        </button>
      </form>

      <p class="footer-note">开启您自我管理之旅，点滴记录，从仪式感开始。</p>
    </div>
  </div>
</template>

<style scoped>
.auth-page {
  height: 100%;
  min-height: 100vh;
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 10px;
  box-sizing: border-box;
}

.auth-card {
  width: min(420px, 100%);
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  border-radius: 12px;
  padding: 28px 22px 22px;
  background: var(--card);
  border: 1px solid var(--card-border);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.10);
  overflow: hidden;
}

/* ── Brand ── */
.brand {
  text-align: center;
  margin-bottom: 22px;
  flex-shrink: 0;
}

.brand-name {
  margin: 0 0 4px;
  font-size: 26px;
  font-weight: 900;
  letter-spacing: 0.04em;
  color: var(--accent-a);
}

.brand-sub {
  margin: 0;
  font-size: 12px;
  color: var(--muted);
}

/* ── Tabs ── */
.tabs {
  display: flex;
  gap: 0;
  background: rgba(0, 0, 0, 0.06);
  border-radius: 12px;
  padding: 4px;
  margin-bottom: 20px;
  flex-shrink: 0;
}

.tab {
  flex: 1;
  padding: 9px;
  border-radius: 9px;
  font-size: 14px;
  font-weight: 600;
  border: none;
  background: transparent;
  color: var(--muted);
  transition: all 0.18s ease;
}

.tab.active {
  background: rgba(2, 132, 199, 0.12);
  color: var(--text);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

/* ── Form ── */
.form {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.label {
  font-size: 12px;
  color: var(--muted);
  font-weight: 600;
  letter-spacing: 0.04em;
}

.input {
  width: 100%;
  padding: 11px 14px;
  border-radius: 12px;
  border: 1px solid var(--card-border);
  background: rgba(0, 0, 0, 0.04);
  color: var(--text);
  font-size: 15px;
  outline: none;
  transition: border-color 0.18s, box-shadow 0.18s;
}

.input:focus {
  border-color: rgba(2, 132, 199, 0.5);
  box-shadow: 0 0 0 3px rgba(2, 132, 199, 0.10);
}

.region-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.region-label {
  margin: 0;
  font-size: 12px;
  color: var(--muted);
  font-weight: 600;
  letter-spacing: 0.04em;
}
.input:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.input::placeholder {
  color: rgba(100, 116, 139, 0.55);
}

/* ── Error ── */
.error-msg {
  margin: 0;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(248, 113, 113, 0.1);
  border: 1px solid rgba(248, 113, 113, 0.25);
  color: var(--danger);
  font-size: 13px;
  line-height: 1.5;
}

/* ── Submit ── */
.submit-btn {
  width: 100%;
  padding: 14px;
  border-radius: 14px;
  border: none;
  background: var(--accent-a);
  color: #fff;
  font-size: 15px;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: opacity 0.2s, transform 0.1s;
  margin-top: 2px;
}

.submit-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  box-shadow: none;
}

.submit-btn:active:not(:disabled) {
  transform: scale(0.98);
}

.spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(4, 18, 10, 0.3);
  border-top-color: rgba(4, 18, 10, 0.9);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
  flex-shrink: 0;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ── Footer ── */
.footer-note {
  margin: 16px 0 0;
  text-align: center;
  font-size: 11px;
  color: var(--muted);
  opacity: 0.75;
  line-height: 1.6;
  flex-shrink: 0;
}

/* ── Transitions ── */
.slide-down-enter-active,
.slide-down-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease, max-height 0.25s ease;
  max-height: 200px;
  overflow: hidden;
}

.slide-down-enter-from,
.slide-down-leave-to {
  opacity: 0;
  transform: translateY(-6px);
  max-height: 0;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
