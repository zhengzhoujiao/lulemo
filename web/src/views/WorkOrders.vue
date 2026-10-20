<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import type { WorkOrderItem, WorkOrderReplyItem } from "../stores/workOrders";
import { useWorkOrders } from "../stores/workOrders";

const router = useRouter();
const {
  loading,
  creating,
  replying,
  isAdmin,
  mine,
  pending,
  processed,
  pendingCount,
  processedCount,
  fetchDashboard,
  createWorkOrder,
  fetchReplies,
  createReply,
} = useWorkOrders();

const activeTab = ref<"pending" | "processed">("pending");
const showCreateModal = ref(false);
const showDetailModal = ref(false);
const detailLoading = ref(false);
const detailErr = ref("");
const detailReplyText = ref("");
const currentOrder = ref<WorkOrderItem | null>(null);
const currentReplies = ref<WorkOrderReplyItem[]>([]);
const subject = ref("");
const content = ref("");
const submitErr = ref("");

const displayedAdminList = computed(() =>
  activeTab.value === "pending" ? pending.value : processed.value,
);

const canSubmit = computed(
  () => subject.value.trim().length > 0 && content.value.trim().length > 0 && !creating.value,
);
const canReply = computed(() => detailReplyText.value.trim().length > 0 && !replying.value);

onMounted(() => {
  fetchDashboard();
});

function goBack() {
  if (window.history.length > 1) {
    router.back();
  } else {
    router.push("/settings");
  }
}

function openCreateModal() {
  submitErr.value = "";
  showCreateModal.value = true;
}

function closeCreateModal() {
  showCreateModal.value = false;
  subject.value = "";
  content.value = "";
  submitErr.value = "";
}

async function openDetailModal(order: WorkOrderItem) {
  showDetailModal.value = true;
  detailLoading.value = true;
  detailErr.value = "";
  detailReplyText.value = "";
  currentOrder.value = order;
  currentReplies.value = [];
  try {
    currentReplies.value = await fetchReplies(order.work_order_id);
  } catch (e) {
    detailErr.value = e instanceof Error ? e.message : "加载工单详情失败";
  } finally {
    detailLoading.value = false;
  }
}

function closeDetailModal() {
  showDetailModal.value = false;
  currentOrder.value = null;
  currentReplies.value = [];
  detailReplyText.value = "";
  detailErr.value = "";
}

async function submitWorkOrder() {
  if (!canSubmit.value) return;
  submitErr.value = "";
  try {
    await createWorkOrder(subject.value.trim(), content.value.trim());
    closeCreateModal();
  } catch (e) {
    submitErr.value = e instanceof Error ? e.message : "提交失败，请稍后再试";
  }
}

async function submitReply() {
  if (!currentOrder.value || !canReply.value) return;
  detailErr.value = "";
  try {
    await createReply(currentOrder.value.work_order_id, detailReplyText.value.trim());
    detailReplyText.value = "";
    currentReplies.value = await fetchReplies(currentOrder.value.work_order_id);
  } catch (e) {
    detailErr.value = e instanceof Error ? e.message : "回复失败，请稍后再试";
  }
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "-";
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  return `${y}-${m}-${day} ${hh}:${mm}`;
}
</script>

