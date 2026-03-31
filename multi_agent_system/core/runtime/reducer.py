from typing import List, Dict, Any
from datetime import datetime
from ..models.state import GlobalState
from ..models.event import Event, EventType
from ..models.step import StepStatus

class Reducer:
    """
    状态更新的核心逻辑 (Reducer)。
    遵循 'apply_event(state, event) -> next_state' 的纯函数式思想。
    确保 GlobalState 的每一次变更都是由显式事件触发的，且路径统一。
    """

    @staticmethod
    def apply_event(state: GlobalState, event: Event) -> GlobalState:
        """
        根据事件类型分发处理逻辑，并返回更新后的 GlobalState。
        """
        # 1. 获取事件类型并分发
        if event.type == EventType.STATE_UPDATE:
            state = Reducer._handle_state_update(state, event.payload)
        elif event.type == EventType.STEP_STATUS_CHANGE:
            state = Reducer._handle_step_status_change(state, event.payload)
        elif event.type == EventType.ARTIFACT_ADDED:
            state = Reducer._handle_artifact_added(state, event.payload)
        elif event.type == EventType.AGENT_ASSIGNED:
            state = Reducer._handle_agent_assigned(state, event.payload)
        elif event.type == EventType.AGENT_RELEASED:
            state = Reducer._handle_agent_released(state, event.payload)
        elif event.type == EventType.ERROR_OCCURRED:
            state = Reducer._handle_error_occurred(state, event.payload)
        elif event.type == "PLAN_PROPOSED":
            state = Reducer._handle_plan_proposed(state, event.payload)
        
        # 2. 统一更新元数据
        state.version += 1
        state.updated_at = datetime.utcnow()
        
        return state

    @staticmethod
    def _handle_state_update(state: GlobalState, payload: Dict[str, Any]) -> GlobalState:
        """
        通用的状态字段更新。
        """
        for key, value in payload.items():
            if hasattr(state, key):
                setattr(state, key, value)
        return state

    @staticmethod
    def _handle_step_status_change(state: GlobalState, payload: Dict[str, Any]) -> GlobalState:
        """
        更新某个具体步骤的状态及其相关的执行信息。
        payload: { "step_id": "...", "status": StepStatus, "error": "...", "started_at": ..., "finished_at": ... }
        """
        step_id = payload.get("step_id")
        if step_id and step_id in state.step_states:
            step = state.step_states[step_id]
            
            # 更新状态
            if "status" in payload:
                step.status = payload["status"]
            
            # 更新执行时间
            if "started_at" in payload:
                step.started_at = payload["started_at"]
            if "finished_at" in payload:
                step.finished_at = payload["finished_at"]
            
            # 记录错误
            if "error" in payload:
                step.error = payload["error"]
                
            # 更新输出引用
            if "output_ref" in payload:
                step.output_ref = payload["output_ref"]

        return state

    @staticmethod
    def _handle_artifact_added(state: GlobalState, payload: Dict[str, Any]) -> GlobalState:
        """
        在全局状态中注册新的中间产物。
        payload: { "artifact": ArtifactObject }
        """
        artifact = payload.get("artifact")
        if artifact:
            state.artifacts[artifact.artifact_id] = artifact
        return state

    @staticmethod
    def _handle_agent_assigned(state: GlobalState, payload: Dict[str, Any]) -> GlobalState:
        """
        记录某个 Agent 进入活跃状态。
        """
        agent_id = payload.get("agent_id")
        if agent_id and agent_id not in state.active_agents:
            state.active_agents.append(agent_id)
        return state

    @staticmethod
    def _handle_agent_released(state: GlobalState, payload: Dict[str, Any]) -> GlobalState:
        """
        记录某个 Agent 任务结束退出活跃。
        """
        agent_id = payload.get("agent_id")
        if agent_id and agent_id in state.active_agents:
            state.active_agents.remove(agent_id)
        return state

    @staticmethod
    def _handle_error_occurred(state: GlobalState, payload: Dict[str, Any]) -> GlobalState:
        """
        记录系统级错误，可能导致整个 Run 失败。
        """
        error_msg = payload.get("error")
        state.status = "failed"
        state.audit_meta["last_error"] = {
            "msg": error_msg,
            "timestamp": datetime.utcnow().isoformat()
        }
        return state

    @staticmethod
    def _handle_plan_proposed(state: GlobalState, payload: Dict[str, Any]) -> GlobalState:
        """
        根据提议的计划初始化所有步骤。
        payload: { "steps": [StepStateDict, ...] }
        """
        steps_data = payload.get("steps", [])
        state.plan_version += 1
        
        # 将字典转换为真正的 StepState 对象并初始化到 GlobalState
        from ..models.step import StepState
        for s_dict in steps_data:
            step = StepState(**s_dict)
            state.step_states[step.step_id] = step
            
        return state
