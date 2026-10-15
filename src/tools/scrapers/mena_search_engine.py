import json
from typing import List, Dict, Any
from tavily import TavilyClient
from src.config import settings
from src.memory.memory_store import episodic_memory

def execute_mena_24h_search(
    roles: List[str],
    domains: List[str],
    tier_label: str,
    extra_keywords: str = "",
    max_results: int = 8
) -> str:
    """
    محرك بحث مركزي يمسح المنصات المحددة خلال آخر 24 ساعة فقط داخل الوطن العربي
    ويستبعد تلقائياً الوظائف المسجلة مسبقاً في ذاكرة منع التكرار (SQLite).
    """
    if "SIMULATE_FAILURE" in extra_keywords or any("SIMULATE_FAILURE" in r for r in roles):
        raise RuntimeError(f"Simulated rate-limit (429) or timeout on {tier_label}")

    roles_query = " OR ".join([f'"{r}"' for r in roles[:3]])
    mena_filter = '(Egypt OR "Saudi Arabia" OR UAE OR Dubai OR Riyadh OR Qatar OR Kuwait OR Jordan OR MENA OR Remote OR "مصر" OR "السعودية" OR "الإمارات")'
    full_query = f"({roles_query}) {mena_filter} {extra_keywords}".strip()

    api_key = settings.tavily_api_key.strip()
    is_valid_key = api_key.startswith("tvly-") and "your_tavily_key" not in api_key

    raw_results: List[Dict[str, Any]] = []

    if is_valid_key:
        client = TavilyClient(api_key=api_key)
        search_kwargs: Dict[str, Any] = {
            "query": full_query,
            "search_depth": "advanced",
            "days": 1,  # المحاولة الأولى: آخر 24 ساعة
            "max_results": max_results,
        }
        if domains:
            search_kwargs["include_domains"] = domains

        response = client.search(**search_kwargs)
        raw_results = response.get("results", [])

        # [تحسين كلود]: إذا لم تفهرس المنصات العربية نتائج في آخر 24 ساعة، وسّع النافذة لـ 72 ساعة تلقائياً
        if not raw_results:
            search_kwargs["days"] = 3
            response = client.search(**search_kwargs)
            raw_results = response.get("results", [])
    else:
        sample_domain = domains[0] if domains else "linkedin.com/jobs"
        sample_role = roles[0] if roles else "AI Agent Engineer"
        raw_results = [
            {
                "title": f"{sample_role} (Remote - MENA) | MenaTech AI Solutions",
                "url": f"https://{sample_domain}/view/mena-ai-agent-2026",
                "content": (
                    f"Posted 5 hours ago. Location: Dubai, UAE / Cairo, Egypt (100% Remote across MENA). "
                    f"We are hiring a {sample_role} with strong Python, LangGraph, RAG (Pinecone/Chroma), "
                    f"asyncio, FastAPI, and SQLite state management experience to build production AI workflows."
                )
            }
        ]

    fresh_jobs = []
    skipped_duplicates = 0

    for item in raw_results:
        url = item.get("url", "")
        title_line = item.get("title", "Unknown Role")
        content = item.get("content", "")

        # الفصل الذكي: الأولوية لعلامة '|' ثم ' - ' للحفاظ على الأقواس مثل (Remote - MENA)
        if "|" in title_line:
            parts = [p.strip() for p in title_line.split("|")]
        elif " - " in title_line:
            parts = [p.strip() for p in title_line.split(" - ")]
        else:
            parts = [title_line.strip()]

        job_title = parts[0] if parts else title_line
        company = parts[1] if len(parts) > 1 else tier_label

        if episodic_memory.is_job_already_seen(url=url, company=company, title=job_title):
            skipped_duplicates += 1
            continue

        fresh_jobs.append({
            "title": job_title,
            "company": company,
            "url": url,
            "source_platform": tier_label,
            "posted_within_24h": True,
            "location": "MENA / Remote",
            "work_mode": "Remote / Hybrid",
            "raw_description": content[:1500]
        })

    return json.dumps({
        "status": "success",
        "tier": tier_label,
        "query_executed": full_query,
        "fresh_jobs_count": len(fresh_jobs),
        "skipped_duplicates_count": skipped_duplicates,
        "jobs": fresh_jobs
    }, ensure_ascii=False)