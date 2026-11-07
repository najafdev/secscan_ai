"""
HackBot Desktop GUI
====================
Native desktop application powered by pywebview + Flask.
Runs as a real desktop window (not in a browser) on Linux, Windows, and macOS.
Falls back to browser mode if pywebview is not available.
"""

from __future__ import annotations

import json
import logging
import os
import queue
import threading
import time
import webbrowser
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Flask, Response, jsonify, render_template, request, stream_with_context

from hackbot import __version__
from hackbot.config import HackBotConfig, detect_platform, detect_tools, save_config
from hackbot.core.engine import AIEngine, PROVIDERS, SUPPORTED_LANGUAGES
from hackbot.core.cve import CVELookup
from hackbot.core.compliance import ComplianceMapper
from hackbot.core.osint import OSINTEngine
from hackbot.core.topology import TopologyParser
from hackbot.core.pdf_report import PDFReportGenerator, HAS_REPORTLAB
from hackbot.core.diff_report import DiffEngine, list_agent_sessions, load_session_findings
from hackbot.core.plugins import get_plugin_manager, reset_plugin_manager, PLUGINS_DIR
from hackbot.core.campaigns import get_campaign_manager
from hackbot.core.remediation import RemediationEngine
from hackbot.core.proxy import ProxyEngine, get_proxy_engine
from hackbot.core.updater import check_for_updates, perform_update
from hackbot.core.vulndb import VulnDB
from hackbot.memory import MemoryManager
from hackbot.modes.agent import AgentMode
from hackbot.modes.chat import ChatMode
from hackbot.modes.plan import PlanMode
from hackbot.reporting import ReportGenerator

logger = logging.getLogger(__name__)

# ── Flask App ────────────────────────────────────────────────────────────────

TEMPLATE_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"
LOGO_PATH = STATIC_DIR / "logo.png"
PUBLIC_DIR = Path(__file__).parent.parent.parent / "public"

app = Flask(
    __name__,
    template_folder=str(TEMPLATE_DIR),
    static_folder=str(STATIC_DIR),
)
app.secret_key = os.urandom(32)

# Global state (per-process; fine for single-user desktop app)
_state: Dict[str, Any] = {
    "config": None,
    "engine": None,
    "chat": None,
    "agent": None,
    "plan": None,
    "mode": "chat",
}


def _init_state(config: HackBotConfig) -> None:
    """Initialize the global application state."""
    _state["config"] = config
    _state["engine"] = AIEngine(config.ai)
    _state["chat"] = ChatMode(_state["engine"], config)
    _state["plan"] = PlanMode(_state["engine"], config)
    _state["agent"] = None
    _state["mode"] = "chat"


# ── Routes: Pages ────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Main GUI page."""
    return render_template("index.html", version=__version__)


# ── Routes: API ──────────────────────────────────────────────────────────────

@app.route("/api/status")
def api_status():
    """Get current application status."""
    config: HackBotConfig = _state["config"]
    engine: AIEngine = _state["engine"]
    return jsonify({
        "version": __version__,
        "mode": _state["mode"],
        "configured": engine.is_configured(),
        "provider": config.ai.provider,
        "model": config.ai.model,
        "safe_mode": config.agent.safe_mode,
        "platform": detect_platform(),
        "agent_active": _state["agent"] is not None and _state["agent"].is_running,
    })


@app.route("/api/providers")
def api_providers():
    """Return all provider definitions and their models."""
    return jsonify(PROVIDERS)


@app.route("/api/update/check")
def api_update_check():
    """Check for available updates."""
    info = check_for_updates()
    return jsonify({
        "current_version": info.current_version,
        "latest_version": info.latest_version,
        "update_available": info.update_available,
        "release_url": info.release_url,
        "release_notes": info.release_notes,
        "published_at": info.published_at,
        "error": info.error,
    })


@app.route("/api/update/install", methods=["POST"])
def api_update_install():
    """Perform self-update from GitHub."""
    data = request.json or {}
    force = data.get("force", False)
    result = perform_update(force=force)
    return jsonify(result)


@app.route("/api/tools")
def api_tools():
    """List available security tools."""
    config: HackBotConfig = _state["config"]
    tools = detect_tools(config.agent.allowed_tools)
    installed = {k: v for k, v in tools.items() if v}
    missing = {k: v for k, v in tools.items() if not v}
    return jsonify({
        "installed": installed,
        "missing": list(missing.keys()),
        "total": len(tools),
        "available": len(installed),
    })


@app.route("/api/config", methods=["GET", "POST"])
def api_config():
    """Get or update configuration."""
    config: HackBotConfig = _state["config"]

    if request.method == "POST":
        data = request.json or {}
        if "api_key" in data:
            config.ai.api_key = data["api_key"]
        if "model" in data:
            config.ai.model = data["model"]
        if "provider" in data:
            config.ai.provider = data["provider"]
        if "base_url" in data:
            config.ai.base_url = data["base_url"]
        if "temperature" in data:
            config.ai.temperature = float(data["temperature"])
        if "max_tokens" in data:
            config.ai.max_tokens = int(data["max_tokens"])
        if "safe_mode" in data:
            config.agent.safe_mode = data["safe_mode"]
        if "auto_confirm" in data:
            config.agent.auto_confirm = data["auto_confirm"]
        if "sudo_mode" in data:
            config.agent.sudo_mode = data["sudo_mode"]
        if "sudo_password" in data:
            config.agent.sudo_password = data["sudo_password"]
            if data["sudo_password"]:
                config.agent.sudo_mode = True
        if "nvd_api_key" in data:
            config.agent.nvd_api_key = data["nvd_api_key"]
        if "report_format" in data:
            config.reporting.format = data["report_format"]
        if "language" in data:
            config.ui.language = data["language"]

        # Reinitialize engine
        _state["engine"] = AIEngine(config.ai)
        _state["chat"] = ChatMode(_state["engine"], config)
        _state["plan"] = PlanMode(_state["engine"], config)
        # Reset agent so it picks up the new engine on next start
        if _state.get("agent"):
            _state["agent"] = None
        save_config(config)

        # Validate API key if one was provided or already exists
        validation = None
        if config.ai.api_key:
            validation = _state["engine"].validate_api_key()

        return jsonify({"ok": True, "validation": validation})

    return jsonify({
        "provider": config.ai.provider,
        "model": config.ai.model,
        "has_key": bool(config.ai.api_key),
        "base_url": config.ai.base_url,
        "temperature": config.ai.temperature,
        "max_tokens": config.ai.max_tokens,
        "safe_mode": config.agent.safe_mode,
        "auto_confirm": config.agent.auto_confirm,
        "sudo_mode": config.agent.sudo_mode,
        "has_sudo_password": bool(config.agent.sudo_password),
        "has_nvd_api_key": bool(config.agent.nvd_api_key),
        "max_steps": config.agent.max_steps,
        "timeout": config.agent.timeout,
        "report_format": config.reporting.format,
        "language": config.ui.language,
        "supported_languages": SUPPORTED_LANGUAGES,
    })


@app.route("/api/validate-key", methods=["POST"])
def api_validate_key():
    """Validate the current API key by making a test request."""
    engine: Optional[AIEngine] = _state.get("engine")
    if not engine:
        return jsonify({"valid": False, "message": "No engine configured"})
    result = engine.validate_api_key()
    return jsonify(result)


@app.route("/api/mode", methods=["POST"])
def api_set_mode():
    """Switch active mode."""
    data = request.json or {}
    mode = data.get("mode", "chat")
    if mode in ("chat", "agent", "plan"):
        _state["mode"] = mode
    return jsonify({"mode": _state["mode"]})


# ── Routes: Chat ─────────────────────────────────────────────────────────────

