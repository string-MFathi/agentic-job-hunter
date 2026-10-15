import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# تحميل متغيرات البيئة من ملف .env
load_dotenv()

# تحديد المسارات الجذرية للمشروع بدقة
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PROFILE_DIR = DATA_DIR / "profile"

class AgentConfig(BaseModel):
    """الإعدادات المركزية لمحرك صيد الوظائف الليلي (Fail-Closed Configuration)"""
    
    # مسارات ملفات الهوية وقواعد البيانات
    cv_markdown_path: Path = Field(default=PROFILE_DIR / "mohamed_fathi_cv.md")
    search_targets_path: Path = Field(default=PROFILE_DIR / "search_targets.json")
    checkpoints_db_path: Path = Field(default=DATA_DIR / "checkpoints.sqlite")
    episodic_db_path: Path = Field(default=DATA_DIR / "episodic_memory.sqlite")
    lock_file_path: Path = Field(default=DATA_DIR / "nightly_runner.lock")
    telegram_offset_path: Path = Field(default=DATA_DIR / "telegram_offset.txt")

    # مفاتيح الـ APIs
    groq_api_key: str = Field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    groq_base_url: str = "https://api.groq.com/openai/v1"
    tavily_api_key: str = Field(default_factory=lambda: os.getenv("TAVILY_API_KEY", ""))
    apify_api_token: str = Field(default_factory=lambda: os.getenv("APIFY_API_TOKEN", ""))
    
    # إعدادات تليجرام
    telegram_bot_token: str = Field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    telegram_chat_id: str = Field(default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID", ""))

    # أقوى ثنائي نشط في حساب Groq الخاص بك (أكتوبر 2026)
    # 1. الأقوى على الإطلاق (120B) للتخطيط، الاستدلال، وكتابة الـ Cover Letter
    agentic_llm_model: str = Field(
        default_factory=lambda: os.getenv("GROQ_AGENTIC_MODEL", "openai/gpt-oss-120b")
    )
    # 2. الأحدث والأدق في JSON Schema لتحليل نسب القبول وحماية سقف الـ Rate Limits
    structured_llm_model: str = Field(
        default_factory=lambda: os.getenv("GROQ_STRUCTURED_MODEL", "qwen/qwen3.8-27b")
    )

    # معايير الفلترة الليلية
    min_acceptance_score: int = Field(default_factory=lambda: int(os.getenv("MIN_ACCEPTANCE_SCORE", "80")))
    search_timeframe_hours: int = Field(default_factory=lambda: int(os.getenv("SEARCH_TIMEFRAME_HOURS", "24")))
    max_critic_retries: int = 3
    dry_run: bool = Field(default_factory=lambda: os.getenv("DRY_RUN", "True").lower() == "true")

    def validate_critical_paths(self) -> None:
        """التأكد من وجود ملفات الهوية الأساسية قبل بدء أي دورة تشغيل (Fail-Closed)"""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        
        if not self.cv_markdown_path.exists():
            raise FileNotFoundError(f"❌ [Fail-Closed]: ملف السيرة الذاتية مفقود في المسار: {self.cv_markdown_path}")
        if not self.search_targets_path.exists():
            raise FileNotFoundError(f"❌ [Fail-Closed]: ملف أهداف البحث مفقود في المسار: {self.search_targets_path}")

# نسخة موحدة لاستيرادها في باقي ملفات المشروع
settings = AgentConfig()