import asyncio
import os
import sys

# 确保能导入 multi_agent_system 模块
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from multi_agent_system.core.models.state import GlobalState
from multi_agent_system.core.models.message import Message, MessageType
from multi_agent_system.core.runtime.orchestrator import Orchestrator
from multi_agent_system.agents.planner import PlannerAgent
from multi_agent_system.agents.executor import ExecutorAgent
from multi_agent_system.agents.critic import CriticAgent
from multi_agent_system.services.mcp_adapter import MCPAdapter

async def main():
    print("==================================================")
    print("🚀 启动 Agent-Reducer 最小可运行实例 (MWE)")
    print("==================================================")
    
    # 1. 启动 MCP 适配器 (给 Agent 挂载外挂)
    mcp_adapter = MCPAdapter()
    
    # 挂载官方的网页抓取工具
    try:
        print("\n[Demo] 正在接入 'web_fetch' MCP Server...")
        # 考虑到 uvx 可能会污染标准输出，这里我们直接使用 .venv 中的 mcp-server-fetch
        fetch_executable = os.path.abspath(os.path.join(os.path.dirname(__file__), ".venv/bin/mcp-server-fetch"))
        await mcp_adapter.connect_and_register(
            server_name="web",
            command=fetch_executable,
            args=[]
        )
    except Exception as e:
        print(f"⚠️ 无法启动 mcp-server-fetch，请检查是否安装了 uv: {e}")
        return
    
    # 2. 定义任务目标和 Agent 人设 (换肤)
    goal = "请使用 web_fetch 工具抓取 Python 官方文档的 CSV 页面，总结出 3 个最佳实践。"
    domain_config = {
        "personas": {
            "planner": "你是一个精通 MCP 工具链的架构师，擅长拆解任务。",
            "executor": "你是一个全能数据工程师，负责调用 web_fetch 工具完成任务。",
            "critic": "你是一个严格的审查员，确保总结的内容准确无误。"
        }
    }
    
    # 3. 初始化中枢与状态
    state = GlobalState(goal=goal, domain_config=domain_config)
    orchestrator = Orchestrator(state)
    
    # 4. 注册打工团队
    orchestrator.register_agent("planner_agent", PlannerAgent().handle)
    orchestrator.register_agent("executor_agent", ExecutorAgent().handle)
    orchestrator.register_agent("critic_agent", CriticAgent().handle)
    
    # 5. 点火发车！向 Planner 发送初始任务
    start_msg = Message(
        run_id=state.run_id,
        sender="user",
        receiver="planner_agent",
        type=MessageType.TASK_ASSIGNMENT,
        payload={"step_id": "root", "title": "Initial Planning"}
    )
    orchestrator.dispatch(start_msg)
    
    print("\n==================================================")
    print("🤖 Agent 团队开始工作...")
    print("==================================================")
    await orchestrator.run_until_complete()
    
    print(f"\n✅ 任务结束状态: {state.status}")
    
    # 打印最终产物
    print("\n==================================================")
    print("📄 最终总结结果:")
    print("==================================================")
    for step_id, step in state.step_states.items():
        if step.status == "done" and step.output_ref:
            artifact = state.artifacts.get(step.output_ref)
            if artifact and "最佳实践" in step.title:
                print(f"[{step.title}]")
                print(artifact.inline_payload)
                print()
    
    # 关闭外挂连接
    await mcp_adapter.close_all()

if __name__ == "__main__":
    asyncio.run(main())
