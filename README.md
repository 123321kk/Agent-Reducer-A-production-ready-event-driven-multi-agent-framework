# 🚀 Agent-Reducer

> **Stop writing toy agents. A production-ready, event-driven multi-agent framework powered by state machines and MCP.**
> 
> 告别玩具级 Prompt 拼接！这是一个基于“事件驱动”与“Reducer 模式”的工业级多智能体编排框架。支持断点续传、严格记忆隔离、角色一键换肤，并无缝接入全网 MCP (Model Context Protocol) 生态。

---

## 💡 为什么造这个轮子？ (Why Agent-Reducer?)

目前的许多开源 Agent 框架（如早期的 LangChain 等）在构建简单 Demo 时很方便，但一旦投入到复杂的企业级业务（如数据清洗、自动化运维、复杂代码生成）中，往往会遇到以下痛点：
- **状态管理混乱**：多个 Agent 随意读写全局变量，导致系统不可预测，难以 Debug。
- **Prompt 面条代码**：业务提示词和框架代码严重耦合。
- **脆弱的运行时**：一旦中途某个 API 调用超时，整个长达几个小时的任务直接白跑，无法恢复。
- **孤岛系统**：接入外部工具（读库、读文件、发消息）需要手写大量“胶水代码”。

**Agent-Reducer** 借鉴了前端 Redux 的单一事实来源 (SSOT) 思想和分布式系统架构，彻底解决了上述问题。

---

## ✨ 核心特性 (Core Features)

### 1. 🛡️ 状态机与 Reducer 驱动 (Deterministic State)
- **单一事实来源**：`GlobalState` 是唯一权威数据源。
- **只读 Agent**：Agent (`Planner`, `Executor`, `Critic`) **无权直接修改状态**，只能产出意图（Proposed Events）。
- **统一落地**：所有的状态变更必须通过中央 `Orchestrator` 校验，交由 `Reducer` 原子化更新。回放日志即可完美复现 Bug。

### 2. 💾 生产级断点续传 (Checkpoint & Resume)
- 内置 `StateRepository`。每一步操作、每一个产物都会自动序列化持久存盘。
- 系统崩溃？断电？只需一行代码 `Orchestrator.resume("run_id")`，Agent 团队就能从上次断掉的节点继续干活。

### 3. 🔌 原生 MCP 扩展支持 (Universal MCP Tooling)
- 内置 `MCPAdapter`。无需手写 API 封装，一键挂载开源社区的 [MCP Servers](https://github.com/modelcontextprotocol/servers)。
- 你的 Agent 瞬间拥有操作本地文件、查 MySQL/PG 库、读写 GitHub、抓取网页等超能力。

### 4. 🧠 带隔离的长期记忆库 (Namespaced Vector Memory)
- 内置基于 `ChromaDB` 的向量检索服务。
- **读写隔离**：`Planner` 读规则，`Executor` 读历史困难样本，**只有 `Critic` (审查员) 拥有写入权**，从根本上杜绝“幻觉污染记忆库”。

### 5. 🎭 角色“一键换肤” (Prompt Skinning)
- 结构化 YAML Prompt + Jinja2 模板渲染。
- “思考逻辑”与“业务皮囊”彻底分离。用户只需在入口配置 `domain_config`，Agent 团队就能瞬间从“数据分析专家”切换成“资深后端开发”。

---

## 🛠️ 核心架构图 (Architecture)

```text
[ 用户目标 / 换肤配置 ]
       │
       ▼
┌──────────────────────────────────────────────┐
│                Orchestrator                  │
│  (Router -> Message Bus -> Transition Guard) │
└──────┬───────────────────────────────▲───────┘
       │ (TASK_ASSIGNMENT)             │ (STEP_RESULT / VALIDATION_RESULT)
       ▼                               │
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│ Planner Agent │ │ Executor Agent│ │  Critic Agent │
└───────────────┘ └───────────────┘ └───────────────┘
       │                 │                 │
       └───────┬─────────┴─────────┬───────┘
               │ (Events)          │ (Skill / Memory Requests)
               ▼                   ▼
      ┌─────────────────┐ ┌─────────────────┐
      │     Reducer     │ │ Services (MCP)  │
      └────────┬────────┘ └─────────────────┘
               │
               ▼
      ┌─────────────────┐
      │   Global State  │  <── Persistent Storage (Checkpoint)
      └─────────────────┘
```

---

## 🚀 最小可运行实例 (Minimal Working Example)

以下代码展示了如何使用 `Agent-Reducer` 快速组建一个团队，并赋予他们网页抓取和本地文件读写的超能力。

### 前置准备
```bash
# 安装核心依赖
pip install pydantic chromadb mcp jinja2

# (可选) 如果需要使用火山引擎大模型
pip install volcengine-python-sdk volcenginesdkarkruntime
```

### `demo.py`
```python
import asyncio
import os
from multi_agent_system.core.models.state import GlobalState
from multi_agent_system.core.models.message import Message, MessageType
from multi_agent_system.core.runtime.orchestrator import Orchestrator
from multi_agent_system.agents.planner import PlannerAgent
from multi_agent_system.agents.executor import ExecutorAgent
from multi_agent_system.agents.critic import CriticAgent
from multi_agent_system.services.mcp_adapter import MCPAdapter

async def main():
    # 1. 启动 MCP 适配器 (给 Agent 挂载外挂)
    mcp_adapter = MCPAdapter()
    
    # 挂载官方的网页抓取工具 (需要环境中安装了 uv)
    await mcp_adapter.connect_and_register(
        server_name="web",
        command="uvx",
        args=["mcp-server-fetch"]
    )
    
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
    
    # 4. 注册工人
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
    
    print("🤖 Agent 团队开始工作...")
    await orchestrator.run_until_complete()
    
    print(f"✅ 任务结束状态: {state.status}")
    
    # 关闭外挂连接
    await mcp_adapter.close_all()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 📂 目录结构说明

- `/core/models`: 强类型的领域驱动模型 (Domain Driven Design)。
- `/core/runtime`: 包含大脑 `Orchestrator` 和单向数据流 `Reducer`。
- `/agents`: 包含抽象基类及三大核心打工人实现。
- `/services`: `PromptManager`, `MemoryService` (向量检索), `SkillService` (工具注册) 及 `MCPAdapter`。
- `/storage`: 状态持久化与断点续传仓库。
- `/prompts`: 结构化的 YAML Prompt 模板库。

---

## 🤝 贡献与共建

欢迎提交 Issue 和 Pull Request！如果你用这个框架跑出了好玩的专属 Agent，也欢迎在 Discussions 里分享你的 `domain_config` 配置！
