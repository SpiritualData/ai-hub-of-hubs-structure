"""Public protocol models the terminal screen and its event handler read. Vendored from Mistral Vibe v2.26.1 (https://github.com/mistralai/mistral-vibe, Apache-2.0, file vibe/app_server/models.py); modified from upstream: trimmed to the models the screen reads (account, identity, workspace trust, vibe-code, teleport, skill, plugin, MCP, session log, debug log, hook, scheduled loop, compaction, turn queue and turn input models cut), and imports rewritten to relative imports."""

from __future__ import annotations

from enum import StrEnum, auto
from functools import cache
from typing import Annotated, Literal

from pydantic import Field, JsonValue, TypeAdapter

from .agents import AgentSafety, AgentType
from .effect_models import (
    MANUAL_SHELL_TOOL_NAME as MANUAL_SHELL_TOOL_NAME,
    EffectDetail as EffectDetail,
    FileEditEffectBatchInput as FileEditEffectBatchInput,
    FileEditEffectChange as FileEditEffectChange,
    FileEditEffectDetail as FileEditEffectDetail,
    FileEditEffectInput as FileEditEffectInput,
    FileEditEffectOccurrence as FileEditEffectOccurrence,
    FileEditEffectOutput as FileEditEffectOutput,
    FileReadEffectDetail as FileReadEffectDetail,
    FileReadEffectInput as FileReadEffectInput,
    FileReadEffectOutput as FileReadEffectOutput,
    FileSearchEffectDetail as FileSearchEffectDetail,
    FileSearchEffectInput as FileSearchEffectInput,
    FileSearchEffectMatch as FileSearchEffectMatch,
    FileSearchEffectOutput as FileSearchEffectOutput,
    FileWriteEffectDetail as FileWriteEffectDetail,
    FileWriteEffectInput as FileWriteEffectInput,
    FileWriteEffectOutput as FileWriteEffectOutput,
    GenericEffectDetail as GenericEffectDetail,
    ProcessEffectDetail as ProcessEffectDetail,
    ScratchpadEffectDetail as ScratchpadEffectDetail,
    ScratchpadEffectInput as ScratchpadEffectInput,
    ScratchpadEffectOutput as ScratchpadEffectOutput,
    ScratchpadListInput as ScratchpadListInput,
    ScratchpadReadInput as ScratchpadReadInput,
    ScratchpadWriteInput as ScratchpadWriteInput,
    ShellEffectDetail as ShellEffectDetail,
    ShellEffectInput as ShellEffectInput,
    ShellEffectOutput as ShellEffectOutput,
    SkillEffectDetail as SkillEffectDetail,
    SkillEffectInput as SkillEffectInput,
    SkillEffectOutput as SkillEffectOutput,
    SubagentEffectDetail as SubagentEffectDetail,
    SubagentEffectInput as SubagentEffectInput,
    SubagentEffectOutput as SubagentEffectOutput,
    TodoEffectDetail as TodoEffectDetail,
    TodoEffectInput as TodoEffectInput,
    TodoEffectItem as TodoEffectItem,
    TodoEffectOutput as TodoEffectOutput,
    TodoEffectPriority as TodoEffectPriority,
    TodoEffectStatus as TodoEffectStatus,
    UserQuestionEffectDetail as UserQuestionEffectDetail,
    WebFetchEffectDetail as WebFetchEffectDetail,
    WebFetchEffectInput as WebFetchEffectInput,
    WebFetchEffectOutput as WebFetchEffectOutput,
    WebSearchEffectDetail as WebSearchEffectDetail,
    WebSearchEffectInput as WebSearchEffectInput,
    WebSearchEffectOutput as WebSearchEffectOutput,
    WebSearchEffectSource as WebSearchEffectSource,
    WorktreeEffectDetail as WorktreeEffectDetail,
    WorktreeEffectInput as WorktreeEffectInput,
    WorktreeEffectProgress as WorktreeEffectProgress,
    effect_input_json as effect_input_json,
)
from .model import ProtocolModel
from .permissions import PathGrantScope, RequiredPermission
from .questions import (
    QuestionChoice as QuestionChoice,
    UserAnswer as UserAnswer,
    UserQuestion as UserQuestion,
    UserQuestionRequest as UserQuestionRequest,
    UserQuestionResult as UserQuestionResult,
)
from .user_content import UserDisplayContent as UserDisplayContent, UserResource
from .tool_presentation import (
    EffectCallDisplay as EffectCallDisplay,
    EffectResultDisplay as EffectResultDisplay,
)


class FileImageSource(ProtocolModel):
    kind: Literal["file"] = "file"
    path: str


class InlineImageSource(ProtocolModel):
    kind: Literal["inline"] = "inline"
    data: str


ImageSource = Annotated[
    FileImageSource | InlineImageSource, Field(discriminator="kind")
]


