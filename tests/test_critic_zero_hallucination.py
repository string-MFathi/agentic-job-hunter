from src.agents.critic import critic_node
from src.agents.cover_letter_writer import cover_letter_writer_node
from src.state.agent_state import DiscoveredJob, AcceptanceAnalysis, CoverLetterDraft

def _sample_discovered_job() -> DiscoveredJob:
    return DiscoveredJob(
        job_fingerprint="fp_test_001",
        title="AI Agent Engineer",
        company="MenaTech AI Solutions",
        location="Dubai, UAE (Remote)",
        work_mode="Remote",
        url="https://linkedin.com/jobs/view/123",
        source_platform="LinkedIn Jobs",
        posted_within_24h=True,
        raw_description="Looking for Python, LangGraph, RAG, and SQLite experience."
    )

def test_critic_rejects_hallucinated_skills_and_cliches():
    """التأكد من أن الناقد يرفض أي مهارة خارج السيرة الذاتية (مثل Kubernetes/Rust) أو الكليشيهات"""
    job = _sample_discovered_job()
    bad_draft = CoverLetterDraft(
        job_fingerprint=job.job_fingerprint,
        content="I hope this email finds you well. I have built Kubernetes and Golang microservices.",
        highlighted_projects=[],
        revision_number=1
    )
    state = {
        "discovered_jobs": [job],
        "cover_letters": {job.job_fingerprint: bad_draft},
        "critique_results": {}
    }
    res = critic_node(state)
    critique = res["critique_results"][job.job_fingerprint]

    assert critique.is_approved is False
    assert critique.zero_hallucination_verified is False
    assert "CRITICAL HALLUCINATION" in critique.feedback_for_rewrite
    assert "CLICHE DETECTED" in critique.feedback_for_rewrite

def test_self_correction_reflection_loop_produces_approved_draft():
    """اختبار حلقة التصحيح الذاتي (Concept #3): الكاتب يصلح المسودة المرفوضة والناقد يعتمدها"""
    job = _sample_discovered_job()
    analysis = AcceptanceAnalysis(
        job_fingerprint=job.job_fingerprint,
        acceptance_score=95,
        probability_label="ممتازة (أولوية قصوى)",
        matching_strengths=["EVNTOWN Outbound Engine fail-closed architecture"],
        identified_gaps=["لا توجد فجوات"],
        strategic_reasoning="تطابق كامل"
    )
    bad_draft = CoverLetterDraft(
        job_fingerprint=job.job_fingerprint,
        content="I hope this email finds you well. I know Rust.",
        highlighted_projects=[],
        revision_number=1
    )
    state = {
        "candidate_cv_text": "Mohamed Fathi CV",
        "discovered_jobs": [job],
        "acceptance_analyses": {job.job_fingerprint: analysis},
        "cover_letters": {job.job_fingerprint: bad_draft},
        "critique_results": {}
    }

    # الجولة الأولى: رفض من الناقد
    state.update(critic_node(state))
    assert state["critique_results"][job.job_fingerprint].is_approved is False

    # الجولة الثانية: إعادة صياغة تلقائية من الكاتب ثم اعتماد الناقد
    state.update(cover_letter_writer_node(state))
    assert state["cover_letters"][job.job_fingerprint].revision_number == 2

    state.update(critic_node(state))
    assert state["critique_results"][job.job_fingerprint].is_approved is True