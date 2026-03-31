from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime
import uuid

# 1. 定义消息协议的类型
class MessageType(str, Enum):
    """
    Agent 之间、Orchestrator 与 Agent 之间的标准消息类型。
    """
    # 任务分派与结果
    TASK_ASSIGNMENT = "TASK_ASSIGNMENT"   # 分派具体 Step 任务给 Agent
    STEP_RESULT = "STEP_RESULT"           # Agent 完成任务并上报结果
    STEP_FAILURE = "STEP_FAILURE"         # Agent 执行失败上报错误
    
    # 规划与控制流
    REPLAN_REQUEST = "REPLAN_REQUEST"     # 申请重新规划任务
    APPROVAL_REQUEST = "APPROVAL_REQUEST" # 申请人工审批
    
    # 记忆与上下文交互
    MEMORY_QUERY = "MEMORY_QUERY"         # 查询长期或短期记忆
    MEMORY_ADD = "MEMORY_ADD"             # 新增一条记忆 (New)
    MEMORY_RESULT = "MEMORY_RESULT"       # 记忆查询结果
    
    # 验证与审查
    VALIDATION_RESULT = "VALIDATION_RESULT" # Critic Agent 给出的验证结果
    
    # 技能/工具调用 (New)
    SKILL_REQUEST = "SKILL_REQUEST"         # Agent 请求执行某个技能
    SKILL_RESULT = "SKILL_RESULT"           # 系统返回技能执行结果

# 2. 定义标准的消息对象
class Message(BaseModel):
    """
    所有 Agent 之间的通信都统一成 Message Object。
    """
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="消息的唯一标识")
    run_id: str = Field(..., description="所属的 Run ID")
    
    # 路由信息
    sender: str = Field(..., description="发送方标识 (如 'orchestrator' 或 'planner_agent')")
    receiver: str = Field(..., description="接收方标识 (如 'executor_agent')")
    
    # 内容与引用
    type: MessageType = Field(..., description="消息类型")
    payload: Dict[str, Any] = Field(default_factory=dict, description="业务载荷内容")
    refs: List[str] = Field(default_factory=list, description="关联的 Artifact ID 列表")
    
    # 审计与版本
    schema_version: str = Field(default="v1.0", description="消息协议的版本号")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="消息生成时间")
    correlation_id: Optional[str] = Field(None, description="关联的消息 ID，用于追踪请求-响应对")
    priority: int = Field(default=0, description="优先级 (0 为默认值，越高表示越优先)")

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
