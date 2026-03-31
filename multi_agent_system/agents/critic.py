from typing import List, Dict, Any, Optional
from .base import BaseAgent
from ..core.models.message import Message, MessageType
from ..core.models.step import StepStatus
from ..services.prompt_manager import prompt_manager
import json

class CriticAgent(BaseAgent):
    """
    审查者智能体 (CriticAgent)。
    职责：
    1. 接收已执行步骤的任务输出产物 (Artifact)。
    2. 根据验收标准 (Acceptance Criteria) 进行校验。
    3. 决定：接受 (Accept)、打回重试 (Reject & Retry) 或打回重规划 (Reject & Replan)。
    """

    def __init__(self, role: str = "critic_agent", model_name: str = "Doubao-2.0"):
        super().__init__(role, model_name)

    async def handle(self, message: Message, context: Dict[str, Any]) -> List[Message]:
        """
        处理分配给 Critic 的验证任务。
        """
        if message.type == MessageType.TASK_ASSIGNMENT:
            return await self._validate_step_result(message, context)
        
        return []

    async def _validate_step_result(self, message: Message, context: Dict[str, Any]) -> List[Message]:
        """
        验证上游步骤产出的 Artifact 是否符合验收标准。
        """
        step_id = message.payload.get("step_id")
        step_title = message.payload.get("title", "Unknown Step")
        goal = context.get("global_goal", "")
        domain_config = context.get("domain_config", {})
        
        # 1. 寻找该步骤相关的 Artifact 引用
        # 假设上游步骤刚完成，Orchestrator 会通过某种方式告诉 Critic 验证哪个步骤
        # 这里简化处理：Critic 接收到的 TASK_ASSIGNMENT 消息中包含了被验证步骤的 step_id
        target_step_id = message.payload.get("target_step_id", step_id)
        target_step_state = context.get("step_states", {}).get(target_step_id)
        
        # 2. 获取 Artifact 内容
        artifact_id = target_step_state.output_ref if target_step_state else None
        artifact = context.get("all_artifacts", {}).get(artifact_id) if artifact_id else None
        
        if not artifact:
            print(f"[{self.role}] Error: No artifact found for step: {target_step_id}")
            return [
                self._create_message(
                    run_id=message.run_id,
                    receiver="orchestrator",
                    msg_type=MessageType.STEP_FAILURE,
                    payload={
                        "step_id": step_id,
                        "error": "No artifact to validate"
                    }
                )
            ]

        # 3. 渲染 Prompt
        prompts = prompt_manager.get_prompt(
            agent_role="critic",
            template_name="default",
            context={
                "global_goal": goal,
                "persona": domain_config.get("personas", {}).get("critic", "审查专家"),
                "target_step_title": target_step_state.title if target_step_state else "Unknown",
                "acceptance_criteria": target_step_state.acceptance_criteria if target_step_state else [],
                "artifact_summary": artifact.summary,
                "artifact_payload": json.dumps(artifact.inline_payload, ensure_ascii=False)
            }
        )

        try:
            # 4. 调用 LLM 进行评审
            response_text = self._call_llm(prompts["user_prompt"], prompts["system_prompt"])
            validation_data = self._parse_json_response(response_text)
            
            # 5. 返回结果消息
            # 这里我们通过 VALIDATION_RESULT 类型告知 Orchestrator
            return [
                self._create_message(
                    run_id=message.run_id,
                    receiver="orchestrator",
                    msg_type=MessageType.VALIDATION_RESULT,
                    payload={
                        "step_id": step_id, # Critic 自己的 step_id
                        "target_step_id": target_step_id, # 被验证的 step_id
                        "decision": validation_data.get("decision", "reject_retry"),
                        "reasoning": validation_data.get("reasoning", ""),
                        "feedback": validation_data.get("feedback", "")
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
                        "error": f"Validation failed: {str(e)}"
                    }
                )
            ]

    def _add_memory(self, run_id: str, content: str, namespace: str, metadata: Dict[str, Any] = None) -> Message:
        """
        向 Orchestrator 请求新增一条长期记忆。
        仅 Critic Agent 有权调用。
        """
        print(f"[{self.role}] Proposing new memory for '{namespace}': {content[:50]}...")
        return self._create_message(
            run_id=run_id,
            receiver="orchestrator",
            msg_type=MessageType.MEMORY_ADD,
            payload={
                "content": content,
                "namespace": namespace,
                "metadata": metadata or {}
            }
        )
