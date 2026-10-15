from typing import List
from langchain_core.tools import tool
from src.tools.error_wrapper import safe_tool_execution
from src.tools.scrapers.mena_search_engine import execute_mena_24h_search

@tool
@safe_tool_execution(
    fallback_suggestion="If Gulf/MENA portals fail, fallback to 'search_mena_tech_boards_24h'."
)
def search_gulf_mena_portals_24h(roles: List[str], extra_keywords: str = "") -> str:
    """
    Tier 3 Tool: Scans major GCC and Arab regional recruitment portals (Bayt, GulfTalent,
    Naukrigulf, Tanqeeb, Jobs-Arab, Akhtaboot, Almehan, Glowork, Jadarat) for last 24h jobs.
    """
    gulf_mena_domains = [
        "bayt.com", "gulftalent.com", "naukrigulf.com", "tanqeeb.com",
        "jobs-arab.com", "akhtaboot.com", "almehan.com", "glowork.net", "jadarat.sa"
    ]
    return execute_mena_24h_search(
        roles=roles,
        domains=gulf_mena_domains,
        tier_label="Tier 3: Regional & GCC Job Portals",
        extra_keywords=extra_keywords
    )