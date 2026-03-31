import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import collections

from ..models.state import GlobalState
from ..models.message import Message, MessageType
from ..models.event import Event, EventType
from ..models.step import StepStatus
from .reducer import Reducer
from ..models.skill import SkillRequest
from ...services.skill_service import skill_service
from ..models.memory import Memory, MemoryQuery
from ...services.memory_service import memory_service
from ...storage.state_repo import state_repo

class Orchestrator:
    """
    系统的运行时大脑 (Orchestrator)。
    职责：
    1. 维护 GlobalState 的生命周期。
    2. 驱动消息循环 (Message Loop)。
    3. 执行状态机流转 (Step Lifecycle)。
    4. 路由消息给对应的 Agent。
    """

    def __init__(self, state: GlobalState):
        self.state = state
        # 进程内消息队列 (Event Bus)
        self.message_queue = collections.deque()
        # 注册的 Agent 处理函数: { "agent_role": handler_func }
        self.agent_registry = {}
        # 事件日志，用于审计和回放
        self.event_log: List[Event] = []

    def register_agent(self, role: str, handler):
        """
        注册 Agent 到编排器。
        handler 应该是一个异步函数: async def handle(message, context) -> List[Message]
        """
        self.agent_registry[role] = handler

    def dispatch(self, message: Message):
        """
        向系统发送一条消息。
        """
        print(f"[Orchestrator] Dispatching message: {message.type} from {message.sender} to {message.receiver}")
        self.message_queue.append(message)

    async def run_until_complete(self):
        """
        启动消息循环，直到所有任务完成或失败。
        """
        print(f"[Orchestrator] Starting Run: {self.state.run_id} - Goal: {self.state.goal}")
        self.state.status = "running"
        
        # 初始状态持久化
        state_repo.save_state(self.state)

        while self.state.status == "running":
            # 1. 处理队列中的消息
            if self.message_queue:
                message = self.message_queue.popleft()
                await self._process_message(message)
            
            # 2. 检查并调度处于 READY 状态的步骤
            self._schedule_ready_steps()

            # 3. 检查整体状态是否结束
            if self._is_all_done():
                self.state.status = "completed"
                print(f"[Orchestrator] Run Completed Successfully!")
                break
            
            if self._is_failed():
                self.state.status = "failed"
                print(f"[Orchestrator] Run Failed.")
                break

            # 防止死循环，稍微停顿
            await asyncio.sleep(0.1)

    async def _process_message(self, message: Message):
        """
        核心消息处理器。
        """
        # A. 如果是发给 Orchestrator 的反馈消息
        if message.receiver == "orchestrator":
            if message.type == MessageType.STEP_RESULT:
                self._handle_step_result(message)
            elif message.type == MessageType.STEP_FAILURE:
                self._handle_step_failure(message)
            elif message.type == MessageType.REPLAN_REQUEST:
                self._handle_replan_request(message)
            elif message.type == MessageType.VALIDATION_RESULT:
                self._handle_validation_result(message)
            elif message.type == MessageType.SKILL_REQUEST:
                await self._handle_skill_request(message)
            elif message.type == MessageType.MEMORY_QUERY:
                await self._handle_memory_query(message)
            elif message.type == MessageType.MEMORY_ADD:
                await self._handle_memory_add(message)
        
        # B. 如果是发给具体 Agent 的任务分配
        elif message.receiver in self.agent_registry:
            handler = self.agent_registry[message.receiver]
            # 构造受控上下文 (Visibility Scope)
            context = self._get_context_for_agent(message.receiver)
            # 调用 Agent (Agent 吐出的是建议变更或后续消息)
            responses = await handler(message, context)
            for resp in responses:
                self.dispatch(resp)

    def _handle_step_result(self, message: Message):
        """
        处理 Agent 上报的成功结果。
        """
        step_id = message.payload.get("step_id")
        artifact = message.payload.get("artifact")
        plan_proposal = message.payload.get("plan_proposal")
        
        # 1. 如果有产物，先登记产物
        if artifact:
            event_art = Event(
                type=EventType.ARTIFACT_ADDED,
                run_id=self.state.run_id,
                payload={"artifact": artifact},
                correlation_id=message.message_id
            )
            self._apply_event(event_art)

        # 2. 如果有计划提议，则更新规划
        if plan_proposal:
            event_plan = Event(
                type=EventType.PLAN_PROPOSED,
                run_id=self.state.run_id,
                payload={"steps": plan_proposal["steps"]},
                correlation_id=message.message_id
            )
            self._apply_event(event_plan)

        # 3. 更新步骤状态为 DONE
        event_step = Event(
            type=EventType.STEP_STATUS_CHANGE,
            run_id=self.state.run_id,
            payload={
                "step_id": step_id,
                "status": StepStatus.DONE,
                "finished_at": datetime.utcnow(),
                "output_ref": artifact.artifact_id if artifact else None
            },
            correlation_id=message.message_id
        )
        self._apply_event(event_step)

    def _handle_step_failure(self, message: Message):
        """
        处理 Agent 上报的失败。
        """
        step_id = message.payload.get("step_id")
        error_msg = message.payload.get("error")
        
        event = Event(
            type=EventType.STEP_STATUS_CHANGE,
            run_id=self.state.run_id,
            payload={
                "step_id": step_id,
                "status": StepStatus.FAILED,
                "error": error_msg,
                "finished_at": datetime.utcnow()
            },
            correlation_id=message.message_id
        )
        self._apply_event(event)

    def _handle_validation_result(self, message: Message):
        """
        处理 Critic Agent 的验证结果。
        """
        critic_step_id = message.payload.get("step_id")
        target_step_id = message.payload.get("target_step_id")
        decision = message.payload.get("decision", "reject_retry")
        feedback = message.payload.get("feedback", "")
        
        print(f"[Orchestrator] Validation Result for step {target_step_id}: {decision.upper()} - {feedback}")

        if decision == "accept":
            # 1. 标记 Critic 步骤为 DONE
            event_critic = Event(
                type=EventType.STEP_STATUS_CHANGE,
                run_id=self.state.run_id,
                payload={"step_id": critic_step_id, "status": StepStatus.DONE}
            )
            self._apply_event(event_critic)
            
            # 2. 标记被验证的 Executor 步骤为 DONE (如果之前是某种待验证状态)
            # 在简化模型中，Executor 结束即为 DONE，Critic 只是锦上添花。
            # 在严谨模型中，Executor 结束应该是 WAITING_APPROVAL，Critic 通过后才变 DONE。
            pass

        elif decision == "reject_retry":
            # 1. 将被验证的 Executor 步骤重置为 READY，等待重新执行
            event_retry = Event(
                type=EventType.STEP_STATUS_CHANGE,
                run_id=self.state.run_id,
                payload={
                    "step_id": target_step_id, 
                    "status": StepStatus.READY,
                    "error": f"Rejected by critic: {feedback}"
                }
            )
            self._apply_event(event_retry)
            
            # 2. 标记 Critic 步骤本身为 DONE (它的任务完成了：找出了问题)
            event_critic_done = Event(
                type=EventType.STEP_STATUS_CHANGE,
                run_id=self.state.run_id,
                payload={"step_id": critic_step_id, "status": StepStatus.DONE}
            )
            self._apply_event(event_critic_done)

        elif decision == "reject_replan":
            # 触发重规划请求
            msg = Message(
                run_id=self.state.run_id,
                sender="orchestrator",
                receiver="planner_agent",
                type=MessageType.REPLAN_REQUEST,
                payload={"target_step_id": target_step_id, "reason": feedback}
            )
            self.dispatch(msg)

    async def _handle_skill_request(self, message: Message):
        """
        处理 Agent 的技能/工具调用请求。
        """
        skill_name = message.payload.get("skill_name")
        arguments = message.payload.get("arguments", {})
        
        request = SkillRequest(skill_name=skill_name, arguments=arguments)
        
        # 1. 执行技能 (通过 SkillService)
        result = await skill_service.execute_skill(request)
        
        # 2. 将结果包装成消息发回给原 Agent (Sender)
        result_msg = Message(
            run_id=self.state.run_id,
            sender="orchestrator",
            receiver=message.sender,
            type=MessageType.SKILL_RESULT,
            payload={
                "request_id": request.request_id,
                "skill_name": skill_name,
                "status": result.status,
                "output": result.output,
                "error": result.error
            },
            correlation_id=message.message_id
        )
        self.dispatch(result_msg)

    async def _handle_memory_query(self, message: Message):
        """
        处理记忆查询请求。
        """
        query_text = message.payload.get("query_text")
        namespace = message.payload.get("namespace")
        top_k = message.payload.get("top_k", 3)
        
        query = MemoryQuery(query_text=query_text, namespace=namespace, top_k=top_k)
        
        # 1. 执行向量检索
        results = await memory_service.search(query)
        
        # 2. 将结果发回 Agent
        result_msg = Message(
            run_id=self.state.run_id,
            sender="orchestrator",
            receiver=message.sender,
            type=MessageType.MEMORY_RESULT,
            payload={
                "query_text": query_text,
                "memories": [m.dict() for m in results]
            },
            correlation_id=message.message_id
        )
        self.dispatch(result_msg)

    async def _handle_memory_add(self, message: Message):
        """
        处理记忆新增请求。
        """
        content = message.payload.get("content")
        namespace = message.payload.get("namespace")
        metadata = message.payload.get("metadata", {})
        
        # 权限校验：仅允许 Critic Agent 写入新记忆
        if message.sender != "critic_agent":
            print(f"[Orchestrator] Access Denied: Agent '{message.sender}' is not allowed to add memories.")
            return

        memory = Memory(
            content=content,
            namespace=namespace,
            metadata={**metadata, "added_by": message.sender}
        )
        
        # 1. 写入向量库
        success = await memory_service.add_memory(memory)
        
        if success:
            print(f"[Orchestrator] Memory successfully added by {message.sender}.")

    def _schedule_ready_steps(self):
        """
        扫描所有 PENDING 步骤，如果依赖已满足，则标记为 READY 并派发任务。
        """
        for step_id, step in self.state.step_states.items():
            if step.status == StepStatus.PENDING:
                # 检查所有依赖是否都已 DONE
                deps_satisfied = all(
                    self.state.step_states[dep_id].status == StepStatus.DONE
                    for dep_id in step.dependencies
                )
                if deps_satisfied:
                    # 更新状态为 READY
                    event = Event(
                        type=EventType.STEP_STATUS_CHANGE,
                        run_id=self.state.run_id,
                        payload={"step_id": step_id, "status": StepStatus.READY}
                    )
                    self._apply_event(event)
                    
                    # 派发任务给对应 Agent
                    msg = Message(
                        run_id=self.state.run_id,
                        sender="orchestrator",
                        receiver=step.assigned_agent,
                        type=MessageType.TASK_ASSIGNMENT,
                        payload={"step_id": step_id, "title": step.title}
                    )
                    self.dispatch(msg)

    def _apply_event(self, event: Event):
        """
        通过 Reducer 更新状态，并记录日志。
        自动触发持久化保存。
        """
        self.state = Reducer.apply_event(self.state, event)
        self.event_log.append(event)
        
        # 自动持久化 (实现断点续传)
        state_repo.save_state(self.state)
        state_repo.save_events(self.state.run_id, [event])

    @staticmethod
    def resume(run_id: str) -> Optional['Orchestrator']:
        """
        根据 run_id 恢复之前的运行环境。
        """
        state = state_repo.load_state(run_id)
        if state:
            print(f"[Orchestrator] Resuming run: {run_id} from version: {state.version}")
            return Orchestrator(state)
        return None

    def _get_context_for_agent(self, agent_role: str) -> Dict[str, Any]:
        """
        根据 Agent 角色提供受控的上下文视图 (Visibility Scope)。
        """
        # 这里可以实现复杂的隔离逻辑
        return {
            "global_goal": self.state.goal,
            "domain_config": self.state.domain_config,
            "all_artifacts": self.state.artifacts,
            "step_states": self.state.step_states
        }

    def _is_all_done(self) -> bool:
        """
        所有步骤是否都已完成。
        """
        if not self.state.step_states:
            return False
        return all(s.status == StepStatus.DONE or s.status == StepStatus.SKIPPED 
                   for s in self.state.step_states.values())

    def _is_failed(self) -> bool:
        """
        是否有任何关键步骤失败且无法重试。
        """
        return any(s.status == StepStatus.FAILED for s in self.state.step_states.values())
