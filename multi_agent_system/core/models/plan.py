from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from .step import StepState

class PlanProposal(BaseModel):
    """
    Planner Agent 产出的初步规划提议。
    Agent 提议的是意图，而非直接修改 GlobalState。
    """
    plan_id: str = Field(..., description="规划 ID")
    steps: List[StepState] = Field(..., description="初始生成的步骤列表")
    reasoning: str = Field(..., description="规划的逻辑说明")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")

class PlanPatchProposal(BaseModel):
    """
    当任务执行中发现需要局部调整时，Planner 产出的补丁提议。
    """
    patch_id: str = Field(..., description="补丁 ID")
    steps_to_add: List[StepState] = Field(default_factory=list, description="需要新增的步骤")
    steps_to_update: List[StepState] = Field(default_factory=list, description="需要修改状态或内容的步骤")
    steps_to_remove: List[str] = Field(default_factory=list, description="需要删除的步骤 ID 列表")
    reasoning: str = Field(..., description="为什么要打补丁的理由")
