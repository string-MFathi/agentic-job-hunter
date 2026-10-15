import functools
import json
import logging
from typing import Any, Callable
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx

logger = logging.getLogger(__name__)

def safe_tool_execution(fallback_suggestion: str = "Switch to an alternative search tool or broaden query keywords."):
    """
    غلاف حماية الأدوات (Concept #7: Tool-Level Error Recovery)
    1. يعيد المحاولة تلقائياً (Exponential Backoff) عند أخطاء الاتصال المؤقتة.
    2. يمنع انهيار الجراف (Fail-Safe) ويُرجع للـ LLM رسالة خطأ مهيكلة ليقوم بتصحيح مساره ذاتياً.
    """
    def decorator(func: Callable) -> Callable:
        
        # إعادة المحاولة مرتين في حال حدوث خطأ شبكة عابر قبل إعلان فشل الأداة
        @retry(
            stop=stop_after_attempt(2),
            wait=wait_exponential(multiplier=1, min=1, max=4),
            retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException, ConnectionError)),
            reraise=True
        )
        def _execute_with_retry(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> str:
            try:
                return _execute_with_retry(*args, **kwargs)
            except Exception as exc:
                error_payload = {
                    "status": "tool_error",
                    "failed_tool": func.__name__,
                    "error_type": type(exc).__name__,
                    "error_details": str(exc),
                    "agent_recovery_instruction": (
                        f"TOOL FAILURE DETECTED in '{func.__name__}'. Do NOT halt execution. "
                        f"Action Required: {fallback_suggestion}"
                    )
                }
                logger.warning(f"⚠️ [Tool Recovery Triggered] {func.__name__}: {exc}")
                return json.dumps(error_payload, ensure_ascii=False)

        return wrapper
    return decorator