from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, Callable
import uuid

class SkillDefinition(BaseModel):
    """
    技能/工具的定义。
    描述了技能是什么、需要什么参数。
    """
    name: str = Field(..., description="技能名称，如 'read_csv'")
    description: str = Field(..., description="技能描述，告诉 Agent 何时该使用它")
    parameters_schema: Dict[str, Any] = Field(default_factory=dict, description="参数的 JSON Schema")
    required_capabilities: list[str] = Field(default_factory=list, description="执行该技能需要的权限")

class SkillResult(BaseModel):
    """
    技能执行的结果。
    """
    skill_name: str
    status: str = "success" # success / failure
    output: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0

class SkillRequest(BaseModel):
    """
    Agent 发出的技能调用请求。
    """
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    skill_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
