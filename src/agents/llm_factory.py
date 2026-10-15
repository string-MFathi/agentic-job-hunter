from langchain_openai import ChatOpenAI
from src.config import settings

def has_valid_groq_key() -> bool:
    """التحقق من وجود مفتاح Groq API فعلي داخل ملف .env"""
    key = settings.groq_api_key.strip()
    return bool(key) and key.startswith("gsk_") and "your_groq_key" not in key

def get_agentic_llm(temperature: float = 0.1) -> ChatOpenAI:
    """
    استدعاء موديل Kimi K2 (moonshotai/kimi-k2-instruct-0905)
    مخصص لمهام التخطيط، حلقات ReAct، صياغة الـ Cover Letter، والنقد الذاتي.
    """
    return ChatOpenAI(
        model=settings.agentic_llm_model,
        base_url=settings.groq_base_url,
        api_key=settings.groq_api_key or "gsk_placeholder",
        temperature=temperature,
        max_retries=2,
    )

def get_structured_llm(temperature: float = 0.0) -> ChatOpenAI:
    """
    استدعاء موديل Llama 4 Maverick (meta-llama/llama-4-maverick-17b-128e-instruct)
    مخصص للمخرجات المهيكلة الصارمة (JSON Schema) وتحليل نسب القبول.
    """
    return ChatOpenAI(
        model=settings.structured_llm_model,
        base_url=settings.groq_base_url,
        api_key=settings.groq_api_key or "gsk_placeholder",
        temperature=temperature,
        max_retries=2,
    )