@app.route("/api/chat", methods=["POST"])
def api_chat():
    """Send a chat message and get streaming response via SSE."""
    data = request.json or {}
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "Empty message"}), 400

    engine: AIEngine = _state["engine"]
    if not engine.is_configured():
        return jsonify({"error": "API key not configured. Go to Settings to set it."}), 400

    chat_mode: ChatMode = _state["chat"]

    def generate():
        token_queue: queue.Queue = queue.Queue()
        result_holder: List[Optional[str]] = [None]

        def on_token(token):
            token_queue.put(token)

        def run_chat():
            try:
                resp = chat_mode.ask(message, stream=True, on_token=on_token)
                result_holder[0] = resp
            except Exception as e:
                token_queue.put(f"\n\n**Error:** {str(e)}")
            finally:
                token_queue.put(None)  # sentinel

        t = threading.Thread(target=run_chat, daemon=True)
        t.start()

        while True:
            token = token_queue.get()
            if token is None:
                yield f"data: [DONE]\n\n"
                break
            yield f"data: {json.dumps({'token': token})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/chat/clear", methods=["POST"])
def api_chat_clear():
    """Clear chat history."""
    _state["chat"] = ChatMode(_state["engine"], _state["config"])
    return jsonify({"ok": True})


@app.route("/api/chat/continue", methods=["POST"])
def api_chat_continue():
    """Continue a chat response that was cut off."""
    engine: AIEngine = _state["engine"]
    if not engine.is_configured():
        return jsonify({"error": "API key not configured"}), 400

    chat_mode: ChatMode = _state["chat"]

    def generate():
        token_queue: queue.Queue = queue.Queue()

        def on_token(token):
            token_queue.put(token)

        def run_continue():
            try:
                chat_mode.continue_response(stream=True, on_token=on_token)
            except Exception as e:
                token_queue.put(f"\n\n**Error:** {str(e)}")
            finally:
                token_queue.put(None)

        t = threading.Thread(target=run_continue, daemon=True)
        t.start()

        while True:
            token = token_queue.get()
            if token is None:
                yield f"data: [DONE]\n\n"
                break
            yield f"data: {json.dumps({'token': token})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/chat/truncated")
def api_chat_truncated():
    """Check if the last chat response was truncated."""
    chat_mode: ChatMode = _state["chat"]
    return jsonify({"truncated": chat_mode.was_truncated})


# ── Routes: Sessions ─────────────────────────────────────────────────────────

@app.route("/api/sessions")
def api_sessions():
    """List all saved sessions."""
    mode = request.args.get("mode", None)
    memory = MemoryManager()
    sessions = memory.list_sessions(mode=mode)
    return jsonify([s.to_dict() for s in sessions])


@app.route("/api/sessions/<session_id>")
def api_session_load(session_id):
    """Load a specific session."""
    memory = MemoryManager()
    data = memory.load_session(session_id)
    if data:
        return jsonify(data)
    return jsonify({"error": "Session not found"}), 404


@app.route("/api/sessions/<session_id>", methods=["DELETE"])
def api_session_delete(session_id):
    """Delete a session."""
    memory = MemoryManager()
    if memory.delete_session(session_id):
        return jsonify({"ok": True})
    return jsonify({"error": "Session not found"}), 404


@app.route("/api/sessions/restore/<session_id>", methods=["POST"])
def api_session_restore(session_id):
    """Restore a saved session into the active chat."""
    chat_mode: ChatMode = _state["chat"]
    success = chat_mode.load_session(session_id)
    if success:
        return jsonify({"ok": True, "message_count": len([
            m for m in chat_mode.conversation.messages if m.role != "system"
        ])})
    return jsonify({"error": "Session not found"}), 404


@app.route("/api/agent/replay/<session_id>", methods=["GET"])
def api_agent_replay(session_id):
    """Fetch the execution logs for a session."""
    from hackbot.config import REPORTS_DIR
    import json
    path = REPORTS_DIR / f"session_{session_id}" / "execution_log.json"
    if not path.exists():
        return jsonify({"error": "Replay data not found"}), 404
    try:
        with open(path) as f:
            steps = json.load(f)
        return jsonify({"steps": steps})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Routes: Agent ────────────────────────────────────────────────────────────

@app.route("/api/agent/start", methods=["POST"])
def api_agent_start():
    """Start an autonomous security assessment."""
    data = request.json or {}
    target = data.get("target", "").strip()
    scope = data.get("scope", "")
    instructions = data.get("instructions", "")

    if not target:
        return jsonify({"error": "Target is required"}), 400

    engine: AIEngine = _state["engine"]
    if not engine.is_configured():
        return jsonify({"error": "API key not configured"}), 400

    config: HackBotConfig = _state["config"]

    # Create fresh agent
    agent = AgentMode(
        engine=engine,
        config=config,
        on_confirm=lambda cmd, reason: config.agent.auto_confirm,
    )
    _state["agent"] = agent
    _state["mode"] = "agent"

    def generate():
        token_queue: queue.Queue = queue.Queue()

        def on_token(token):
            token_queue.put(("token", token))

        def on_step(step):
            token_queue.put(("step", step.to_dict()))

        agent.on_token = on_token
        agent.on_step = on_step

        def run_agent():
            try:
                agent.start(target, scope=scope, instructions=instructions)
            except Exception as e:
                token_queue.put(("token", f"\n\n**Error:** {str(e)}"))
            finally:
                token_queue.put(("done", None))

        t = threading.Thread(target=run_agent, daemon=True)
        t.start()

        while True:
            kind, value = token_queue.get()
            if kind == "done":
                yield f"data: [DONE]\n\n"
                break
            elif kind == "step":
                yield f"data: {json.dumps({'step': value})}\n\n"
            else:
                yield f"data: {json.dumps({'token': value})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/agent/step", methods=["POST"])
def api_agent_step():
    """Execute next agent step."""
    agent: Optional[AgentMode] = _state["agent"]
    if not agent or not agent.is_running:
        return jsonify({"error": "No active assessment"}), 400

    data = request.json or {}
    user_input = data.get("message", "")

    def generate():
        assert agent is not None
        token_queue: queue.Queue = queue.Queue()

        def on_token(token):
            token_queue.put(("token", token))

        def on_step(step):
            token_queue.put(("step", step.to_dict()))

        agent.on_token = on_token
        agent.on_step = on_step

        def run_step():
            assert agent is not None
            try:
                response, is_complete = agent.step(user_input)
                token_queue.put(("meta", {"complete": is_complete}))
            except Exception as e:
                token_queue.put(("token", f"\n\n**Error:** {str(e)}"))
            finally:
                token_queue.put(("done", None))

        t = threading.Thread(target=run_step, daemon=True)
        t.start()

        while True:
            kind, value = token_queue.get()
            if kind == "done":
                yield f"data: [DONE]\n\n"
                break
            elif kind == "meta":
                yield f"data: {json.dumps(value)}\n\n"
            elif kind == "step":
                yield f"data: {json.dumps({'step': value})}\n\n"
            else:
                yield f"data: {json.dumps({'token': value})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/agent/run", methods=["POST"])
def api_agent_run_command():
    """Execute a manual command through the agent."""
    data = request.json or {}
    command = data.get("command", "").strip()
    if not command:
        return jsonify({"error": "No command provided"}), 400

    config: HackBotConfig = _state["config"]
    agent: Optional[AgentMode] = _state["agent"]

    if not agent:
        agent = AgentMode(
            engine=_state["engine"],
            config=config,
            on_confirm=lambda cmd, reason: config.agent.auto_confirm,
        )
        _state["agent"] = agent

    result = agent.run_command(command)
    return jsonify({
        "tool": result.tool,
        "command": result.command,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "return_code": result.return_code,
        "duration": round(result.duration, 2),
        "success": result.success,
    })


