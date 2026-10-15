from typing import Literal
from langgraph.graph import StateGraph, START, END
from src.state.agent_state import NightlyHuntState
from src.memory.checkpointer import get_sqlite_checkpointer
from src.agents.planner import planner_node
from src.agents.supervisor import supervisor_node
from src.agents.mena_scout_react import mena_scout_react_node
from src.agents.acceptance_analyst import acceptance_analyst_node
from src.agents.cover_letter_writer import cover_letter_writer_node
from src.agents.critic import critic_node
from src.delivery.telegram_bot import telegram_delivery_node, feedback_resume_node

def route_from_supervisor(
    state: NightlyHuntState
) -> Literal[
    "mena_scout_worker",
    "acceptance_analyst_worker",
    "cover_letter_writer_worker",
    "critic_node",
    "telegram_delivery"
]:
    """توجيه المسار الشرطي بناءً على قرار المايسترو (Supervisor Node)"""
    next_step = state.get("next_worker", "telegram_delivery")
    valid_routes = {
        "mena_scout_worker",
        "acceptance_analyst_worker",
        "cover_letter_writer_worker",
        "critic_node",
        "telegram_delivery",
    }
    if next_step in valid_routes:
        return next_step  # type: ignore[return-value]
    return "telegram_delivery"

def build_job_hunter_graph(enable_interrupt: bool = True):
    """
    بناء وتجميع جراف صيد الوظائف الليلي (Step 5.1 & Concept #5)
    يربط جميع الوكلاء مع حافظة SQLite ونقطة التوقف التفاعلية (interrupt_before).
    """
    workflow = StateGraph(NightlyHuntState)

    # 1. إضافة جميع العقد (Nodes) إلى الجراف
    workflow.add_node("planner", planner_node)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("mena_scout_worker", mena_scout_react_node)
    workflow.add_node("acceptance_analyst_worker", acceptance_analyst_node)
    workflow.add_node("cover_letter_writer_worker", cover_letter_writer_node)
    workflow.add_node("critic_node", critic_node)
    workflow.add_node("telegram_delivery", telegram_delivery_node)
    workflow.add_node("feedback_resume_node", feedback_resume_node)

    # 2. ربط نقطة البداية بوكيل التخطيط ثم المايسترو
    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "supervisor")

    # 3. المسارات الشرطية الخارجة من المايسترو (Supervisor-Worker Routing)
    workflow.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "mena_scout_worker": "mena_scout_worker",
            "acceptance_analyst_worker": "acceptance_analyst_worker",
            "cover_letter_writer_worker": "cover_letter_writer_worker",
            "critic_node": "critic_node",
            "telegram_delivery": "telegram_delivery",
        }
    )

    # 4. عودة جميع الوكلاء المتخصصين إلى المايسترو بعد كل خطوة
    workflow.add_edge("mena_scout_worker", "supervisor")
    workflow.add_edge("acceptance_analyst_worker", "supervisor")
    workflow.add_edge("cover_letter_writer_worker", "supervisor")
    workflow.add_edge("critic_node", "supervisor")

    # 5. بعد إرسال البطاقات لتليجرام، ينتقل الجراف إلى عقدة استئناف القرار ثم النهاية
    workflow.add_edge("telegram_delivery", "feedback_resume_node")
    workflow.add_edge("feedback_resume_node", END)

    # 6. ربط حافظة SQLite ونقطة التوقف التفاعلية (Concept #5)
    checkpointer = get_sqlite_checkpointer()
    interrupt_nodes = ["feedback_resume_node"] if enable_interrupt else []

    compiled_graph = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=interrupt_nodes
    )
    return compiled_graph