from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from src.agents.llm_factory import get_structured_llm, has_valid_groq_key
from src.memory.memory_store import episodic_memory
from src.state.agent_state import NightlyHuntState, AcceptanceAnalysis, DiscoveredJob

# المهارات الموثقة في سيرة محمد فتحي الذاتية للفحص المبدئي السريع
VERIFIED_CV_SKILLS = [
    "python", "langgraph", "langchain", "rag", "pinecone", "chroma",
    "asyncio", "fastapi", "rest", "sqlite", "imap", "docker", "aws",
    "ci/cd", "opentelemetry", "pytest", "tenacity", "zapier", "make",
    "product manager", "swagger", "postman", "clean architecture"
]

# مهارات خارج السيرة الذاتية لرصدها كفجوات محتملة إن طُلبت في إعلان الوظيفة
COMMON_EXTERNAL_SKILLS = [
    "kubernetes", "k8s", "golang", "rust", "c++", "terraform", "pytorch", "spark"
]

def _build_local_fallback_analysis(job: DiscoveredJob) -> AcceptanceAnalysis:
    """محرك تحليل حتمي يعمل عند عدم وجود مفتاح Groq API في ملف .env"""
    desc_lower = f"{job.title} {job.raw_description}".lower()
    
    matched = [s for s in VERIFIED_CV_SKILLS if s in desc_lower]
    gaps = [g for g in COMMON_EXTERNAL_SKILLS if g in desc_lower]

    base_score = 84 + min(len(matched) * 2, 14) - (len(gaps) * 5)
    final_score = max(min(base_score, 98), 65)

    if final_score >= 90:
        label = "ممتازة (أولوية قصوى)"
    elif final_score >= 80:
        label = "قوية"
    elif final_score >= 70:
        label = "متوسطة"
    else:
        label = "ضعيفة"

    strengths = [
        "خبرة 6 سنوات تدمج بين هندسة البرمجيات وإدارة المنتجات التقنية (TPM) وبناء أنظمة ذكاء اصطناعي إنتاجية.",
        "تطبيق عملي لمعمارية Fail-Closed وأقفال SQLite لمنع التكرار في مشروع EVNTOWN Outbound Engine.",
        f"تطابق مباشر في المهارات التقنية المطلوبة: {', '.join(matched[:6]) if matched else 'Python, LangGraph, AI Workflows'}."
    ]

    return AcceptanceAnalysis(
        job_fingerprint=job.job_fingerprint,
        acceptance_score=final_score,
        probability_label=label,
        matching_strengths=strengths,
        identified_gaps=gaps if gaps else ["لا توجد فجوات جوهرية مقارنة بمتطلبات الإعلان الأساسية."],
        strategic_reasoning=(
            f"الوظيفة ({job.title}) في ({job.company}) تتقاطع بقوة مع مشاريعك في LangGraph و RAG "
            f"وخلفية الـ Technical Product Management. ركز عند التقديم على موثوقية الأنظمة (Idempotency & Error Handling)."
        )
    )

def acceptance_analyst_node(state: NightlyHuntState) -> Dict[str, Any]:
    """
    وكيل تحليل فرصة القبول (Step 4.4: Acceptance Analyst Worker)
    يقارن الوظيفة المكتشفة مع السيرة الذاتية عبر Llama 4 Maverick (Structured Output).
    """
    discovered_jobs = state.get("discovered_jobs", [])
    analyses = dict(state.get("acceptance_analyses", {}))
    cv_text = state.get("candidate_cv_text", "")
    error_logs: List[str] = []

    # البحث عن أول وظيفة مكتشفة لم يتم تحليلها بعد
    target_job: DiscoveredJob | None = None
    for job in discovered_jobs:
        if job.job_fingerprint not in analyses:
            target_job = job
            break

    if target_job is None:
        return {"next_worker": "supervisor"}

    analysis_result: AcceptanceAnalysis | None = None

    if has_valid_groq_key():
        try:
            llm = get_structured_llm(temperature=0.0)
            structured_llm = llm.with_structured_output(AcceptanceAnalysis)
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", (
                    "أنت خبير تقييم توظيف تقني صارم وواقعي. مهمتك مقارنة إعلان الوظيفة مع السيرة الذاتية المعتمدة "
                    "لمحمد فتحي (Ground Truth CV) وإخراج تقييم دقيق باللغة العربية داخل قالب AcceptanceAnalysis.\n"
                    "قواعد صارمة:\n"
                    "1. لا تخترع أي مهارة غير موجودة في السيرة الذاتية.\n"
                    "2. حدد نقاط القوة من مشاريعه الحقيقية (EVNTOWN Outbound Engine, CompetiTrack, Multi-Agent Systems, Ready Pro Academy, SAPQ Tech).\n"
                    "3. اذكر بصراحة أي مهارة مطلوبة في الإعلان وغير موجودة في سيرته الذاتية داخل حقل identified_gaps."
                )),
                ("human", (
                    "=== السيرة الذاتية المعتمدة ===\n{cv_text}\n\n"
                    "=== الوظيفة المطلوب تحليلها ===\n"
                    "Fingerprint: {fp}\nTitle: {title}\nCompany: {company}\nLocation: {location}\n"
                    "Description: {desc}"
                ))
            ])
            chain = prompt | structured_llm
            analysis_result = chain.invoke({
                "cv_text": cv_text,
                "fp": target_job.job_fingerprint,
                "title": target_job.title,
                "company": target_job.company,
                "location": target_job.location,
                "desc": target_job.raw_description
            })
            analysis_result.job_fingerprint = target_job.job_fingerprint
        except Exception as exc:
            error_logs.append(f"[Analyst Fallback Triggered] Groq API error: {exc}")
            analysis_result = _build_local_fallback_analysis(target_job)
    else:
        analysis_result = _build_local_fallback_analysis(target_job)

    analyses[target_job.job_fingerprint] = analysis_result

    # تسجيل الوظيفة مبدئياً في قاعدة البيانات مع نسبة قبولها
    episodic_memory.register_job(
        url=target_job.url,
        company=target_job.company,
        title=target_job.title,
        source_platform=target_job.source_platform,
        acceptance_score=analysis_result.acceptance_score,
        status="analyzed"
    )

    return {
        "acceptance_analyses": analyses,
        "error_logs": error_logs,
        "next_worker": "supervisor"
    }