@app.route("/api/agent/continue", methods=["POST"])
def api_agent_continue():
    """Continue an agent response that was cut off."""
    agent: Optional[AgentMode] = _state["agent"]
    if not agent:
        return jsonify({"error": "No active assessment"}), 400

    def generate():
        token_queue: queue.Queue = queue.Queue()

        def on_token(token):
            token_queue.put(("token", token))

        def run_continue():
            try:
                response, is_complete = agent.continue_response(on_token=on_token)
                token_queue.put(("meta", {"complete": is_complete}))
            except Exception as e:
                token_queue.put(("token", f"\n\n**Error:** {str(e)}"))
            finally:
                token_queue.put(("done", None))

        t = threading.Thread(target=run_continue, daemon=True)
        t.start()

        while True:
            kind, value = token_queue.get()
            if kind == "done":
                yield f"data: [DONE]\n\n"
                break
            elif kind == "meta":
                yield f"data: {json.dumps(value)}\n\n"
            else:
                yield f"data: {json.dumps({'token': value})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/agent/truncated")
def api_agent_truncated():
    """Check if the last agent response was truncated."""
    agent: Optional[AgentMode] = _state["agent"]
    if not agent:
        return jsonify({"truncated": False})
    return jsonify({"truncated": agent.was_truncated})


@app.route("/api/agent/findings")
def api_agent_findings():
    """Get current assessment findings."""
    agent: Optional[AgentMode] = _state["agent"]
    if not agent:
        return jsonify({"findings": [], "summary": ""})

    return jsonify({
        "findings": [f.to_dict() for f in agent.findings],
        "scripts": [s.to_dict() for s in agent.scripts],
        "summary": agent.get_findings_summary(),
        "steps": len(agent.steps),
        "target": agent.target,
        "is_running": agent.is_running,
    })


@app.route("/api/agent/scripts")
def api_agent_scripts():
    """Get generated scripts for the current assessment."""
    agent: Optional[AgentMode] = _state["agent"]
    if not agent:
        return jsonify({"scripts": [], "target": "", "count": 0})

    return jsonify({
        "scripts": [s.to_dict() for s in agent.scripts],
        "target": agent.target,
        "count": len(agent.scripts),
    })


@app.route("/api/agent/stop", methods=["POST"])
def api_agent_stop():
    """Stop the current assessment."""
    agent: Optional[AgentMode] = _state["agent"]
    if agent and agent.is_running:
        summary = agent.stop()
        return jsonify({"ok": True, "summary": summary})
    return jsonify({"ok": False, "error": "No active assessment"})


@app.route("/api/agent/remediate", methods=["POST"])
def api_agent_remediate():
    """Generate remediation guidance for findings."""
    agent: Optional[AgentMode] = _state["agent"]
    if not agent:
        return jsonify({"ok": False, "error": "No active assessment"})
    findings = [f.to_dict() for f in agent.findings]
    if not findings:
        return jsonify({"ok": False, "error": "No findings to remediate"})

    body = request.get_json(silent=True) or {}
    use_ai = body.get("use_ai", False)
    finding_idx = body.get("index")  # optional: single finding

    engine_inst = _state.get("engine")
    remed = RemediationEngine(ai_engine=engine_inst if use_ai else None)

    if finding_idx is not None:
        idx = int(finding_idx)
        if 0 <= idx < len(findings):
            r = remed.remediate_finding(findings[idx], use_ai=use_ai)
            return jsonify({
                "ok": True,
                "remediations": [r.to_dict()],
                "markdown": r.get_markdown(),
            })
        return jsonify({"ok": False, "error": f"Finding index {idx} out of range"})

    results = remed.remediate_findings(findings, use_ai=use_ai)
    return jsonify({
        "ok": True,
        "remediations": [r.to_dict() for r in results],
        "markdown": RemediationEngine.get_summary_markdown(results),
        "count": len(results),
        "total_steps": sum(len(r.steps) for r in results),
    })


# ── Vulnerability Database ───────────────────────────────────────────────────


@app.route("/api/vulndb/stats")
def api_vulndb_stats():
    """Get vulnerability database statistics."""
    target = request.args.get("target", "")
    db = VulnDB()
    stats = db.get_stats(target)
    return jsonify({
        "total_assessments": stats.total_assessments,
        "total_findings": stats.total_findings,
        "open_findings": stats.open_findings,
        "resolved_findings": stats.resolved_findings,
        "in_progress_findings": stats.in_progress_findings,
        "false_positive_findings": stats.false_positive_findings,
        "accepted_findings": stats.accepted_findings,
        "by_severity": stats.by_severity,
        "by_target": stats.by_target,
        "overall_risk_score": stats.overall_risk_score,
        "unique_targets": stats.unique_targets,
        "avg_findings_per_assessment": stats.avg_findings_per_assessment,
        "oldest_open_finding_days": stats.oldest_open_finding_days,
        "last_assessment_at": stats.last_assessment_at,
        "db_size": db.db_size,
    })


@app.route("/api/vulndb/findings")
def api_vulndb_findings():
    """Search/query findings from the vulnerability database."""
    db = VulnDB()
    results = db.search_findings(
        query=request.args.get("q", ""),
        target=request.args.get("target", ""),
        severity=request.args.get("severity", ""),
        status=request.args.get("status", ""),
        limit=int(request.args.get("limit", "100")),
        offset=int(request.args.get("offset", "0")),
    )
    return jsonify({
        "findings": [f.to_dict() for f in results],
        "count": len(results),
    })


@app.route("/api/vulndb/findings/<int:finding_id>")
def api_vulndb_finding_detail(finding_id: int):
    """Get a single finding with remediation log."""
    db = VulnDB()
    finding = db.get_finding(finding_id)
    if not finding:
        return jsonify({"ok": False, "error": "Finding not found"}), 404
    return jsonify({
        "ok": True,
        "finding": finding.to_dict(),
        "remediation_log": db.get_remediation_log(finding_id),
    })


@app.route("/api/vulndb/findings/<int:finding_id>/status", methods=["POST"])
def api_vulndb_update_status(finding_id: int):
    """Update the status of a finding."""
    body = request.get_json(silent=True) or {}
    new_status = body.get("status", "")
    note = body.get("note", "")
    db = VulnDB()
    try:
        ok = db.update_status(finding_id, new_status, note=note, changed_by="gui")
        if ok:
            return jsonify({"ok": True})
        return jsonify({"ok": False, "error": "Finding not found"}), 404
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.route("/api/vulndb/assessments")
def api_vulndb_assessments():
    """List assessments."""
    db = VulnDB()
    target = request.args.get("target", "")
    assessments = db.list_assessments(target=target)
    return jsonify({
        "assessments": [
            {
                "id": a.id,
                "target": a.target,
                "scope": a.scope,
                "started_at": a.started_at,
                "finished_at": a.finished_at,
                "total_steps": a.total_steps,
                "total_findings": a.total_findings,
                "tools_used": a.tools_used,
                "notes": a.notes,
            }
            for a in assessments
        ],
        "count": len(assessments),
    })


@app.route("/api/vulndb/risk")
def api_vulndb_risk():
    """Get risk score and history for a target."""
    db = VulnDB()
    target = request.args.get("target", "")
    return jsonify({
        "risk_score": db.calculate_risk_score(target),
        "history": db.get_risk_history(target) if target else [],
    })


# ── RAG Memory ───────────────────────────────────────────────────────────────


@app.route("/api/memory/stats")
def api_memory_stats():
    """Get RAG memory statistics."""
    from hackbot.core.rag_memory import get_rag_memory
    rag = get_rag_memory()
    if not rag.is_available():
        return jsonify({"available": False, "error": "ChromaDB not installed"})
    return jsonify(rag.stats())


