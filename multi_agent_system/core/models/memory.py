from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

class Memory(BaseModel):
    """
    记忆数据模型。
    用于在向量数据库中存储和检索。
    """
    memory_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="记忆的唯一标识")
    namespace: str = Field(..., description="命名空间隔离，如 'qa_rules', 'hard_cases'")
    content: str = Field(..., description="记忆的具体文本内容")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据（作者、时间、引用次数等）")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="记忆创建时间")

class MemoryQuery(BaseModel):
    """
    记忆检索请求。
    """
    query_text: str = Field(..., description="搜索关键词或问题")
    namespace: str = Field(..., description="要检索的命名空间")
    top_k: int = Field(default=3, description="返回最相关的记忆数量")
    min_score: float = Field(default=0.0, description="最低相似度阈值")

class MemoryResult(BaseModel):
    """
    记忆检索结果。
    """
    query_id: str
    memories: List[Memory] = Field(default_factory=list)
    scores: List[float] = Field(default_factory=list, description="相似度得分列表")
