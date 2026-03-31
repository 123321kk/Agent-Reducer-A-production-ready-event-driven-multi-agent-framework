from typing import List, Dict, Any, Optional
from .base import BaseAgent
from ..core.models.message import Message, MessageType
from ..core.models.artifact import Artifact
from ..services.prompt_manager import prompt_manager
import uuid

class ExecutorAgent(BaseAgent):
    """
    执行者智能体 (ExecutorAgent)。
    职责：
    1. 接收具体步骤任务。
    2. 执行任务逻辑（调用 LLM 或工具）。
    3. 产出中间产物 (Artifact)。
    """

    def __init__(self, role: str = "executor_agent", model_name: str = "Doubao-2.0"):
        super().__init__(role, model_name)

    async def handle(self, message: Message, context: Dict[str, Any]) -> List[Message]:
        """
        处理分配给 Executor 的任务。
        """
        if message.type == MessageType.TASK_ASSIGNMENT:
            return await self._execute_step(message, context)
        
        return []

    async def _execute_step(self, message: Message, context: Dict[str, Any]) -> List[Message]:
        """
        执行具体步骤的逻辑。
        """
        step_id = message.payload.get("step_id")
        step_title = message.payload.get("title", "Unknown Step")
        goal = context.get("global_goal", "")
        domain_config = context.get("domain_config", {})
        
        # 获取该步骤的详细状态定义
        step_state = context.get("step_states", {}).get(step_id)
        acceptance_criteria = step_state.acceptance_criteria if step_state else []

        print(f"[{self.role}] Executing step: {step_title}")

        # 1. 渲染 Prompt
        prompts = prompt_manager.get_prompt(
            agent_role="executor",
            template_name="default",
            context={
                "global_goal": goal,
                "persona": domain_config.get("personas", {}).get("executor", "执行专家"),
                "step_title": step_title,
                "acceptance_criteria": acceptance_criteria,
                "input_context": "No specific input context provided."
            }
        )

        try:
            # 2. 调用 LLM 模拟执行
            response_text = self._call_llm(prompts["user_prompt"], prompts["system_prompt"])
            result_data = self._parse_json_response(response_text)

            # 3. 创建产物 (Artifact)
            artifact = Artifact(
                type="step_output",
                owner_step_id=step_id,
                inline_payload=result_data.get("detail_output"),
                summary=result_data.get("summary"),
                metadata={"step_title": step_title}
            )

            # 4. 返回 STEP_RESULT 消息
            return [
                self._create_message(
                    run_id=message.run_id,
                    receiver="orchestrator",
                    msg_type=MessageType.STEP_RESULT,
                    payload={
                        "step_id": step_id,
                        "artifact": artifact
                    }
                )
            ]

        except Exception as e:
            return [
                self._create_message(
                    run_id=message.run_id,
                    receiver="orchestrator",
                    msg_type=MessageType.STEP_FAILURE,
                    payload={
                        "step_id": step_id,
                        "error": f"Execution failed: {str(e)}"
                    }
                )
            ]
