<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { ApiError, apiFetch } from "../api/client";
import CommentSheet from "./CommentSheet.vue";

interface CommentItem {
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

const props = defineProps<{
  show: boolean;
  postId: string;
  parentCommentId?: string;
  title?: string;
  /** 弹层嵌套深度，用于 z-index 叠层 */
  depth?: number;
}>();

const overlayZ = computed(() => 300 + (props.depth ?? 0) * 20);
const composerZ = computed(() => overlayZ.value + 10);

const emit = defineEmits<{
  close: [];
  commented: [];
}>();

const comments = ref<CommentItem[]>([]);
const loading = ref(false);
const composeText = ref("");
const submitting = ref(false);
const err = ref("");

// 回复撰写浮层
const replyTarget = ref<CommentItem | null>(null);
const replyText = ref("");
const replySubmitting = ref(false);
const replyInputRef = ref<HTMLTextAreaElement | null>(null);

// 嵌套回复弹层
const replySheetTarget = ref<CommentItem | null>(null);

function fmt(iso: string) {
  const d = new Date(iso);
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

async function load() {
  if (!props.postId) return;
  loading.value = true;
  err.value = "";
  try {
    if (props.parentCommentId) {
      comments.value = await apiFetch<CommentItem[]>(
        `/social/comments/${props.parentCommentId}/replies`,
      );
    } else {
      comments.value = await apiFetch<CommentItem[]>(
        `/social/posts/${props.postId}/comments`,
      );
    }
  } catch (e) {
    err.value = e instanceof ApiError ? e.detail : "加载失败";
  } finally {
    loading.value = false;
  }
}

watch(
  () => [props.show, props.postId, props.parentCommentId] as const,
  ([show]) => {
    if (show) {
      load();
    } else {
      comments.value = [];
      composeText.value = "";
      replyTarget.value = null;
      replySheetTarget.value = null;
      err.value = "";
    }
  },
  { immediate: true },
);

async function toggleLike(c: CommentItem) {
  try {
    const res = await apiFetch<{ liked: boolean; like_count: number }>(
      `/social/comments/${c.comment_id}/like`,
      { method: "POST" },
    );
    c.liked = res.liked;
    c.like_count = res.like_count;
  } catch {
    // 静默失败
  }
}

async function submit() {
  const t = composeText.value.trim();
  if (!t || submitting.value) return;
  submitting.value = true;
  err.value = "";
  try {
    await apiFetch(`/social/posts/${props.postId}/comments`, {
      method: "POST",
      body: {
        content: t,
        parent_comment_id: props.parentCommentId ?? null,
      },
    });
    composeText.value = "";
    emit("commented");
    await load();
  } catch (e) {
    err.value = e instanceof ApiError ? e.detail : "发送失败";
  } finally {
    submitting.value = false;
  }
}

function openReplyComposer(c: CommentItem) {
  replyTarget.value = c;
  replyText.value = "";
  nextTick(() => replyInputRef.value?.focus());
}

function cancelReply() {
  replyTarget.value = null;
  replyText.value = "";
}

async function submitReply() {
  const t = replyText.value.trim();
  const target = replyTarget.value;
  if (!t || !target || replySubmitting.value) return;
  replySubmitting.value = true;
  try {
    await apiFetch(`/social/posts/${props.postId}/comments`, {
      method: "POST",
      body: {
        content: t,
        parent_comment_id: target.comment_id,
      },
    });
    replyText.value = "";
    replyTarget.value = null;
    emit("commented");
    await load();
  } catch (e) {
    err.value = e instanceof ApiError ? e.detail : "发送失败";
  } finally {
    replySubmitting.value = false;
  }
}

function openReplySheet(c: CommentItem) {
  replyTarget.value = null;
  replyText.value = "";
  replySheetTarget.value = c;
}

function closeReplySheet() {
  replySheetTarget.value = null;
  if (props.show) void load();
}

async function onNestedCommented() {
  emit("commented");
  if (props.show) await load();
}

const sheetTitle = () => props.title ?? (props.parentCommentId ? "回复" : "评论");
</script>

<template>
  <Teleport to="body">
    <Transition name="cs-fade">
      <div
        v-if="show"
        class="cs-overlay"
        :style="{ zIndex: overlayZ }"
        @click.self="emit('close')"
      >
        <div class="cs-sheet" role="dialog" :aria-label="sheetTitle()">
          <!-- 头部 -->
          <div class="cs-header">
            <span class="cs-title">{{ sheetTitle() }}</span>
            <button type="button" class="cs-close" @click="emit('close')">
              <svg viewBox="0 0 24 24" fill="none" width="20" height="20">
                <path d="M6 18L18 6M6 6l12 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              </svg>
            </button>
          </div>

          <!-- 评论列表 -->
          <div class="cs-body">
            <p v-if="loading" class="cs-hint">加载中…</p>
            <p v-else-if="!loading && comments.length === 0 && !err" class="cs-hint">
              {{ parentCommentId ? "还没有回复，来第一个吧。" : "还没有评论，来第一个吧。" }}
            </p>
            <p v-if="err" class="cs-err">{{ err }}</p>

            <ul class="cs-list">
              <li v-for="c in comments" :key="c.comment_id" class="cs-item">
                <div class="cs-meta">
                  <span class="cs-name">{{ c.author_display_name }}</span>
                  <span class="cs-time">{{ fmt(c.created_at) }}</span>
                </div>
                <p class="cs-content">{{ c.content }}</p>
                <div class="cs-actions">
                  <!-- 左：查看回复 -->
                  <button
                    v-if="c.reply_count > 0"
                    type="button"
                    class="cs-view-replies"
                    @click.stop="openReplySheet(c)"
                  >
                    查看 {{ c.reply_count }} 条回复
                  </button>
                  <span v-else class="cs-spacer" />
                  <!-- 右：点赞 + 回复 -->
                  <div class="cs-action-right">
                    <button
                      type="button"
                      class="cs-like-btn"
                      :class="{ liked: c.liked }"
                      @click="toggleLike(c)"
                    >
                      <svg viewBox="0 0 24 24" fill="none" width="14" height="14">
                        <path
                          d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"
                          :fill="c.liked ? 'currentColor' : 'none'"
                          stroke="currentColor"
                          stroke-width="1.8"
                        />
                      </svg>
                      <span>{{ c.like_count }}</span>
                    </button>
                    <button
                      type="button"
                      class="cs-reply-btn"
                      @click.stop="openReplyComposer(c)"
                    >
                      回复
                    </button>
                  </div>
                </div>
              </li>
            </ul>
          </div>

          <!-- 底部输入栏 -->
          <div class="cs-input-bar">
            <textarea
              v-model="composeText"
              class="cs-ta"
              rows="1"
              maxlength="600"
              :placeholder="parentCommentId ? '写一句回复…' : '写一句评论…'"
              autocomplete="off"
            />
            <button
              type="button"
              class="cs-send"
              :disabled="submitting || !composeText.trim()"
              @click="submit"
            >
              {{ submitting ? "…" : "发送" }}
            </button>
          </div>
        </div>

        <!-- 回复撰写浮层 -->
        <Transition name="rc-fade">
          <div
            v-if="replyTarget"
            class="rc-overlay"
            :style="{ zIndex: composerZ }"
            @click.self="cancelReply"
          >
            <div class="rc-box">
              <div class="rc-header">
                <span class="rc-title">回复 {{ replyTarget.author_display_name }}</span>
                <button type="button" class="rc-cancel" @click="cancelReply">取消</button>
              </div>
              <textarea
                ref="replyInputRef"
                v-model="replyText"
                class="rc-ta"
                rows="3"
                maxlength="600"
                placeholder="写一句回复…"
                autocomplete="off"
              />
              <div class="rc-footer">
                <button
                  type="button"
                  class="rc-send"
                  :disabled="replySubmitting || !replyText.trim()"
                  @click="submitReply"
                >
                  {{ replySubmitting ? "发送中…" : "发送" }}
                </button>
              </div>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>

  </Teleport>

  <!-- 嵌套评论列表弹层（层中层，独立 Teleport 保证叠在最上层） -->
  <CommentSheet
    v-if="replySheetTarget"
    :show="!!replySheetTarget"
    :post-id="postId"
    :parent-comment-id="replySheetTarget.comment_id"
    :title="`${replySheetTarget.author_display_name} 的回复`"
    :depth="(depth ?? 0) + 1"
    @close="closeReplySheet"
    @commented="onNestedCommented"
  />
</template>

<style scoped>
/* ── 主弹层 ── */
.cs-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding-bottom: var(--safe-bottom, 0);
}

.cs-sheet {
  width: 100%;
  max-width: 480px;
  background: var(--card);
  border: 1px solid var(--card-border);
  border-bottom: none;
  border-radius: 22px 22px 0 0;
  display: flex;
  flex-direction: column;
  max-height: 85vh;
  box-shadow: 0 -4px 24px rgba(0, 0, 0, 0.10);
}

.cs-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid var(--card-border);
  flex-shrink: 0;
}

