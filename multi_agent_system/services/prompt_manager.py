import os
import yaml
from jinja2 import Template
from typing import Dict, Any, Optional

class PromptManager:
    """
    结构化 Prompt 管理器。
    负责加载 YAML 配置文件，并使用 Jinja2 渲染模板。
    实现了 '看什么' (Context Selector) 与 '怎么问' (Prompt Builder) 的分离。
    """

    def __init__(self, base_dir: str = "./multi_agent_system/prompts"):
        self.base_dir = base_dir

    def get_prompt(self, agent_role: str, template_name: str, context: Dict[str, Any]) -> Dict[str, str]:
        """
        获取并渲染指定 Agent 角色的 Prompt。
        
        Args:
            agent_role: Agent 角色 (planner, executor, critic)
            template_name: 模板文件名 (不含 .yaml)
            context: 渲染模板所需的上下文变量
            
        Returns:
            Dict[str, str]: 包含 'system_prompt' 和 'user_prompt' 的字典
        """
        file_path = os.path.join(self.base_dir, agent_role, f"{template_name}.yaml")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Prompt template not found at: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # 使用 Jinja2 渲染模板
        system_tmpl = Template(config.get("system_prompt", ""))
        user_tmpl = Template(config.get("user_prompt", ""))

        return {
            "system_prompt": system_tmpl.render(**context),
            "user_prompt": user_tmpl.render(**context)
        }

# 实例化全局单例
prompt_manager = PromptManager()