@app.route("/api/memory/search", methods=["POST"])
def api_memory_search():
    """Search RAG memory for relevant past context."""
    from hackbot.core.rag_memory import get_rag_memory
    rag = get_rag_memory()
    if not rag.is_available():
        return jsonify({"error": "ChromaDB not installed"}), 400

    body = request.get_json(silent=True) or {}
    query = body.get("query", "").strip()
    if not query:
        return jsonify({"error": "Query is required"}), 400

    n_results = int(body.get("n_results", 10))
    doc_type = body.get("doc_type")

    results = rag.query(query, n_results=n_results, doc_type=doc_type)
    return jsonify({
        "results": [r.to_dict() for r in results],
        "count": len(results),
        "query": query,
    })


@app.route("/api/memory/clear", methods=["POST"])
def api_memory_clear():
    """Clear RAG memory (optionally filtered by doc_type)."""
    from hackbot.core.rag_memory import get_rag_memory
    rag = get_rag_memory()
    if not rag.is_available():
        return jsonify({"error": "ChromaDB not installed"}), 400

    body = request.get_json(silent=True) or {}
    doc_type = body.get("doc_type")

    count = rag.clear(doc_type=doc_type)
    return jsonify({"ok": True, "cleared": count})


@app.route("/api/memory/context", methods=["POST"])
def api_memory_context():
    """Get formatted RAG context for a query (same as what gets injected into prompts)."""
    from hackbot.core.rag_memory import get_rag_memory
    rag = get_rag_memory()
    if not rag.is_available():
        return jsonify({"error": "ChromaDB not installed"}), 400

    body = request.get_json(silent=True) or {}
    query = body.get("query", "").strip()
    if not query:
        return jsonify({"error": "Query is required"}), 400

    config: HackBotConfig = _state["config"]
    context = rag.get_context(
        query,
        max_results=config.rag.max_results,
        max_chars=config.rag.max_context_tokens * 4,
    )
    return jsonify({"context": context, "query": query})


@app.route("/api/memory/import", methods=["POST"])
def api_memory_import():
    """Import existing JSON sessions into RAG memory."""
    from hackbot.core.rag_memory import get_rag_memory
    rag = get_rag_memory()
    if not rag.is_available():
        return jsonify({"error": "ChromaDB not installed"}), 400

    memory = MemoryManager()
    sessions = memory.list_sessions()
    if not sessions:
        return jsonify({"ok": True, "imported": 0, "chunks": 0})

    total_chunks = 0
    for s in sessions:
        data = memory.load_session(s.id)
        if data:
            total_chunks += rag.import_session(data)

    return jsonify({
        "ok": True,
        "imported": len(sessions),
        "chunks": total_chunks,
    })


# ── Proxy / Traffic Capture ─────────────────────────────────────────────────


@app.route("/api/proxy/start", methods=["POST"])
def api_proxy_start():
    """Start the interception proxy."""
    body = request.get_json(silent=True) or {}
    port = int(body.get("port", 8080))
    proxy = get_proxy_engine()
    result = proxy.start(port=port)
    return jsonify(result)


@app.route("/api/proxy/stop", methods=["POST"])
def api_proxy_stop():
    """Stop the interception proxy."""
    proxy = get_proxy_engine()
    result = proxy.stop()
    return jsonify(result)


@app.route("/api/proxy/status", methods=["GET"])
def api_proxy_status():
    """Get proxy status and statistics."""
    proxy = get_proxy_engine()
    stats = proxy.get_stats()
    stats["is_running"] = proxy.is_running
    stats["port"] = proxy.port
    return jsonify(stats)


@app.route("/api/proxy/traffic", methods=["GET"])
def api_proxy_traffic():
    """Get captured traffic."""
    proxy = get_proxy_engine()
    limit = request.args.get("limit", type=int)
    filter_term = request.args.get("filter", "")
    method = request.args.get("method", "")
    traffic = proxy.get_traffic(limit=limit, filter_term=filter_term or None,
                                method=method or None)
    return jsonify({
        "ok": True,
        "traffic": [r.to_dict() for r in traffic],
        "count": len(traffic),
    })


@app.route("/api/proxy/traffic/<int:req_id>", methods=["GET"])
def api_proxy_traffic_detail(req_id: int):
    """Get details of a single captured request."""
    proxy = get_proxy_engine()
    req = proxy.get_request_by_id(req_id)
    if not req:
        return jsonify({"ok": False, "error": f"Request #{req_id} not found"})
    return jsonify({"ok": True, "request": req.to_dict(),
                     "markdown": ProxyEngine.get_request_detail_markdown(req)})


@app.route("/api/proxy/flags", methods=["GET"])
def api_proxy_flags():
    """Get flagged traffic (security-relevant requests)."""
    proxy = get_proxy_engine()
    flagged = proxy.get_flagged_traffic()
    return jsonify({
        "ok": True,
        "traffic": [r.to_dict() for r in flagged],
        "count": len(flagged),
    })


@app.route("/api/proxy/scope", methods=["POST"])
def api_proxy_scope():
    """Set or clear proxy scope domains."""
    body = request.get_json(silent=True) or {}
    proxy = get_proxy_engine()
    domains = body.get("domains", [])
    if domains:
        proxy.set_scope(domains)
    else:
        proxy.clear_scope()
    return jsonify({"ok": True, "scope": list(proxy.scope)})


@app.route("/api/proxy/clear", methods=["POST"])
def api_proxy_clear():
    """Clear captured traffic."""
    proxy = get_proxy_engine()
    count = proxy.clear()
    return jsonify({"ok": True, "cleared": count})


@app.route("/api/proxy/replay", methods=["POST"])
def api_proxy_replay():
    """Replay a captured request."""
    body = request.get_json(silent=True) or {}
    req_id = body.get("id")
    if req_id is None:
        return jsonify({"ok": False, "error": "Missing request 'id'"})
    proxy = get_proxy_engine()
    result = proxy.replay_request(int(req_id))
    if not result:
        return jsonify({"ok": False, "error": f"Request #{req_id} not found"})
    return jsonify({
        "ok": True,
        "request": result.to_dict(),
        "markdown": ProxyEngine.get_request_detail_markdown(result),
    })


@app.route("/api/proxy/export", methods=["GET"])
def api_proxy_export():
    """Export captured traffic as JSON."""
    proxy = get_proxy_engine()
    fmt = request.args.get("format", "json")
    if fmt == "markdown":
        return jsonify({"ok": True, "markdown": proxy.export_traffic_markdown()})
    return jsonify({"ok": True, "data": proxy.export_traffic_json()})


@app.route("/api/agent/export", methods=["POST"])
def api_agent_export():
    """Export assessment report."""
    agent: Optional[AgentMode] = _state["agent"]
    if not agent:
        return jsonify({"error": "No assessment data"}), 400

    data = request.json or {}
    fmt: str = str(data.get("format", _state["config"].reporting.format))

    reporter = ReportGenerator(
        include_raw=_state["config"].reporting.include_raw_output,
        report_format=fmt,
    )
    findings = [f.to_dict() for f in agent.findings]
    tool_history = [r.to_dict() for r in agent.runner.history]
    scripts = [s.to_dict() for s in agent.scripts]

    path = reporter.generate(
        target=agent.target,
        findings=findings,
        tool_history=tool_history,
        scripts=scripts,
        scope=agent.scope,
    )
    return jsonify({"ok": True, "path": path})


