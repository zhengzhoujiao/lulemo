<script setup lang="ts">
defineOptions({ name: "SocialPlaza" });

import { nextTick, onActivated, onMounted, ref } from "vue";
import { ApiError, apiFetch } from "../../api/client";
import { useAuth } from "../../stores/auth";
import CommentSheet from "../../components/CommentSheet.vue";

interface HotComment {
  comment_id: string;
  post_id: string;
  author_display_name: string;
  content: string;
  created_at: string;
  mine: boolean;
  like_count: number;
  liked: boolean;
  reply_count: number;
}

interface Post {
  post_id: string;
  author_display_name: string;
  content: string;
  created_at: string;
  mine: boolean;
  like_count: number;
  liked: boolean;
  comment_count: number;
  hot_comment: HotComment | null;
}

const { fetchMe } = useAuth();
const loading = ref(false);
const syncing = ref(false);
const posting = ref(false);
const err = ref("");

const posts = ref<Post[]>([]);
const compose = ref("");
const anonymous = ref(false);

const showCompose = ref(false);

// 评论列表弹层（去看亮回复）
const commentSheetVisible = ref(false);
const activePost = ref<Post | null>(null);

// 回复撰写弹层
const showReplySheet = ref(false);
const replyPost = ref<Post | null>(null);
const replyText = ref("");
const replySubmitting = ref(false);
const replyErr = ref("");
const replyInputRef = ref<HTMLTextAreaElement | null>(null);

