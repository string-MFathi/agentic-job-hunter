import logging
from typing import Dict, Any, List
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from src.config import settings
from src.memory.memory_store import episodic_memory
from src.state.agent_state import (
    NightlyHuntState,
    DiscoveredJob,
    AcceptanceAnalysis,
    CoverLetterDraft,
)

logger = logging.getLogger(__name__)

def has_valid_telegram_config() -> bool:
    """التحقق من وجود مفاتيح تليجرام حقيقية في ملف .env"""
    token = settings.telegram_bot_token.strip()
    chat_id = settings.telegram_chat_id.strip()
    return (
        bool(token)
        and bool(chat_id)
        and "your_telegram" not in token
        and "your_personal" not in chat_id
    )

def format_telegram_job_card(
    job: DiscoveredJob,
    analysis: AcceptanceAnalysis,
    draft: CoverLetterDraft
) -> str:
    """تنسيق بطاقة الوظيفة النهائية الجاهزة للإرسال على تليجرام"""
    strengths_bullets = "\n".join([f"  • {s}" for s in analysis.matching_strengths])
    gaps_bullets = "\n".join([f"  • {g}" for g in analysis.identified_gaps])

    card = (
        f"🎯 *فرصة جديدة | مطابقة بنسبة {analysis.acceptance_score}%*\n"
        f"🏷️ *تصنيف الفرصة:* {analysis.probability_label}\n\n"
        f"📌 *المسمى الوظيفي:* {job.title}\n"
        f"🏢 *الشركة:* {job.company}\n"
        f"🌍 *المكان ونظام العمل:* {job.location} ({job.work_mode})\n"
        f"📡 *المصدر:* {job.source_platform}\n"
        f"🆔 *بصمة الوظيفة:* `{job.job_fingerprint}`\n\n"
        f"📊 *تحليل قوة القبول (الواقعي):*\n"
        f"✅ *نقاط القوة المطابقة:*\n{strengths_bullets}\n\n"
        f"⚠️ *نقاط الانتباه / الثغرات:*\n{gaps_bullets}\n\n"
        f"💡 *النصيحة الاستراتيجية:*\n{analysis.strategic_reasoning}\n\n"
        f"📝 *الـ Cover Letter المخصص (نسخة معتمدة #{draft.revision_number}):*\n"
        f"```text\n{draft.content}\n```\n\n"
        f"🔗 *رابط الوظيفة المباشر:*\n{job.url}"
    )
    return card

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=6), reraise=True)
def _post_to_telegram_api(card_text: str, run_id: str, job_fp: str) -> None:
    """إرسال البطاقة عبر Telegram Bot API مع تضمين run_id و job_fp في الأزرار التفاعلية"""
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    # callback_data limit in Telegram is 64 bytes -> keep it compact: act|run_id|fp
    short_run = run_id[-18:]
    short_fp = job_fp[:16]
    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "✅ تم التقديم", "callback_data": f"apply|{short_run}|{short_fp}"},
                {"text": "❌ استبعاد (تحديث الذاكرة)", "callback_data": f"reject|{short_run}|{short_fp}"}
            ]
        ]
    }
    payload = {
        "chat_id": settings.telegram_chat_id,
        "text": card_text,
        "reply_markup": reply_markup,
        "disable_web_page_preview": False
    }
    with httpx.Client(timeout=15.0) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()

def send_heartbeat_summary(run_id: str, discovered_count: int, approved_count: int, error_count: int) -> None:
    """إشعار نبض الحياة (Dead Man's Switch) ليضمن لك أن الـ Cron يعمل حتى لو كانت الحصيلة صفراً"""
    if not has_valid_telegram_config() or settings.dry_run:
        return
    msg = (
        f"🤖 *تقرير نبض الحياة الليلي (MENA Job Hunter)*\n"
        f"• معرف الدورة: `{run_id}`\n"
        f"• إجمالي الوظائف المرصودة: {discovered_count}\n"
        f"• الوظائف المعتمدة والمرسلة (≥{settings.min_acceptance_score}%): {approved_count}\n"
        f"• ملاحظات التعافي التلقائي: {error_count}"
    )
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    try:
        with httpx.Client(timeout=10.0) as client:
            client.post(url, json={"chat_id": settings.telegram_chat_id, "text": msg})
    except Exception as exc:
        logger.warning(f"Failed to send heartbeat summary: {exc}")