@app.route("/api/agent/export-pdf", methods=["POST"])
def api_agent_export_pdf():
    """Generate a professional PDF pentest report."""
    if not HAS_REPORTLAB:
        return jsonify({"error": "PDF generation requires reportlab. Install with: pip install 'hackbot[pdf]'"}), 400

    agent: Optional[AgentMode] = _state["agent"]
    if not agent:
        return jsonify({"error": "No assessment data"}), 400

    findings = [f.to_dict() for f in agent.findings]
    tool_history = [r.to_dict() for r in agent.runner.history]
    scripts = [s.to_dict() for s in agent.scripts]

    # Auto-generate compliance data
    compliance_data = None
    if findings:
        try:
            from hackbot.core.compliance import ComplianceMapper
            mapper = ComplianceMapper()
            creport = mapper.map_findings(findings, target=agent.target)
            if creport.mappings:
                compliance_data = creport.to_dict()
        except Exception:
            pass

    gen = PDFReportGenerator(include_raw=_state["config"].reporting.include_raw_output)
    path = gen.generate(
        target=agent.target,
        findings=findings,
        tool_history=tool_history,
        scripts=scripts,
        scope=agent.scope,
        compliance_data=compliance_data,
    )
    return jsonify({"ok": True, "path": path})


# ── Routes: Plan ─────────────────────────────────────────────────────────────

@app.route("/api/plan/templates")
def api_plan_templates():
    """List available plan templates."""
    return jsonify(PlanMode.list_templates())


@app.route("/api/plan/create", methods=["POST"])
def api_plan_create():
    """Create a pentest plan with streaming."""
    data = request.json or {}
    target = data.get("target", "").strip()
    plan_type = data.get("type", "web_pentest")
    scope = data.get("scope", "")
    constraints = data.get("constraints", "")

    if not target:
        return jsonify({"error": "Target required"}), 400

    engine: AIEngine = _state["engine"]
    if not engine.is_configured():
        return jsonify({"error": "API key not configured"}), 400

    plan_mode: PlanMode = _state["plan"]

    def generate():
        token_queue: queue.Queue = queue.Queue()

        def on_token(token):
            token_queue.put(token)

        def run_plan():
            try:
                plan_mode.create_plan(target, plan_type, scope, constraints, on_token=on_token)
            except Exception as e:
                token_queue.put(f"\n\n**Error:** {str(e)}")
            finally:
                token_queue.put(None)

        t = threading.Thread(target=run_plan, daemon=True)
        t.start()

        while True:
            token = token_queue.get()
            if token is None:
                yield f"data: [DONE]\n\n"
                break
            yield f"data: {json.dumps({'token': token})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/plan/ask", methods=["POST"])
def api_plan_ask():
    """Ask a planning question with streaming."""
    data = request.json or {}
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "Empty message"}), 400

    plan_mode: PlanMode = _state["plan"]

    def generate():
        token_queue: queue.Queue = queue.Queue()

        def on_token(token):
            token_queue.put(token)

        def run_ask():
            try:
                plan_mode.ask(message, on_token=on_token)
            except Exception as e:
                token_queue.put(f"\n\n**Error:** {str(e)}")
            finally:
                token_queue.put(None)

        t = threading.Thread(target=run_ask, daemon=True)
        t.start()

        while True:
            token = token_queue.get()
            if token is None:
                yield f"data: [DONE]\n\n"
                break
            yield f"data: {json.dumps({'token': token})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/plan/clear", methods=["POST"])
def api_plan_clear():
    """Reset planning session."""
    _state["plan"] = PlanMode(_state["engine"], _state["config"])
    return jsonify({"ok": True})


# ── Routes: CVE Lookup ───────────────────────────────────────────────────────

@app.route("/api/cve/lookup", methods=["POST"])
def api_cve_lookup():
    """Look up a specific CVE by ID."""
    data = request.json or {}
    cve_id = data.get("cve_id", "").strip()
    if not cve_id:
        return jsonify({"error": "CVE ID required"}), 400

    cve_engine = CVELookup()
    entry = cve_engine.lookup_cve(cve_id)
    if entry:
        return jsonify({"result": entry.to_dict(), "report": CVELookup.format_cve_report([entry])})
    return jsonify({"error": f"CVE not found: {cve_id}"}), 404


@app.route("/api/cve/search", methods=["POST"])
def api_cve_search():
    """Search CVEs by keyword."""
    data = request.json or {}
    keyword = data.get("keyword", "").strip()
    severity = data.get("severity", "")
    max_results = min(int(data.get("max_results", 20)), 50)

    if not keyword:
        return jsonify({"error": "Keyword required"}), 400

    cve_engine = CVELookup()
    cves = cve_engine.search_cve(keyword, max_results=max_results, severity=severity)
    return jsonify({
        "results": [c.to_dict() for c in cves],
        "count": len(cves),
        "report": CVELookup.format_cve_report(cves, title=f"CVE Search: {keyword}"),
    })


@app.route("/api/cve/exploits", methods=["POST"])
def api_cve_exploits():
    """Search for exploits."""
    data = request.json or {}
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error": "Search query required"}), 400

    cve_engine = CVELookup()
    exploits = cve_engine.search_exploits(query)
    return jsonify({"exploits": exploits, "count": len(exploits)})


@app.route("/api/cve/nmap", methods=["POST"])
def api_cve_nmap_map():
    """Map nmap output to CVEs."""
    data = request.json or {}
    nmap_output = data.get("output", "").strip()
    if not nmap_output:
        return jsonify({"error": "Nmap output required"}), 400

    cve_engine = CVELookup()
    results = cve_engine.parse_nmap_and_lookup(nmap_output, max_per_service=5)
    formatted: Dict[str, Any] = {}
    for service, cves in results.items():
        formatted[service] = [c.to_dict() for c in cves]

    return jsonify({
        "results": formatted,
        "report": CVELookup.format_nmap_cve_report(results),
    })


# ── Routes: OSINT ────────────────────────────────────────────────────────────

@app.route("/api/osint/scan", methods=["POST"])
def api_osint_scan():
    """Run a full OSINT scan on a domain."""
    data = request.json or {}
    domain = data.get("domain", "").strip()
    if not domain:
        return jsonify({"error": "Domain required"}), 400

    osint = OSINTEngine()

    def generate():
        stages_done = []

        def on_progress(stage: str, detail: str) -> None:
            stages_done.append({"stage": stage, "detail": detail})

        try:
            result = osint.full_scan(domain, on_progress=on_progress)
            report_md = OSINTEngine.format_report(result)
            final = json.dumps({
                "report": result.to_dict(),
                "markdown": report_md,
                "stages": stages_done,
            })
            yield f"data: {final}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield f"data: [DONE]\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/osint/subdomains", methods=["POST"])
def api_osint_subdomains():
    """Enumerate subdomains."""
    data = request.json or {}
    domain = data.get("domain", "").strip()
    if not domain:
        return jsonify({"error": "Domain required"}), 400

    osint = OSINTEngine()
    subs = osint.enumerate_subdomains(domain)
    return jsonify({
        "subdomains": [s.to_dict() for s in subs],
        "count": len(subs),
    })


@app.route("/api/osint/dns", methods=["POST"])
def api_osint_dns():
    """Get DNS records."""
    data = request.json or {}
    domain = data.get("domain", "").strip()
    if not domain:
        return jsonify({"error": "Domain required"}), 400

    osint = OSINTEngine()
    records = osint.get_dns_records(domain)
    return jsonify({"records": [r.to_dict() for r in records], "count": len(records)})


@app.route("/api/osint/whois", methods=["POST"])
def api_osint_whois():
    """WHOIS lookup."""
    data = request.json or {}
    domain = data.get("domain", "").strip()
    if not domain:
        return jsonify({"error": "Domain required"}), 400

    osint = OSINTEngine()
    result = osint.whois_lookup(domain)
    if result:
        return jsonify(result.to_dict())
    return jsonify({"error": "WHOIS lookup failed"}), 404


@app.route("/api/osint/techstack", methods=["POST"])
def api_osint_techstack():
    """Fingerprint technology stack."""
    data = request.json or {}
    target = data.get("target", "").strip()
    if not target:
        return jsonify({"error": "Target URL/domain required"}), 400

    osint = OSINTEngine()
    result = osint.fingerprint_tech_stack(target)
    return jsonify(result.to_dict())


