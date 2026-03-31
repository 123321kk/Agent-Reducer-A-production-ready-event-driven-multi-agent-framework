from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import json
import os
import sys

# 确保能导入 utils 目录下的 volc_clients
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from utils.volc_clients import LLMChatClient

from ..core.models.message import Message, MessageType

class BaseAgent(ABC):
    """
    所有 Agent 的抽象基类。
    封装了通用的 LLM 调用、Prompt 构建、输出解析和错误处理逻辑。
    """

    def __init__(self, role: str, model_name: str = "Doubao-2.0"):
        self.role = role
        self.model_name = model_name
        # 初始化 LLM 客户端
        self.llm_client = LLMChatClient(default_model=model_name)

    @abstractmethod
    async def handle(self, message: Message, context: Dict[str, Any]) -> List[Message]:
        """
        核心处理逻辑，子类必须实现。
        给定一条消息和受控上下文，产出后续消息建议。
        """
        pass

    def _call_llm(self, prompt: str, system_prompt: str = "") -> str:
        """
        统一的 LLM 调用入口。
        """
        try:
            print(f"[{self.role}] Calling LLM ({self.model_name})...")
            response = self.llm_client.get_response(
                user_input=prompt,
                system_prompt=system_prompt,
                model=self.model_name
            )
            return response
        except Exception as e:
            print(f"[{self.role}] LLM Call Error: {str(e)}")
            raise e

    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """
        尝试从模型返回的文本中解析 JSON。
        """
        try:
            # 简单清洗：去除可能存在的 markdown 代码块标记
            cleaned_text = response_text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()
            
            return json.loads(cleaned_text)
        except json.JSONDecodeError as e:
            print(f"[{self.role}] Failed to parse JSON from response: {response_text}")
            raise ValueError(f"Invalid JSON response from LLM: {str(e)}")

    def _create_message(self, run_id: str, receiver: str, msg_type: MessageType, payload: Dict[str, Any]) -> Message:
        """
        便捷的消息创建方法。
        """
        return Message(
            run_id=run_id,
            sender=self.role,
            receiver=receiver,
            type=msg_type,
            payload=payload
        )

    def _request_skill(self, run_id: str, skill_name: str, arguments: Dict[str, Any]) -> Message:
        """
        向 Orchestrator 请求执行一个技能。
        """
        print(f"[{self.role}] Requesting skill: {skill_name} with args: {arguments}")
        return self._create_message(
            run_id=run_id,
            receiver="orchestrator",
            msg_type=MessageType.SKILL_REQUEST,
            payload={
                "skill_name": skill_name,
                "arguments": arguments
            }
        )

    def _query_memory(self, run_id: str, query_text: str, namespace: str, top_k: int = 3) -> Message:
        """
        向 Orchestrator 请求查询记忆。
        """
        print(f"[{self.role}] Querying memory in '{namespace}': {query_text}")
        return self._create_message(
            run_id=run_id,
            receiver="orchestrator",
            msg_type=MessageType.MEMORY_QUERY,
            payload={
                "query_text": query_text,
                "namespace": namespace,
                "top_k": top_k
            }
        )