.cs-title {
  font-size: 15px;
  font-weight: 800;
  color: var(--text);
}

.cs-close {
  border: none;
  background: none;
  color: var(--muted);
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.cs-body {
  flex: 1;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  padding: 8px 0;
}

.cs-hint {
  text-align: center;
  font-size: 13px;
  color: var(--muted);
  padding: 24px 16px;
  margin: 0;
}

.cs-err {
  color: var(--danger);
  font-size: 12px;
  margin: 0 16px 8px;
}

.cs-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.cs-item {
  padding: 12px 16px;
  border-bottom: 1px solid var(--card-border);
}

.cs-item:last-child {
  border-bottom: none;
}

.cs-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 5px;
}

.cs-name {
  font-size: 12px;
  font-weight: 700;
  color: var(--accent-b);
}

.cs-time {
  font-size: 11px;
  color: var(--muted);
}

.cs-content {
  margin: 0 0 8px;
  font-size: 14px;
  line-height: 1.55;
  color: var(--text);
  white-space: pre-wrap;
}

.cs-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.cs-view-replies {
  font-size: 12px;
  border: none;
  background: none;
  color: var(--accent-b);
  font-weight: 600;
  padding: 0;
}

.cs-spacer {
  flex: 1;
}

.cs-action-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.cs-like-btn {
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

.cs-like-btn.liked {
  color: var(--danger);
}

.cs-reply-btn {
  font-size: 12px;
  border: none;
  background: none;
  color: var(--muted);
  font-weight: 600;
  padding: 0;
}

/* 底部输入栏 */
.cs-input-bar {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 10px 16px calc(10px + var(--safe-bottom, 0px));
  border-top: 1px solid var(--card-border);
  flex-shrink: 0;
  background: var(--card);
}

.cs-ta {
  flex: 1;
  padding: 9px 12px;
  border-radius: 20px;
  border: 1px solid var(--card-border);
  background: rgba(0, 0, 0, 0.04);
  color: var(--text);
  resize: none;
  font-size: 14px;
  line-height: 1.5;
  outline: none;
  transition: border-color 0.18s;
  max-height: 100px;
  overflow-y: auto;
}

.cs-ta:focus {
  border-color: rgba(2, 132, 199, 0.4);
}

.cs-send {
  flex-shrink: 0;
  padding: 8px 16px;
  border-radius: 20px;
  border: none;
  background: var(--accent-a);
  color: #fff;
  font-size: 14px;
  font-weight: 700;
  transition: opacity 0.15s;
}

.cs-send:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

/* ── 回复撰写浮层 ── */
.rc-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.rc-box {
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

.rc-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.rc-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text);
}