<template>
  <div class="work-orders-page">
    <header class="work-orders-topbar">
      <button type="button" class="back-btn" aria-label="返回" @click="goBack">
        <svg viewBox="0 0 24 24" fill="none" width="22" height="22" aria-hidden="true">
          <path d="M14 6l-6 6 6 6" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </button>
      <h1 class="topbar-title">{{ isAdmin ? "工单列表" : "我的工单" }}</h1>
      <button v-if="!isAdmin" type="button" class="create-btn" @click="openCreateModal">+ 新建工单</button>
      <span v-else class="topbar-spacer" aria-hidden="true" />
    </header>

    <main class="work-orders-main">
      <p v-if="loading" class="busy-hint">加载中...</p>

      <template v-else-if="isAdmin">
        <div class="tabs">
          <button
            type="button"
            class="tab"
            :class="{ active: activeTab === 'pending' }"
            @click="activeTab = 'pending'"
          >
            待处理（{{ pendingCount }}）
          </button>
          <button
            type="button"
            class="tab"
            :class="{ active: activeTab === 'processed' }"
            @click="activeTab = 'processed'"
          >
            已处理（{{ processedCount }}）
          </button>
        </div>

        <section v-if="displayedAdminList.length" class="order-list">
          <article
            v-for="item in displayedAdminList"
            :key="item.work_order_id"
            class="order-card"
            role="button"
            tabindex="0"
            @click="openDetailModal(item)"
            @keydown.enter.prevent="openDetailModal(item)"
          >
            <div class="order-head">
              <h3 class="order-subject">{{ item.subject }}</h3>
              <span class="order-state" :class="item.last_reply_by === 'user' ? 'pending' : 'processed'">
                {{ item.last_reply_by === "user" ? "待处理" : "已处理" }}
              </span>
            </div>
            <p class="order-meta">提交人：{{ item.user_display_name }}</p>
            <p class="order-time">最后更新：{{ formatTime(item.latest_reply_at) }}</p>
          </article>
        </section>
        <p v-else class="empty-hint">当前分组暂无工单</p>
      </template>

      <template v-else>
        <section v-if="mine.length" class="order-list">
          <article
            v-for="item in mine"
            :key="item.work_order_id"
            class="order-card"
            role="button"
            tabindex="0"
            @click="openDetailModal(item)"
            @keydown.enter.prevent="openDetailModal(item)"
          >
            <div class="order-head">
              <h3 class="order-subject">{{ item.subject }}</h3>
              <span class="order-state" :class="item.last_reply_by === 'user' ? 'pending' : 'processed'">
                {{ item.last_reply_by === "user" ? "待处理" : "已处理" }}
              </span>
            </div>
            <p class="order-preview">{{ item.latest_reply_preview || "暂无内容" }}</p>
            <p class="order-time">最后更新：{{ formatTime(item.latest_reply_at) }}</p>
          </article>
        </section>

        <section v-else class="empty-wrap">
          <div class="empty-icon" aria-hidden="true">📄</div>
          <p class="empty-title">暂无工单</p>
          <button type="button" class="empty-action" @click="openCreateModal">创建第一个工单</button>
        </section>
      </template>
    </main>

    <transition name="fade">
      <div v-if="showCreateModal" class="mask" @click.self="closeCreateModal">
        <div class="modal">
          <div class="modal-head">
            <h3 class="modal-title">新建工单</h3>
            <button type="button" class="close-btn" aria-label="关闭" @click="closeCreateModal">×</button>
          </div>
          <label class="field">
            <span class="label">工单主题</span>
            <input v-model="subject" type="text" class="input" maxlength="80" placeholder="请简要描述您的问题" />
          </label>
          <label class="field">
            <span class="label">详细描述</span>
            <textarea
              v-model="content"
              class="textarea"
              maxlength="2000"
              placeholder="请详细说明您遇到的问题或需要咨询的内容..."
            />
          </label>
          <p v-if="submitErr" class="submit-err">{{ submitErr }}</p>
          <div class="modal-actions">
            <button type="button" class="action-btn ghost" @click="closeCreateModal">取消</button>
            <button type="button" class="action-btn primary" :disabled="!canSubmit" @click="submitWorkOrder">
              {{ creating ? "提交中..." : "提交" }}
            </button>
          </div>
        </div>
      </div>
    </transition>

    <transition name="fade">
      <div v-if="showDetailModal && currentOrder" class="mask" @click.self="closeDetailModal">
        <div class="modal detail-modal">
          <div class="modal-head">
            <h3 class="modal-title">工单详情</h3>
            <button type="button" class="close-btn" aria-label="关闭" @click="closeDetailModal">×</button>
          </div>

          <div class="detail-header">
            <p class="detail-subject">{{ currentOrder.subject }}</p>
            <p class="detail-meta">
              提交人：{{ currentOrder.user_display_name }} · {{ formatTime(currentOrder.created_at) }}
            </p>
          </div>

          <div class="reply-list-wrap">
            <p v-if="detailLoading" class="busy-hint">加载会话中...</p>
            <p v-else-if="detailErr" class="submit-err">{{ detailErr }}</p>
            <div v-else-if="currentReplies.length" class="reply-list">
              <article
                v-for="reply in currentReplies"
                :key="reply.reply_id"
                class="reply-item"
                :class="reply.sender_role === 'admin' ? 'reply-staff' : 'reply-user'"
              >
                <div class="reply-head">
                  <span class="reply-author">
                    {{ reply.sender_role === "admin" ? "管理员" : "用户" }} · {{ reply.sender_display_name }}
                  </span>
                  <span class="reply-time">{{ formatTime(reply.created_at) }}</span>
                </div>
                <p class="reply-content">{{ reply.content }}</p>
              </article>
            </div>
            <p v-else class="empty-hint">暂无回复</p>
          </div>

          <div class="reply-editor">
            <textarea
              v-model="detailReplyText"
              class="textarea"
              maxlength="2000"
              placeholder="输入回复内容..."
            />
            <div class="modal-actions">
              <button type="button" class="action-btn ghost" @click="closeDetailModal">关闭</button>
              <button type="button" class="action-btn primary" :disabled="!canReply" @click="submitReply">
                {{ replying ? "发送中..." : "发送回复" }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.work-orders-page {
  min-height: 100vh;
  min-height: 100dvh;
  max-width: 560px;
  margin: 0 auto;
}

.work-orders-topbar {
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
}

.topbar-title {
  margin: 0;
  font-size: 17px;
  font-weight: 800;
  color: var(--text);
}

.create-btn {
  border: none;
  border-radius: 10px;
  padding: 8px 12px;
  background: var(--accent-b);
  color: #fff;
  font-size: 14px;
  font-weight: 700;
}

.topbar-spacer {
  width: 36px;
}

.work-orders-main {
  padding: 12px;
}

.busy-hint,
.empty-hint {
  margin: 20px 0 0;
  text-align: center;
  color: var(--muted);
}

.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.tab {
  flex: 1;
  border-radius: 10px;
  border: 1px solid var(--card-border);
  background: var(--card);
  color: var(--text);
  font-weight: 700;
  padding: 10px 12px;
}

.tab.active {
  color: var(--accent-b);
  border-color: color-mix(in srgb, var(--accent-b) 38%, transparent);
  background: color-mix(in srgb, var(--accent-b) 10%, transparent);
}

.order-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.order-card {
  border-radius: 12px;
  border: 1px solid var(--card-border);
  background: var(--card);
  padding: 12px;
  cursor: pointer;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.order-card:active {
  transform: translateY(1px);
}

.order-card:hover {
  border-color: color-mix(in srgb, var(--accent-b) 30%, transparent);
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.08);
}

.order-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.order-subject {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
}

.order-state {
  flex-shrink: 0;
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 700;
}

.order-state.pending {
  color: #d97706;
  background: rgba(245, 158, 11, 0.15);
}

.order-state.processed {
  color: #16a34a;
  background: rgba(34, 197, 94, 0.14);
}

.order-meta,
.order-preview,
.order-time {
  margin: 4px 0 0;
  font-size: 13px;
}

.order-meta,
.order-time {
  color: var(--muted);
}

.order-preview {
  color: var(--text);
  line-height: 1.5;
}

.empty-wrap {
  padding: 72px 12px;
  text-align: center;
}

.empty-icon {
  font-size: 42px;
  line-height: 1;
}

.empty-title {
  margin: 12px 0 0;
  font-size: 24px;
  font-weight: 700;
  color: var(--text);
}

.empty-action {
  margin-top: 10px;
  border: none;
  background: transparent;
  color: var(--accent-b);
  font-size: 18px;
  font-weight: 700;
}

.mask {
  position: fixed;
  inset: 0;
  z-index: 40;
  background: rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(1px);
  display: grid;
  place-items: center;
  padding: 16px;
}

.modal {
  width: min(100%, 460px);
  border-radius: 16px;
  background: #fff;
  border: 1px solid var(--card-border);
  box-shadow: 0 20px 48px rgba(15, 23, 42, 0.2);
  padding: 18px 14px 14px;
}

.modal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.modal-title {
  margin: 0;
  font-size: 24px;
  font-weight: 800;
  color: var(--text);
}

.close-btn {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: #94a3b8;
  font-size: 26px;
  line-height: 1;
}

.field {
  display: block;
  margin-top: 12px;
}

.label {
  display: block;
  margin-bottom: 6px;
  color: var(--text);
  font-size: 14px;
  font-weight: 700;
}

.input,
.textarea {
  width: 100%;
  border-radius: 10px;
  border: 1px solid #cbd5e1;
  background: #f8fafc;
  color: var(--text);
  padding: 10px 12px;
  font-size: 14px;
  box-sizing: border-box;
}

.textarea {
  min-height: 120px;
  resize: vertical;
}

.submit-err {
  margin: 10px 0 0;
  color: var(--danger);
  font-size: 13px;
}

.modal-actions {
  display: flex;
  gap: 10px;
  margin-top: 14px;
}

.action-btn {
  flex: 1;
  border-radius: 10px;
  border: 1px solid #cbd5e1;
  background: #f8fafc;
  color: var(--text);
  padding: 10px 12px;
  font-size: 15px;
  font-weight: 700;
}

.action-btn.primary {
  border-color: var(--accent-b);
  background: var(--accent-b);
  color: #fff;
}

.action-btn:disabled {
  background: #cbd5e1;
  border-color: #cbd5e1;
  color: rgba(255, 255, 255, 0.8);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.detail-modal {
  max-height: min(88vh, 760px);
  max-height: min(88dvh, 760px);
  display: flex;
  flex-direction: column;
}

.detail-header {
  margin-top: 8px;
  border: 1px solid var(--card-border);
  border-radius: 10px;
  background: #f8fafc;
  padding: 10px 12px;
}

.detail-subject {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
}

.detail-meta {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--muted);
}

.reply-list-wrap {
  margin-top: 12px;
  flex: 1;
  min-height: 180px;
  max-height: 300px;
  overflow: auto;
}

.reply-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.reply-item {
  border: 1px solid var(--card-border);
  border-radius: 10px;
  padding: 10px;
}

.reply-item.reply-user {
  background: #fff;
}

.reply-item.reply-staff {
  background: color-mix(in srgb, var(--accent-b) 8%, transparent);
  border-color: color-mix(in srgb, var(--accent-b) 28%, transparent);
}

.reply-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.reply-author {
  font-size: 12px;
  font-weight: 700;
  color: var(--text);
}

.reply-time {
  font-size: 11px;
  color: var(--muted);
}

.reply-content {
  margin: 8px 0 0;
  font-size: 13px;
  color: var(--text);
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

.reply-editor {
  margin-top: 10px;
}
</style>
