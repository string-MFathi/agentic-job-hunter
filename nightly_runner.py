import argparse
import fcntl
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
import httpx
from src.config import settings
from src.delivery.telegram_bot import has_valid_telegram_config
from src.graph.workflow import build_job_hunter_graph
from src.memory.memory_store import episodic_memory

@contextmanager
def atomic_process_lock(lock_path):
    """
    قفل عمليات ذري على مستوى نظام التشغيل (Process-Level Locking)
    يمنع تشغيل دورتين من الإيجنت في نفس اللحظة (Fail-Closed).
    """
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_file = open(lock_path, "w")
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_file.write(f"PID: {sys.platform} | Started: {datetime.now(timezone.utc).isoformat()}\n")
        lock_file.flush()
        yield
    except BlockingIOError:
        raise RuntimeError("❌ [Fail-Closed Lock]: هناك نسخة أخرى من الإيجنت تعمل حالياً. تم إلغاء التشغيل المكرر.")
    finally:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        except Exception:
            pass
        lock_file.close()

def _answer_callback_query(callback_id: str, text: str) -> None:
    """إرسال إشعار منبثق سريع داخل تليجرام يؤكد استلام ضغطة الزر"""
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/answerCallbackQuery"
    try:
        with httpx.Client(timeout=10.0) as client:
            client.post(url, json={"callback_query_id": callback_id, "text": text})
    except Exception:
        pass

def sync_telegram_callbacks() -> int:
    """
    سحب ضغطات الأزرار التفاعلية (✅ تم التقديم / ❌ استبعاد) من تليجرام
    وتحديث ذاكرة الإيجنت واستئناف الـ Checkpoints تلقائياً.
    """
    if not has_valid_telegram_config():
        return 0

    offset = 0
    if settings.telegram_offset_path.exists():
        try:
            offset = int(settings.telegram_offset_path.read_text().strip())
        except ValueError:
            offset = 0

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/getUpdates"
    params = {"timeout": 2, "allowed_updates": ["callback_query"]}
    if offset > 0:
        params["offset"] = offset

    processed_count = 0
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            updates = resp.json().get("result", [])
    except Exception as exc:
        print(f"⚠️ [Telegram Sync Warning]: {exc}")
        return 0

    for upd in updates:
        update_id = upd.get("update_id", 0)
        cb = upd.get("callback_query", {})
        data = cb.get("data", "")
        cb_id = cb.get("id", "")

        # صيغة الزر: action|short_run_id|short_job_fp
        parts = data.split("|") if "|" in data else data.split(":")
        if len(parts) >= 2:
            action = parts[0].strip().lower()
            short_fp = parts[-1].strip()

            # البحث عن الوظيفة في قاعدة البيانات لتحديث حالتها فوراً
            with episodic_memory._get_connection() as conn:
                row = conn.execute(
                    "SELECT job_fingerprint, company, title FROM seen_jobs WHERE job_fingerprint LIKE ? LIMIT 1",
                    (f"{short_fp}%",)
                ).fetchone()

            if row:
                full_fp = row["job_fingerprint"]
                company = row["company"]
                title = row["title"]

                if action == "apply":
                    episodic_memory.update_job_status(full_fp, "applied")
                    _answer_callback_query(cb_id, "✅ تم تسجيل التقديم على الوظيفة بنجاح")
                    print(f"✅ [Telegram Action]: Marked '{title}' @ '{company}' as APPLIED.")
                elif action == "reject":
                    episodic_memory.record_rejection_lesson(
                        job_fingerprint=full_fp,
                        company=company,
                        title=title,
                        rejection_reason="تم الاستبعاد بواسطة محمد فتحي عبر زر تليجرام"
                    )
                    _answer_callback_query(cb_id, "❌ تم استبعاد الوظيفة وتحديث الذاكرة الإبيسودية")
                    print(f"❌ [Telegram Action]: Rejected '{title}' @ '{company}' & stored avoidance rule.")
                processed_count += 1

        offset = max(offset, update_id + 1)

    if offset > 0:
        settings.telegram_offset_path.write_text(str(offset))

    return processed_count

def run_nightly_hunt(thread_id: str) -> None:
    """تشغيل دورة الصيد الليلية الكاملة ثم الإغلاق الآمن"""
    settings.validate_critical_paths()

    # 1. مزامنة أي ضغطات أزرار سابقة على تليجرام قبل بدء الدورة الجديدة
    synced = sync_telegram_callbacks()
    if synced:
        print(f"🔄 Synced {synced} button decision(s) from Telegram before starting hunt.")

    graph = build_job_hunter_graph(enable_interrupt=True)
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 150}

    print(f"🚀 [Nightly Runner] Starting Live Hunt | Thread ID: {thread_id}")
    print(f"📊 Initial Memory Stats: {episodic_memory.get_memory_stats()}")

    initial_state = {
        "run_id": thread_id,
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
        "discovered_jobs": [],
        "acceptance_analyses": {},
        "cover_letters": {},
        "critique_results": {},
        "approved_job_ids_for_telegram": [],
        "human_feedback_payload": None,
        "error_logs": [],
    }

    graph.invoke(initial_state, config=config)
    snapshot = graph.get_state(config)
    approved = snapshot.values.get("approved_job_ids_for_telegram", [])
    discovered = snapshot.values.get("discovered_jobs", [])
    print(f"🎯 Hunt Completed | Discovered: {len(discovered)} | Approved & Sent to Telegram: {len(approved)}")
    print(f"⏸️ State Saved in SQLite Checkpointer (Next Node: {snapshot.next})")

def main():
    parser = argparse.ArgumentParser(description="MENA Autonomous Job Hunter Nightly Runner")
    parser.add_argument("--mode", choices=["hunt", "sync", "listen"], default="hunt")
    parser.add_argument("--thread-id", default=f"hunt_{datetime.now().strftime('%Y%m%d_%H%M')}")
    args = parser.parse_args()

    with atomic_process_lock(settings.lock_file_path):
        if args.mode == "hunt":
            run_nightly_hunt(thread_id=args.thread_id)
        elif args.mode == "sync":
            count = sync_telegram_callbacks()
            print(f"✅ Synced {count} Telegram button action(s). Memory Stats: {episodic_memory.get_memory_stats()}")
        elif args.mode == "listen":
            print("👂 Listening for Telegram button clicks (Press Ctrl+C to stop)...")
            try:
                while True:
                    sync_telegram_callbacks()
                    time.sleep(3)
            except KeyboardInterrupt:
                print("\n🛑 Listener stopped safely.")

if __name__ == "__main__":
    main()