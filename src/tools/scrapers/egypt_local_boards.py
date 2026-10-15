from typing import List
from langchain_core.tools import tool
from src.tools.error_wrapper import safe_tool_execution
from src.tools.scrapers.mena_search_engine import execute_mena_24h_search

@tool
@safe_tool_execution(
    fallback_suggestion="If Egypt local boards fail, fallback to 'search_mena_social_posts_24h'."
)
def search_egypt_local_boards_24h(roles: List[str], extra_keywords: str = "") -> str:
    """
    Tier 4 Tool: Scans Egyptian and classified job platforms (Wuzzuf, Forasna, Mihnati,
    Indeed Middle East, Bezaat, OLX/Dubizzle) for roles posted in the last 24 hours.
    """
    egypt_domains = [
        "wuzzuf.net", "forasna.com", "mihnati.com",
        "eg.indeed.com", "bezaat.com", "dubizzle.com.eg"
    ]
    return execute_mena_24h_search(
        roles=roles,
        domains=egypt_domains,
        tier_label="Tier 4: Egypt & Classified Boards",
        extra_keywords=extra_keywords
    )