function fmt(iso: string) {
  const d = new Date(iso);
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

async function refresh(opts?: { silent?: boolean }) {
  const silent = opts?.silent === true && posts.value.length > 0;
  if (silent) syncing.value = true;
  else loading.value = true;
  err.value = "";
  try {
    await fetchMe().catch(() => {});
    posts.value = await apiFetch<Post[]>("/social/posts?limit=40");
  } catch (e) {
    err.value = e instanceof ApiError ? e.detail : "加载失败";
  } finally {
    loading.value = false;
    syncing.value = false;
  }
}

let activatedOnce = false;

onMounted(() => refresh());

onActivated(() => {
  if (!activatedOnce) {
    activatedOnce = true;
    return;
  }
  refresh({ silent: true });
});

async function submitPost() {
  const t = compose.value.trim();
  if (!t || posting.value) return;
  posting.value = true;
  err.value = "";
  try {
    await apiFetch("/social/posts", {
      method: "POST",
      body: { content: t, anonymous: anonymous.value },
    });
    compose.value = "";
    anonymous.value = false;
    showCompose.value = false;
    await refresh();
  } catch (e) {
    err.value = e instanceof ApiError ? e.detail : "发送失败";
  } finally {
    posting.value = false;
  }
}

async function delPost(id: string) {
  try {
    await apiFetch(`/social/posts/${id}`, { method: "DELETE" });
    await refresh();
  } catch (e) {
    err.value = e instanceof ApiError ? e.detail : "删除失败";
  }
}

function openComposeSheet() {
  err.value = "";
  anonymous.value = false;
  showCompose.value = true;
}

function closeComposeSheet() {
  showCompose.value = false;
  anonymous.value = false;
}

function openComments(post: Post) {
  activePost.value = post;
  commentSheetVisible.value = true;
}

function closeComments() {
  commentSheetVisible.value = false;
}

function openReply(post: Post) {
  replyPost.value = post;
  replyText.value = "";
  replyErr.value = "";
  showReplySheet.value = true;
  nextTick(() => replyInputRef.value?.focus());
}

function closeReply() {
  showReplySheet.value = false;
  replyPost.value = null;
  replyText.value = "";
  replyErr.value = "";
}

async function submitReply() {
  const post = replyPost.value;
  const t = replyText.value.trim();
  if (!post || !t || replySubmitting.value) return;
  replySubmitting.value = true;
  replyErr.value = "";
  try {
    await apiFetch(`/social/posts/${post.post_id}/comments`, {
      method: "POST",
      body: { content: t },
    });
    closeReply();
    await refresh();
  } catch (e) {
    replyErr.value = e instanceof ApiError ? e.detail : "发送失败";
  } finally {
    replySubmitting.value = false;
  }
}

async function togglePostLike(post: Post) {
  try {
    const res = await apiFetch<{ liked: boolean; like_count: number }>(
      `/social/posts/${post.post_id}/like`,
      { method: "POST" },
    );
    post.liked = res.liked;
    post.like_count = res.like_count;
  } catch {
    // 静默失败
  }
}

async function toggleHotCommentLike(hc: HotComment) {
  try {
    const res = await apiFetch<{ liked: boolean; like_count: number }>(
      `/social/comments/${hc.comment_id}/like`,
      { method: "POST" },
    );
    hc.liked = res.liked;
    hc.like_count = res.like_count;
  } catch {
    // 静默失败
  }
}

function onCommented() {
  refresh({ silent: posts.value.length > 0 });
}
</script>

<template>
  <div class="plaza">
    <!-- 说点啥 -->
    <section class="card">
      <div class="head">
        <h2 class="title">说点啥么</h2>
        <button type="button" class="ghost" @click="() => refresh()">刷新</button>
      </div>
      <p v-if="loading" class="muted">加载中…</p>
      <p v-else-if="syncing" class="muted sync-hint">更新中…</p>

      <ul class="posts">
        <li v-for="p in posts" :key="p.post_id" class="post">
          <!-- 作者信息 -->
          <div class="meta">
            <span class="name">{{ p.author_display_name }}</span>
            <span class="time">{{ fmt(p.created_at) }}</span>
            <button v-if="p.mine" type="button" class="del" @click="delPost(p.post_id)">删</button>
          </div>

          <!-- 正文 -->
          <p class="body">{{ p.content }}</p>

          <!-- 操作行：点赞 + 回复 -->
          <div class="post-actions">
            <button
              type="button"
              class="action-btn like-btn"
              :class="{ liked: p.liked }"
              @click="togglePostLike(p)"
            >
              <svg viewBox="0 0 24 24" fill="none" width="15" height="15">
                <path
                  d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"
                  :fill="p.liked ? 'currentColor' : 'none'"
                  stroke="currentColor"
                  stroke-width="1.8"
                />
              </svg>
              <span>{{ p.like_count }}</span>
            </button>
            <button type="button" class="action-btn reply-btn" @click="openReply(p)">
              回复
            </button>
          </div>

          <!-- 热评区 -->
          <template v-if="p.hot_comment">
            <div class="hot-cmt">
              <p class="hc-text">
                <span class="hc-name">{{ p.hot_comment.author_display_name }}</span>：{{ p.hot_comment.content }}
              </p>
              <div class="hc-footer">
                <button
                  type="button"
                  class="hc-view-btn"
                  @click="openComments(p)"
                >
                  去看 {{ p.comment_count }} 条亮回复
                </button>
                <button
                  type="button"
                  class="hc-like-btn"
                  :class="{ liked: p.hot_comment.liked }"
                  @click="toggleHotCommentLike(p.hot_comment!)"
                >
                  <svg viewBox="0 0 24 24" fill="none" width="13" height="13">
                    <path
                      d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"
                      :fill="p.hot_comment.liked ? 'currentColor' : 'none'"
                      stroke="currentColor"
                      stroke-width="1.8"
                    />
                  </svg>
                  <span>{{ p.hot_comment.like_count }}</span>
                </button>
              </div>
            </div>
          </template>
        </li>
      </ul>
      <p v-if="!loading && posts.length === 0" class="muted empty">暂无帖子，来发第一条吧。</p>
    </section>

    <!-- 评论弹层 -->
    <CommentSheet
      :show="commentSheetVisible"
      :post-id="activePost?.post_id ?? ''"
      @close="closeComments"
      @commented="onCommented"
    />

    <!-- 悬浮加号按钮 -->
    <button type="button" class="fab" aria-label="发言" @click="openComposeSheet">
      <svg viewBox="0 0 24 24" fill="none" width="26" height="26" aria-hidden="true">
        <path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/>
      </svg>
    </button>

    <!-- 回复撰写弹层 -->
    <Teleport to="body">
      <Transition name="reply-fade">
        <div v-if="showReplySheet && replyPost" class="reply-overlay" @click.self="closeReply">
          <div class="reply-box" role="dialog" aria-label="回复">
            <div class="reply-header">
              <span class="reply-title">回复 {{ replyPost.author_display_name }}</span>
              <button type="button" class="reply-cancel" @click="closeReply">取消</button>
            </div>
            <textarea
              ref="replyInputRef"
              v-model="replyText"
              class="reply-ta"
              rows="3"
              maxlength="600"
              placeholder="写一句回复…"
              autocomplete="off"
            />
            <p v-if="replyErr" class="reply-err">{{ replyErr }}</p>
            <div class="reply-footer">
              <button
                type="button"
                class="reply-send"
                :disabled="replySubmitting || !replyText.trim()"
                @click="submitReply"
              >
                {{ replySubmitting ? "发送中…" : "发送" }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- 发言弹出层 -->
    <Teleport to="body">
      <Transition name="sheet-fade">
        <div v-if="showCompose" class="sheet-overlay" @click.self="closeComposeSheet">
          <div class="sheet" role="dialog" aria-modal="true" aria-label="发言">
            <!-- 头部 -->
            <div class="sheet-header">
              <button type="button" class="sheet-cancel" @click="closeComposeSheet">取消</button>
              <span class="sheet-title">发言</span>
              <button
                type="button"
                class="sheet-submit"
                :disabled="posting || !compose.trim()"
                @click="submitPost"
              >
                {{ posting ? "发送中…" : "发布" }}
              </button>
            </div>

            <div class="sheet-body">
              <label class="anon-row">
                <span class="anon-label">匿名发言</span>
                <span class="anon-hint muted">开启后以 momo 显示</span>
                <input v-model="anonymous" type="checkbox" class="anon-switch" />
              </label>

              <!-- 正文 -->
              <textarea
                v-model="compose"
                class="ta"
                maxlength="900"
                placeholder="说点什么…"
                rows="5"
                autocomplete="off"
              />
              <p v-if="err" class="err">{{ err }}</p>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.plaza {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding-bottom: 20px;
}

.card {
  border-radius: var(--radius-lg);
  background: var(--card);
  border: 1px solid var(--card-border);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.title {
  margin: 0;
  font-size: 17px;
  font-weight: 800;
}

.muted {
  margin: 0;
  font-size: 12px;
  color: var(--muted);
}

.muted.empty {
  text-align: center;
  padding: 16px 0;
}

.ta {
  width: 100%;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid var(--card-border);
  background: rgba(0, 0, 0, 0.04);
  color: var(--text);
  resize: none;
  min-height: 72px;
  font-size: 15px;
  line-height: 1.6;
  outline: none;
  transition: border-color 0.18s;
  box-sizing: border-box;
}

.ta:focus {
  border-color: rgba(2, 132, 199, 0.4);
}

.err {
  color: var(--danger);
  font-size: 12px;
  margin: 0;
}

.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.section-divider {
  border: none;
  border-top: 1px solid var(--card-border);
  margin: 0 0 5px;
}

.ghost {
  background: transparent;
  border: 1px solid var(--card-border);
  border-radius: 999px;
  font-size: 12px;
  padding: 4px 12px;
  color: var(--muted);
}

/* ── 帖子列表 ── */
.posts {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 0;
}

.post {
  border-top: 1px solid var(--card-border);
  padding: 12px 0 8px 0;
}

.meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  margin-bottom: 8px;
}

.name {
  font-weight: 800;
  color: var(--accent-b);
}

.time {
  color: var(--muted);
  flex: 1;
}

.del {
  margin-left: auto;
  font-size: 11px;
  border: none;
  background: none;
  color: rgba(239, 68, 68, 0.65);
}

.body {
  margin: 0 0 2px;
  white-space: pre-wrap;
  line-height: 1.55;
  font-size: 14px;
  color: var(--text);
}

/* 操作行 */
.post-actions {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 16px;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  border: none;
  background: none;
  color: var(--muted);
  padding: 4px 0;
  font-weight: 600;
  transition: color 0.15s;
}

.like-btn.liked {
  color: var(--danger);
}

.reply-btn {
  color: var(--accent-b);
}

/* ── 回复撰写弹层 ── */
.reply-overlay {
  position: fixed;
  inset: 0;
  z-index: 300;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.reply-box {
  width: 100%;
  max-width: 480px;
  background: var(--card);
  border-radius: 18px 18px 0 0;
  padding: 16px 16px calc(16px + var(--safe-bottom, 0px));
  display: flex;
  flex-direction: column;
  gap: 12px;
  box-shadow: 0 -4px 24px rgba(0, 0, 0, 0.10);
}

.reply-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.reply-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text);
}

.reply-cancel {
  border: none;
  background: none;
  font-size: 14px;
  color: var(--muted);
  padding: 0;
}

.reply-ta {
  width: 100%;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid var(--card-border);
  background: rgba(0, 0, 0, 0.04);
  color: var(--text);
  resize: none;
  font-size: 14px;
  line-height: 1.6;
  outline: none;
  transition: border-color 0.18s;
  box-sizing: border-box;
}

.reply-ta:focus {
  border-color: rgba(2, 132, 199, 0.4);
}

.reply-err {
  margin: 0;
  font-size: 12px;
  color: var(--danger);
}

.reply-footer {
  display: flex;
  justify-content: flex-end;
}

.reply-send {
  padding: 9px 24px;
  border-radius: 20px;
  border: none;
  background: var(--accent-a);
  color: #fff;
  font-size: 14px;
  font-weight: 700;
  transition: opacity 0.15s;
}

.reply-send:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.reply-fade-enter-active,
.reply-fade-leave-active {
  transition: opacity 0.18s ease;
}

.reply-fade-enter-active .reply-box,
.reply-fade-leave-active .reply-box {
  transition: transform 0.18s cubic-bezier(0.32, 0.72, 0, 1);
}

.reply-fade-enter-from,
.reply-fade-leave-to {
  opacity: 0;
}

.reply-fade-enter-from .reply-box,
.reply-fade-leave-to .reply-box {
  transform: translateY(100%);
}

/* 热评区 */
.hot-cmt {
  margin-top: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  background: var(--bg);
  border: 1px solid var(--card-border);
}

.hc-text {
  margin: 0 0 8px;
  font-size: 13px;
  color: var(--muted);
  line-height: 1.5;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.hc-name {
  font-weight: 700;
  color: var(--text);
}

.hc-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.hc-view-btn {
  font-size: 12px;
  border: none;
  background: none;
  color: var(--accent-b);
  font-weight: 600;
  padding: 0;
}

.hc-like-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  border: none;
  background: none;
  color: var(--muted);
  padding: 0;
  transition: color 0.15s;
}

.hc-like-btn.liked {
  color: var(--danger);
}

/* ── 悬浮按钮 ── */
.fab {
  position: fixed;
  right: 20px;
  bottom: calc(88px + var(--safe-bottom, 0px));
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: var(--accent-a);
  color: #fff;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
  transition: transform 0.15s, background 0.15s;
  z-index: 50;
  -webkit-tap-highlight-color: transparent;
}

.fab:active {
  transform: scale(0.93);
}

/* ── 发帖弹出层 ── */
.sheet-overlay {
  position: fixed;
  inset: 0;
  z-index: 300;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding-bottom: var(--safe-bottom, 0);
}

.sheet {
  width: 100%;
  max-width: 480px;
  background: var(--card);
  border: 1px solid var(--card-border);
  border-bottom: none;
  border-radius: 22px 22px 0 0;
  display: flex;
  flex-direction: column;
  max-height: 88vh;
  box-shadow: 0 -4px 24px rgba(0, 0, 0, 0.10);
}

.sheet-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid var(--card-border);
  flex-shrink: 0;
}

