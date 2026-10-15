from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from src.config import settings
from src.agents.llm_factory import get_agentic_llm, has_valid_groq_key
from src.state.agent_state import NightlyHuntState, CoverLetterDraft, DiscoveredJob, AcceptanceAnalysis

def _build_local_fallback_cover_letter(
    job: DiscoveredJob,
    analysis: AcceptanceAnalysis,
    revision_number: int,
    critic_feedback: str = ""
) -> CoverLetterDraft:
    """توليد خطاب تقديم احترافي وموزون يعتمد حصرياً على مشاريع السيرة الذاتية"""
    content = (
        f"Dear Hiring Team at {job.company},\n\n"
        f"I am applying for the {job.title} role. With 6 years of experience spanning software engineering "
        f"and technical product management, I specialize in architecting reliable, production-ready Python "
        f"and LangGraph AI systems.\n\n"
        f"In my recent work on the EVNTOWN Outbound Engine, I engineered a fail-closed, asynchronous lead "
        f"discovery pipeline using Python, Groq LLMs, Tavily API, SQLite idempotency locks, and Tenacity "
        f"backoff mechanisms to guarantee zero duplicate processing. Additionally, I architected CompetiTrack "
        f"(an agentic RAG pipeline using Pinecone and Chroma) and automated backend operations at Ready Pro Academy.\n\n"
        f"Combining hands-on agentic engineering with 6 years of product lifecycle ownership across MENA SaaS "
        f"platforms, I am ready to deliver immediate impact to {job.company}.\n\n"
        f"Best regards,\n"
        f"Mohamed Fathi\n"
        f"Cairo, Egypt | +201101633056 | string.mohamedfathi@gmail.com"
    )

    return CoverLetterDraft(
        job_fingerprint=job.job_fingerprint,
        content=content,
        highlighted_projects=[
            "EVNTOWN Outbound Engine",
            "Competitive Intelligence Agent (CompetiTrack)",
            "Ready Pro Academy Automation"
        ],
        revision_number=revision_number
    )

def cover_letter_writer_node(state: NightlyHuntState) -> Dict[str, Any]:
    """
    وكيل صياغة خطاب التقديم (Step 4.5: Cover Letter Writer Worker)
    يصيغ خطاب تقديم مخصص للوظيفة، ويعيد الصياغة تلقائياً إذا تلقى ملاحظات نقد من Critic Node.
    """
    discovered_jobs = state.get("discovered_jobs", [])
    analyses = state.get("acceptance_analyses", {})
    cover_letters = dict(state.get("cover_letters", {}))
    critiques = dict(state.get("critique_results", {}))
    cv_text = state.get("candidate_cv_text", "")
    error_logs: List[str] = []

    target_job: DiscoveredJob | None = None
    target_analysis: AcceptanceAnalysis | None = None
    revision_num = 1
    critic_feedback = ""

    # البحث عن الوظيفة التي تحتاج كتابة مسودة أولى أو إعادة كتابة بعد رفض الناقد
    for job in discovered_jobs:
        fp = job.job_fingerprint
        analysis = analyses.get(fp)
        if not analysis or analysis.acceptance_score < settings.min_acceptance_score:
            continue

        existing_draft = cover_letters.get(fp)
        existing_critique = critiques.get(fp)

        if existing_draft is None:
            target_job = job
            target_analysis = analysis
            revision_num = 1
            break

        if existing_critique and not existing_critique.is_approved and existing_draft.revision_number < settings.max_critic_retries:
            target_job = job
            target_analysis = analysis
            revision_num = existing_draft.revision_number + 1
            critic_feedback = existing_critique.feedback_for_rewrite
            break

    if target_job is None or target_analysis is None:
        return {"next_worker": "supervisor"}

    fp = target_job.job_fingerprint
    draft_result: CoverLetterDraft | None = None

    if has_valid_groq_key():
        try:
            llm = get_agentic_llm(temperature=0.2)
            structured_llm = llm.with_structured_output(CoverLetterDraft)

            prompt = ChatPromptTemplate.from_messages([
                ("system", (
                    "أنت كاتب خطابات تقديم تقنية (Technical Cover Letters) محترف. اكتب Cover Letter موجزاً ومباشراً "
                    "(150-220 كلمة) باللغة الإنجليزية المهنية البسيطة والواضحة لمحمد فتحي.\n"
                    "قواعد صارمة:\n"
                    "1. ممنوع استخدام مقدمات مبتذلة مثل 'I hope this email finds you well' أو 'I am writing to express my interest'.\n"
                    "2. ممنوع منعاً باتاً ذكر أي تقنية أو مشروع غير موجود في السيرة الذاتية المرفقة.\n"
                    "3. اربط متطلبات الوظيفة بمشاريعه الحقيقية (مثل EVNTOWN Outbound Engine, CompetiTrack, Hierarchical Multi-Agent System) وخبرته كـ TPM.\n"
                    "4. إذا وُجدت ملاحظات من المراجع (Critic Feedback)، التزم بتصحيحها فوراً."
                )),
                ("human", (
                    "=== السيرة الذاتية المعتمدة ===\n{cv_text}\n\n"
                    "=== الوظيفة المستهدفة ===\nTitle: {title}\nCompany: {company}\nDescription: {desc}\n\n"
                    "=== نقاط القوة من التحليل ===\n{strengths}\n\n"
                    "=== ملاحظات الناقد للتصحيح (إن وجدت - النسخة رقم {rev}) ===\n{feedback}"
                ))
            ])
            chain = prompt | structured_llm
            draft_result = chain.invoke({
                "cv_text": cv_text,
                "title": target_job.title,
                "company": target_job.company,
                "desc": target_job.raw_description,
                "strengths": "\n".join(target_analysis.matching_strengths),
                "rev": revision_num,
                "feedback": critic_feedback or "None (First Draft)"
            })
            draft_result.job_fingerprint = fp
            draft_result.revision_number = revision_num
        except Exception as exc:
            error_logs.append(f"[Writer Fallback Triggered] Groq API error: {exc}")
            draft_result = _build_local_fallback_cover_letter(target_job, target_analysis, revision_num, critic_feedback)
    else:
        draft_result = _build_local_fallback_cover_letter(target_job, target_analysis, revision_num, critic_feedback)

    cover_letters[fp] = draft_result

    # مسح نتيجة النقد القديمة (إن وجدت) لإجبار المايسترو على إرسال النسخة الجديدة إلى Critic Node
    if fp in critiques:
        del critiques[fp]

    return {
        "cover_letters": cover_letters,
        "critique_results": critiques,
        "error_logs": error_logs,
        "next_worker": "supervisor"
    }