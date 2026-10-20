<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiFetch, getStoredToken } from "../../api/client";
import { useAuth } from "../../stores/auth";
import AppTopBar from "../../components/AppTopBar.vue";

interface TeamInfo {
  team_id: string;
  name: string;
  member_count: number;
  owner_user_id: string;
  team_type: string;
  description: string;
  is_mine: boolean;
}

interface TeamDetailResponse {
  team: TeamInfo;
}

interface ChatMessage {
  type: string;
  message_id: string;
  team_id: string;
  user_id: string;
  display_name: string;
  content: string;
  created_at: string;
}

const route = useRoute();
const router = useRouter();
const { user } = useAuth();

const teamId = route.params.teamId as string;
const team = ref<TeamInfo | null>(null);
const messages = ref<ChatMessage[]>([]);
const inputText = ref("");
const wsStatus = ref<"connecting" | "connected" | "disconnected">("connecting");
const reconnectAttempt = ref(0);
const messagesEl = ref<HTMLElement | null>(null);
const hasMore = ref(false);
const loadingMore = ref(false);

const BASE_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000/api/v1";

let ws: WebSocket | null = null;

// ─── 当前用户 ────────────────────────────────────────────────────────────────

const myUserId = computed(() => user.value?.user_id ?? "");

function isSelf(msg: ChatMessage) {
  return msg.user_id === myUserId.value;
}

// ─── 时间格式化 ───────────────────────────────────────────────────────────────

function fmtTime(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "";
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  return `${hh}:${mm}`;
}

// ─── 滚动控制 ────────────────────────────────────────────────────────────────

async function scrollToBottom(force = false) {
  await nextTick();
  const el = messagesEl.value;
  if (!el) return;
  const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 120;
  if (force || nearBottom) {
    el.scrollTop = el.scrollHeight;
  }
}

function onMessagesScroll() {
  const el = messagesEl.value;
  if (!el || loadingMore.value || !hasMore.value) return;
  // 滚动到顶部附近时加载更多
  if (el.scrollTop < 80) {
    loadMore();
  }
}

// ─── 数据加载 ────────────────────────────────────────────────────────────────

interface MessagesResponse {
  messages: ChatMessage[];
  has_more: boolean;
}

async function loadTeamInfo() {
  try {
    const data = await apiFetch<TeamDetailResponse>(`/teams/${teamId}`);
    team.value = data.team;
  } catch {
    // 失败时保留 null，顶部显示占位
  }
}

async function markMessagesRead() {
  try {
    await apiFetch(`/teams/${teamId}/messages/read`, { method: "POST" });
  } catch {
    // ignore
  }
}

async function loadHistory() {
  try {
    const data = await apiFetch<MessagesResponse>(`/teams/${teamId}/messages?limit=50`);
    messages.value = data.messages;
    hasMore.value = data.has_more;
    await scrollToBottom(true);
    await markMessagesRead();
  } catch {
    // ignore
  }
}

async function loadMore() {
  if (loadingMore.value || !hasMore.value) return;
  const oldest = messages.value[0];
  if (!oldest) return;

  loadingMore.value = true;
  const prevHeight = messagesEl.value?.scrollHeight ?? 0;

  try {
    const before = encodeURIComponent(oldest.created_at);
    const data = await apiFetch<MessagesResponse>(
      `/teams/${teamId}/messages?limit=50&before=${before}`
    );
    messages.value = [...data.messages, ...messages.value];
    hasMore.value = data.has_more;

    // 保持滚动位置，防止新消息插入导致跳动
    await nextTick();
    if (messagesEl.value) {
      messagesEl.value.scrollTop = messagesEl.value.scrollHeight - prevHeight;
    }
  } catch {
    // ignore
  } finally {
    loadingMore.value = false;
  }
}

// ─── WebSocket ───────────────────────────────────────────────────────────────

const MAX_BACKOFF_MS = 30_000;
const CONNECT_TIMEOUT_MS = 10_000;

let reconnectDelay = 1000;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let connectTimeout: ReturnType<typeof setTimeout> | null = null;
let heartbeatTimer: ReturnType<typeof setInterval> | null = null;
let errorFallbackTimer: ReturnType<typeof setTimeout> | null = null;

