from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime
import uuid

# 1. 定义 Step 的有限状态机
class StepStatus(str, Enum):
    """
    每个具体步骤的生命周期状态。
    严格的状态流转可以避免系统逻辑混乱。
    """
    PENDING = "pending"          # 初始状态，等待依赖完成
    READY = "ready"              # 依赖已完成，可以被调度执行
    RUNNING = "running"          # 正在执行中
    BLOCKED = "blocked"          # 被外部因素阻碍（如等待人工审批）
    DONE = "done"                # 执行成功并产出结果
    FAILED = "failed"            # 执行失败
    SKIPPED = "skipped"          # 被跳过
    WAITING_APPROVAL = "waiting_approval" # 等待人工干预
    NEED_REPLAN = "need_replan"  # 发现当前步骤无法执行，需要重新规划

# 2. 定义具体的 Step 数据结构
class StepState(BaseModel):
    """
    每个步骤单独的生命周期和元数据。
    """
    step_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="步骤的唯一标识")
    title: str = Field(..., description="步骤的简短描述")
    assigned_agent: str = Field(..., description="负责执行该步骤的 Agent 角色名 (如 'executor')")
    dependencies: List[str] = Field(default_factory=list, description="依赖的前置 step_id 列表")
    status: StepStatus = Field(default=StepStatus.PENDING, description="当前步骤的执行状态")
    
    # 输入与输出引用
    input_refs: List[str] = Field(default_factory=list, description="该步骤需要的输入 Artifact ID 列表")
    output_ref: Optional[str] = Field(None, description="该步骤产出的 Artifact ID")
    
    # 执行统计与控制
    retry_count: int = Field(default=0, description="重试次数")
    error: Optional[str] = Field(None, description="失败时的错误堆栈或原因")
    started_at: Optional[datetime] = Field(None, description="开始执行的时间")
    finished_at: Optional[datetime] = Field(None, description="执行结束的时间")
    
    # 验收与版本
    acceptance_criteria: List[str] = Field(default_factory=list, description="验收标准，供 Critic Agent 检查")
    version: int = Field(default=1, description="步骤定义的版本号")

    class Config:
        use_enum_values = True
