from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

# 导入已经定义的子模型
from .step import StepState
from .artifact import Artifact

class GlobalState(BaseModel):
    """
    整个 Run 的单一事实来源 (Single Source of Truth)。
    代码层面它不是 Prompt 文本，而是一个结构化对象，
    代表了整个系统的“世界状态”。
    """
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Run 的唯一标识")
    goal: str = Field(..., description="最终目标，如 '清洗 2023 年 10 月的数据集'")
    status: str = Field(default="initialized", description="整体运行状态 (如 'initialized', 'running', 'completed', 'failed')")
    
    # 规划与步骤
    plan_version: int = Field(default=0, description="当前规划的版本，每次重规划 +1")
    step_states: Dict[str, StepState] = Field(default_factory=dict, description="所有 Step 的状态机容器")
    
    # 资源与上下文
    artifacts: Dict[str, Artifact] = Field(default_factory=dict, description="所有产物引用容器")
    constraints: List[str] = Field(default_factory=list, description="全局限制，供 Agent 决策参考")
    domain_config: Dict[str, Any] = Field(default_factory=dict, description="领域/角色配置，如 personas")
    shared_context_refs: List[str] = Field(default_factory=list, description="共享上下文的 Artifact ID 引用")
    
    # 消息总线与控制流
    pending_messages: List[str] = Field(default_factory=list, description="等待处理的消息 ID 列表")
    active_agents: List[str] = Field(default_factory=list, description="当前活跃或正在执行任务的 Agent")
    
    # 审计与版本控制
    checkpoint_meta: Dict[str, Any] = Field(default_factory=dict, description="断点续传所需的元数据")
    audit_meta: Dict[str, Any] = Field(default_factory=dict, description="用于审计的元数据（如耗时、Token 消耗等）")
    version: int = Field(default=1, description="GlobalState 本身的状态版本号")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="最后更新时间")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
