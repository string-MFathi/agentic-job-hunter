import json
from src.agents.mena_scout_react import _passes_mena_and_avoidance_filter
from src.tools.tool_router import DynamicToolRouter
from src.tools.scrapers.social_posts_24h import search_mena_social_posts_24h
from src.memory.memory_store import EpisodicMemoryStore

def test_mena_24h_filter_accepts_valid_arab_remote_job():
    """التأكد من قبول الوظائف المنشورة خلال 24 ساعة داخل الوطن العربي أو المتاحة Remote"""
    valid_job = {
        "title": "AI Agent Engineer",
        "location": "Riyadh, Saudi Arabia (Remote)",
        "posted_within_24h": True,
        "raw_description": "Building LangGraph agents for a MENA enterprise."
    }
    assert _passes_mena_and_avoidance_filter(valid_job, []) is True

def test_mena_24h_filter_rejects_old_or_non_mena_jobs():
    """التأكد من رفض الوظائف الأقدم من 24 ساعة أو المشروطة بالإقامة في أمريكا"""
    old_job = {
        "title": "AI Agent Developer",
        "location": "Cairo, Egypt",
        "posted_within_24h": False,
        "raw_description": "Great role in Egypt."
    }
    us_only_job = {
        "title": "Applied AI Engineer",
        "location": "Remote",
        "posted_within_24h": True,
        "raw_description": "US Citizens Only. Must reside in US."
    }
    assert _passes_mena_and_avoidance_filter(old_job, []) is False
    assert _passes_mena_and_avoidance_filter(us_only_job, []) is False

def test_dynamic_tool_router_and_error_recovery():
    """اختبار التوجيه الديناميكي للأدوات (Concept #6) والتعافي من الأعطال (Concept #7)"""
    tools = DynamicToolRouter.get_tools_for_tier("tier_1_social_and_direct_hiring")
    assert len(tools) == 2
    assert tools[0].name == "search_mena_social_posts_24h"

    # محاكاة سقوط الأداة والتأكد من عدم انهيار النظام
    err_json = search_mena_social_posts_24h.invoke({"roles": ["SIMULATE_FAILURE"]})
    err_payload = json.loads(err_json)
    assert err_payload["status"] == "tool_error"
    assert "TOOL FAILURE DETECTED" in err_payload["agent_recovery_instruction"]

def test_deduplication_and_episodic_lessons(tmp_path):
    """اختبار ذاكرة منع التكرار وتخزين دروس الاستبعاد (Concept #9)"""
    temp_db = tmp_path / "test_memory.sqlite"
    store = EpisodicMemoryStore(db_path=str(temp_db))

    fp = store.register_job(
        url="https://wuzzuf.net/jobs/p/999?utm_source=linkedin",
        company="Cairo AI Labs",
        title="AI Agent Developer",
        source_platform="Wuzzuf",
        acceptance_score=91
    )
    # حتى لو اختلف رابط التتبع، يجب اكتشاف التكرار
    assert store.is_job_already_seen("https://wuzzuf.net/jobs/p/999", "Cairo AI Labs", "AI Agent Developer") is True

    store.record_rejection_lesson(fp, "Cairo AI Labs", "AI Agent Developer", "راتب غير مناسب")
    rules = store.get_active_avoidance_rules()
    assert len(rules) == 1
    assert "راتب غير مناسب" in rules[0]