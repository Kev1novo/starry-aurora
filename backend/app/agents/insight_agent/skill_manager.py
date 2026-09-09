"""
Skill 方法论约束管理器
验证用户请求是否满足允许的 Skill 规则（YAML 配置），检查权限与查询范围。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field

from app.core.exceptions import ValidationException

# ---------- Pydantic 模型 ----------


class SkillSchema(BaseModel):
    """Skill 定义的数据模型"""

    name: str
    display_name: str = ""
    description: str = ""
    allowed_models: list[str] = Field(default_factory=list, alias="allowed-models")
    required_permissions: list[str] = Field(default_factory=list, alias="required-permissions")
    max_query_duration_days: int = Field(default=365, alias="max-query-duration-days")
    allowed_datasource_types: list[str] = Field(
        default_factory=list, alias="allowed-datasource-types"
    )
    allowed_actions: list[str] = Field(default_factory=list, alias="allowed-actions")
    requires_attribution: bool = Field(default=False, alias="requires-attribution")
    config: dict[str, Any] = Field(default_factory=dict)


class SkillConstraintResult(BaseModel):
    """Skill 约束校验结果"""

    passed: bool = False
    skill: str = ""
    permissions: list[str] = Field(default_factory=list)
    max_duration_days: int = 365
    allowed_actions: list[str] = Field(default_factory=list)
    requires_attribution: bool = False
    errors: list[str] = Field(default_factory=list)


# ---------- Skill 管理器 ----------


class SkillManager:
    """
    Skill 方法论约束管理器

    职责：
        1. 从 YAML 配置加载所有可用 Skill 定义
        2. 根据用户请求的 intent 匹配对应的 Skill
        3. 校验用户权限、查询范围、数据源类型等约束
    """

    def __init__(self, config_path: Optional[str] = None) -> None:
        self._skills: dict[str, SkillSchema] = {}
        self._config_path = config_path or self._default_config_path()

    # ---------- 公开方法 ----------

    async def load_skills(self) -> dict[str, SkillSchema]:
        """
        从 YAML 配置加载所有 Skill 定义。
        若已加载则直接返回缓存。
        """
        if self._skills:
            return self._skills

        path = Path(self._config_path)
        if not path.exists():
            self._skills = self._builtin_skills()
            return self._skills

        raw = path.read_text(encoding="utf-8")
        data: dict[str, Any] = yaml.safe_load(raw) or {}
        skills_raw: list[dict[str, Any]] = data.get("skills", [])

        for item in skills_raw:
            schema = SkillSchema.model_validate(item)
            self._skills[schema.name] = schema

        # 若 YAML 为空则回退内置配置
        if not self._skills:
            self._skills = self._builtin_skills()

        return self._skills

    async def validate(
        self,
        skill_name: str,
        user_role: str,
        datasource_type: str = "",
        query_duration_days: int = 0,
        user_permissions: Optional[list[str]] = None,
    ) -> SkillConstraintResult:
        """
        校验用户请求是否满足指定 Skill 的约束。

        Args:
            skill_name: 请求的 Skill 名称
            user_role: 用户角色（admin / analyst / viewer）
            datasource_type: 数据源类型（例如 mysql / postgresql / clickhouse）
            query_duration_days: 查询时间跨度（天）
            user_permissions: 用户已具备的权限列表

        Returns:
            SkillConstraintResult 包含校验结果与错误信息

        Raises:
            ValidationException: Skill 名称不存在
        """
        skills = await self.load_skills()
        skill = skills.get(skill_name)
        if skill is None:
            raise ValidationException(
                detail=f"未知的 Skill: {skill_name}，可用: {list(skills.keys())}",
                code="SKILL_NOT_FOUND",
            )

        errors: list[str] = []
        perms = user_permissions or []

        # 1. 权限检查
        for req_perm in skill.required_permissions:
            if req_perm not in perms:
                errors.append(f"缺少必要权限: {req_perm}")

        # 2. 角色兜底检查：viewer 角色不可写
        if user_role == "viewer" and skill.name != "dashboard-view":
            errors.append("viewer 角色仅允许 dashboard-view 操作")

        # 3. 数据源类型
        if datasource_type and skill.allowed_datasource_types:
            if datasource_type not in skill.allowed_datasource_types:
                errors.append(
                    f"数据源类型 '{datasource_type}' 不在 Skill 允许范围内: {skill.allowed_datasource_types}"
                )

        # 4. 查询时间跨度
        if query_duration_days > skill.max_query_duration_days:
            errors.append(
                f"查询时间跨度 {query_duration_days} 天超过 Skill 允许上限 {skill.max_query_duration_days} 天"
            )

        return SkillConstraintResult(
            passed=len(errors) == 0,
            skill=skill_name,
            permissions=skill.required_permissions,
            max_duration_days=skill.max_query_duration_days,
            allowed_actions=skill.allowed_actions,
            requires_attribution=skill.requires_attribution,
            errors=errors,
        )

    async def get_skill(self, skill_name: str) -> Optional[SkillSchema]:
        """按名称获取 Skill 定义"""
        skills = await self.load_skills()
        return skills.get(skill_name)

    async def list_skills(self) -> list[dict[str, Any]]:
        """列出所有可用 Skill 的摘要信息"""
        skills = await self.load_skills()
        return [
            {
                "name": s.name,
                "display_name": s.display_name or s.name,
                "description": s.description,
                "allowed_actions": s.allowed_actions,
            }
            for s in skills.values()
        ]

    # ---------- 内置 Skill ----------

    def _builtin_skills(self) -> dict[str, SkillSchema]:
        """若无配置文件时返回的内置 Skill 定义"""
        return {
            "data-query": SkillSchema(
                name="data-query",
                display_name="数据查询",
                description="对已接入数据源进行自然语言查询",
                allowed_models=["gpt-4o", "deepseek-chat"],
                required_permissions=["query:execute"],
                allowed_actions=["ask", "explain", "chart"],
            ),
            "data-explore": SkillSchema(
                name="data-explore",
                display_name="数据探索",
                description="对数据源进行探索性分析",
                allowed_models=["gpt-4o"],
                required_permissions=["query:execute", "schema:read"],
                max_query_duration_days=90,
                allowed_actions=["ask", "explain", "chart", "pivot"],
            ),
            "attribution-analysis": SkillSchema(
                name="attribution-analysis",
                display_name="归因分析",
                description="执行营销归因计算（如首次触点、末次触点、马尔可夫链等）",
                allowed_models=["gpt-4o"],
                required_permissions=["attribution:run"],
                requires_attribution=True,
                allowed_actions=["calculate", "compare", "report"],
            ),
            "dashboard-view": SkillSchema(
                name="dashboard-view",
                display_name="仪表盘查看",
                description="查看已发布的报表与仪表盘",
                required_permissions=["dashboard:read"],
                allowed_actions=["view", "export"],
            ),
        }

    # ---------- 私有帮助 ----------

    @staticmethod
    def _default_config_path() -> str:
        """返回默认的 Skill 配置文件路径"""
        return str(Path(__file__).resolve().parent.parent.parent.parent / "config" / "skills.yaml")