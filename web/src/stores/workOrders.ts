import { computed, ref } from "vue";
import { apiFetch } from "../api/client";

export interface WorkOrderItem {
  work_order_id: string;
  user_id: string;
  user_display_name: string;
  subject: string;
  created_at: string;
  updated_at: string;
  last_reply_by: "user" | "admin";
  latest_reply_preview: string;
  latest_reply_at: string;
}

interface WorkOrderDashboardResponse {
  is_admin: boolean;
  mine: WorkOrderItem[];
  pending: WorkOrderItem[];
  processed: WorkOrderItem[];
}

export interface WorkOrderReplyItem {
  reply_id: string;
  work_order_id: string;
  sender_role: "user" | "admin";
  sender_user_id: string;
  sender_display_name: string;
  content: string;
  created_at: string;
}

const loading = ref(false);
const creating = ref(false);
const replying = ref(false);
const isAdmin = ref(false);
const mine = ref<WorkOrderItem[]>([]);
const pending = ref<WorkOrderItem[]>([]);
const processed = ref<WorkOrderItem[]>([]);

export function useWorkOrders() {
  async function fetchDashboard(): Promise<void> {
    loading.value = true;
    try {
      const data = await apiFetch<WorkOrderDashboardResponse>("/work-orders/me");
      isAdmin.value = data.is_admin;
      mine.value = data.mine;
      pending.value = data.pending;
      processed.value = data.processed;
    } finally {
      loading.value = false;
    }
  }

  async function createWorkOrder(subject: string, content: string): Promise<void> {
    if (creating.value) return;
    creating.value = true;
    try {
      await apiFetch<WorkOrderItem>("/work-orders", {
        method: "POST",
        body: { subject, content },
      });
      await fetchDashboard();
    } finally {
      creating.value = false;
    }
  }

  async function fetchReplies(workOrderId: string): Promise<WorkOrderReplyItem[]> {
    return apiFetch<WorkOrderReplyItem[]>(`/work-orders/${workOrderId}/replies`);
  }

  async function createReply(workOrderId: string, content: string): Promise<void> {
    if (replying.value) return;
    replying.value = true;
    try {
      await apiFetch<WorkOrderReplyItem>(`/work-orders/${workOrderId}/replies`, {
        method: "POST",
        body: { content },
      });
      await fetchDashboard();
    } finally {
      replying.value = false;
    }
  }

  const pendingCount = computed(() => pending.value.length);
  const processedCount = computed(() => processed.value.length);

  return {
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
  };
}
