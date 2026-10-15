import operator
from typing import Annotated, Dict, List, Literal, Optional, TypedDict
from pydantic import BaseModel, Field

# ==========================================
# 1. قوالب البيانات المهيكلة (Pydantic Schemas)
# ==========================================

class SearchTask(BaseModel):
    """مهمة بحث فرعية يولدها وكيل التخطيط (Planner Node)"""
    task_id: str = Field(description="معرف فريد للمهمة مثل task_1")
    role_cluster: str = Field(description="مجموعة الوظائف المستهدفة")
    target_roles: List[str] = Field(description="المسميات الوظيفية المطلوب البحث عنها في هذه المهمة")
    tier_name: str = Field(description="اسم باقة المنصات المستهدفة (Tier 1 to 4)")
    domains: List[str] = Field(description="النطاقات أو المنصات التي سيتم مسحها")
    status: Literal["pending", "completed", "failed"] = Field(default="pending")

class DiscoveredJob(BaseModel):
    """بيانات الوظيفة المكتشفة بعد اجتياز فلتر الوطن العربي وآخر 24 ساعة"""
    job_fingerprint: str = Field(description="البصمة الفريدة للوظيفة لمنع التكرار")
    title: str = Field(description="المسمى الوظيفي المعلن")
    company: str = Field(description="اسم الشركة أو الجهة المعلنة")
    location: str = Field(description="الدولة أو المدينة داخل الوطن العربي")
    work_mode: str = Field(description="نظام العمل: Remote / Hybrid / On-site")
    url: str = Field(description="الرابط المباشر للوظيفة أو المنشور")
    source_platform: str = Field(description="المنصة التي تم اكتشاف الوظيفة عليها")
    posted_within_24h: bool = Field(default=True, description="تأكيد النشر خلال آخر 24 ساعة")
    raw_description: str = Field(description="النص الكامل لتفاصيل ومتطلبات الوظيفة")

class AcceptanceAnalysis(BaseModel):
    """تقرير وكيل تحليل القبول الواقعي بناءً على السيرة الذاتية المعتمدة"""
    job_fingerprint: str = Field(description="البصمة الفريدة للوظيفة")
    acceptance_score: int = Field(ge=0, le=100, description="نسبة القبول المئوية المتوقعة من 0 إلى 100")
    probability_label: Literal["ممتازة (أولوية قصوى)", "قوية", "متوسطة", "ضعيفة"] = Field(
        description="تصنيف قوة الفرصة"
    )
    matching_strengths: List[str] = Field(
        description="نقاط القوة في سيرة محمد فتحي ومشاريعه المطابقة مباشرة للوظيفة"
    )
    identified_gaps: List[str] = Field(
        description="المتطلبات المذكورة في الإعلان وغير الموجودة صراحة في السيرة الذاتية (إن وجدت)"
    )
    strategic_reasoning: str = Field(
        description="تحليل صريح ومختصر يشرح لماذا هذه الوظيفة مناسبة وما الذي يجب التركيز عليه"
    )

class CoverLetterDraft(BaseModel):
    """مسودة خطاب التقديم المخصص للوظيفة"""
    job_fingerprint: str = Field(description="البصمة الفريدة للوظيفة")
    content: str = Field(description="نص الـ Cover Letter الاحترافي الجاهز للنسخ")
    highlighted_projects: List[str] = Field(
        description="أسماء المشاريع الحقيقية من السيرة الذاتية التي تم الاستشهاد بها في الخطاب"
    )
    revision_number: int = Field(default=1, description="رقم النسخة بعد مراجعة الناقد")

class CritiqueResult(BaseModel):
    """قرار وكيل المراجعة والنقد الذاتي (Critic & Reflection Node)"""
    job_fingerprint: str = Field(description="البصمة الفريدة للوظيفة")
    is_approved: bool = Field(description="هل تم اعتماد التحليل والخطاب للإرسال إلى تليجرام؟")
    quality_score: int = Field(ge=1, le=10, description="تقييم الجودة من 1 إلى 10")
    zero_hallucination_verified: bool = Field(
        description="تأكيد عدم اختراع أي مهارة أو مشروع خارج ملف السيرة الذاتية"
    )
    mena_and_24h_verified: bool = Field(
        description="تأكيد أن الوظيفة داخل الوطن العربي ومنشورة خلال آخر 24 ساعة"
    )
    feedback_for_rewrite: str = Field(
        default="", description="ملاحظات التصحيح الموجهة لكاتب الخطاب في حال الرفض"
    )

# ==========================================
# 2. حالة الجراف اللحظية (Short-Term Graph State)
# ==========================================

class NightlyHuntState(TypedDict):
    """
    الذاكرة قصيرة المدى للجراف (Concept #8: Short-Term State Management)
    تحمل جميع البيانات المتداولة بين الوكلاء أثناء تشغيل دورة الساعة 10:00 مساءً.
    """
    run_id: str
    run_timestamp: str
    
    # بيانات الهوية والقواعد المسحوبة في بداية الليلة
    candidate_cv_text: str
    episodic_avoidance_rules: List[str]
    
    # خطة البحث الليلية وتوجيه المهام
    search_plan: List[SearchTask]
    current_task_index: int
    next_worker: str
    
    # حصيلة الصيد والتحليل والكتابة والمراجعة
    discovered_jobs: List[DiscoveredJob]
    acceptance_analyses: Dict[str, AcceptanceAnalysis]
    cover_letters: Dict[str, CoverLetterDraft]
    critique_results: Dict[str, CritiqueResult]
    
    # إدارة التوقف التفاعلي (Human-in-the-Loop via Telegram)
    approved_job_ids_for_telegram: List[str]
    human_feedback_payload: Optional[Dict[str, str]]
    
    # سجل الأخطاء والتعافي أثناء التشغيل (يتراكم تلقائياً)
    error_logs: Annotated[List[str], operator.add]