"""
Insight Agent——业务编排层·大脑/总指挥

职责：
    1. 读取并解析用户意图（intent）
    2. 应用 Skill 方法论约束校验
    3. 维护工作区与附件上下文
    4. 将任务委派给 NL2SQL Agent 或归因模型
    5. 管理消息的持久化与事件发布
    6. 跟踪整个编排流程的状态

编排流程：
    validate_input → resolve_intent → check_skill → prepare_context
        → delegate (NL2SQL / attribution) → format_output → publish_events
"""

from __future__ import annotations

import re
import time
import uuid
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.core.exceptions import AppException, PermissionException, ValidationException

from .attachment_manager import AttachmentManager
from .message_bus import EventType, MessageBus
from .skill_manager import SkillConstraintResult, SkillManager
from .workspace_manager import WorkspaceManager

# ---------- 枚举 ----------


class AgentTaskType(str, Enum):
    """编排任务类型"""

    NL2SQL_QUERY = "nl2sql_query"
    NL2SQL_EXPLAIN = "nl2sql_explain"
    ATTRIBUTION_CALCULATE = "attribution_calculate"
    ATTRIBUTION_COMPARE = "attribution_compare"
    DASHBOARD_VIEW = "dashboard_view"
    UNKNOWN = "unknown"


class OrchestrationStatus(str, Enum):
    """编排状态"""

    PENDING = "pending"
    VALIDATING = "validating"
    RESOLVING = "resolving"
    CHECKING_SKILL = "checking_skill"
    PREPARING = "preparing"
    DELEGATING = "delegating"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ---------- Pydantic 模型 ----------


class InsightInput(BaseModel):
    """Insight Agent 输入模型"""

    question: str = Field(..., min_length=1, max_length=2000, description="用户自然语言问题")
    user_id: int = Field(..., description="用户 ID")
    user_role: str = Field(default="analyst", description="用户角色")
    user_permissions: list[str] = Field(default_factory=list, description="用户权限列表")
    conversation_id: Optional[str] = Field(
        None, max_length=64, description="会话 ID（用于多轮对话）"
    )
    workspace_id: Optional[int] = Field(None, description="工作区 ID")
    datasource_id: Optional[int] = Field(None, description="数据源 ID")
    datasource_type: str = Field(default="", description="数据源类型")
    attached_file_ids: list[int] = Field(default_factory=list, description="附件文件 ID 列表")


class IntentResult(BaseModel):
    """意图解析结果"""

    intent: str = ""
    task_type: AgentTaskType = AgentTaskType.UNKNOWN
    skill_name: str = ""
    confidence: float = 0.0
    entities: dict[str, Any] = Field(default_factory=dict)
    time_range: Optional[dict[str, Any]] = None


class OrchestrationResult(BaseModel):
    """编排结果"""

    orchestration_id: str = ""
    status: OrchestrationStatus = OrchestrationStatus.PENDING
    intent: Optional[IntentResult] = None
    skill_result: Optional[SkillConstraintResult] = None
    delegate_result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    elapsed_ms: float = 0.0


# ---------- 编排器 ----------


