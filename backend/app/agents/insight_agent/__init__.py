"""
Insight Agent——业务编排层·大脑/总指挥

负责意图解析、Skill 约束校验、工作区/附件上下文管理、任务委派与事件发布。
"""

from .agent import (
    AgentTaskType,
    InsightAgent,
    InsightInput,
    IntentResult,
    OrchestrationResult,
    OrchestrationStatus,
    create_insight_agent,
)
from .attachment_manager import (
    Attachment,
    AttachmentCreate,
    AttachmentManager,
    AttachmentResponse,
    AttachmentStatus,
    AttachmentType,
)
from .message_bus import EventEnvelope, EventType, MessageBus, MessagePayload, MessagePriority, MessageStatus, dispatch_event
from .skill_manager import SkillConstraintResult, SkillManager, SkillSchema
from .workspace_manager import (
    Workspace,
    WorkspaceCreate,
    WorkspaceManager,
    WorkspaceResponse,
    WorkspaceUpdate,
)

__all__ = [
    # agent
    "InsightAgent",
    "InsightInput",
    "IntentResult",
    "OrchestrationResult",
    "OrchestrationStatus",
    "AgentTaskType",
    "create_insight_agent",
    # skill
    "SkillManager",
    "SkillSchema",
    "SkillConstraintResult",
    # workspace
    "WorkspaceManager",
    "Workspace",
    "WorkspaceCreate",
    "WorkspaceUpdate",
    "WorkspaceResponse",
    # attachment
    "AttachmentManager",
    "Attachment",
    "AttachmentCreate",
    "AttachmentResponse",
    "AttachmentStatus",
    "AttachmentType",
    # message bus
    "MessageBus",
    "MessagePayload",
    "MessageStatus",
    "MessagePriority",
    "EventType",
    "EventEnvelope",
    "dispatch_event",
]