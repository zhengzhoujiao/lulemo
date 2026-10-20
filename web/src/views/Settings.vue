<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useAuth } from "../stores/auth";
import { useIdentity } from "../stores/identity";
import avatarImage from "../assets/images/avatar.png";
import workOrderIcon from "../assets/images/工单.png";
import logoutIcon from "../assets/images/退出.png";

const router = useRouter();
const { user, fetchMe, logout, isAdmin } = useAuth();
const { activeRole } = useIdentity();
const showLogoutConfirm = ref(false);

onMounted(() => {
  if (!user.value) fetchMe();
});

const identityLabel = computed(() => activeRole.value.label);

const regionText = computed(() => {
  const r = user.value?.region;
  if (!r) return "—";
  const parts = [r.province_name, r.city_name, r.district_name].filter(Boolean);
  return parts.length ? parts.join(" · ") : "—";
});

const joinedText = computed(() => {
  const raw = user.value?.created_at;
  if (!raw) return "—";
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return "—";
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
});

const showVeteranNameplate = computed(() => {
  const seq = user.value?.register_seq;
  return seq != null && seq > 0 && seq <= 100;
});

function goBack() {
  if (window.history.length > 1) {
    router.back();
  } else {
    router.push("/");
  }
}

function handleLogout() {
  logout();
  router.push("/auth");
}

function goWorkOrders() {
  router.push("/work-orders");
}

function goUsers() {
  router.push("/admin/users");
}

function openLogoutConfirm() {
  showLogoutConfirm.value = true;
}

function closeLogoutConfirm() {
  showLogoutConfirm.value = false;
}

function confirmLogout() {
  closeLogoutConfirm();
  handleLogout();
}
</script>

