from typing import Dict, Any
from src.config import settings
from src.state.agent_state import NightlyHuntState

def supervisor_node(state: NightlyHuntState) -> Dict[str, Any]:
    """
    المايسترو الموجه (Concept #4: Multi-Agent Supervisor-Worker Pattern)
    يفحص حالة الجراف اللحظية ويوجه التنفيذ للوكيل المتخصص التالي بشكل حتمي وآمن.
    """
    search_plan = state.get("search_plan", [])
    current_idx = state.get("current_task_index", 0)
    discovered_jobs = state.get("discovered_jobs", [])
    analyses = state.get("acceptance_analyses", {})
    cover_letters = state.get("cover_letters", {})
    critiques = state.get("critique_results", {})

    # 1. هل لا تزال هناك مهام صيد في الخطة الليلية؟
    if current_idx < len(search_plan):
        return {"next_worker": "mena_scout_worker"}

    # 2. هل هناك وظائف مكتشفة لم يتم تحليل فرصة قبولها بعد؟
    for job in discovered_jobs:
        if job.job_fingerprint not in analyses:
            return {"next_worker": "acceptance_analyst_worker"}

    # 3. هل هناك وظائف مؤهلة (>= min_acceptance_score) تحتاج كتابة أو إعادة صياغة Cover Letter؟
    for job in discovered_jobs:
        fp = job.job_fingerprint
        analysis = analyses.get(fp)
        if not analysis or analysis.acceptance_score < settings.min_acceptance_score:
            continue

        draft = cover_letters.get(fp)
        critique = critiques.get(fp)

        # لم يُكتب لها خطاب بعد
        if draft is None:
            return {"next_worker": "cover_letter_writer_worker"}

        # كُتب لها خطاب ولم يمر على الناقد بعد
        if critique is None:
            return {"next_worker": "critic_node"}

        # رفضها الناقد ولم تتجاوز الحد الأقصى لمحاولات التصحيح (Reflection Loop)
        if not critique.is_approved and draft.revision_number < settings.max_critic_retries:
            return {"next_worker": "cover_letter_writer_worker"}

    # 4. اكتملت جميع المهام والفحوصات -> الانتقال للإرسال عبر تليجرام
    approved_ids = [
        fp for fp, crit in critiques.items()
        if crit.is_approved
    ]
    return {
        "approved_job_ids_for_telegram": approved_ids,
        "next_worker": "telegram_delivery"
    }