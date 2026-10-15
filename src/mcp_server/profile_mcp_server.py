import json
from pathlib import Path
from src.config import settings

class ProfileMCPServer:
    """
    سيرفر بروتوكول السياق (MCP Server - Concept #10)
    يعمل كمزود موحد لبيانات الهوية وسيرة محمد فتحي الذاتية وأهداف البحث للوكلاء.
    """
    def __init__(self):
        self.cv_path = settings.cv_markdown_path
        self.targets_path = settings.search_targets_path

    def get_candidate_profile(self) -> str:
        """قراءة السيرة الذاتية الكاملة كمرجع حقيقي (Ground Truth) لمنع الهلوسة"""
        if not self.cv_path.exists():
            return "Error: CV profile markdown not found."
        with open(self.cv_path, "r", encoding="utf-8") as f:
            return f.read()

    def get_search_targets(self) -> dict:
        """جلب مصفوفة الـ 12 مسمى وظيفي والـ 20 منصة ودول الوطن العربي المستهدفة"""
        if not self.targets_path.exists():
            return {"error": "Search targets JSON not found."}
        with open(self.targets_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_roles_list(self) -> list:
        """استخراج قائمة المسميات الـ 12 بشكل مسطح ليسهل على وكيل التخطيط البحث بها"""
        targets = self.get_search_targets()
        if "error" in targets:
            return []
        roles_dict = targets.get("target_roles_by_cluster", {})
        flat_roles = []
        for cluster, roles in roles_dict.items():
            flat_roles.extend(roles)
        return flat_roles

# كائن موحد يتم استدعاؤه داخل نظام الوكلاء
mcp_server = ProfileMCPServer()