<template>
  <div class="settings-page">
    <!-- 顶部导航 -->
    <header class="settings-topbar">
      <button type="button" class="back-btn" aria-label="返回" @click="goBack">
        <svg viewBox="0 0 24 24" fill="none" width="22" height="22" aria-hidden="true">
          <path d="M14 6l-6 6 6 6" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
      <h1 class="topbar-title">设置</h1>
      <span class="topbar-spacer" aria-hidden="true" />
    </header>

    <div class="settings-body">
      <!-- 学生卡式个人信息 -->
      <section v-if="user" class="student-card-wrap" aria-label="个人信息">
        <article class="student-card">
          <div class="card-blob card-blob-1" aria-hidden="true" />
          <div class="card-blob card-blob-2" aria-hidden="true" />

          <div class="card-header">
            <div class="school-block">
              <p class="school-name">噜了么身份证</p>
            </div>
            <span v-if="user.register_seq > 0" class="student-no">
              NO. {{ user.register_seq }}
            </span>
          </div>

          <div class="card-body">
            <div class="photo-box">
              <img :src="avatarImage" alt="头像" class="photo-avatar" />
            </div>
            <div class="profile-block">
              <div class="profile-field">
                <span class="field-label">昵称</span>
                <div class="field-value field-value-name">
                  <span class="field-val-main">{{ user.display_name }}</span>
                  <span v-if="showVeteranNameplate" class="nameplate" aria-label="内测级元老">
                    <span class="nameplate-shine" aria-hidden="true" />
                    内测级元老
                  </span>
                </div>
              </div>
              <div class="profile-field">
                <span class="field-label">账号</span>
                <span class="field-value">{{ user.account }}</span>
              </div>
              <div class="profile-field">
                <span class="field-label">身份</span>
                <span class="field-value">{{ identityLabel }}</span>
              </div>
              <div class="profile-field">
                <span class="field-label">地区</span>
                <span class="field-value">{{ regionText }}</span>
              </div>
            </div>
          </div>

          <div class="card-footer">
            <div class="footer-item">
              <span class="footer-label">开证日期</span>
              <span class="footer-val">{{ joinedText }}</span>
            </div>
            <div class="footer-divider" aria-hidden="true" />
            <div class="footer-item footer-item-right">
              <span class="footer-label">卡号</span>
              <span class="footer-val mono">{{ user.user_id.slice(-12).toUpperCase() }}</span>
            </div>
          </div>

          <div class="card-hole" aria-hidden="true" />
        </article>
      </section>

      <p v-else class="busy-hint">加载中…</p>

      <section class="menu-card" aria-label="设置菜单">
        <button type="button" class="menu-item" @click="goWorkOrders">
          <span class="menu-content">
            <img :src="workOrderIcon" alt="" class="menu-icon" width="20" height="20" />
            <span class="menu-main">
              <span class="menu-text">工单</span>
              <span class="menu-meta">内测阶段欢迎提交任何问题</span>
            </span>
          </span>
          <span class="menu-arrow" aria-hidden="true">›</span>
        </button>
        <button v-if="isAdmin" type="button" class="menu-item" @click="goUsers">
          <span class="menu-content">
            <svg viewBox="0 0 24 24" fill="none" width="20" height="20" class="menu-icon-svg" aria-hidden="true">
              <circle cx="12" cy="8" r="4" stroke="currentColor" stroke-width="1.8"/>
              <path d="M4 20c0-4.418 3.582-8 8-8s8 3.582 8 8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
            </svg>
            <span class="menu-main">
              <span class="menu-text">用户</span>
              <span class="menu-meta">查看所有注册用户</span>
            </span>
          </span>
          <span class="menu-arrow" aria-hidden="true">›</span>
        </button>
        <button type="button" class="menu-item menu-item-danger" @click="openLogoutConfirm">
          <span class="menu-content">
            <img :src="logoutIcon" alt="" class="menu-icon" width="20" height="20" />
            <span class="menu-text">退出</span>
          </span>
          <span class="menu-arrow" aria-hidden="true">›</span>
        </button>
      </section>
    </div>

    <transition name="fade">
      <div v-if="showLogoutConfirm" class="confirm-mask" @click.self="closeLogoutConfirm">
        <div class="confirm-dialog" role="dialog" aria-modal="true" aria-label="退出确认">
          <h3 class="confirm-title">确认退出登录？</h3>
          <p class="confirm-desc">退出后需要重新登录才能继续使用。</p>
          <div class="confirm-actions">
            <button type="button" class="confirm-btn ghost" @click="closeLogoutConfirm">取消</button>
            <button type="button" class="confirm-btn danger" @click="confirmLogout">确认退出</button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.settings-page {
  min-height: 100%;
  max-width: 560px;
  margin: 0 auto;
  padding-bottom: calc(24px + var(--safe-bottom, 0px));
}

.settings-topbar {
  position: sticky;
  top: 0;
  z-index: 10;
  display: grid;
  grid-template-columns: 40px 1fr auto;
  align-items: center;
  gap: 10px;
  padding: calc(10px + var(--safe-top, 0px)) 12px 10px;
  background: rgba(241, 245, 249, 0.92);
  backdrop-filter: blur(16px) saturate(1.4);
  -webkit-backdrop-filter: blur(16px) saturate(1.4);
  border-bottom: 1px solid var(--card-border);
}

.back-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: var(--text);
  -webkit-tap-highlight-color: transparent;
}

.back-btn:active {
  background: rgba(0, 0, 0, 0.06);
}

.topbar-title {
  margin: 0;
  font-size: 17px;
  font-weight: 800;
  color: var(--text);
}

.topbar-spacer {
  width: 36px;
}

