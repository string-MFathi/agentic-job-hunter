from typing import Dict, Any, List
from src.state.agent_state import NightlyHuntState, CritiqueResult, DiscoveredJob, CoverLetterDraft

# قائمة المهارات غير الموجودة في سيرة محمد فتحي الذاتية (إذا ادعاها الكاتب في الخطاب يعتبر هلوسة!)
UNVERIFIED_SKILLS_BLACKLIST = [
    "kubernetes", "k8s", "golang", "rust", "c++", "ruby on rails",
    "angular", "vue.js", "laravel", ".net", "spring boot"
]

# قائمة العبارات المبتذلة الممنوعة
BANNED_CLICHES = [
    "i hope this email finds you well",
    "i hope this message finds you well",
    "to whom it may concern",
    "please find attached my resume for your consideration"
]

# أسماء المشاريع والشركات الموثقة في السيرة الذاتية التي يجب الاستشهاد بواحد منها على الأقل
VERIFIED_PORTFOLIO_ANCHORS = [
    "evntown", "competitrack", "ready pro", "sapq", "langgraph"
]

def critic_node(state: NightlyHuntState) -> Dict[str, Any]:
    """
    عقدة النقد والمراجعة الذاتية (Step 4.6 & Concept #3: Reflection & Self-Critique Loop)
    تفحص الـ Cover Letter والتحليل بصرامة، وترفض أي هلوسة أو كليشيه لتعيده للكاتب تلقائياً.
    """
    discovered_jobs = state.get("discovered_jobs", [])
    cover_letters = state.get("cover_letters", {})
    critiques = dict(state.get("critique_results", {}))

    target_job: DiscoveredJob | None = None
    target_draft: CoverLetterDraft | None = None

    for job in discovered_jobs:
        fp = job.job_fingerprint
        if fp in cover_letters and fp not in critiques:
            target_job = job
            target_draft = cover_letters[fp]
            break

    if target_job is None or target_draft is None:
        return {"next_worker": "supervisor"}

    fp = target_job.job_fingerprint
    text_lower = target_draft.content.lower()

    issues: List[str] = []
    zero_hallucination_ok = True
    mena_24h_ok = bool(target_job.posted_within_24h)

    # 1. فحص الهلوسة (هل ادعى الخطاب مهارة غير موجودة في السيرة الذاتية؟)
    hallucinated_terms = [term for term in UNVERIFIED_SKILLS_BLACKLIST if term in text_lower]
    if hallucinated_terms:
        zero_hallucination_ok = False
        issues.append(
            f"CRITICAL HALLUCINATION: Remove unverified skills not in Mohamed's CV: {', '.join(hallucinated_terms)}."
        )

    # 2. فحص الكليشيهات الممنوعة
    detected_cliches = [c for c in BANNED_CLICHES if c in text_lower]
    if detected_cliches:
        issues.append(
            f"CLICHE DETECTED: Remove generic opening/closing phrase: '{detected_cliches[0]}'."
        )

    # 3. التأكد من الاستشهاد بمشروع حقيقي من السيرة الذاتية
    if not any(anchor in text_lower for anchor in VERIFIED_PORTFOLIO_ANCHORS):
        issues.append(
            "MISSING EVIDENCE: Must cite concrete achievements from Mohamed's CV (e.g., EVNTOWN Outbound Engine or CompetiTrack)."
        )

    # 4. فحص شرط الـ 24 ساعة والوطن العربي
    if not mena_24h_ok:
        issues.append("TIMEFRAME VIOLATION: Job is not verified as posted within the last 24 hours.")

    # قرار الناقد النهائي
    if not issues:
        critique_res = CritiqueResult(
            job_fingerprint=fp,
            is_approved=True,
            quality_score=9,
            zero_hallucination_verified=True,
            mena_and_24h_verified=True,
            feedback_for_rewrite=""
        )
    else:
        critique_res = CritiqueResult(
            job_fingerprint=fp,
            is_approved=False,
            quality_score=4,
            zero_hallucination_verified=zero_hallucination_ok,
            mena_and_24h_verified=mena_24h_ok,
            feedback_for_rewrite=" | ".join(issues)
        )

    critiques[fp] = critique_res

    return {
        "critique_results": critiques,
        "next_worker": "supervisor"
    }