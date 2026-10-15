from typing import List
from langchain_core.tools import BaseTool
from src.tools.scrapers.social_posts_24h import search_mena_social_posts_24h
from src.tools.scrapers.tech_boards_mena import search_mena_tech_boards_24h
from src.tools.scrapers.gulf_mena_portals import search_gulf_mena_portals_24h
from src.tools.scrapers.egypt_local_boards import search_egypt_local_boards_24h

class DynamicToolRouter:
    """
    موجّه الأدوات الديناميكي (Concept #6: Dynamic Tool Routing & Selection)
    يختار فقط الأداة المناسبة للمهمة الحالية + أداة بديلة واحدة للطوارئ (Failover)
    لتقليل استهلاك الـ Tokens وزيادة دقة استدعاء الأدوات.
    """

    TIER_TOOL_MAP = {
        "tier_1_social_and_direct_hiring": [
            search_mena_social_posts_24h,
            search_mena_tech_boards_24h  # Backup tool if Tier 1 fails
        ],
        "tier_2_tech_and_startup_boards": [
            search_mena_tech_boards_24h,
            search_gulf_mena_portals_24h  # Backup tool if Tier 2 fails
        ],
        "tier_3_regional_and_gulf_portals": [
            search_gulf_mena_portals_24h,
            search_mena_tech_boards_24h  # Backup tool if Tier 3 fails
        ],
        "tier_4_egypt_and_classified_boards": [
            search_egypt_local_boards_24h,
            search_mena_social_posts_24h  # Backup tool if Tier 4 fails
        ],
    }

    @classmethod
    def get_tools_for_tier(cls, tier_name: str) -> List[BaseTool]:
        """إرجاع الأداة المخصصة للباقة الحالية مع أداة الطوارئ البديلة فقط"""
        return cls.TIER_TOOL_MAP.get(
            tier_name,
            [search_mena_tech_boards_24h, search_egypt_local_boards_24h]
        )

    @classmethod
    def get_all_tools(cls) -> List[BaseTool]:
        """إرجاع القائمة الكاملة للأدوات عند الحاجة للفحص الشامل"""
        return [
            search_mena_social_posts_24h,
            search_mena_tech_boards_24h,
            search_gulf_mena_portals_24h,
            search_egypt_local_boards_24h,
        ]