import asyncio
from typing import Dict, Any, List, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ..core.models.skill import SkillDefinition
from .skill_service import skill_service

class MCPAdapter:
    """
    MCP (Model Context Protocol) 适配器。
    负责连接外部 MCP Server，并将其工具自动桥接到我们的 Skill 机制中。
    """

    def __init__(self):
        # 存储已建立连接的 MCP Server 会话: { "server_name": session }
        self.sessions: Dict[str, ClientSession] = {}
        # 存储对应的 transport，用于后续正确关闭
        self._transports = {}

    async def connect_and_register(self, server_name: str, command: str, args: List[str]):
        """
        通过 Stdio 连接到一个 MCP Server，并将其提供的所有工具注册为我们系统的 Skill。
        
        Args:
            server_name (str): 你为该 Server 定义的命名空间前缀
            command (str): 启动 Server 的命令 (如 'npx', 'python')
            args (List[str]): 启动参数
        """
        print(f"[MCPAdapter] Connecting to MCP Server '{server_name}' using: {command} {' '.join(args)}")
        
        try:
            # 1. 建立基于 stdio 的传输通道
            server_params = StdioServerParameters(command=command, args=args)
            
            # 我们需要手动管理 context 以便在外部使用
            transport_ctx = stdio_client(server_params)
            read_stream, write_stream = await transport_ctx.__aenter__()
            
            # 2. 初始化会话
            session = ClientSession(read_stream, write_stream)
            await session.initialize()
            
            self.sessions[server_name] = session
            self._transports[server_name] = transport_ctx
            
            # 3. 获取 Server 提供的工具列表
            tools_response = await session.list_tools()
            print(f"[MCPAdapter] Successfully connected to '{server_name}'. Found {len(tools_response.tools)} tools.")
            
            # 4. 遍历并注册每一个工具
            for tool in tools_response.tools:
                # 构造符合我们框架要求的 SkillDefinition
                # 我们通过前缀避免不同 Server 之间的工具同名冲突
                skill_name = f"{server_name}_{tool.name}"
                
                definition = SkillDefinition(
                    name=skill_name,
                    description=f"[MCP Tool from {server_name}] {tool.description or ''}",
                    parameters_schema=tool.inputSchema
                )
                
                # 创建一个闭包函数，用于执行该 MCP 工具
                async def mcp_wrapper(skill_args: Dict[str, Any], t_name=tool.name, s_session=session):
                    print(f"[MCPAdapter] Calling remote tool '{t_name}' on server '{server_name}'")
                    result = await s_session.call_tool(t_name, arguments=skill_args)
                    
                    # MCP 返回的结果通常是内容列表，我们简单提取文本部分
                    outputs = []
                    for content in result.content:
                        if content.type == "text":
                            outputs.append(content.text)
                    
                    return outputs if len(outputs) > 1 else (outputs[0] if outputs else None)

                # 注册到全局 SkillService
                skill_service.register_skill(definition, mcp_wrapper)
                print(f"[MCPAdapter] Registered MCP tool: {skill_name}")

        except Exception as e:
            print(f"[MCPAdapter] Failed to connect to MCP Server '{server_name}': {str(e)}")
            raise e

    async def close_all(self):
        """
        关闭所有 MCP 连接。
        """
        for server_name, ctx in self._transports.items():
            print(f"[MCPAdapter] Closing connection to '{server_name}'...")
            await ctx.__aexit__(None, None, None)
        self.sessions.clear()
        self._transports.clear()