class ImageAttachment(ProtocolModel):
    source: ImageSource
    alias: str
    mime_type: str


class TextContentBlock(ProtocolModel):
    type: Literal["text"] = "text"
    text: str


class ImageContentBlock(ProtocolModel):
    type: Literal["image"] = "image"
    attachment: ImageAttachment


class ResourceContentBlock(ProtocolModel):
    type: Literal["resource"] = "resource"
    resource: UserResource


ContentBlock = Annotated[
    TextContentBlock | ImageContentBlock | ResourceContentBlock,
    Field(discriminator="type"),
]


class ApprovalDecisionType(StrEnum):
    APPROVE = auto()
    APPROVE_FOR_SESSION = auto()
    APPROVE_PERMANENTLY = auto()
    DENY = auto()
    CANCEL_TURN = auto()


class ApprovalDecision(ProtocolModel):
    type: ApprovalDecisionType
    path_scope: PathGrantScope | None = None


class ApprovalCallbackDetail(ProtocolModel):
    kind: Literal["approval"] = "approval"
    effect: EffectDetail
    required_permissions: list[RequiredPermission] = Field(default_factory=list)
    choices: list[ApprovalDecisionType] = Field(
        default_factory=lambda: list(ApprovalDecisionType)
    )
    path_scope_choices: list[PathGrantScope] = Field(default_factory=list)
    related_entry_id: str | None = None
    # Why approval is being requested (e.g. smart approve's risk reason); shown in the
    # approval dialog. None for the static per-tool permission gate.
    reason: str | None = None


class UserInputCallbackDetail(ProtocolModel):
    kind: Literal["user_input"] = "user_input"
    request: UserQuestionRequest
    related_entry_id: str | None = None


CallbackDetail = Annotated[
    ApprovalCallbackDetail | UserInputCallbackDetail, Field(discriminator="kind")
]


class ApprovalCallbackOutput(ProtocolModel):
    type: Literal["approval"] = "approval"
    decision: ApprovalDecision
    feedback: str | None = None


class UserInputCallbackOutput(ProtocolModel):
    type: Literal["user_input"] = "user_input"
    result: UserQuestionResult


CallbackOutput = Annotated[
    ApprovalCallbackOutput | UserInputCallbackOutput, Field(discriminator="type")
]


class PublicEntryGenerationStatus(StrEnum):
    IN_PROGRESS = auto()
    COMPLETED = auto()


class PublicTurnStatus(StrEnum):
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()
    INTERRUPTED = auto()


class PublicTurnStopReason(StrEnum):
    """Why a completed Turn stopped short of the agent finishing on its own."""

    LIMIT = auto()  # an iteration, token or price limit
    LENGTH = auto()  # the last answer was cut off at the output-token cap


class TurnErrorCode(StrEnum):
    RATE_LIMIT = auto()
    CONTEXT_TOO_LONG = auto()
    RESPONSE_TOO_LONG = auto()
    REFUSAL = auto()
    INVALID_IMAGE_ATTACHMENT = auto()
    IMAGES_NOT_SUPPORTED = auto()
    COMPACTION_FAILED = auto()
    INCOMPLETE_STREAM = auto()
    BACKEND_ERROR = auto()
    INVALID_MODEL = auto()
    INVALID_API_KEY = auto()
    INTERNAL_ERROR = auto()


class PublicError(ProtocolModel):
    message: str
    code: str | None = None
    details: JsonValue = None