def telegram_delivery_node(state: NightlyHuntState) -> Dict[str, Any]:
    """عقدة الإرسال لتليجرام + إرسال نبض الحياة (Dead Man's Switch)"""
    run_id = state.get("run_id", "nightly_run")
    approved_ids = state.get("approved_job_ids_for_telegram", [])
    discovered_jobs = {j.job_fingerprint: j for j in state.get("discovered_jobs", [])}
    analyses = state.get("acceptance_analyses", {})
    cover_letters = state.get("cover_letters", {})
    error_logs: List[str] = list(state.get("error_logs", []))

    sent_count = 0
    for fp in approved_ids:
        job = discovered_jobs.get(fp)
        analysis = analyses.get(fp)
        draft = cover_letters.get(fp)

        if not (job and analysis and draft):
            continue

        card_text = format_telegram_job_card(job, analysis, draft)

        if has_valid_telegram_config() and not settings.dry_run:
            try:
                _post_to_telegram_api(card_text, run_id, fp)
                episodic_memory.update_job_status(fp, "sent_to_telegram")
                sent_count += 1
            except Exception as exc:
                error_logs.append(f"[Telegram Send Error] Job {fp}: {exc}")
        else:
            print("\n" + "=" * 70)
            print("📱 [TELEGRAM DRY-RUN PREVIEW CARD]")
            print("=" * 70)
            print(card_text)
            print("🔘 Inline Buttons: [✅ تم التقديم]  |  [❌ استبعاد (تحديث الذاكرة)]")
            print("=" * 70 + "\n")
            episodic_memory.update_job_status(fp, "sent_to_telegram_dry_run")
            sent_count += 1

    # إرسال ملخص نبض الحياة في نهاية كل ليلة
    send_heartbeat_summary(
        run_id=run_id,
        discovered_count=len(discovered_jobs),
        approved_count=sent_count,
        error_count=len(error_logs)
    )

    return {
        "error_logs": error_logs,
        "next_worker": "feedback_resume_node"
    }

def feedback_resume_node(state: NightlyHuntState) -> Dict[str, Any]:
    """عقدة استئناف القرار البشري بعد ضغط الزر في تليجرام"""
    feedback = state.get("human_feedback_payload")
    if not feedback:
        return {"next_worker": "END"}

    job_fp = feedback.get("job_fingerprint", "")
    action = feedback.get("action", "").lower()
    reason = feedback.get("reason", "").strip()

    discovered_map = {j.job_fingerprint: j for j in state.get("discovered_jobs", [])}
    # مطابقة البصمة حتى لو كانت مختصرة لـ 16 حرفاً من زر تليجرام
    target_job = discovered_map.get(job_fp)
    if not target_job:
        for full_fp, j_obj in discovered_map.items():
            if full_fp.startswith(job_fp):
                target_job = j_obj
                job_fp = full_fp
                break

    company = target_job.company if target_job else feedback.get("company", "Unknown Company")
    title = target_job.title if target_job else feedback.get("title", "Unknown Role")

    if action == "apply":
        episodic_memory.update_job_status(job_fp, "applied")
    elif action == "reject":
        rejection_reason = reason or "تم الاستبعاد عبر زر تليجرام التفاعلي"
        episodic_memory.record_rejection_lesson(
            job_fingerprint=job_fp,
            company=company,
            title=title,
            rejection_reason=rejection_reason
        )

    return {"next_worker": "END"}