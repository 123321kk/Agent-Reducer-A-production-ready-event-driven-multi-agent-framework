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
from multi_agent_system.services.mcp_adapter import MCPAdapter

async def main():
    print("==================================================")
    print("🚀 正在启动 MCP (Model Context Protocol) 演示 Demo")
    print("==================================================")
    
    # 1. 启动 MCP 适配器并接入外部工具
    mcp_adapter = MCPAdapter()
    
    try:
        # A. 接入 fetch (网页抓取)
        # 使用 uvx 运行官方的 fetch server (Python 实现)
        print("\n[Demo] 正在接入 'fetch' MCP Server...")
        await mcp_adapter.connect_and_register(
            server_name="web",
            command="uvx",
            args=["--quiet", "mcp-server-fetch"]
        )
        
        # B. 接入 filesystem (本地文件系统)
        # 允许访问当前工作目录
        allowed_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        print(f"\n[Demo] 正在接入 'filesystem' MCP Server (授权目录: {allowed_dir})...")
        await mcp_adapter.connect_and_register(
            server_name="fs",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", allowed_dir]
        )

        # C. 接入 memory (知识图谱)
        print("\n[Demo] 正在接入 'memory' MCP Server...")
        await mcp_adapter.connect_and_register(
            server_name="kg",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-memory"]
        )

        # D. 接入 sequentialthinking (思维链)
        print("\n[Demo] 正在接入 'sequentialthinking' MCP Server...")
        await mcp_adapter.connect_and_register(
            server_name="logic",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-sequential-thinking"]
        )
        
        print("\n✅ 所有 MCP 工具已成功挂载！Agent 现已获得超能力。\n")

        # 2. 定义一个需要综合运用这些工具的复杂任务
        goal = """
        请完成以下综合调研任务：
        1. 使用 web_fetch 工具抓取 https://docs.python.org/3/library/csv.html 的内容。
        2. 使用 logic_sequentialthinking 工具，分析抓取到的文档，总结出 3 个最佳实践。
        3. 使用 kg_create_entities 工具，将这 3 个最佳实践作为节点存入知识图谱。
        4. 使用 fs_write_file 工具，将总结报告写入本地文件 'csv_best_practices.md' 中。
        """
        
        # 3. 初始化系统
        domain_config = {
            "personas": {
                "planner": "你是一个拥有丰富工具使用经验的系统架构师。你知道如何把复杂任务拆解成调用各种 MCP 工具的步骤。",
                "executor": "你是一个全能的数据工程师。当收到任务时，你会调用对应的 MCP Skill (如 web_fetch, fs_write_file 等) 来完成操作。",
                "critic": "你是一个严格的代码和流程审查员，确保文件成功写入，图谱成功创建。"
            }
        }
        
        state = GlobalState(goal=goal, domain_config=domain_config)
        orchestrator = Orchestrator(state)
        
        # 注册 Agent
        planner = PlannerAgent()
        executor = ExecutorAgent()
        critic = CriticAgent()
        
        orchestrator.register_agent("planner_agent", planner.handle)
        orchestrator.register_agent("executor_agent", executor.handle)
        orchestrator.register_agent("critic_agent", critic.handle)
        
        # 4. 点火发车
        print("==================================================")
        print("🤖 Agent 团队开始工作...")
        print("==================================================")
        
        start_msg = Message(
            run_id=state.run_id,
            sender="user",
            receiver="planner_agent",
            type=MessageType.TASK_ASSIGNMENT,
            payload={"step_id": "root", "title": "Initial Planning"}
        )
        orchestrator.dispatch(start_msg)
        
        await orchestrator.run_until_complete()
        
        if state.status == "completed":
            print(f"\n🎉 演示任务圆满完成！你可以查看本地是否生成了 'csv_best_practices.md' 文件。")
        else:
            print(f"\n❌ 演示任务异常终止。状态: {state.status}")

    except Exception as e:
        print(f"\n⚠️ 启动演示时发生错误: {e}")
        print("请确保你本地已安装 Node.js (npx 命令可用)。")
        
    finally:
        # 清理资源
        print("\n🧹 正在关闭 MCP 连接...")
        await mcp_adapter.close_all()

if __name__ == "__main__":
    asyncio.run(main())
