from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

class Artifact(BaseModel):
    """
    中间产物定义。不要都塞回聊天上下文，
    抽象成 Artifact 可以减小 Context 压力，提高精度。
    """
    artifact_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="产物的唯一标识")
    type: str = Field(..., description="产物类型，如 'search_result', 'table', 'code_patch', 'final_report'")
    owner_step_id: str = Field(..., description="产生该产物的 Step ID")
    
    # 存储路径或内联载荷
    storage_uri: Optional[str] = Field(None, description="如果产物过大（如 CSV 文件），存储在本地或云端的 URI")
    inline_payload: Optional[Any] = Field(None, description="如果产物较小（如 JSON/文本），直接存储载荷内容")
    
    # 摘要与元数据
    summary: Optional[str] = Field(None, description="产物的简短摘要，供其他 Agent 参考")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="其他额外信息（如版本、大小、格式等）")
    version: int = Field(default=1, description="产物的版本号")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
