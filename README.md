# 🎯 Autonomous MENA Job Hunter Agent (Fail-Closed LangGraph System)

An autonomous, production-grade multi-agent system engineered by **Mohamed Fathi** to scout, qualify, analyze acceptance probability, and draft zero-hallucination technical cover letters across **20 Arab World (MENA) job platforms and social hiring feeds** (published within the last 24 hours).

## 🏗️ Architectural Highlights (11 Advanced Agentic Patterns)
1. **ReAct Scout Loop (`mena_scout_react.py`):** Interleaves reasoning, tool execution, and automatic failover across 4 MENA search tiers.
2. **Plan-and-Execute (`planner.py`):** Decomposes 12 target AI/Product/Automation roles and 20 MENA platforms into a structured nightly task graph.
3. **Reflection & Self-Critique (`critic.py`):** Enforces zero-hallucination verification against the candidate's CV and rejects generic clichés before delivery.
4. **Supervisor-Worker Orchestration (`supervisor.py`):** Deterministic hub-and-spoke routing across specialized workers.
5. **Human-in-the-Loop Interrupts (`workflow.py` + `checkpointer.py`):** Freezes graph execution via `SqliteSaver` (`interrupt_before`) after sending interactive Telegram cards (`✅ Apply` / `❌ Reject`).
6. **Dynamic Tool Routing (`tool_router.py`):** Binds only tier-relevant tools + 1 failover backup tool per task to minimize token overhead.
7. **Tool-Level Error Recovery (`error_wrapper.py`):** `Tenacity` exponential backoff + structured JSON error return for autonomous agent self-healing.
8. **Short-Term Graph State (`agent_state.py`):** Strictly typed `NightlyHuntState` and `Pydantic` schemas.
9. **Long-Term Deduplication & Episodic Memory (`memory_store.py`):** SQLite WAL database tracking SHA-256 job fingerprints and learning avoidance rules from Telegram rejections.
10. **Model Context Protocol (`mcp_server/`):** Decouples candidate CV ground truth and search targets from agent logic.
11. **Reusable Agent Skill (`.claude/skills/`):** Packaged architectural blueprint for rapid multi-agent scaffolding.

## 🚀 Quick Start
```bash
source venv/bin/activate
pytest -v
python nightly_runner.py --mode hunt