# ── Routes: Topology ─────────────────────────────────────────────────────────

@app.route("/api/topology/parse", methods=["POST"])
def api_topology_parse():
    """Parse scan output into network topology graph data."""
    data = request.json or {}
    output = data.get("output", "").strip()

    if not output:
        # Try to get from last agent scan
        agent: Optional[AgentMode] = _state["agent"]
        if agent and agent.runner.history:
            for result in reversed(agent.runner.history):
                if "nmap" in result.command.lower() or "masscan" in result.command.lower():
                    output = result.stdout
                    break

    if not output:
        return jsonify({"error": "Scan output required (paste nmap/masscan output)"}), 400

    parser = TopologyParser()
    topo = parser.auto_parse(output)

    return jsonify({
        "topology": topo.to_dict(),
        "ascii": TopologyParser.render_ascii(topo),
        "markdown": TopologyParser.format_markdown(topo),
    })


@app.route("/api/topology/from-agent")
def api_topology_from_agent():
    """Build topology from agent's scan history."""
    agent: Optional[AgentMode] = _state["agent"]
    if not agent or not agent.runner.history:
        return jsonify({"error": "No agent scan data available"}), 400

    # Combine all nmap/masscan results
    scan_outputs: List[str] = []
    for result in agent.runner.history:
        if ("nmap" in result.command.lower() or "masscan" in result.command.lower()) and result.stdout:
            scan_outputs.append(result.stdout)

    if not scan_outputs:
        return jsonify({"error": "No nmap/masscan scans found in agent history"}), 404

    parser = TopologyParser()
    # Parse the most complete scan (usually the longest output)
    best_output = max(scan_outputs, key=len)
    topo = parser.auto_parse(best_output)

    return jsonify({
        "topology": topo.to_dict(),
        "ascii": TopologyParser.render_ascii(topo),
        "markdown": TopologyParser.format_markdown(topo),
    })


# ── Compliance Routes ────────────────────────────────────────────────────────

@app.route("/api/compliance/map", methods=["POST"])
def api_compliance_map():
    """Map findings to compliance frameworks."""
    data = request.get_json(force=True)
    findings = data.get("findings", [])
    frameworks = data.get("frameworks", None)
    target = data.get("target", "")

    mapper = ComplianceMapper(frameworks=frameworks)
    report = mapper.map_findings(findings, target=target)
    return jsonify(report.to_dict())


@app.route("/api/compliance/from-agent")
def api_compliance_from_agent():
    """Map current agent findings to compliance frameworks."""
    agent: Optional[AgentMode] = _state["agent"]
    if not agent or not agent.findings:
        return jsonify({"error": "No agent findings available"}), 400

    fw_arg = request.args.get("frameworks", "")
    frameworks = [f.strip() for f in fw_arg.split(",") if f.strip()] or None

    mapper = ComplianceMapper(frameworks=frameworks)
    findings_dicts = [f.to_dict() for f in agent.findings]
    report = mapper.map_findings(findings_dicts, target=agent.target)

    return jsonify({
        "report": report.to_dict(),
        "markdown": ComplianceMapper.format_report(report),
    })


@app.route("/api/compliance/frameworks")
def api_compliance_frameworks():
    """List available compliance frameworks."""
    return jsonify(ComplianceMapper.list_frameworks())


@app.route("/api/compliance/controls/<framework>")
def api_compliance_controls(framework):
    """List controls for a specific framework."""
    controls = ComplianceMapper.get_framework_controls(framework)
    if not controls:
        return jsonify({"error": f"Unknown framework: {framework}"}), 404
    return jsonify([c.to_dict() for c in controls])


# ── ATT&CK Routes ────────────────────────────────────────────────────────────

@app.route("/api/attack/map", methods=["POST"])
def api_attack_map():
    """Map findings to ATT&CK techniques."""
    data = request.get_json(force=True)
    findings = data.get("findings", [])
    target = data.get("target", "")
    tool_history = data.get("tool_history", [])

    from hackbot.core.attack import AttackMapper
    mapper = AttackMapper()
    report = mapper.map_findings(findings, target=target, tool_history=tool_history)
    return jsonify(report.to_dict())


@app.route("/api/attack/from-agent")
def api_attack_from_agent():
    """Map current agent findings to ATT&CK techniques."""
    agent: Optional[AgentMode] = _state["agent"]
    if not agent or not agent.findings:
        return jsonify({"error": "No agent findings available"}), 400

    from hackbot.core.attack import AttackMapper
    mapper = AttackMapper()
    findings_dicts = [f.to_dict() for f in agent.findings]
    tool_history = [r.to_dict() for r in agent.runner.history]
    report = mapper.map_findings(findings_dicts, target=agent.target, tool_history=tool_history)

    return jsonify({
        "report": report.to_dict(),
        "markdown": AttackMapper.format_report(report),
    })


@app.route("/api/attack/layer")
def api_attack_layer():
    """Generate ATT&CK Navigator layer JSON from current agent findings."""
    agent: Optional[AgentMode] = _state["agent"]
    if not agent or not agent.findings:
        return jsonify({"error": "No agent findings available"}), 400

    from hackbot.core.attack import AttackMapper
    mapper = AttackMapper()
    findings_dicts = [f.to_dict() for f in agent.findings]
    tool_history = [r.to_dict() for r in agent.runner.history]
    report = mapper.map_findings(findings_dicts, target=agent.target, tool_history=tool_history)
    layer = mapper.generate_navigator_layer(report)
    return jsonify(layer)


@app.route("/api/attack/tactics")
def api_attack_tactics():
    """List all ATT&CK tactics."""
    from hackbot.core.attack import AttackMapper
    return jsonify(AttackMapper.list_tactics())


@app.route("/api/attack/techniques")
def api_attack_techniques():
    """List ATT&CK techniques, optionally filtered by tactic."""
    tactic_id = request.args.get("tactic_id", "")
    from hackbot.core.attack import AttackMapper
    return jsonify(AttackMapper.list_techniques(tactic_id))


@app.route("/api/attack/technique/<technique_id>")
def api_attack_technique(technique_id):
    """Get a specific ATT&CK technique by ID."""
    from hackbot.core.attack import AttackMapper
    tech = AttackMapper.get_technique(technique_id.upper())
    if not tech:
        return jsonify({"error": f"Technique not found: {technique_id}"}), 404
    return jsonify(tech)


@app.route("/api/attack/tool/<tool_name>")
def api_attack_tool(tool_name):
    """Get ATT&CK techniques mapped to a tool."""
    from hackbot.core.attack import AttackMapper
    techs = AttackMapper.get_tool_techniques(tool_name)
    return jsonify(techs)


# ── Diff Report Routes ───────────────────────────────────────────────────────

@app.route("/api/diff/sessions")
def api_diff_sessions():
    """List agent sessions that have findings (for diff selection)."""
    sessions = list_agent_sessions()
    return jsonify(sessions)


@app.route("/api/diff/compare", methods=["POST"])
def api_diff_compare():
    """Compare two agent sessions."""
    data = request.get_json(force=True)
    old_id = data.get("old_session_id", "")
    new_id = data.get("new_session_id", "")
    use_current = data.get("use_current", False)

    if not old_id:
        return jsonify({"error": "old_session_id is required"}), 400

    old_data = load_session_findings(old_id)
    if not old_data:
        return jsonify({"error": f"Session not found: {old_id}"}), 404

    if use_current:
        agent: Optional[AgentMode] = _state["agent"]
        if not agent or not agent.findings:
            return jsonify({"error": "No active agent with findings"}), 400
        import time as _time
        new_data = {
            "id": agent.session_id,
            "name": f"Agent: {agent.target}",
            "target": agent.target,
            "created": _time.time(),
            "findings": [f.to_dict() for f in agent.findings],
        }
    else:
        if not new_id:
            return jsonify({"error": "new_session_id is required"}), 400
        new_data = load_session_findings(new_id)
        if not new_data:
            return jsonify({"error": f"Session not found: {new_id}"}), 404

    engine = DiffEngine()
    report = engine.compare(old_data, new_data)
    return jsonify({
        "report": report.to_dict(),
        "markdown": report.to_markdown(),
    })


