import asyncio
import os
import sys

# 确保能导入 multi_agent_system 模块
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from multi_agent_system.core.models.state import GlobalState
from multi_agent_system.core.models.message import Message, MessageType
from multi_agent_system.core.runtime.orchestrator import Orchestrator
from multi_agent_system.agents.planner import PlannerAgent
from multi_agent_system.agents.executor import ExecutorAgent
from multi_agent_system.agents.critic import CriticAgent

async def main():
    # 1. 初始化系统全局状态 (用户定义目标和人设)
    goal = "对线上客服对话的 Query 进行质检"
    domain_config = {
        "personas": {
            "planner": "你是一个资深的数据中台架构师，擅长处理复杂的数据流规划。",
            "executor": "你是一个精通自然语言处理（NLP）的数据分析师。",
            "critic": "你是一个对数据准确性有极高要求的质检专家。"
        }
    }
    state = GlobalState(goal=goal, domain_config=domain_config)
    
    # 2. 初始化编排器
    orchestrator = Orchestrator(state)
    
    # 3. 初始化并注册 Agent (工人就位)
    planner = PlannerAgent(role="planner_agent")
    executor = ExecutorAgent(role="executor_agent")
    critic = CriticAgent(role="critic_agent")
    
    # 注册消息处理函数
    orchestrator.register_agent("planner_agent", planner.handle)
    orchestrator.register_agent("executor_agent", executor.handle)
    orchestrator.register_agent("critic_agent", critic.handle)
    
    # 4. 发送初始启动任务给 Planner (让规划师开工)
    start_msg = Message(
        run_id=state.run_id,
        sender="user",
        receiver="planner_agent",
        type=MessageType.TASK_ASSIGNMENT,
        payload={"step_id": "root", "title": "Initial Planning"}
    )
    orchestrator.dispatch(start_msg)
    
    # 5. 启动运行时主循环
    print("\n--- [System Booting] ---")
    await orchestrator.run_until_complete()
    
    # 6. 任务完成后处理结果
    if state.status == "completed":
        print(f"\n--- [Task Completed] ---")
    else:
        print(f"\n--- [Task Terminated] Status: {state.status} ---")

if __name__ == "__main__":
    asyncio.run(main())
