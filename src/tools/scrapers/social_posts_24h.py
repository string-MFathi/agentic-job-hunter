from typing import List
from langchain_core.tools import tool
from src.tools.error_wrapper import safe_tool_execution
from src.tools.scrapers.mena_search_engine import execute_mena_24h_search

@tool
@safe_tool_execution(
    fallback_suggestion="If social X-Ray search fails, call 'search_mena_tech_boards_24h' to scan LinkedIn Jobs and Wellfound directly."
)
def search_mena_social_posts_24h(roles: List[str], extra_keywords: str = "") -> str:
    """
    Tier 1 Tool: Scans direct hiring posts published in the last 24 hours across
    LinkedIn Posts, Facebook tech groups, and public Telegram channels in the Arab World (MENA).
    """
    social_domains = ["linkedin.com/posts", "facebook.com", "t.me"]
    hiring_signals = '("hiring" OR "we are looking for" OR "مطلوب" OR "تعيين" OR "فرصة عمل") ' + extra_keywords
    return execute_mena_24h_search(
        roles=roles,
        domains=social_domains,
        tier_label="Tier 1: Social Hiring Posts (LinkedIn/FB/Telegram)",
        extra_keywords=hiring_signals
    )