# ── Plugin Routes ────────────────────────────────────────────────────────────

@app.route("/api/plugins")
def api_plugins_list():
    """List all registered plugins."""
    try:
        pm = get_plugin_manager()
        plugins = pm.list_plugins()
        return jsonify({
            "plugins": plugins,
            "plugins_dir": str(PLUGINS_DIR),
            "errors": pm.get_load_errors(),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/plugins/reload", methods=["POST"])
def api_plugins_reload():
    """Reload / rediscover plugins."""
    try:
        reset_plugin_manager()
        pm = get_plugin_manager()
        return jsonify({
            "count": len(pm.plugins),
            "plugins": pm.list_plugins(),
            "errors": pm.get_load_errors(),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/plugins/execute", methods=["POST"])
def api_plugins_execute():
    """Execute a plugin by name with optional args."""
    data = request.get_json(force=True)
    name = data.get("name", "")
    args = data.get("args", {})
    if not name:
        return jsonify({"error": "Plugin name is required"}), 400
    try:
        pm = get_plugin_manager()
        result = pm.execute(name, **args)
        return jsonify(result.to_dict())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Campaign Routes ──────────────────────────────────────────────────────────

@app.route("/api/campaigns")
def api_campaigns_list():
    """List all saved campaigns."""
    try:
        cm = get_campaign_manager()
        campaigns = cm.list_campaigns()
        active_id = cm.active_campaign.id if cm.active_campaign else None
        return jsonify({"campaigns": campaigns, "active_id": active_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/campaigns", methods=["POST"])
def api_campaigns_create():
    """Create a new campaign."""
    data = request.get_json(force=True)
    name = data.get("name", "").strip()
    targets = data.get("targets", [])
    scope = data.get("scope", "")
    instructions = data.get("instructions", "")
    max_steps = data.get("max_steps_per_target", 50)

    if not name:
        return jsonify({"error": "Campaign name is required"}), 400
    if not targets or not isinstance(targets, list):
        return jsonify({"error": "At least one target is required"}), 400

    cm = get_campaign_manager()
    campaign = cm.create_campaign(
        name=name, targets=targets, scope=scope,
        instructions=instructions, max_steps_per_target=max_steps,
    )
    cm.active_campaign = campaign
    return jsonify(campaign.to_dict())


@app.route("/api/campaigns/<campaign_id>")
def api_campaign_get(campaign_id: str):
    """Get a campaign by ID."""
    cm = get_campaign_manager()
    campaign = cm.load_campaign(campaign_id)
    if not campaign:
        return jsonify({"error": "Campaign not found"}), 404
    return jsonify(campaign.to_dict())


@app.route("/api/campaigns/<campaign_id>", methods=["DELETE"])
def api_campaign_delete(campaign_id: str):
    cm = get_campaign_manager()
    if cm.delete_campaign(campaign_id):
        return jsonify({"ok": True})
    return jsonify({"error": "Campaign not found"}), 404


@app.route("/api/campaigns/<campaign_id>/activate", methods=["POST"])
def api_campaign_activate(campaign_id: str):
    """Set a campaign as the active one."""
    cm = get_campaign_manager()
    campaign = cm.load_campaign(campaign_id)
    if not campaign:
        return jsonify({"error": "Campaign not found"}), 404
    cm.active_campaign = campaign
    return jsonify(campaign.to_dict())


@app.route("/api/campaigns/active")
def api_campaign_active():
    """Get the active campaign status."""
    cm = get_campaign_manager()
    if not cm.active_campaign:
        return jsonify({"error": "No active campaign"}), 404
    return jsonify(cm.active_campaign.to_dict())


@app.route("/api/campaigns/active/start", methods=["POST"])
def api_campaign_start():
    """Start the active campaign and begin first target."""
    cm = get_campaign_manager()
    campaign = cm.active_campaign
    if not campaign:
        return jsonify({"error": "No active campaign"}), 404

    result = cm.start_campaign(campaign)
    if result.startswith("ERROR"):
        return jsonify({"error": result}), 400

    return jsonify({
        "status": campaign.status.value,
        "first_target": result,
        "campaign": campaign.to_dict(),
    })


@app.route("/api/campaigns/active/start-target", methods=["POST"])
def api_campaign_start_target():
    """Start assessment of a specific target within the active campaign via SSE."""
    cm = get_campaign_manager()
    campaign = cm.active_campaign
    if not campaign:
        return jsonify({"error": "No active campaign"}), 404

    data = request.get_json(force=True)
    target = data.get("target", "")
    if not target or target not in campaign.targets:
        return jsonify({"error": f"Invalid target: {target}"}), 400

    cm.begin_target(campaign, target)

    config: HackBotConfig = _state["config"]
    engine: AIEngine = _state["engine"]
    token_queue: queue.Queue = queue.Queue()

    agent = AgentMode(
        engine=engine, config=config,
        on_confirm=lambda cmd, reason: config.agent.auto_confirm,
        on_token=lambda t: token_queue.put(t),
    )
    _state["agent"] = agent
    _state["mode"] = "agent"

    campaign_ctx = campaign.get_agent_context(target)
    instructions = (campaign.instructions or "") + "\n" + campaign_ctx

    def run():
        assert campaign is not None
        try:
            agent.start(target, scope=campaign.scope, instructions=instructions)
        except Exception as e:
            cm.fail_target(campaign, target, error=str(e))
            token_queue.put(None)
            return
        token_queue.put(None)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

    def generate():
        while True:
            tok = token_queue.get()
            if tok is None:
                yield f"data: [DONE]\n\n"
                break
            yield f"data: {json.dumps({'token': tok})}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


@app.route("/api/campaigns/active/complete-target", methods=["POST"])
def api_campaign_complete_target():
    """Mark current target as completed, collecting findings from the agent."""
    cm = get_campaign_manager()
    campaign = cm.active_campaign
    if not campaign:
        return jsonify({"error": "No active campaign"}), 404

    data = request.get_json(force=True)
    target = data.get("target", "")
    if not target:
        return jsonify({"error": "Target is required"}), 400

    agent: Optional[AgentMode] = _state.get("agent")
    findings = []
    tool_history = []
    session_id = ""
    steps = 0
    summary = ""

    if agent:
        findings = [f.to_dict() for f in agent.findings]
        tool_history = [r.to_dict() for r in agent.runner.history]
        session_id = agent.session_id
        steps = len(agent.steps)
        if agent.findings:
            summary = agent.get_findings_summary()

    cm.complete_target(
        campaign, target,
        findings=findings, tool_history=tool_history,
        session_id=session_id, steps=steps, summary=summary,
    )
    return jsonify(campaign.to_dict())


@app.route("/api/campaigns/active/skip-target", methods=["POST"])
def api_campaign_skip_target():
    """Skip a target."""
    cm = get_campaign_manager()
    campaign = cm.active_campaign
    if not campaign:
        return jsonify({"error": "No active campaign"}), 404
    data = request.get_json(force=True)
    target = data.get("target", "")
    reason = data.get("reason", "Skipped by user")
    if not target:
        return jsonify({"error": "Target is required"}), 400
    cm.skip_target(campaign, target, reason=reason)
    return jsonify(campaign.to_dict())


@app.route("/api/campaigns/active/pause", methods=["POST"])
def api_campaign_pause():
    cm = get_campaign_manager()
    campaign = cm.active_campaign
    if not campaign:
        return jsonify({"error": "No active campaign"}), 404
    cm.pause_campaign(campaign)
    return jsonify(campaign.to_dict())


@app.route("/api/campaigns/active/abort", methods=["POST"])
def api_campaign_abort():
    cm = get_campaign_manager()
    campaign = cm.active_campaign
    if not campaign:
        return jsonify({"error": "No active campaign"}), 404
    cm.abort_campaign(campaign)
    return jsonify(campaign.to_dict())


@app.route("/api/campaigns/active/findings")
def api_campaign_findings():
    cm = get_campaign_manager()
    campaign = cm.active_campaign
    if not campaign:
        return jsonify({"error": "No active campaign"}), 404
    return jsonify({
        "all_findings": campaign.all_findings(),
        "severity_counts": campaign.severity_counts(),
        "findings_by_target": {t: fs for t, fs in campaign.findings_by_target().items()},
        "markdown": campaign.get_summary_markdown(),
    })


@app.route("/api/campaigns/active/report", methods=["POST"])
def api_campaign_report():
    cm = get_campaign_manager()
    campaign = cm.active_campaign
    if not campaign:
        return jsonify({"error": "No active campaign"}), 404
    path = cm.save_campaign_report(campaign)
    return jsonify({"path": str(path), "campaign": campaign.to_dict()})


# ── Routes: Telegram Bot ─────────────────────────────────────────────────────

@app.route("/api/telegram/start", methods=["POST"])
def api_telegram_start():
    """Start the Telegram bot."""
    try:
        from hackbot.integrations.telegram_bot import (
            check_telegram_deps, get_telegram_bot,
        )
    except ImportError:
        return jsonify({"ok": False, "error": "Telegram dependencies not installed"}), 400

    if not check_telegram_deps():
        return jsonify({"ok": False, "error": "Telegram dependencies not installed"}), 400

    data = request.json or {}
    token = data.get("token", "")
    config = _state["config"]
    bot = get_telegram_bot(config, token=token)
    result = bot.start_background()
    if not result.get("ok"):
        return jsonify(result), 400

    # Don't send raw QR bytes through JSON
    result.pop("qr_png", None)
    return jsonify(result)


@app.route("/api/telegram/stop", methods=["POST"])
def api_telegram_stop():
    """Stop the Telegram bot."""
    try:
        from hackbot.integrations.telegram_bot import get_telegram_bot, reset_telegram_bot
    except ImportError:
        return jsonify({"ok": False, "error": "Not available"}), 400

    bot = get_telegram_bot(_state["config"])
    result = bot.stop()
    if result.get("ok"):
        reset_telegram_bot()
    return jsonify(result)


@app.route("/api/telegram/status")
def api_telegram_status():
    """Get Telegram bot status."""
    try:
        from hackbot.integrations.telegram_bot import get_telegram_bot
    except ImportError:
        return jsonify({"available": False, "running": False})

    bot = get_telegram_bot(_state["config"])
    return jsonify({
        "available": True,
        "running": bot.is_running,
        "bot_username": bot.bot_username,
        "authorized_users": len(bot.pairing.authorized_users),
        "active_sessions": len(bot.sessions),
    })


@app.route("/api/telegram/qr", methods=["POST"])
def api_telegram_qr():
    """Generate a new QR pairing code."""
    try:
        from hackbot.integrations.telegram_bot import get_telegram_bot
    except ImportError:
        return jsonify({"ok": False, "error": "Not available"}), 400

    bot = get_telegram_bot(_state["config"])
    if not bot.is_running:
        return jsonify({"ok": False, "error": "Bot is not running"}), 400

    info = bot.get_pairing_info()
    info.pop("qr_png", None)  # Don't send raw bytes
    info["ok"] = True
    return jsonify(info)


@app.route("/api/telegram/qr-image")
def api_telegram_qr_image():
    """Return QR code as a PNG image."""
    try:
        from hackbot.integrations.telegram_bot import get_telegram_bot
    except ImportError:
        return "Not available", 404

    bot = get_telegram_bot(_state["config"])
    if not bot.is_running:
        return "Bot not running", 400

    info = bot.get_pairing_info()
    qr_bytes = info.get("qr_png")
    if not qr_bytes:
        return "QR not available", 404

    return Response(qr_bytes, mimetype="image/png")


# ── Launch ───────────────────────────────────────────────────────────────────

def _start_flask(host: str, port: int) -> None:
    """Start Flask in a background thread (used when pywebview is available)."""
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.ERROR)
    app.run(host=host, port=port, debug=False, threaded=True, use_reloader=False)


def launch_gui(config: HackBotConfig, host: str = "127.0.0.1", port: int = 1337) -> None:
    """
    Launch HackBot as a native desktop application.

    Uses pywebview to create a real OS-native window with an embedded webview.
    Falls back to opening in the default browser if pywebview is not installed.
    """
    _init_state(config)

    url = f"http://{host}:{port}"

    # Suppress Flask request logging
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.WARNING)

    # Try native desktop window via pywebview
    flask_started = False
    try:
        import webview  # pywebview  # type: ignore[import-not-found]

        # ── GPU workaround for Raspberry Pi / low-end GPUs ──────────────
        # The Pi's Mesa driver doesn't expose GL_EXT_shader_texture_lod,
        # which causes dozens of shader compilation errors and crashes in
        # the WebKit/GTK compositing path.  Force software rendering so
        # the embedded webview never touches the hardware GL driver.
        os.environ.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")
        os.environ.setdefault("WEBKIT_DISABLE_COMPOSITING_MODE", "1")

        # Start Flask server in background thread
        flask_thread = threading.Thread(
            target=_start_flask, args=(host, port), daemon=True
        )
        flask_thread.start()
        flask_started = True

        # Wait for Flask to be ready
        import urllib.request
        for _ in range(50):
            try:
                urllib.request.urlopen(url, timeout=0.5)
                break
            except Exception:
                time.sleep(0.1)

        print(f"\n  ⚡ HackBot launching as desktop application...")

        # Create native window
        icon_path = str(LOGO_PATH) if LOGO_PATH.exists() else None
        window = webview.create_window(
            title="HackBot — AI Cybersecurity Assistant",
            url=url,
            width=1280,
            height=820,
            min_size=(900, 600),
            background_color="#0d1117",
            text_select=True,
        )

        # Start the native event loop (blocks until window is closed)
        webview.start(
            gui=None,       # auto-detect best backend (gtk, qt, cef, etc.)
            debug=False,
        )

        print("  HackBot closed. Goodbye!\n")
        return

    except ImportError:
        logger.info("pywebview not available, falling back to browser mode")
    except Exception as e:
        logger.warning(f"pywebview failed ({e}), falling back to browser mode")

    # Fallback: run in browser
    print(f"\n  ⚡ HackBot GUI running at {url}")
    print(f"  Native desktop backend is missing (Qt/GTK Python bindings).")
    print(f"  Install one backend for native desktop mode:")
    print(f"    Option A (venv-friendly): pip install PyQt5 qtpy")
    print(f"    Option B (system GTK, Debian/Kali):")
    print(f"      sudo apt install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.1")
    print(f"  If using a venv with GTK, recreate it with --system-site-packages.")
    print(f"  (Browser mode works without these packages.)")
    print(f"  Press Ctrl+C to stop\n")

    def open_browser():
        time.sleep(1.2)
        webbrowser.open(url)

    threading.Thread(target=open_browser, daemon=True).start()

    if flask_started:
        # Flask is already running on this port from the pywebview attempt;
        # just block the main thread until interrupted.
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n  HackBot stopped. Goodbye!\n")
    else:
        app.run(host=host, port=port, debug=False, threaded=True)
