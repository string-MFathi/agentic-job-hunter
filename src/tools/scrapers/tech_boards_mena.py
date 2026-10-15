from typing import List
from langchain_core.tools import tool
from src.tools.error_wrapper import safe_tool_execution
from src.tools.scrapers.mena_search_engine import execute_mena_24h_search

@tool
@safe_tool_execution(
    fallback_suggestion="If Tech Boards search fails, switch to 'search_gulf_mena_portals_24h' or 'search_egypt_local_boards_24h'."
)
def search_mena_tech_boards_24h(roles: List[str], extra_keywords: str = "") -> str:
    """
    Tier 2 Tool: Scans primary tech and startup job boards (LinkedIn Jobs, Wellfound,
    Glassdoor, and Qureos) for AI, Product, and Python roles in MENA posted in the last 24h.
    """
    tech_domains = ["linkedin.com/jobs", "wellfound.com", "glassdoor.com", "qureos.com"]
    return execute_mena_24h_search(
        roles=roles,
        domains=tech_domains,
        tier_label="Tier 2: MENA Tech & Startup Boards",
        extra_keywords=extra_keywords
    )