function buildWsUrl(): string {
  const token = getStoredToken() ?? "";
  const qs = `token=${encodeURIComponent(token)}`;
  // 开发模式：BASE_URL 是绝对 http(s) 地址
  if (BASE_URL.startsWith("http://") || BASE_URL.startsWith("https://")) {
    const wsBase = BASE_URL.replace(/^https/, "wss").replace(/^http/, "ws");
    return `${wsBase}/teams/${teamId}/ws?${qs}`;
  }
  // 生产模式：BASE_URL 是相对路径，基于当前页面 origin 构建
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}${BASE_URL}/teams/${teamId}/ws?${qs}`;
}

function clearReconnect() {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
}

function clearConnectTimeout() {
  if (connectTimeout) {
    clearTimeout(connectTimeout);
    connectTimeout = null;
  }
}

function clearHeartbeat() {
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer);
    heartbeatTimer = null;
  }
}

function clearErrorFallback() {
  if (errorFallbackTimer) {
    clearTimeout(errorFallbackTimer);
    errorFallbackTimer = null;
  }
}

function scheduleReconnect() {
  clearReconnect();
  clearConnectTimeout();
  clearHeartbeat();
  clearErrorFallback();
  if (reconnectDelay > MAX_BACKOFF_MS) reconnectDelay = MAX_BACKOFF_MS;
  reconnectAttempt.value += 1;
  reconnectTimer = setTimeout(() => {
    reconnectDelay = Math.min(reconnectDelay * 2, MAX_BACKOFF_MS);
    connectWs();
  }, reconnectDelay);
}

function connectWs() {
  clearReconnect();
  clearConnectTimeout();
  clearHeartbeat();
  clearErrorFallback();

  // 如果已有连接，先关闭
  if (ws) {
    try { ws.close(); } catch { /* ignore */ }
    ws = null;
  }

  wsStatus.value = "connecting";

  let url: string;
  try {
    url = buildWsUrl();
  } catch {
    wsStatus.value = "disconnected";
    scheduleReconnect();
    return;
  }

  ws = new WebSocket(url);

  // 连接超时
  connectTimeout = setTimeout(() => {
    if (ws && ws.readyState !== WebSocket.OPEN) {
      try { ws.close(); } catch { /* ignore */ }
    }
  }, CONNECT_TIMEOUT_MS);

  ws.onopen = () => {
    clearConnectTimeout();
    clearErrorFallback();
    wsStatus.value = "connected";
    reconnectDelay = 1000;
    reconnectAttempt.value = 0;
    startHeartbeat();
  };

  ws.onmessage = async (event: MessageEvent) => {
    try {
      const msg = JSON.parse(event.data as string) as ChatMessage;
      if (msg.type === "message") {
        messages.value.push(msg);
        await scrollToBottom();
        if (!isSelf(msg)) {
          await markMessagesRead();
        }
      }
    } catch {
      // ignore
    }
  };

  ws.onclose = () => {
    clearConnectTimeout();
    clearHeartbeat();
    clearErrorFallback();
    ws = null;
    wsStatus.value = "disconnected";
    scheduleReconnect();
  };

  ws.onerror = () => {
    clearConnectTimeout();
    clearHeartbeat();
    // onclose 通常在 onerror 之后触发；但 iOS Safari/WKWebView
    // 在 WebSocket 握手阶段失败时可能不触发 onclose，加兜底定时器
    clearErrorFallback();
    errorFallbackTimer = setTimeout(() => {
      if (wsStatus.value === "connecting") {
        if (ws) {
          try { ws.close(); } catch { /* ignore */ }
          ws = null;
        }
        wsStatus.value = "disconnected";
        scheduleReconnect();
      }
    }, 2000);
  };
}

function startHeartbeat() {
  clearHeartbeat();
  // 定期检查连接是否还活着；浏览器 TCP 层会自行探测断线
  heartbeatTimer = setInterval(() => {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      clearHeartbeat();
      if (ws) {
        try { ws.close(); } catch { /* ignore */ }
      }
    }
  }, 30_000);
}

function reconnect() {
  reconnectDelay = 1000;
  reconnectAttempt.value = 0;
  clearReconnect();
  if (ws) {
    try { ws.close(); } catch { /* ignore */ }
    ws = null;
  }
  clearConnectTimeout();
  clearHeartbeat();
  clearErrorFallback();
  connectWs();
}

// ─── 发送消息 ────────────────────────────────────────────────────────────────

function sendMessage() {
  const text = inputText.value.trim();
  if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;
  ws.send(text);
  inputText.value = "";
}

function onEnterKey(e: KeyboardEvent) {
  if (e.shiftKey) return;
  e.preventDefault();
  sendMessage();
}

// ─── 生命周期 ────────────────────────────────────────────────────────────────

onMounted(async () => {
  await Promise.all([loadTeamInfo(), loadHistory()]);
  connectWs();
});

onUnmounted(() => {
  clearReconnect();
  clearConnectTimeout();
  clearHeartbeat();
  clearErrorFallback();
  if (ws) { try { ws.close(); } catch { /* ignore */ } ws = null; }
  void markMessagesRead();
});
</script>

<template>
  <div class="chat-page">
    <AppTopBar>
      <template #leading>
        <button type="button" class="icon-btn" aria-label="返回" @click="router.back()">
          <svg viewBox="0 0 24 24" fill="none" width="22" height="22" aria-hidden="true">
            <path d="M14 6l-6 6 6 6" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
      </template>

      <template #title>
        <div class="chat-title">
          <span class="chat-title-name">{{ team?.name ?? "…" }}</span>
          <span v-if="team" class="chat-title-count">({{ team.member_count }})</span>
        </div>
      </template>

      <template #trailing>
        <div class="topbar-actions">
          <span
            class="ws-dot"
            :class="wsStatus"
            :title="wsStatus === 'connected' ? '已连接' : wsStatus === 'connecting' ? '连接中' : '已断开'"
          />
          <button
            type="button"
            class="icon-btn"
            aria-label="菜单"
            @click="router.push({ name: 'team-detail', params: { teamId } })"
          >
            <svg viewBox="0 0 24 24" fill="none" width="22" height="22" aria-hidden="true">
              <path d="M4 6h16M4 12h16M4 18h16" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
          </button>
        </div>
      </template>
    </AppTopBar>

    <div class="chat-body">
    <div v-if="wsStatus !== 'connected'" class="reconnect-bar">
      <template v-if="wsStatus === 'connecting'">
        <span>连接中{{ reconnectAttempt > 0 ? `（第 ${reconnectAttempt} 次重试）` : '' }}…</span>
      </template>
      <template v-else>
        <span>连接已断开{{ reconnectAttempt > 0 ? `（已尝试 ${reconnectAttempt} 次）` : '' }}</span>
        <button type="button" class="reconnect-btn" @click="reconnect">重连</button>
      </template>
    </div>

    <!-- ── 消息列表 ── -->
    <main ref="messagesEl" class="messages-area" @scroll="onMessagesScroll">
      <p v-if="loadingMore" class="load-more-hint">加载历史消息…</p>
      <p v-else-if="hasMore" class="load-more-hint">向上滚动加载更多</p>
      <p v-if="messages.length === 0 && !loadingMore" class="empty-hint">暂无消息，快来打个招呼吧</p>

      <div
        v-for="msg in messages"
        :key="msg.message_id"
        class="msg-row"
        :class="{ self: isSelf(msg) }"
      >
        <!-- 他人消息：左侧 -->
        <template v-if="!isSelf(msg)">
          <div class="avatar" aria-hidden="true">{{ msg.display_name.slice(0, 1) }}</div>
          <div class="bubble-wrap">
            <span class="sender-name">{{ msg.display_name }}</span>
            <div class="bubble bubble-other">{{ msg.content }}</div>
            <span class="msg-time">{{ fmtTime(msg.created_at) }}</span>
          </div>
        </template>

        <!-- 自己消息：右侧 -->
        <template v-else>
          <div class="bubble-wrap self-wrap">
            <div class="bubble bubble-self">{{ msg.content }}</div>
            <span class="msg-time self-time">{{ fmtTime(msg.created_at) }}</span>
          </div>
        </template>
      </div>

      <!-- 底部空白，防止最后一条被输入框遮住 -->
      <div class="bottom-spacer" />
    </main>

    <!-- ── 底部输入区 ── -->
    <footer class="input-area">
      <textarea
        v-model="inputText"
        class="chat-input"
        placeholder="输入消息…"
        rows="1"
        :disabled="wsStatus !== 'connected'"
        @keydown.enter.exact="onEnterKey"
      />
      <button
        type="button"
        class="send-btn"
        :disabled="!inputText.trim() || wsStatus !== 'connected'"
        @click="sendMessage"
      >
        发送
      </button>
    </footer>
    </div>
  </div>
</template>

<style scoped>
.chat-page {
  min-height: 100vh;
  min-height: 100dvh;
  min-height: 100svh;
  background: var(--bg);
  position: relative;
}

.chat-body {
  display: flex;
  flex-direction: column;
  height: 100vh;
  height: 100dvh;
  height: 100svh;
  padding-top: calc(var(--app-topbar-h) + var(--safe-top, 0px) + 20px);
  box-sizing: border-box;
}

.icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  background: transparent;
  border-radius: 10px;
  color: var(--text);
  -webkit-tap-highlight-color: transparent;
}

.icon-btn:active {
  background: rgba(0, 0, 0, 0.06);
}

.chat-title {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  font-size: 18px;
  font-weight: 700;
  line-height: 1.2;
}

.chat-title-name {
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chat-title-count {
  flex-shrink: 0;
  color: var(--muted);
}

.topbar-actions {
  position: relative;
  display: flex;
  align-items: center;
  gap: 4px;
}

.ws-dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  transition: background 0.3s;
}
.ws-dot.connected { background: #22c55e; }
.ws-dot.connecting { background: #f59e0b; }
.ws-dot.disconnected { background: #ef4444; }

/* ── 连接状态提示 ── */
.reconnect-bar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 8px 16px;
  background: rgba(245, 158, 11, 0.1);
  border-bottom: 1px solid rgba(245, 158, 11, 0.22);
  font-size: 13px;
  color: #b45309;
  animation: reconnect-pulse 1.8s ease-in-out infinite;
}

@keyframes reconnect-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.reconnect-btn {
  padding: 3px 12px;
  border-radius: 999px;
  border: 1px solid rgba(239, 68, 68, 0.4);
  background: transparent;
  color: var(--danger);
  font-size: 12px;
  font-weight: 700;
  -webkit-tap-highlight-color: transparent;
}

/* ── 消息区 ── */
.messages-area {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 16px 14px 0;
  max-width: 560px;
  width: 100%;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
  scroll-behavior: smooth;
}

.empty-hint {
  margin: auto;
  text-align: center;
  color: var(--muted);
  font-size: 14px;
}

.load-more-hint {
  text-align: center;
  color: var(--muted);
  font-size: 12px;
  padding: 8px 0;
  flex-shrink: 0;
}

.bottom-spacer {
  flex-shrink: 0;
  height: 8px;
}

/* ── 消息行 ── */
.msg-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  max-width: 88%;
}

.msg-row.self {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.avatar {
  flex-shrink: 0;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: var(--card);
  border: 1px solid var(--card-border);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
  color: var(--text);
}

.bubble-wrap {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.self-wrap {
  align-items: flex-end;
}

.sender-name {
  font-size: 11px;
  color: var(--muted);
  font-weight: 600;
  padding-left: 2px;
}

.bubble {
  padding: 9px 13px;
  border-radius: 18px;
  font-size: 14px;
  line-height: 1.55;
  word-break: break-all;
  white-space: pre-wrap;
}

.bubble-other {
  background: var(--card);
  border: 1px solid var(--card-border);
  color: var(--text);
  border-top-left-radius: 4px;
}

.bubble-self {
  background: var(--accent-a, #0284c7);
  color: #fff;
  border-top-right-radius: 4px;
}

.msg-time {
  font-size: 10px;
  color: var(--muted);
  padding-left: 2px;
}
.self-time {
  padding-left: 0;
  padding-right: 2px;
}

/* ── 输入区 ── */
.input-area {
  flex-shrink: 0;
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 10px 14px calc(10px + var(--safe-bottom, 0px));
  max-width: 560px;
  width: 100%;
  margin: 0 auto;
  background: var(--card);
  border-top: 1px solid var(--card-border);
}

.chat-input {
  flex: 1;
  min-height: 40px;
  max-height: 100px;
  padding: 9px 13px;
  border-radius: 20px;
  border: 1px solid var(--card-border);
  background: var(--bg);
  color: var(--text);
  font-size: 14px;
  line-height: 1.4;
  resize: none;
  outline: none;
  font-family: inherit;
  overflow-y: auto;
}

.chat-input:focus {
  border-color: var(--accent-a, #0284c7);
}

.chat-input:disabled {
  opacity: 0.5;
}

.send-btn {
  flex-shrink: 0;
  height: 40px;
  padding: 0 18px;
  border-radius: 20px;
  border: none;
  background: var(--accent-a, #0284c7);
  color: #fff;
  font-size: 14px;
  font-weight: 700;
  transition: opacity 0.15s;
  -webkit-tap-highlight-color: transparent;
}

.send-btn:disabled {
  opacity: 0.45;
}

.send-btn:not(:disabled):active {
  opacity: 0.8;
}
</style>
