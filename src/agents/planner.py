from datetime import datetime, timezone
from typing import Dict, Any, List
from src.mcp_server.mcp_client import MCPClient
from src.memory.memory_store import episodic_memory
from src.state.agent_state import NightlyHuntState, SearchTask

def planner_node(state: NightlyHuntState) -> Dict[str, Any]:
    """
    وكيل التخطيط الليلي (Concept #2: Plan-and-Execute Pattern)
    يقرأ الهوية من MCP والدروس السابقة من الذاكرة الإبيسودية،
    ويولد خريطة مهام بحث منظمة (Task Graph) تغطي الـ 12 مسمى والـ 20 منصة.
    """
    # 1. سحب السيرة الذاتية وإعدادات البحث من سيرفر MCP (Concept #10)
    cv_text = MCPClient.fetch_full_cv()
    search_config = MCPClient.fetch_search_config()

    # 2. سحب قواعد التجنب من الذاكرة الإبيسودية (Concept #9)
    avoidance_rules = episodic_memory.get_active_avoidance_rules(limit=15)

    role_clusters: Dict[str, List[str]] = search_config.get("target_roles_by_cluster", {})
    platform_tiers: Dict[str, Any] = search_config.get("platform_tiers", {})

    # ترتيب الباقات حسب الأولوية (من Tier 1 إلى Tier 4)
    sorted_tiers = sorted(
        platform_tiers.items(),
        key=lambda item: item[1].get("priority", 99)
    )

    search_plan: List[SearchTask] = []
    task_counter = 1

    # 3. توليد جدول المهام الليلي (ربط مجموعات المسميات الوظيفية بباقات المنصات)
    for tier_key, tier_info in sorted_tiers:
        domains = [src.get("domain", "") for src in tier_info.get("sources", []) if src.get("domain")]
        
        for cluster_name, roles in role_clusters.items():
            if not roles:
                continue
            search_plan.append(
                SearchTask(
                    task_id=f"task_{task_counter:02d}",
                    role_cluster=cluster_name,
                    target_roles=roles,
                    tier_name=tier_key,
                    domains=domains,
                    status="pending"
                )
            )
            task_counter += 1

    run_id = state.get("run_id") or f"nightly_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    run_timestamp = state.get("run_timestamp") or datetime.now(timezone.utc).isoformat()

    return {
        "run_id": run_id,
        "run_timestamp": run_timestamp,
        "candidate_cv_text": cv_text,
        "episodic_avoidance_rules": avoidance_rules,
        "search_plan": search_plan,
        "current_task_index": 0,
        "next_worker": "supervisor",
    }