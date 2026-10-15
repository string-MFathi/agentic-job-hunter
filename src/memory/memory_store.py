import hashlib
import sqlite3
from typing import Dict, List, Optional
from urllib.parse import urlparse, urlunparse
from src.config import settings

class EpisodicMemoryStore:
    """
    محرك الذاكرة طويلة المدى والإبيسودية (Concept #9: Long-Term & Episodic Memory)
    يدير:
    1. منع تكرار الوظائف عبر الليالي (Deduplication Store - Step 2.2)
    2. التعلم من أسباب الاستبعاد البشرية (Episodic Lessons Table - Step 2.3)
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = str(db_path or settings.episodic_db_path)
        self._initialize_tables()

    def _get_connection(self) -> sqlite3.Connection:
        """إنشاء اتصال آمن بقاعدة بيانات SQLite مع تفعيل وضع WAL لمنع قفل القاعدة"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _initialize_tables(self) -> None:
        """إنشاء جداول منع التكرار والدروس المستفادة إذا لم تكن موجودة"""
        with self._get_connection() as conn:
            # 1. جدول منع تكرار الوظائف (Step 2.2)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS seen_jobs (
                    job_fingerprint TEXT PRIMARY KEY,
                    url_hash TEXT NOT NULL,
                    canonical_url TEXT NOT NULL,
                    company TEXT NOT NULL,
                    title TEXT NOT NULL,
                    source_platform TEXT,
                    acceptance_score INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'discovered',
                    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_seen_jobs_url_hash ON seen_jobs(url_hash);")

            # 2. جدول الدروس الإبيسودية المستفادة من رفض المستخدم في تليجرام (Step 2.3)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS episodic_lessons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_fingerprint TEXT,
                    company TEXT,
                    title TEXT,
                    rejection_reason TEXT NOT NULL,
                    avoidance_rule TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    @staticmethod
    def normalize_url(url: str) -> str:
        """تنظيف الرابط من معاملات التتبع (UTM parameters) لضمان دقة البصمة"""
        if not url:
            return ""
        parsed = urlparse(url.strip())
        # الاحتفاظ بالمسار الأساسي فقط بدون استعلامات التتبع العشوائية
        clean_url = urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip("/"), "", "", ""))
        return clean_url

    @classmethod
    def generate_job_fingerprint(cls, url: str, company: str, title: str) -> str:
        """
        توليد بصمة فولاذية (SHA-256) تجمع بين اسم الشركة والمسمى الوظيفي.
        هذا يضمن أنه حتى لو نُشرت نفس الوظيفة على منصتين مختلفتين لن تتكرر.
        """
        norm_company = "".join(company.lower().split())
        norm_title = "".join(title.lower().split())
        raw_key = f"{norm_company}::{norm_title}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:24]

    @classmethod
    def generate_url_hash(cls, url: str) -> str:
        """توليد بصمة خاصة بالرابط المنظف كخط دفاع ثانٍ ضد التكرار"""
        clean = cls.normalize_url(url)
        return hashlib.sha256(clean.encode("utf-8")).hexdigest()[:24]

    def is_job_already_seen(self, url: str, company: str, title: str) -> bool:
        """التحقق الفوري مما إذا كانت الوظيفة قد مرت على الإيجنت في أي ليلة سابقة"""
        fingerprint = self.generate_job_fingerprint(url, company, title)
        url_hash = self.generate_url_hash(url)
        
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM seen_jobs WHERE job_fingerprint = ? OR url_hash = ? LIMIT 1",
                (fingerprint, url_hash)
            ).fetchone()
            return row is not None

    def register_job(
        self,
        url: str,
        company: str,
        title: str,
        source_platform: str,
        acceptance_score: int = 0,
        status: str = "discovered"
    ) -> str:
        """تسجيل الوظيفة في ذاكرة منع التكرار وإرجاع بصمتها الفريدة"""
        fingerprint = self.generate_job_fingerprint(url, company, title)
        url_hash = self.generate_url_hash(url)
        clean_url = self.normalize_url(url)

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO seen_jobs (
                    job_fingerprint, url_hash, canonical_url, company, title,
                    source_platform, acceptance_score, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_fingerprint) DO UPDATE SET
                    acceptance_score = excluded.acceptance_score,
                    status = excluded.status
            """, (fingerprint, url_hash, clean_url, company.strip(), title.strip(), source_platform, acceptance_score, status))
            conn.commit()
            
        return fingerprint

    def update_job_status(self, job_fingerprint: str, new_status: str) -> None:
        """تحديث حالة الوظيفة (مثلاً: sent_to_telegram, applied, rejected)"""
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE seen_jobs SET status = ? WHERE job_fingerprint = ?",
                (new_status, job_fingerprint)
            )
            conn.commit()

    def record_rejection_lesson(
        self,
        job_fingerprint: str,
        company: str,
        title: str,
        rejection_reason: str,
        avoidance_rule: Optional[str] = None
    ) -> None:
        """
        حفظ درس جديد في الذاكرة الإبيسودية عندما يضغط محمد فتحي على 'استبعاد' في تليجرام.
        """
        rule = avoidance_rule or f"تجنب الوظائف المشابهة لـ ({title} في {company}) للسبب التالي: {rejection_reason}"
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO episodic_lessons (job_fingerprint, company, title, rejection_reason, avoidance_rule)
                VALUES (?, ?, ?, ?, ?)
            """, (job_fingerprint, company, title, rejection_reason.strip(), rule.strip()))
            
            # تحديث حالة الوظيفة في جدول الوظائف المرصودة إلى مستبعدة
            conn.execute(
                "UPDATE seen_jobs SET status = 'rejected' WHERE job_fingerprint = ?",
                (job_fingerprint,)
            )
            conn.commit()

    def get_active_avoidance_rules(self, limit: int = 15) -> List[str]:
        """استرجاع أحدث قواعد التجنب لحقنها في عقل وكيل التخطيط والصيد كل ليلة"""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT avoidance_rule FROM episodic_lessons
                WHERE is_active = 1
                ORDER BY id DESC
                LIMIT ?
            """, (limit,)).fetchall()
            return [row["avoidance_rule"] for row in rows]

    def get_memory_stats(self) -> Dict[str, int]:
        """إحصائيات سريعة عن حالة الذاكرة لطباعتها عند بدء التشغيل الليلي"""
        with self._get_connection() as conn:
            total_seen = conn.execute("SELECT COUNT(*) AS cnt FROM seen_jobs").fetchone()["cnt"]
            total_lessons = conn.execute("SELECT COUNT(*) AS cnt FROM episodic_lessons WHERE is_active = 1").fetchone()["cnt"]
            return {"seen_jobs_count": total_seen, "active_lessons_count": total_lessons}

# كائن موحد لاستخدامه في كافة أنحاء المشروع
episodic_memory = EpisodicMemoryStore()