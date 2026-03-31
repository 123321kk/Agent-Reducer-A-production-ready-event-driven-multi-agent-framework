from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from enum import Enum
from datetime import datetime
import uuid

class EventType(str, Enum):
    """
    状态变更的原子事件类型。
    """
    # 状态变更
    STATE_UPDATE = "STATE_UPDATE"       # 直接更新 GlobalState 的某些字段
    STEP_STATUS_CHANGE = "STEP_STATUS_CHANGE" # 更新某个 Step 的状态
    ARTIFACT_ADDED = "ARTIFACT_ADDED"   # 成功产生并登记了新的产物
    
    # 任务分派与回收
    AGENT_ASSIGNED = "AGENT_ASSIGNED"   # 记录 Agent 被分派
    AGENT_RELEASED = "AGENT_RELEASED"   # 记录 Agent 执行完毕释放
    
    # 规划
    PLAN_PROPOSED = "PLAN_PROPOSED"     # 成功生成了新的执行规划
    
    # 错误记录
    ERROR_OCCURRED = "ERROR_OCCURRED"   # 记录系统内部发生的非预期错误

class Event(BaseModel):
    """
    原子事件记录，所有的 GlobalState 更新都必须通过 Event 由 Reducer 合并。
    """
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="事件 ID")
    type: str = Field(..., description="事件类型")
    run_id: str = Field(..., description="所属的 Run ID")
    
    # 事件详情
    payload: Dict[str, Any] = Field(default_factory=dict, description="事件携带的具体载荷信息")
    correlation_id: Optional[str] = Field(None, description="触发该事件的消息 ID")
    
    # 审计与追踪
    created_at: datetime = Field(default_factory=datetime.utcnow, description="事件发生时间")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="事件的额外追踪元数据")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
