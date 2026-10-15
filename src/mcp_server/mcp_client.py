from src.mcp_server.profile_mcp_server import mcp_server

class MCPClient:
    """العميل البرمجي لربط وكلاء LangGraph بسيرفر الـ MCP المحلي"""
    
    @staticmethod
    def fetch_full_cv() -> str:
        return mcp_server.get_candidate_profile()

    @staticmethod
    def fetch_target_roles() -> list:
        return mcp_server.get_roles_list()

    @staticmethod
    def fetch_search_config() -> dict:
        return mcp_server.get_search_targets()