class TokenUsage(ProtocolModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class AgentStatsSnapshot(ProtocolModel):
    steps: int = 0
    # Model calls the session's own agent made: neither its subagents' calls nor
    # utility calls such as compaction. None until one is counted, or when the
    # runtime does not count them.
    model_calls: int | None = None
    session_prompt_tokens: int = 0
    session_completion_tokens: int = 0
    session_cached_tokens: int = 0
    input_price_per_million: float = 0.0
    output_price_per_million: float = 0.0
    cached_input_price_per_million: float | None = None
    tool_calls_agreed: int = 0
    tool_calls_rejected: int = 0
    tool_calls_failed: int = 0
    tool_calls_succeeded: int = 0
    context_tokens: int = 0
    last_turn_prompt_tokens: int = 0
    last_turn_completion_tokens: int = 0
    last_turn_cached_tokens: int = 0
    last_turn_duration: float = 0.0
    tokens_per_second: float = 0.0

    @property
    def session_total_llm_tokens(self) -> int:
        return self.session_prompt_tokens + self.session_completion_tokens

    @property
    def last_turn_total_tokens(self) -> int:
        return self.last_turn_prompt_tokens + self.last_turn_completion_tokens

    @property
    def token_usage(self) -> TokenUsage:
        return TokenUsage(
            input_tokens=self.session_prompt_tokens,
            output_tokens=self.session_completion_tokens,
            total_tokens=self.session_total_llm_tokens,
        )


class AgentSummary(ProtocolModel):
    name: str
    display_name: str
    description: str
    safety: AgentSafety
    agent_type: AgentType


class PendingEffectState(ProtocolModel):
    status: Literal["pending"] = "pending"


class RunningEffectState(ProtocolModel):
    status: Literal["running"] = "running"
    output_text: str = ""


class BlockedEffectState(ProtocolModel):
    status: Literal["blocked"] = "blocked"
    callback_id: str
    output_text: str = ""


class CompletedEffectState(ProtocolModel):
    status: Literal["completed"] = "completed"
    output: JsonValue = None
    output_text: str = ""
    duration_ms: float = 0.0
    display: EffectResultDisplay
    decision: Literal["execute", "skip"] | None = None
    approval_type: Literal["always", "never", "ask"] | None = None
    approval_source: Literal["config", "smart", "user", "bypass", "never"] | None = None


class FailedEffectState(ProtocolModel):
    status: Literal["failed"] = "failed"
    error: PublicError
    output: JsonValue = None
    output_text: str = ""
    duration_ms: float = 0.0
    display: EffectResultDisplay
    decision: Literal["execute", "skip"] | None = None
    approval_type: Literal["always", "never", "ask"] | None = None
    approval_source: Literal["config", "smart", "user", "bypass", "never"] | None = None


class CancelledEffectState(ProtocolModel):
    status: Literal["cancelled"] = "cancelled"
    reason: str
    output_text: str = ""
    duration_ms: float = 0.0
    display: EffectResultDisplay | None = None
    decision: Literal["execute", "skip"] | None = None
    approval_type: Literal["always", "never", "ask"] | None = None
    approval_source: Literal["config", "smart", "user", "bypass", "never"] | None = None


class SkippedEffectState(ProtocolModel):
    status: Literal["skipped"] = "skipped"
    reason: str
    display: EffectResultDisplay
    decision: Literal["execute", "skip"] | None = None
    approval_type: Literal["always", "never", "ask"] | None = None
    approval_source: Literal["config", "smart", "user", "bypass", "never"] | None = None


EffectState = Annotated[
    PendingEffectState
    | RunningEffectState
    | BlockedEffectState
    | CompletedEffectState
    | FailedEffectState
    | CancelledEffectState
    | SkippedEffectState,
    Field(discriminator="status"),
]


class OpenCallbackState(ProtocolModel):
    status: Literal["open"] = "open"


class AnsweredCallbackState(ProtocolModel):
    status: Literal["answered"] = "answered"
    output: CallbackOutput


class CancelledCallbackState(ProtocolModel):
    status: Literal["cancelled"] = "cancelled"
    reason: str


class ExpiredCallbackState(ProtocolModel):
    status: Literal["expired"] = "expired"
    reason: str


CallbackState = Annotated[
    OpenCallbackState
    | AnsweredCallbackState
    | CancelledCallbackState
    | ExpiredCallbackState,
    Field(discriminator="status"),
]


class _PublicHistoryEntryBase(ProtocolModel):
    id: str
    session_id: str
    turn_id: str | None = None
    input_entry_id: str | None = None
    created_at: int
    updated_at: int
    generation_status: PublicEntryGenerationStatus
    related_entry_id: str | None = None


PublicMessageSource = Literal["turn_start", "turn_steer", "harness"]


class PublicMessageEntry(_PublicHistoryEntryBase):
    type: Literal["message"] = "message"
    role: Literal["system", "user", "assistant"]
    content: list[ContentBlock]
    source: PublicMessageSource | None = None
    user_display_content: UserDisplayContent | None = None

    @property
    def text(self) -> str:
        return "\n\n".join(
            block.text for block in self.content if isinstance(block, TextContentBlock)
        )

    @property
    def images(self) -> list[ImageAttachment]:
        return [
            block.attachment
            for block in self.content
            if isinstance(block, ImageContentBlock)
        ]


class PublicReasoningEntry(_PublicHistoryEntryBase):
    type: Literal["reasoning"] = "reasoning"
    text: str
    summary: list[str] = Field(default_factory=list)


class PublicEffectEntry(_PublicHistoryEntryBase):
    type: Literal["effect"] = "effect"
    title: str
    detail: EffectDetail
    state: EffectState


class PublicCallbackEntry(_PublicHistoryEntryBase):
    type: Literal["callback"] = "callback"
    callback_id: str
    title: str
    detail: CallbackDetail
    state: CallbackState


class ContextClearedNoticeDetail(ProtocolModel):
    kind: Literal["context_cleared"] = "context_cleared"
    plan_file_path: str | None = None


class WaitingForInputNoticeDetail(ProtocolModel):
    kind: Literal["waiting_for_input"] = "waiting_for_input"
    task_id: str
    label: str | None = None
    predefined_answers: list[str] | None = None


NoticeDetail = Annotated[
    ContextClearedNoticeDetail | WaitingForInputNoticeDetail,
    Field(discriminator="kind"),
]


class PublicCheckpointEntry(_PublicHistoryEntryBase):
    type: Literal["checkpoint"] = "checkpoint"
    kind: Literal["compaction"] = "compaction"
    message: str | None = None
    details: JsonValue = None


class PublicNoticeEntry(_PublicHistoryEntryBase):
    type: Literal["notice"] = "notice"
    level: Literal["info", "warning", "error"]
    message: str
    detail: NoticeDetail


PublicHistoryEntry = Annotated[
    PublicMessageEntry
    | PublicReasoningEntry
    | PublicEffectEntry
    | PublicCallbackEntry
    | PublicCheckpointEntry
    | PublicNoticeEntry,
    Field(discriminator="type"),
]


@cache
def _public_history_entry_adapter() -> TypeAdapter[PublicHistoryEntry]:
    return TypeAdapter(PublicHistoryEntry)


def validate_history_entry(value: object) -> PublicHistoryEntry:
    return _public_history_entry_adapter().validate_python(
        value, by_alias=True, by_name=False
    )


class IdleSessionStatus(ProtocolModel):
    type: Literal["idle"] = "idle"


class RunningSessionStatus(ProtocolModel):
    type: Literal["running"] = "running"
    active_turn_id: str


class BlockedSessionStatus(ProtocolModel):
    type: Literal["blocked"] = "blocked"
    active_turn_id: str
    callback_id: str
    reason: str


class FailedSessionStatus(ProtocolModel):
    type: Literal["failed"] = "failed"
    message: str


class ArchivedSessionStatus(ProtocolModel):
    type: Literal["archived"] = "archived"


PublicSessionStatus = Annotated[
    IdleSessionStatus
    | RunningSessionStatus
    | BlockedSessionStatus
    | FailedSessionStatus
    | ArchivedSessionStatus,
    Field(discriminator="type"),
]


class PublicSessionWorktree(ProtocolModel):
    """The managed worktree a session runs in, as the session state reports it.

    Carried on ``PublicSession`` so a client learns the move the moment the
    session does, without waiting for the deferred first turn's transcript
    effect: a session opened and quit without a prompt still knows its
    worktree, which is what an exit cleanup prompt needs.
    """

    name: str
    branch: str
    path: str
    # Whether the run that moved the session created the worktree; reused
    # ones are never auto-cleaned.
    created: bool


class PublicSession(ProtocolModel):
    id: str
    root_session_id: str | None = None
    parent_session_id: str | None = None
    title: str | None = None
    preview: str = ""
    status: PublicSessionStatus
    created_at: int
    updated_at: int
    bumped_at: int | None = None
    pinned_at: int | None = None
    archived_at: int | None = None
    is_unseen: bool = False
    cwd: str | None = None
    workspace_roots: list[str] = Field(default_factory=list)
    # The managed worktree the session runs in, when it does; the additive
    # default keeps old clients and old servers working (ADR 0014).
    worktree: PublicSessionWorktree | None = None
    # What this session runs; ``None`` follows the current default.
    model: str | None = None
    reasoning_effort: str | None = None
    agent: AgentSummary | None = None
    token_usage: TokenUsage | None = None
    context_usage: TokenUsage | None = None
    harness: Literal["legacy", "unified"] | None = None


class PublicChildSession(ProtocolModel):
    id: str
    name: str
    agent_type: str
    status: PublicSessionStatus
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    context_usage: TokenUsage | None = None
    created_at: int
    updated_at: int


class PublicTurn(ProtocolModel):
    id: str
    session_id: str
    status: PublicTurnStatus
    input_entry_id: str | None = None
    started_at: int
    completed_at: int | None = None
    error: PublicError | None = None
    stop_reason: PublicTurnStopReason | None = None
    queue_item_id: str | None = None


class PublicSessionState(ProtocolModel):
    format: Literal["vibe.public-session-state/v1"] = "vibe.public-session-state/v1"
    event_id: int = Field(ge=0, strict=True)
    session: PublicSession
    is_quiescent: bool | None = None
    history: list[PublicHistoryEntry] | None = None
    history_before_cursor: str | None = None
    turns: list[PublicTurn] | None = None
    active_callbacks: list[PublicCallbackEntry] = Field(default_factory=list)
    child_sessions: list[PublicChildSession] = Field(default_factory=list)

    @property
    def latest_turn(self) -> PublicTurn | None:
        if not self.turns:
            return None
        return self.turns[-1]


class JsonPatchOperation(ProtocolModel):
    op: Literal["add", "append", "replace", "remove", "test"]
    path: str
    value: JsonValue = None