.rc-cancel {
  border: none;
  background: none;
  font-size: 14px;
  color: var(--muted);
  padding: 0;
}

.rc-ta {
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

.rc-ta:focus {
  border-color: rgba(2, 132, 199, 0.4);
}

.rc-footer {
  display: flex;
  justify-content: flex-end;
}

.rc-send {
  padding: 9px 24px;
  border-radius: 20px;
  border: none;
  background: var(--accent-a);
  color: #fff;
  font-size: 14px;
  font-weight: 700;
  transition: opacity 0.15s;
}

.rc-send:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

/* ── 过渡动画 ── */
.cs-fade-enter-active,
.cs-fade-leave-active {
  transition: opacity 0.22s ease;
}

.cs-fade-enter-active .cs-sheet,
.cs-fade-leave-active .cs-sheet {
  transition: transform 0.22s cubic-bezier(0.32, 0.72, 0, 1);
}

.cs-fade-enter-from,
.cs-fade-leave-to {
  opacity: 0;
}

.cs-fade-enter-from .cs-sheet,
.cs-fade-leave-to .cs-sheet {
  transform: translateY(100%);
}

.rc-fade-enter-active,
.rc-fade-leave-active {
  transition: opacity 0.18s ease;
}

.rc-fade-enter-active .rc-box,
.rc-fade-leave-active .rc-box {
  transition: transform 0.18s cubic-bezier(0.32, 0.72, 0, 1);
}

.rc-fade-enter-from,
.rc-fade-leave-to {
  opacity: 0;
}

.rc-fade-enter-from .rc-box,
.rc-fade-leave-to .rc-box {
  transform: translateY(100%);
}
</style>
