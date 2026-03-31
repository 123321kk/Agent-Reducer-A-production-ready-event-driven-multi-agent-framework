from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import uuid

from .base import BaseAgent
from ..core.models.message import Message, MessageType
from ..core.models.step import StepState, StepStatus
from ..services.prompt_manager import prompt_manager

class PlannerAgent(BaseAgent):
    """
    规划者智能体 (PlannerAgent)。
    职责：
    1. 接收最终目标。
    2. 生成分步计划 (Plan)。
    3. 在任务执行失败或环境变化时，进行重规划 (Replan)。
    """

    def __init__(self, role: str = "planner_agent", model_name: str = "Doubao-2.0"):
        super().__init__(role, model_name)

    async def handle(self, message: Message, context: Dict[str, Any]) -> List[Message]:
        """
        处理分配给 Planner 的任务。
        """
        if message.type == MessageType.TASK_ASSIGNMENT:
            # 执行初始规划逻辑
            return await self._plan(message, context)
        elif message.type == MessageType.REPLAN_REQUEST:
            # 执行重规划逻辑
            return await self._replan(message, context)
        
        return []

    async def _plan(self, message: Message, context: Dict[str, Any]) -> List[Message]:
        """
        根据目标生成初始计划。
        """
        goal = context.get("global_goal", "No goal provided")
        domain_config = context.get("domain_config", {})
        print(f"[{self.role}] Generating plan for goal: {goal}")

        # 1. 渲染 Prompt
        prompts = prompt_manager.get_prompt(
            agent_role="planner",
            template_name="default",
            context={
                "goal": goal,
                "persona": domain_config.get("personas", {}).get("planner", "专业架构师")
            }
        )

        # 2. 调用 LLM
        response_text = self._call_llm(prompts["user_prompt"], prompts["system_prompt"])
        
        # 3. 解析结果并转换为 StepState
        try:
            proposal_data = self._parse_json_response(response_text)
            steps_data = proposal_data.get("steps", [])
            
            # 将标题映射为 ID，以便处理依赖关系
            title_to_id = {s["title"]: str(uuid.uuid4()) for s in steps_data}
            
            final_steps = []
            for s_data in steps_data:
                step_id = title_to_id[s_data["title"]]
                # 解析依赖项标题到 ID
                deps_ids = [title_to_id[dep_title] for dep_title in s_data.get("dependencies", []) if dep_title in title_to_id]
                
                step = StepState(
                    step_id=step_id,
                    title=s_data["title"],
                    assigned_agent=s_data["assigned_agent"],
                    dependencies=deps_ids,
                    status=StepStatus.PENDING,
                    acceptance_criteria=s_data.get("acceptance_criteria", [])
                )
                final_steps.append(step)

            # 4. 封装成 STEP_RESULT 消息返回给 Orchestrator
            # payload 中包含生成的计划数据，由 Orchestrator 交给 Reducer 落地
            return [
                self._create_message(
                    run_id=message.run_id,
                    receiver="orchestrator",
                    msg_type=MessageType.STEP_RESULT,
                    payload={
                        "step_id": message.payload.get("step_id"), # 完成的是规划步骤
                        "plan_proposal": {
                            "reasoning": proposal_data.get("reasoning", ""),
                            "steps": [s.dict() for s in final_steps]
                        }
                    }
                )
            ]

        except Exception as e:
            # 如果解析失败，上报错误
            return [
                self._create_message(
                    run_id=message.run_id,
                    receiver="orchestrator",
                    msg_type=MessageType.STEP_FAILURE,
                    payload={
                        "step_id": message.payload.get("step_id"),
                        "error": f"Failed to generate or parse plan: {str(e)}"
                    }
                )
            ]

    async def _replan(self, message: Message, context: Dict[str, Any]) -> List[Message]:
        """
        重规划逻辑 (待后续完善)。
        """
        print(f"[{self.role}] Replan requested due to: {message.payload.get('reason')}")
        # 这里可以实现更复杂的逻辑：分析失败原因，打 Patch 
        # 目前先简单上报失败，后续可以扩展 PlanPatchProposal
        return []