.sheet-title {
  font-size: 15px;
  font-weight: 800;
  color: var(--text);
}

.sheet-cancel {
  border: none;
  background: none;
  font-size: 15px;
  font-weight: 600;
  color: var(--muted);
  padding: 4px 0;
  min-width: 44px;
  text-align: left;
}

.sheet-submit {
  border: none;
  background: none;
  font-size: 15px;
  font-weight: 700;
  color: var(--accent-a);
  padding: 4px 0;
  min-width: 44px;
  text-align: right;
  transition: opacity 0.15s;
}

.sheet-submit:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.sheet-body {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}

/* 昵称区块 */
.anon-row {
  display: grid;
  grid-template-columns: 1fr auto;
  grid-template-rows: auto auto;
  align-items: center;
  gap: 2px 10px;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.04);
  border: 1px solid var(--card-border);
}

.anon-label {
  font-size: 13px;
  font-weight: 700;
  color: var(--text);
}

.anon-hint {
  grid-column: 1;
  font-size: 11px;
}

.anon-switch {
  grid-column: 2;
  grid-row: 1 / span 2;
  width: 18px;
  height: 18px;
  accent-color: var(--accent-a);
}

.dn-block {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.dn-label {
  margin: 0;
  font-size: 12px;
  font-weight: 600;
  color: var(--muted);
  letter-spacing: 0.04em;
}

.dn-row {
  display: flex;
  gap: 8px;
}

.dn-input {
  flex: 1;
  padding: 9px 12px;
  border-radius: 10px;
  border: 1px solid var(--card-border);
  background: rgba(0, 0, 0, 0.04);
  color: var(--text);
  font-size: 14px;
  outline: none;
  transition: border-color 0.18s;
}

.dn-input:focus {
  border-color: rgba(2, 132, 199, 0.4);
}

.dn-save {
  padding: 9px 14px;
  border-radius: 10px;
  border: 1px solid var(--card-border);
  background: rgba(0, 0, 0, 0.05);
  color: var(--text);
  font-size: 13px;
  font-weight: 700;
  transition: opacity 0.15s;
}

.dn-save:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.dn-msg {
  margin: 0;
  font-size: 12px;
  color: var(--accent-b);
}

/* ── 过渡动画 ── */
.sheet-fade-enter-active,
.sheet-fade-leave-active {
  transition: opacity 0.22s ease;
}

.sheet-fade-enter-active .sheet,
.sheet-fade-leave-active .sheet {
  transition: transform 0.22s cubic-bezier(0.32, 0.72, 0, 1);
}

.sheet-fade-enter-from,
.sheet-fade-leave-to {
  opacity: 0;
}

.sheet-fade-enter-from .sheet,
.sheet-fade-leave-to .sheet {
  transform: translateY(100%);
}
</style>
