import csv
import os
from typing import List, Dict, Any
from ..models.state import GlobalState

class CSVExportService:
    """
    负责将最终处理好的 Artifact 导出为 CSV。
    包含：原数据、AI 标签、打分说明 (Critic Feedback)。
    """
    
    @staticmethod
    def export(state: GlobalState, output_path: str):
        """
        导出 GlobalState 中的所有清洗/质检结果。
        """
        print(f"[CSVExportService] Exporting results to {output_path}...")
        
        # 提取所有的 executor 产物和对应的 critic 反馈
        # 这是一个简单的合并逻辑示例
        rows = []
        
        # 1. 遍历所有的步骤产物
        for artifact_id, artifact in state.artifacts.items():
            if artifact.type == "step_output":
                row = {
                    "step_id": artifact.owner_step_id,
                    "summary": artifact.summary,
                    "detail": artifact.inline_payload,
                    "critic_feedback": "N/A"
                }
                
                # 尝试寻找该步骤对应的 Critic 验证反馈 (这里可以根据业务逻辑增强)
                # 简化处理：假设 metadata 中存了相关信息，或者通过 audit 查找
                rows.append(row)
        
        # 2. 写入 CSV
        if not rows:
            print("[CSVExportService] No results to export.")
            return

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        keys = rows[0].keys()
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            dict_writer = csv.DictWriter(f, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(rows)
        
        print(f"[CSVExportService] Successfully exported {len(rows)} records.")
