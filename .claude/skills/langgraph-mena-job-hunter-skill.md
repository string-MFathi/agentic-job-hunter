---
name: fail-closed-langgraph-multi-agent-blueprint
description: Production blueprint for building fail-closed, multi-agent LangGraph systems with MCP context ingestion, dual SQLite memory (deduplication + episodic learning), dynamic tool routing, tool-level error recovery, self-critique reflection loops, and human-in-the-loop interrupts.
---

# Fail-Closed Multi-Agent LangGraph Skill (Mohamed Fathi Architecture)

Use this architectural blueprint whenever generating or extending a multi-agent AI system in Python.

## 1. Core Architectural Rules (Non-Negotiable)
1. **Fail-Closed Startup (`src/config.py` + `fcntl.flock`):**
   - Validate all critical file paths and environment configurations at startup before any LLM call.
   - Enforce an OS-level atomic process lock (`fcntl.flock`) in the runner script so concurrent cron jobs never collide.
2. **Model-Agnostic OpenAI-Compatible Factory (`src/agents/llm_factory.py`):**
   - Route reasoning/planning/writing nodes to an agentic model (`moonshotai/kimi-k2-instruct-0905` via Groq).
   - Route strict schema extraction/scoring nodes to a schema-strict model (`meta-llama/llama-4-maverick-17b-128e-instruct` via Groq).
   - Always maintain a deterministic local fallback when running in `DRY_RUN` or offline test environments.
3. **Ground-Truth Context via MCP (`src/mcp_server/`):**
   - Never hardcode domain profiles or target lists inside prompts. Expose them via a dedicated `MCPServer` + `MCPClient` layer.
4. **Dual SQLite Memory (`src/memory/`):**
   - **Short-Term State:** Strictly typed `TypedDict` + `Pydantic` models in `src/state/agent_state.py`.
   - **Long-Term Deduplication (`seen_jobs`):** Compute deterministic `SHA-256` fingerprints over normalized entities before LLM processing.
   - **Episodic Learning (`episodic_lessons`):** Store human rejection reasons and inject them into the Planner and Scout nodes on subsequent runs.
5. **Dynamic Tool Routing & Self-Healing Tools (`src/tools/`):**
   - Wrap every external tool with `@safe_tool_execution` (using `tenacity` retries + structured JSON error payload on failure).
   - Provide each worker only its tier-specific primary tool + 1 backup failover tool via `DynamicToolRouter`.
6. **Reflection & Zero-Hallucination Critic (`src/agents/critic.py`):**
   - Every generated artifact must pass a deterministic + LLM Critic check verifying: (a) zero hallucinated claims outside the MCP ground truth, (b) zero banned clichés, and (c) concrete portfolio citations.
   - Route rejected drafts back to the writer node automatically up to `max_critic_retries`.
7. **Human-in-the-Loop Checkpointer (`SqliteSaver` + `interrupt_before`):**
   - Compile `StateGraph` with `SqliteSaver` (using `JsonPlusSerializer` with registered Pydantic models) and pause execution via `interrupt_before=["feedback_resume_node"]` until human approval/rejection arrives from Telegram.