class InsightAgent(BaseAgent):
    """
    Insight Agent——业务编排层·大脑/总指挥

    作为系统唯一的编排入口，负责：
        - 理解用户输入并解析意图
        - 校验 Skill 约束（权限、范围、角色）
        - 管理工作区与附件上下文
        - 委派任务到 NL2SQL Agent 或归因模型
        - 发布编排事件到消息总线
    """

    name: str = "insight_agent"
    description: str = "业务编排层——大脑/总指挥，负责意图解析、Skill 校验与任务委派"

    # ---------- 初始化 ----------

    def __init__(
        self,
        db: AsyncSession,
        redis_client: Optional[Any] = None,
        skill_manager: Optional[SkillManager] = None,
        workspace_manager: Optional[WorkspaceManager] = None,
        attachment_manager: Optional[AttachmentManager] = None,
        message_bus: Optional[MessageBus] = None,
    ) -> None:
        self.db = db
        self.skill_mgr = skill_manager or SkillManager()
        self.workspace_mgr = WorkspaceManager(db) if workspace_manager is None else workspace_manager
        self.attachment_mgr = AttachmentManager(db) if attachment_manager is None else attachment_manager
        self.message_bus = message_bus or MessageBus(redis=redis_client)

        # 运行时状态
        self._current_input: Optional[InsightInput] = None
        self._current_intent: Optional[IntentResult] = None
        self._current_result: Optional[OrchestrationResult] = None
        self._orchestration_id: str = ""

    # ---------- BaseAgent 接口实现 ----------

    async def run(self, input_data: dict, **kwargs: Any) -> dict[str, Any]:
        """
        编排入口：执行完整的编排流程。

        Args:
            input_data: 输入字典（将转换为 InsightInput）
            **kwargs: 额外参数（传递给编排步骤）

        Returns:
            OrchestrationResult 的 dict 表示
        """
        start = time.perf_counter()
        self._orchestration_id = uuid.uuid4().hex

        try:
            # 1. 校验输入
            validated = await self.validate_input(input_data)
            if not validated:
                raise ValidationException(detail="输入参数校验失败")

            # 2. 意图解析
            intent = await self._resolve_intent()

            # 3. Skill 约束检查
            skill_result = await self._check_skill(intent)

            # 4. 准备上下文
            context = await self._prepare_context()

            # 5. 委派任务
            delegate_result = await self._delegate(intent, context, **kwargs)

            # 完成
            elapsed = (time.perf_counter() - start) * 1000
            result = OrchestrationResult(
                orchestration_id=self._orchestration_id,
                status=OrchestrationStatus.COMPLETED,
                intent=intent,
                skill_result=skill_result,
                delegate_result=delegate_result,
                elapsed_ms=round(elapsed, 2),
            )
            self._current_result = result

            # 发送完成事件
            await self._emit_event(EventType.QUERY_COMPLETED, result)

            return result.model_dump(mode="json")

        except AppException:
            elapsed = (time.perf_counter() - start) * 1000
            result = OrchestrationResult(
                orchestration_id=self._orchestration_id,
                status=OrchestrationStatus.FAILED,
                error="编排过程中发生业务异常",
                elapsed_ms=round(elapsed, 2),
            )
            self._current_result = result
            await self._emit_event(EventType.QUERY_FAILED, result)
            raise

        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            result = OrchestrationResult(
                orchestration_id=self._orchestration_id,
                status=OrchestrationStatus.FAILED,
                error=f"未预期的编排异常: {exc}",
                elapsed_ms=round(elapsed, 2),
            )
            self._current_result = result
            await self._emit_event(EventType.ERROR_OCCURRED, result)
            raise

    async def validate_input(self, input_data: dict) -> bool:
        """
        校验并转换输入数据。

        Returns:
            True 表示校验通过

        Raises:
            ValidationException: 输入不合法
        """
        try:
            self._current_input = InsightInput(**input_data)
            return True
        except Exception as exc:
            raise ValidationException(detail=f"输入参数无效: {exc}") from exc

    def parse_result(self, result: dict) -> dict[str, Any]:
        """解析并标准化编排结果"""
        return OrchestrationResult(**result).model_dump(mode="json")

    # ---------- 外部便捷接口 ----------

    async def handle_query(
        self,
        question: str,
        user_id: int,
        datasource_id: int | None = None,
        conversation_id: int | None = None,
    ) -> dict[str, Any]:
        """对外便捷接口：处理 NL2SQL 查询"""
        result = await self.run({
            "question": question,
            "user_id": user_id,
            "datasource_id": datasource_id,
            "conversation_id": conversation_id,
        })
        return result.get("delegate_result", result)

    async def handle_attribution(
        self,
        model_name: str,
        datasource_id: int,
        touchpoint_table: str,
        conversion_table: str,
        time_range: dict | None = None,
        user_id: int = 0,
        params: dict | None = None,
    ) -> dict[str, Any]:
        """对外便捷接口：处理归因分析"""
        result = await self.run({
            "question": f"归因分析：模型={model_name} 数据源ID={datasource_id}",
            "user_id": user_id,
            "datasource_id": datasource_id,
            "task_type": AgentTaskType.ATTRIBUTION_CALCULATE.value,
            "attribution_params": {
                "model": model_name,
                "touchpoint_table": touchpoint_table,
                "conversion_table": conversion_table,
                "time_range": time_range or {},
                "params": params or {},
            },
        })
        return result.get("delegate_result", result)

    async def handle_query_stream(
        self,
        question: str,
        user_id: int,
        datasource_id: int | None = None,
        conversation_id: int | None = None,
    ):
        """流式查询——逐步产出 DataAgent 的中间事件"""
        from app.agents.nl2sql_agent.agent import DataAgent

        try:
            validated = InsightInput(
                question=question,
                user_id=user_id,
                datasource_id=datasource_id,
                conversation_id=conversation_id,
            )
            self._current_input = validated
        except Exception as exc:
            yield {"type": "error", "data": {"error": f"参数错误: {exc}"}}
            return

        # 解析意图并输出
        intent = await self._resolve_intent()
        yield {"type": "intent", "data": {"intent": intent.intent, "confidence": intent.confidence}}

        if intent.task_type in (AgentTaskType.NL2SQL_QUERY, AgentTaskType.NL2SQL_EXPLAIN):
            data_agent = DataAgent(db=self.db)
            ds_id = datasource_id or self._current_input.datasource_id

            # 转发 DataAgent 流式事件
            async for event in data_agent.stream_run({
                "question": question,
                "user_id": user_id,
                "datasource_id": ds_id,
                "conversation_id": conversation_id,
            }):
                yield event
        else:
            yield {"type": "result", "data": {"message": f"不支持流式处理: {intent.intent}"}}
            yield {"type": "done", "data": {}}

    async def handle_attribution_stream(
        self,
        model_name: str,
        datasource_id: int,
        touchpoint_table: str,
        conversion_table: str,
        time_range: dict | None = None,
        user_id: int = 0,
        params: dict | None = None,
    ):
        """流式归因——逐步产出归因模型的中间事件"""
        yield {"type": "start", "data": {"model": model_name, "message": "开始加载归因数据..."}}

        try:
            import pandas as pd
            touchpoints, conversions = await self._load_attribution_data(
                datasource_id=datasource_id,
                touchpoint_table=touchpoint_table,
                conversion_table=conversion_table,
                time_range=time_range or {},
            )
            yield {"type": "progress", "data": {"message": f"数据加载完成: {len(touchpoints)} 条触点, {len(conversions)} 条转化"}}

            from app.agents.attribution_models.registry import registry
            model = registry.get(model_name)
            yield {"type": "progress", "data": {"message": f"开始归因计算: {model_name}"}}

            result = await model.calculate(
                touchpoints=touchpoints,
                conversions=conversions,
                **(params or {}),
            )
            yield {"type": "result", "data": {"model": model_name, "result": result}}
        except KeyError as e:
            yield {"type": "error", "data": {"error": f"未知归因模型: {e}"}}
        except Exception as e:
            yield {"type": "error", "data": {"error": f"归因计算异常: {e}"}}

        yield {"type": "done", "data": {}}

    async def _resolve_intent(self) -> IntentResult:
        """
        意图解析步骤。

        根据用户问题判断任务类型与匹配的 Skill。
        MVP 阶段采用简单的关键词 + 规则匹配，
        后续可替换为 LLM-based 意图分类。

        Returns:
            IntentResult 实例
        """
        input_data = self._current_input
        assert input_data is not None

        question = input_data.question.lower()

        # 规则匹配引擎（MVP）
        intent = IntentResult(
            task_type=AgentTaskType.UNKNOWN,
            confidence=0.0,
        )

        # 归因分析关键词
        attribution_keywords = ["归因", "attribution", "贡献", "触点", "转化", "渠道"]
        if any(kw in question for kw in attribution_keywords):
            intent = IntentResult(
                intent="attribution_analysis",
                task_type=AgentTaskType.ATTRIBUTION_CALCULATE,
                skill_name="attribution-analysis",
                confidence=0.8,
                entities={"keywords": [kw for kw in attribution_keywords if kw in question]},
            )
        # 数据查询/探索
        business_keywords = ["销售", "金额", "收入", "利润", "成本", "增长", "环比", "同比", "占比",
                            "上月", "本月", "上个月", "这个月", "最近", "昨天", "今天", "本周",
                            "总", "合计", "平均", "最高", "最低", "前"]
        if any(kw in question for kw in ["查询", "多少", "统计", "趋势", "对比", "排名"]):
            intent = IntentResult(
                intent="data_query",
                task_type=AgentTaskType.NL2SQL_QUERY,
                skill_name="data-query",
                confidence=0.9,
            )
        elif any(kw in question for kw in business_keywords):
            intent = IntentResult(
                intent="data_query",
                task_type=AgentTaskType.NL2SQL_QUERY,
                skill_name="data-query",
                confidence=0.7,
            )

        # 仪表盘
        elif "仪表盘" in question or "dashboard" in question:
            intent = IntentResult(
                intent="dashboard_view",
                task_type=AgentTaskType.DASHBOARD_VIEW,
                skill_name="dashboard-view",
                confidence=0.85,
            )

        # Fallback：有内容的非空问题但无规则匹配时默认 NL2SQL
        if intent.task_type == AgentTaskType.UNKNOWN and len(question.strip()) > 0:
            intent = IntentResult(
                intent="data_query",
                task_type=AgentTaskType.NL2SQL_QUERY,
                skill_name="data-query",
                confidence=0.5,
            )

        self._current_intent = intent
        await self._emit_event(EventType.QUERY_STARTED, {"intent": intent.model_dump()})
        return intent

    async def _check_skill(self, intent: IntentResult) -> SkillConstraintResult:
        """
        Skill 约束检查步骤。

        根据意图解析出的 Skill 名称，校验用户是否具备相应权限与范围。

        Args:
            intent: 意图解析结果

        Returns:
            SkillConstraintResult 实例

        Raises:
            PermissionException: Skill 校验不通过
        """
        input_data = self._current_input
        assert input_data is not None

        result = await self.skill_mgr.validate(
            skill_name=intent.skill_name or "",
            user_role=input_data.user_role,
            datasource_type=input_data.datasource_type,
            query_duration_days=self._estimate_duration(intent),
            user_permissions=input_data.user_permissions,
        )

        if not result.passed:
            raise PermissionException(
                detail=f"Skill 约束检查不通过: {'; '.join(result.errors)}",
                code="SKILL_CONSTRAINT_FAILED",
            )

        return result

    async def _prepare_context(self) -> dict[str, Any]:
        """
        准备上下文步骤。

        获取当前活跃工作区信息、关联数据源、附件列表等上下文数据，
        供下游 Agent 使用。

        Returns:
            上下文字典
        """
        input_data = self._current_input
        assert input_data is not None

        context: dict[str, Any] = {
            "user_id": input_data.user_id,
            "workspace_id": input_data.workspace_id,
            "datasource_id": input_data.datasource_id,
            "conversation_id": input_data.conversation_id,
        }

        # 获取工作区信息
        if input_data.workspace_id is not None:
            try:
                ws = await self.workspace_mgr.get(
                    input_data.workspace_id, input_data.user_id
                )
                source_ids = await self.workspace_mgr.get_data_source_ids(
                    input_data.workspace_id, input_data.user_id
                )
                context["workspace_name"] = ws.name
                context["datasource_ids"] = source_ids
            except Exception:
                context["datasource_ids"] = []

        # 获取附件信息
        if input_data.attached_file_ids:
            attached = []
            for fid in input_data.attached_file_ids:
                try:
                    att = await self.attachment_mgr.get(fid, input_data.user_id)
                    attached.append({
                        "id": att.id,
                        "file_name": att.file_name,
                        "file_type": att.file_type,
                    })
                except Exception:
                    continue
            context["attachments"] = attached

        return context

    async def _delegate(
        self,
        intent: IntentResult,
        context: dict[str, Any],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        委派步骤。

        根据意图类型将任务委派给对应的下游 Agent 或归因模型。

        Args:
            intent: 意图解析结果
            context: 上下文数据
            **kwargs: 额外参数（包含 attribution_params 等）

        Returns:
            委派任务的结果字典
        """
        await self._emit_event(EventType.QUERY_STARTED, {"delegating": intent.task_type.value})

        if intent.task_type in (AgentTaskType.NL2SQL_QUERY, AgentTaskType.NL2SQL_EXPLAIN):
            return await self._delegate_to_data_agent(intent, context, **kwargs)
        elif intent.task_type == AgentTaskType.ATTRIBUTION_CALCULATE:
            return await self._delegate_to_attribution(intent, context, **kwargs)
        else:
            return {
                "delegated_to": intent.task_type.value,
                "status": "unsupported",
                "error": f"不支持的任务类型: {intent.task_type.value}",
            }

    async def _delegate_to_data_agent(
        self,
        intent: IntentResult,
        context: dict[str, Any],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """委派 NL2SQL 查询任务到 DataAgent"""
        from app.agents.nl2sql_agent.agent import DataAgent

        data_agent = DataAgent(db=self.db)

        input_data = {
            "question": self._current_input.question if self._current_input else "",
            "user_id": self._current_input.user_id if self._current_input else 0,
            "datasource_id": context.get("datasource_id"),
            "conversation_id": context.get("conversation_id"),
        }

        result = await data_agent.run(input_data)
        return {
            "delegated_to": "data_agent",
            "task_type": intent.task_type.value,
            "result": result,
        }

    async def _delegate_to_attribution(
        self,
        intent: IntentResult,
        context: dict[str, Any],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """委派归因分析任务到归因模型"""
        from app.agents.attribution_models.registry import registry

        attribution_params = kwargs.get("attribution_params", {})
        model_name = attribution_params.get("model", "")
        datasource_id = attribution_params.get("datasource_id") or context.get("datasource_id")

        try:
            model = registry.get(model_name)
        except KeyError as e:
            return {
                "delegated_to": "attribution_model",
                "status": "error",
                "error": str(e),
            }

        # 加载触点和转化数据
        touchpoints, conversions = await self._load_attribution_data(
            datasource_id=datasource_id,
            touchpoint_table=attribution_params.get("touchpoint_table"),
            conversion_table=attribution_params.get("conversion_table"),
            time_range=attribution_params.get("time_range", {}),
        )

        # 执行归因计算
        result = await model.calculate(
            touchpoints=touchpoints,
            conversions=conversions,
            **attribution_params.get("params", {}),
        )

        return {
            "delegated_to": f"attribution_model/{model_name}",
            "model": model_name,
            "result": result,
        }

    async def _load_attribution_data(
        self,
        datasource_id: int | None,
        touchpoint_table: str | None,
        conversion_table: str | None,
        time_range: dict,
    ) -> tuple[Any, Any]:
        """
        加载归因分析所需的触点数据和转化数据。

        MVP 阶段：从 DataSource 连接读取数据。
        返回 (touchpoints_df, conversions_df)。
        """
        import pandas as pd

        if not all([datasource_id, touchpoint_table, conversion_table]):
            return pd.DataFrame(), pd.DataFrame()

        try:
            from app.repositories.datasource_repo import DataSourceRepository
            from sqlalchemy import text

            repo = DataSourceRepository(self.db)
            ds = await repo.get_by_id(datasource_id)
            if not ds or not ds.config:
                return pd.DataFrame(), pd.DataFrame()

            config = ds.config

            # 校验表名防止 SQL 注入
            tp_table = self._sanitize_table_name(touchpoint_table)
            cv_table = self._sanitize_table_name(conversion_table)

            if config.get("connection_uri", "").startswith("mysql"):
                import aiomysql

                conn = await aiomysql.connect(
                    host=config.get("host", "localhost"),
                    port=config.get("port", 3306),
                    user=config.get("username", "root"),
                    password=config.get("password", ""),
                    db=config.get("database", ""),
                    charset="utf8mb4",
                )
                try:
                    async with conn.cursor() as cursor:
                        start = time_range.get("start", "")
                        end = time_range.get("end", "")
                        where_clause = ""
                        if start and end:
                            # 转义单引号防止注入
                            safe_start = start.replace("'", "''")
                            safe_end = end.replace("'", "''")
                            where_clause = f" WHERE time BETWEEN '{safe_start}' AND '{safe_end}'"

                        await cursor.execute(f"SELECT * FROM {tp_table}{where_clause} LIMIT 50000")
                        tp_cols = [d[0] for d in cursor.description]
                        tp_rows = await cursor.fetchall()

                        await cursor.execute(f"SELECT * FROM {cv_table}{where_clause} LIMIT 50000")
                        cv_cols = [d[0] for d in cursor.description]
                        cv_rows = await cursor.fetchall()
                finally:
                    await conn.close()

                return pd.DataFrame(tp_rows, columns=tp_cols) if tp_rows else pd.DataFrame(), \
                       pd.DataFrame(cv_rows, columns=cv_cols) if cv_rows else pd.DataFrame()
            else:
                return pd.DataFrame(), pd.DataFrame()

        except Exception:
            return pd.DataFrame(), pd.DataFrame()

    # ---------- 事件发布 ----------

    async def _emit_event(self, event_type: EventType, data: Any) -> None:
        """
        发布编排事件到消息总线。

        Args:
            event_type: 事件类型
            data: 事件关联数据
        """
        try:
            payload = (
                data.model_dump(mode="json")
                if isinstance(data, BaseModel)
                else data
            )
            message = self.message_bus.build_message(
                event_type=event_type,
                data=payload or {},
                user_id=self._current_input.user_id if self._current_input else None,
                conversation_id=self._current_input.conversation_id if self._current_input else None,
            )
            # 发布到 Redis 事件总线并持久化
            await self.message_bus.publish_event(message)
            await self.message_bus.store_message(message)
        except Exception:
            # 事件发布失败不应影响主流程
            pass

    # ---------- 工具方法 ----------

    @staticmethod
    def _estimate_duration(intent: IntentResult) -> int:
        """根据意图估计查询时间跨度（天），用于 Skill 约束检查"""
        tr = intent.time_range
        if tr is None:
            return 0
        start = tr.get("start")
        end = tr.get("end")
        if start and end:
            try:
                from datetime import datetime

                s = datetime.fromisoformat(start)
                e = datetime.fromisoformat(end)
                return (e - s).days
            except (ValueError, TypeError):
                pass
        return 0

    @staticmethod
    def _sanitize_table_name(name: str) -> str:
        """校验表名只含安全字符，防止 SQL 注入"""
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_.]*$', name):
            raise ValueError(f"非法表名: {name}")
        return name


# ---------- 快捷工厂 ----------


async def create_insight_agent(
    db: AsyncSession,
    redis_client: Optional[Any] = None,
) -> InsightAgent:
    """创建配置完成的 Insight Agent 实例"""
    return InsightAgent(
        db=db,
        redis_client=redis_client,
    )
