from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class MessageType(str, Enum):
    USER = "user"
    BOT = "bot"
    SYSTEM = "system"


class Channel(str, Enum):
    WEB = "web"
    SLACK = "slack"
    WHATSAPP = "whatsapp"


class IntentType(str, Enum):
    ORDER_INQUIRY = "order_inquiry"
    ACCOUNT_INFO = "account_info"
    PRODUCT_INFO = "product_info"
    BILLING = "billing"
    TECHNICAL_SUPPORT = "technical_support"
    GENERAL = "general"
    ESCALATE = "escalate"


class ChatMessage(BaseModel):
    message: str = Field(..., description="The message content")
    user_id: str = Field(..., description="Unique user identifier")
    session_id: Optional[str] = Field(None, description="Session identifier")
    channel: Channel = Field(default=Channel.WEB, description="Communication channel")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    response: str = Field(..., description="Bot response message")
    intent: Optional[str] = Field(None, description="Detected intent")
    confidence: Optional[float] = Field(None, description="Intent confidence score")
    requires_escalation: bool = Field(default=False, description="Whether to escalate to human")
    session_id: str = Field(..., description="Session identifier")
    response_time_ms: Optional[int] = Field(None, description="Response time in milliseconds")


class ChatHistory(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    user_id: str
    session_id: str
    message: str
    response: str
    message_type: MessageType
    intent: Optional[str] = None
    confidence: Optional[float] = None
    channel: Channel
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class UserContext(BaseModel):
    user_id: str
    customer_id: Optional[str] = None
    current_session: Optional[str] = None
    conversation_state: Dict[str, Any] = Field(default_factory=dict)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    last_interaction: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class IntentPrediction(BaseModel):
    intent: IntentType
    confidence: float
    entities: Dict[str, Any] = Field(default_factory=dict)
    alternative_intents: List[Dict[str, float]] = Field(default_factory=list)


class SalesforceContact(BaseModel):
    id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    account_id: Optional[str] = None
    last_activity_date: Optional[datetime] = None


class SalesforceCase(BaseModel):
    id: str
    case_number: str
    subject: str
    description: Optional[str] = None
    status: str
    priority: str
    contact_id: Optional[str] = None
    account_id: Optional[str] = None
    created_date: datetime
    last_modified_date: datetime


class SalesforceOrder(BaseModel):
    id: str
    order_number: str
    account_id: str
    contact_id: Optional[str] = None
    status: str
    total_amount: Optional[float] = None
    order_date: datetime
    items: List[Dict[str, Any]] = Field(default_factory=list)


class SlackEvent(BaseModel):
    type: str
    channel: str
    user: str
    text: str
    ts: str
    thread_ts: Optional[str] = None


class WhatsAppMessage(BaseModel):
    from_number: str
    to_number: str
    body: str
    message_sid: str
    account_sid: str


class HealthResponse(BaseModel):
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    services: Dict[str, str] = Field(default_factory=dict)
    version: str = "1.0.0"


class ErrorResponse(BaseModel):
    error: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None


class AnalyticsData(BaseModel):
    total_conversations: int
    resolved_automatically: int
    escalated_to_human: int
    avg_response_time: float
    most_common_intents: List[Dict[str, int]]
    period: str  # daily, weekly, monthly


# Webhook payloads
class SlackWebhookPayload(BaseModel):
    token: str
    team_id: str
    team_domain: str
    channel_id: str
    channel_name: str
    user_id: str
    user_name: str
    command: str
    text: str
    response_url: str
    trigger_id: str