.settings-body {
  padding: 10px 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.busy-hint {
  margin: 0;
  text-align: center;
  color: var(--muted);
  font-size: 14px;
}

/* ── 冰蓝微光 ── */
.student-card-wrap {
  padding: 4px 2px 8px;
}

.student-card {
  position: relative;
  border-radius: 22px;
  overflow: hidden;
  background: linear-gradient(155deg, #e8f2fa 0%, #dce8f5 48%, #e4f0f9 100%);
  border: 1px solid rgba(147, 186, 224, 0.55);
  box-shadow:
    0 10px 26px rgba(44, 74, 110, 0.1),
    0 0 0 1px rgba(190, 218, 245, 0.45),
    0 1px 3px rgba(61, 106, 158, 0.08);
  transform: rotate(-0.6deg);
}

.card-blob {
  position: absolute;
  border-radius: 50%;
  pointer-events: none;
}

.card-blob-1 {
  width: 120px;
  height: 120px;
  top: -40px;
  right: -30px;
  background: rgba(100, 160, 220, 0.16);
}

.card-blob-2 {
  width: 80px;
  height: 80px;
  bottom: 48px;
  left: -24px;
  background: rgba(140, 190, 235, 0.2);
}

.card-header {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 16px 18px 12px;
  background: linear-gradient(
    108deg,
    #2c4a6e 0%,
    #345a82 45%,
    #3d6a9e 100%
  );
  color: #eef6fc;
  box-shadow: inset 0 -1px 0 rgba(140, 190, 255, 0.18);
}

.school-block {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.school-mark {
  font-size: 28px;
  line-height: 1;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.15));
}

.school-name {
  margin: 0;
  font-size: 16px;
  font-weight: 900;
  letter-spacing: 0.06em;
  color: inherit;
}

.nameplate {
  position: relative;
  overflow: hidden;
  align-self: flex-start;
  flex-shrink: 0;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.08em;
  color: #8b6914;
  background: linear-gradient(
    180deg,
    #fff8e7 0%,
    #f5e6b8 45%,
    #ecd78a 100%
  );
  border: 1px solid #c9a227;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.65),
    inset 0 -1px 0 rgba(139, 105, 20, 0.12),
    0 1px 4px rgba(139, 105, 20, 0.18);
  text-shadow: 0 1px 0 rgba(255, 255, 255, 0.45);
}

.nameplate-shine {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    105deg,
    transparent 0%,
    transparent 18%,
    rgba(255, 255, 255, 0.45) 42%,
    rgba(255, 255, 255, 0.55) 50%,
    rgba(255, 255, 255, 0.45) 58%,
    transparent 82%,
    transparent 100%
  );
  transform: translateX(-120%);
  animation: nameplate-shimmer 2.5s ease-in-out infinite;
  pointer-events: none;
}

@keyframes nameplate-shimmer {
  0%,
  40% {
    transform: translateX(-120%);
  }
  100% {
    transform: translateX(120%);
  }
}

.school-en {
  margin: 2px 0 0;
  font-size: 10px;
  font-weight: 600;
  opacity: 0.85;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.student-no {
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 800;
  padding: 5px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
  border: 1px solid rgba(180, 220, 255, 0.22);
  color: inherit;
  font-variant-numeric: tabular-nums;
}

.card-body {
  position: relative;
  display: flex;
  gap: 16px;
  padding: 18px 18px 14px;
  align-items: flex-start;
}

.photo-box {
  position: relative;
  flex-shrink: 0;
  width: 78px;
  height: 96px;
  border-radius: 14px;
  background: linear-gradient(180deg, #f0f7fc 0%, #e4f0fa 100%);
  border: 1px solid rgba(120, 170, 220, 0.42);
  box-shadow:
    0 2px 10px rgba(44, 74, 110, 0.07),
    inset 0 1px 0 rgba(255, 255, 255, 0.75);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  overflow: hidden;
}

.photo-box::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, transparent 65%, rgba(61, 106, 158, 0.07) 100%);
  pointer-events: none;
}

.photo-avatar {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: top center;
  display: block;
}

.profile-block {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-top: 2px;
}

.profile-field {
  display: flex;
  align-items: baseline;
  gap: 10px;
  min-width: 0;
}

.field-label {
  flex-shrink: 0;
  width: 2.4em;
  font-size: 11px;
  color: var(--muted);
  font-weight: 600;
}

