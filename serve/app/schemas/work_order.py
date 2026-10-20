from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

WorkOrderLastReplyBy = Literal["user", "admin"]


class CreateWorkOrderRequest(BaseModel):
    subject: str = Field(..., min_length=1, max_length=80)
    content: str = Field(..., min_length=1, max_length=2000)


class CreateWorkOrderReplyRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class WorkOrderReplyResponse(BaseModel):
    reply_id: str
    work_order_id: str
    sender_role: WorkOrderLastReplyBy
    sender_user_id: str
    sender_display_name: str
    content: str
    created_at: datetime


class WorkOrderResponse(BaseModel):
    work_order_id: str
    user_id: str
    user_display_name: str
    subject: str
    created_at: datetime
    updated_at: datetime
    last_reply_by: WorkOrderLastReplyBy
    latest_reply_preview: str
    latest_reply_at: datetime


class WorkOrderAdminListResponse(BaseModel):
    pending: list[WorkOrderResponse]
    processed: list[WorkOrderResponse]
