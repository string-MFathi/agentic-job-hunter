import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from src.config import settings

ALLOWED_STATE_MODULES = [
    ("src.state.agent_state", "SearchTask"),
    ("src.state.agent_state", "DiscoveredJob"),
    ("src.state.agent_state", "AcceptanceAnalysis"),
    ("src.state.agent_state", "CoverLetterDraft"),
    ("src.state.agent_state", "CritiqueResult"),
]

def get_sqlite_checkpointer() -> SqliteSaver:
    """
    إنشاء وتجهيز حافظة حالة الجراف (Concept #5: LangGraph Checkpointer & Interrupts)
    مع التصريح المسبق بقوالب Pydantic لمنع أي تحذيرات أثناء استرجاع الحالة.
    """
    settings.validate_critical_paths()
    db_path = str(settings.checkpoints_db_path)

    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")

    serde = JsonPlusSerializer(allowed_msgpack_modules=ALLOWED_STATE_MODULES)
    checkpointer = SqliteSaver(conn, serde=serde)
    checkpointer.setup()
    return checkpointer