.field-value {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  font-weight: 700;
  color: var(--text);
  line-height: 1.4;
  word-break: break-all;
}

.field-value-name {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.field-val-main {
  font-size: 13px;
  font-weight: 900;
  line-height: 1.25;
}

.card-footer {
  position: relative;
  display: flex;
  align-items: center;
  margin: 0 14px 14px;
  padding: 10px 14px;
  border-radius: 14px;
  background: rgba(232, 242, 250, 0.92);
  border: 1px dashed rgba(120, 170, 220, 0.48);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.65);
}

.footer-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.footer-item-right {
  align-items: flex-end;
  text-align: right;
}

.footer-label {
  font-size: 10px;
  color: var(--muted);
  font-weight: 600;
}

.footer-val {
  font-size: 12px;
  font-weight: 800;
  color: var(--text);
}

.footer-val.mono {
  font-family: ui-monospace, monospace;
  letter-spacing: 0.08em;
  font-size: 11px;
}

.footer-divider {
  width: 1px;
  height: 28px;
  background: rgba(100, 150, 210, 0.25);
  margin: 0 12px;
  flex-shrink: 0;
}

.card-hole {
  position: absolute;
  top: 52px;
  left: 14px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #cce0f0;
  box-shadow: inset 0 1px 2px rgba(44, 74, 110, 0.14);
  opacity: 0.85;
}

.menu-card {
  border-radius: 14px;
  border: 1px solid var(--card-border);
  background: var(--card);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
  overflow: hidden;
}

.menu-item {
  width: 100%;
  border: none;
  border-bottom: 1px solid var(--card-border);
  background: transparent;
  padding: 16px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  font-size: 17px;
  color: var(--text);
  -webkit-tap-highlight-color: transparent;
}

.menu-item:last-child {
  border-bottom: none;
}

.menu-item:active {
  background: rgba(15, 23, 42, 0.04);
}

.menu-item-danger {
  color: var(--danger);
}

.menu-text {
  font-size: 14px;
  font-weight: 500;
}

.menu-content {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.menu-icon {
  width: 20px;
  height: 20px;
  object-fit: contain;
  flex-shrink: 0;
}

.menu-icon-svg {
  flex-shrink: 0;
  color: var(--muted);
}

.menu-main {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
}

.menu-meta {
  font-size: 12px;
  color: var(--muted);
  line-height: 1.3;
  min-width: 0;
}

.menu-arrow {
  color: #94a3b8;
  font-size: 20px;
  line-height: 1;
}

.confirm-mask {
  position: fixed;
  inset: 0;
  z-index: 30;
  background: rgba(15, 23, 42, 0.38);
  display: grid;
  place-items: center;
  padding: 18px;
}

.confirm-dialog {
  width: min(100%, 340px);
  border-radius: 16px;
  background: #fff;
  border: 1px solid var(--card-border);
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.24);
  padding: 18px 16px 14px;
}

.confirm-title {
  margin: 0;
  font-size: 17px;
  font-weight: 700;
  color: var(--text);
}

.confirm-desc {
  margin: 8px 0 0;
  font-size: 13px;
  line-height: 1.6;
  color: var(--muted);
}

.confirm-actions {
  margin-top: 14px;
  display: flex;
  gap: 10px;
}

.confirm-btn {
  flex: 1;
  width: 100%;
  border-radius: 10px;
  border: 1px solid var(--card-border);
  background: #fff;
  color: var(--text);
  font-size: 14px;
  font-weight: 700;
  padding: 10px 12px;
  -webkit-tap-highlight-color: transparent;
}

.confirm-btn.ghost {
  background: rgba(15, 23, 42, 0.02);
}

.confirm-btn.danger {
  color: #fff;
  border-color: rgba(239, 68, 68, 0.85);
  background: rgba(239, 68, 68, 0.9);
}

.confirm-btn:active {
  transform: translateY(1px);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.18s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
