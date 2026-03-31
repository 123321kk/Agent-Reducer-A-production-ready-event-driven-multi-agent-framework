import pandas as pd
import os
import time
from typing import Dict, Any, List, Optional, Callable
from ..core.models.skill import SkillDefinition, SkillResult, SkillRequest

class SkillService:
    """
    技能/工具服务中心。
    管理并执行所有可用的技能。
    """

    def __init__(self):
        # 技能注册表: { "skill_name": { "definition": ..., "function": ... } }
        self._skills = {}

    def register_skill(self, definition: SkillDefinition, func: Callable):
        """
        注册一个新技能。
        """
        self._skills[definition.name] = {
            "definition": definition,
            "function": func
        }
        print(f"[SkillService] Skill '{definition.name}' registered.")

    def get_all_skill_definitions(self) -> List[SkillDefinition]:
        """
        获取所有已注册技能的定义，用于生成 Prompt。
        """
        return [s["definition"] for s in self._skills.values()]

    async def execute_skill(self, request: SkillRequest) -> SkillResult:
        """
        执行一个技能调用请求。
        """
        skill_name = request.skill_name
        arguments = request.arguments
        
        if skill_name not in self._skills:
            return SkillResult(
                skill_name=skill_name,
                status="failure",
                error=f"Skill '{skill_name}' not found."
            )
        
        func = self._skills[skill_name]["function"]
        start_time = time.time()
        
        try:
            # 执行技能逻辑
            print(f"[SkillService] Executing '{skill_name}' with args: {arguments}")
            
            # 支持同步或异步函数
            import inspect
            if inspect.iscoroutinefunction(func):
                output = await func(**arguments)
            else:
                output = func(**arguments)
                
            return SkillResult(
                skill_name=skill_name,
                status="success",
                output=output,
                execution_time_ms=(time.time() - start_time) * 1000
            )
            
        except Exception as e:
            return SkillResult(
                skill_name=skill_name,
                status="failure",
                error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000
            )

# 实例化全局服务单例
skill_service = SkillService()
