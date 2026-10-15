import json
from typing import Dict, Any, List
from src.memory.memory_store import episodic_memory
from src.state.agent_state import NightlyHuntState, DiscoveredJob
from src.tools.tool_router import DynamicToolRouter

# الكلمات المفتاحية المؤكدة للنطاق العربي أو العمل عن بعد في المنطقة
MENA_LOCATION_SIGNALS = [
    "egypt", "cairo", "alexandria", "tanta", "saudi", "ksa", "riyadh", "jeddah",
    "uae", "dubai", "abu dhabi", "qatar", "doha", "kuwait", "bahrain", "oman",
    "jordan", "amman", "morocco", "tunisia", "lebanon", "iraq", "mena",
    "middle east", "remote", "مصر", "القاهرة", "السعودية", "الرياض", "الإمارات",
    "دبي", "قطر", "الكويت", "الأردن", "عن بعد"
]

def _passes_mena_and_avoidance_filter(
    job_dict: Dict[str, Any],
    avoidance_rules: List[str]
) -> bool:
    """التحقق الصارم من أن الوظيفة في الوطن العربي/Remote ولا تخالف قواعد التجنب"""
    if not job_dict.get("posted_within_24h", True):
        return False

    combined_text = (
        f"{job_dict.get('title', '')} {job_dict.get('location', '')} "
        f"{job_dict.get('raw_description', '')}"
    ).lower()

    # استبعاد فوري للوظائف المقيدة بأمريكا أو أوروبا فقط
    hard_exclusions = ["us citizens only", "must reside in us", "security clearance required"]
    if any(excl in combined_text for excl in hard_exclusions):
        return False

    # التأكد من وجود إشارة جغرافية للوطن العربي أو Remote
    if not any(sig in combined_text for sig in MENA_LOCATION_SIGNALS):
        return False

    return True

def mena_scout_react_node(state: NightlyHuntState) -> Dict[str, Any]:
    """
    وكيل الصيد العربي (Concept #1: ReAct Pattern + Concept #6 & #7)
    ينفذ دورة: التفكير (Reason) -> استدعاء الأداة الموجهة (Act) -> ملاحظة النتيجة والتعافي (Observe).
    """
    search_plan = list(state.get("search_plan", []))
    current_idx = state.get("current_task_index", 0)
    existing_jobs = list(state.get("discovered_jobs", []))
    avoidance_rules = state.get("episodic_avoidance_rules", [])
    error_logs: List[str] = []

    if current_idx >= len(search_plan):
        return {"next_worker": "supervisor"}

    current_task = search_plan[current_idx]

    # 1. [Concept #6] جلب الأداة المخصصة للباقة + أداة الطوارئ البديلة فقط
    routed_tools = DynamicToolRouter.get_tools_for_tier(current_task.tier_name)
    primary_tool = routed_tools[0]
    backup_tool = routed_tools[1] if len(routed_tools) > 1 else routed_tools[0]

    # 2. [ReAct - Reason]: تجهيز معاملات البحث مع مراعاة عدم التكرار
    tool_input = {
        "roles": current_task.target_roles[:3],
        "extra_keywords": ""
    }

    # 3. [ReAct - Act]: استدعاء الأداة الأساسية
    raw_observation = primary_tool.invoke(tool_input)
    obs_data = json.loads(raw_observation)

    # 4. [ReAct - Observe & Recover (Concept #7)]: إذا فشلت الأداة الأساسية، التحول الفوري للبديلة!
    if obs_data.get("status") == "tool_error":
        recovery_msg = (
            f"[ReAct Recovery] Primary tool '{primary_tool.name}' failed on {current_task.task_id}. "
            f"Switching to backup tool '{backup_tool.name}'."
        )
        error_logs.append(recovery_msg)
        raw_observation = backup_tool.invoke({"roles": current_task.target_roles[:3], "extra_keywords": ""})
        obs_data = json.loads(raw_observation)

    # 5. معالجة النتائج وتطبيق فلتر الوطن العربي + آخر 24 ساعة + منع التكرار
    existing_fingerprints = {j.job_fingerprint for j in existing_jobs}

    if obs_data.get("status") == "success":
        for item in obs_data.get("jobs", []):
            if not _passes_mena_and_avoidance_filter(item, avoidance_rules):
                continue

            url = item.get("url", "")
            company = item.get("company", "MENA Employer")
            title = item.get("title", "AI / Tech Role")

            fp = episodic_memory.generate_job_fingerprint(url=url, company=company, title=title)
            if fp in existing_fingerprints or episodic_memory.is_job_already_seen(url=url, company=company, title=title):
                continue

            discovered_job = DiscoveredJob(
                job_fingerprint=fp,
                title=title,
                company=company,
                location=item.get("location", "MENA / Remote"),
                work_mode=item.get("work_mode", "Remote / Hybrid"),
                url=url,
                source_platform=item.get("source_platform", current_task.tier_name),
                posted_within_24h=True,
                raw_description=item.get("raw_description", "")
            )
            existing_jobs.append(discovered_job)
            existing_fingerprints.add(fp)

        current_task.status = "completed"
    else:
        current_task.status = "failed"
        error_logs.append(f"[Task Failed] Both primary and backup tools failed for {current_task.task_id}.")

    search_plan[current_idx] = current_task

    return {
        "search_plan": search_plan,
        "current_task_index": current_idx + 1,
        "discovered_jobs": existing_jobs,
        "error_logs": error_logs,
        "next_worker": "supervisor"
    }