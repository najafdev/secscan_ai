"""
Telegram Bot — Command Handlers
=================================
All Telegram /command handlers live here.
Each handler is an ``async`` function that receives an ``Update`` + ``context``
and interacts with the user's `TelegramUserSession`.
"""

from __future__ import annotations

import asyncio
import io
import logging
import time
from typing import Any, Dict, Optional, TYPE_CHECKING

from hackbot import __version__
from hackbot.config import detect_platform, detect_tools, save_config
from hackbot.core.engine import PROVIDERS, SUPPORTED_LANGUAGES
from hackbot.core.cve import CVELookup
from hackbot.core.compliance import ComplianceMapper
from hackbot.core.osint import OSINTEngine
from hackbot.core.vulndb import VulnDB
from hackbot.core.attack import AttackMapper
from hackbot.modes.agent import AgentMode
from hackbot.modes.chat import ChatMode
from hackbot.modes.plan import PlanMode
from hackbot.reporting import ReportGenerator

from hackbot.integrations.telegram_bot.utils import format_html, split_message

if TYPE_CHECKING:
    from hackbot.integrations.telegram_bot.bot import HackBotTelegram

logger = logging.getLogger(__name__)

# These are only available when python-telegram-bot is installed.
# The bot.py module gate-checks this at init time so handlers are
# never actually called unless the lib is present.
try:
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
    from telegram.constants import ChatAction, ParseMode
    from telegram.ext import ContextTypes
except ImportError:
    pass


# ── /start ───────────────────────────────────────────────────────────────────

async def cmd_start(bot: "HackBotTelegram", update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start — QR pairing gate & welcome dashboard."""
    user_id = update.effective_user.id
    args = context.args

    # ── Pairing attempt via deep-link (/start <code>) ────────────────
    if args and len(args) == 1:
        code = args[0]
        if bot.pairing.verify(code):
            ttl_days = bot.config.telegram.session_ttl_days
            bot.pairing.authorize(user_id)
            bot.pairing.save()
            await update.message.reply_text(
                f"✅ <b>Connected successfully!</b>\n\n"
                f"Welcome to HackBot v{__version__}, "
                f"{update.effective_user.first_name}!\n\n"
                f"Your device is now linked. You have full control "
                f"of your HackBot instance from Telegram.\n\n"
                f"📅 Session valid for <b>{ttl_days} days</b>.\n"
                f"Use /logout to disconnect at any time.\n\n"
                f"Type /help to see available commands.",
                parse_mode=ParseMode.HTML,
            )
            logger.info("Telegram user %s authorized via QR pairing", user_id)
            return
        else:
            await update.message.reply_text(
                "❌ <b>Invalid or expired pairing code.</b>\n\n"
                "Please generate a fresh QR code from your HackBot terminal:\n"
                "<code>hackbot telegram</code>\n\n"
                "Then scan the new QR code.",
                parse_mode=ParseMode.HTML,
            )
            return

    # ── Already paired — show dashboard ──────────────────────────────
    if bot.pairing.is_authorized(user_id):
        # Refresh session clock on /start
        bot.pairing.refresh(user_id)
        bot.pairing.save()

        ts = bot.pairing.authorized_users.get(user_id, 0)
        import datetime
        expires = datetime.datetime.fromtimestamp(
            ts + bot.config.telegram.session_ttl_days * 86400
        ).strftime("%b %d, %Y")

        keyboard = [
            [
                InlineKeyboardButton("💬 Chat", callback_data="mode_chat"),
                InlineKeyboardButton("🤖 Agent", callback_data="mode_agent"),
                InlineKeyboardButton("📋 Plan", callback_data="mode_plan"),
            ],
            [
                InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
                InlineKeyboardButton("ℹ️ Help", callback_data="help"),
            ],
            [
                InlineKeyboardButton("🚪 Logout", callback_data="logout"),
            ],
        ]
        session = bot._get_session(user_id)
        await update.message.reply_text(
            f"🤖 <b>HackBot v{__version__}</b>\n\n"
            f"Current mode: <b>{session.mode.upper()}</b>\n"
            f"Provider: <b>{bot.config.ai.provider}/{bot.config.ai.model}</b>\n"
            f"Language: <b>{bot.config.ui.language}</b>\n"
            f"Session expires: <b>{expires}</b>\n\n"
            f"Send any message to chat, or use the buttons below.",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    # ── Not paired — show connection instructions ────────────────────
    await update.message.reply_text(
        "🤖 <b>HackBot — AI Cybersecurity Assistant</b>\n\n"
        "To connect this bot to your HackBot instance:\n\n"
        "1️⃣  Run on your machine:\n"
        "    <code>hackbot telegram</code>\n\n"
        "2️⃣  A QR code will appear in your terminal\n\n"
        "3️⃣  Scan that QR code with your phone camera\n"
        "    (it will open this chat automatically)\n\n"
        "4️⃣  You're connected! Full HackBot control from here.\n\n"
        "<i>Don't have HackBot yet?</i>\n"
        "<code>pip install hackbot</code>",
        parse_mode=ParseMode.HTML,
    )


# ── /help ────────────────────────────────────────────────────────────────────

async def cmd_help(bot: "HackBotTelegram", update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "🤖 <b>HackBot — Telegram Commands</b>\n\n"
        "<b>Modes:</b>\n"
        "/chat — Switch to Chat mode\n"
        "/agent &lt;target&gt; — Start Agent mode\n"
        "/plan &lt;target&gt; — Generate pentest plan\n\n"
        "<b>Agent:</b>\n"
        "/step — Execute next agent step\n"
        "/findings — Show current findings\n"
        "/stop — Stop current assessment\n\n"
        "<b>Intelligence:</b>\n"
        "/cve &lt;query&gt; — CVE / exploit lookup\n"
        "/osint &lt;domain&gt; — OSINT scan\n"
        "/compliance — Map findings to frameworks\n\n"
        "<b>Settings:</b>\n"
        "/model &lt;name&gt; — Switch AI model\n"
        "/provider &lt;name&gt; — Switch AI provider\n"
        "/language &lt;lang&gt; — Set response language\n"
        "/tools [installed|missing|all] — Show tool availability\n"
        "/config — Show current config\n\n"
        "<b>Session:</b>\n"
        "/reset — Reset conversation\n"
        "/export — Export report\n"
        "/version — Show version\n"
        "/status — Show connection status\n"
        "/logout — Disconnect from HackBot\n\n"
        "<i>Or just type any message to chat!</i>"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)


# ── Mode switching ───────────────────────────────────────────────────────────

async def cmd_chat(bot: "HackBotTelegram", update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = bot._get_session(update.effective_user.id)
    session.mode = "chat"
    await update.message.reply_text("💬 Switched to <b>Chat Mode</b>", parse_mode=ParseMode.HTML)


# ── Agent ────────────────────────────────────────────────────────────────────

async def cmd_agent(bot: "HackBotTelegram", update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = bot._get_session(update.effective_user.id)
    target = " ".join(context.args) if context.args else ""

    if not target:
        await update.message.reply_text(
            "Usage: /agent &lt;target&gt;\n"
            "Example: <code>/agent 192.168.1.1</code>\n"
            "Example: <code>/agent example.com</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    if not bot.engine.is_configured():
        await update.message.reply_text("❌ API key not configured. Use /config to check.")
        return

    session.mode = "agent"
    session.agent_mode = AgentMode(engine=bot.engine, config=bot.config)

    await update.message.reply_text(
        f"🤖 <b>Agent Mode — Starting assessment</b>\n"
        f"Target: <code>{target}</code>\n\n"
        f"⏳ Planning assessment...",
        parse_mode=ParseMode.HTML,
    )

    agent = session.agent_mode
    if not agent:
        await update.message.reply_text("❌ Failed to initialize agent mode.")
        return

    loop = asyncio.get_event_loop()
    try:
        response = await loop.run_in_executor(None, lambda: agent.start(target))
        for chunk in split_message(response):
            await update.message.reply_text(format_html(chunk), parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"❌ Agent error: {e}")


async def cmd_step(bot: "HackBotTelegram", update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = bot._get_session(update.effective_user.id)
    agent = session.agent_mode
    if session.mode != "agent" or not agent or not agent.is_running:
        await update.message.reply_text(
            "No active assessment. Start one with:\n<code>/agent &lt;target&gt;</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    user_input = " ".join(context.args) if context.args else ""
    await update.message.chat.send_action(ChatAction.TYPING)
    loop = asyncio.get_event_loop()
    try:
        response, is_complete = await loop.run_in_executor(None, lambda: agent.step(user_input))
        for chunk in split_message(response):
            await update.message.reply_text(format_html(chunk), parse_mode=ParseMode.HTML)
        if is_complete:
            await update.message.reply_text(
                "✅ <b>Assessment complete!</b>\nUse /findings to view results, /export for report.",
                parse_mode=ParseMode.HTML,
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Step error: {e}")


async def cmd_findings(bot: "HackBotTelegram", update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = bot._get_session(update.effective_user.id)
    if not session.agent_mode or not session.agent_mode.findings:
        await update.message.reply_text("No findings yet.")
        return

    severity_icons = {"Critical": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🔵", "Info": "⚪"}
    lines = [f"🔍 <b>Findings ({len(session.agent_mode.findings)})</b>\n"]
    for i, f in enumerate(session.agent_mode.findings, 1):
        icon = severity_icons.get(f.severity.value, "•")
        lines.append(f"{icon} <b>#{i} {f.title}</b> [{f.severity.value}]")
        if f.description:
            desc = f.description[:150] + "..." if len(f.description) > 150 else f.description
            lines.append(f"   {desc}")
        lines.append("")

    text = "\n".join(lines)
    for chunk in split_message(text):
        await update.message.reply_text(chunk, parse_mode=ParseMode.HTML)


async def cmd_stop(bot: "HackBotTelegram", update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = bot._get_session(update.effective_user.id)
    if session.agent_mode and session.agent_mode.is_running:
        session.agent_mode.is_running = False
        count = len(session.agent_mode.findings)
        await update.message.reply_text(
            f"🛑 Assessment stopped. {count} findings collected.\n"
            f"Use /findings to view, /export for report.",
        )
    else:
        await update.message.reply_text("No active assessment to stop.")


# ── Plan ─────────────────────────────────────────────────────────────────────

async def cmd_plan(bot: "HackBotTelegram", update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = bot._get_session(update.effective_user.id)
    target = " ".join(context.args) if context.args else ""

    if not target:
        await update.message.reply_text(
            "Usage: /plan &lt;target&gt;\n"
            "Example: <code>/plan example.com web_pentest</code>\n\n"
            "Templates: web_pentest, network_pentest, api_pentest, "
            "cloud_audit, ad_pentest, wireless, mobile, bug_bounty",
            parse_mode=ParseMode.HTML,
        )
        return

    if not bot.engine.is_configured():
        await update.message.reply_text("❌ API key not configured.")
        return

    session.mode = "plan"
    if not session.plan_mode:
        session.plan_mode = PlanMode(engine=bot.engine, config=bot.config)
    plan_mode = session.plan_mode
    parts = target.split()
    plan_target = parts[0]
    plan_type = parts[1] if len(parts) > 1 else "web_pentest"

    await update.message.chat.send_action(ChatAction.TYPING)
    loop = asyncio.get_event_loop()
    try:
        response = await loop.run_in_executor(
            None, lambda: plan_mode.create_plan(plan_target, plan_type)
        )
        for chunk in split_message(response):
            await update.message.reply_text(format_html(chunk), parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"❌ Plan error: {e}")


# ── Intelligence ─────────────────────────────────────────────────────────────

async def cmd_cve(bot: "HackBotTelegram", update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = " ".join(context.args) if context.args else ""
    if not query:
        await update.message.reply_text(
            "Usage:\n"
            "<code>/cve CVE-2021-44228</code> — Lookup by ID\n"
            "<code>/cve Apache 2.4.49</code> — Search by keyword",
            parse_mode=ParseMode.HTML,
        )
        return

    await update.message.chat.send_action(ChatAction.TYPING)
    cve_engine = CVELookup(nvd_api_key=bot.config.agent.nvd_api_key)
    loop = asyncio.get_event_loop()

    try:
        if query.strip().upper().startswith("CVE-"):
            entry = await loop.run_in_executor(None, lambda: cve_engine.lookup_cve(query.strip()))
            if entry:
                report = CVELookup.format_cve_report([entry], title=f"CVE: {entry.cve_id}")
                for chunk in split_message(report):
                    await update.message.reply_text(format_html(chunk), parse_mode=ParseMode.HTML)
            else:
                await update.message.reply_text(f"CVE not found: {query.strip()}")
        else:
            cves = await loop.run_in_executor(None, lambda: cve_engine.search_cve(query, max_results=10))
            report = CVELookup.format_cve_report(cves, title=f"CVE Search: {query}")
            for chunk in split_message(report):
                await update.message.reply_text(format_html(chunk), parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"❌ CVE lookup error: {e}")


async def cmd_osint(bot: "HackBotTelegram", update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    domain = " ".join(context.args) if context.args else ""
    if not domain:
        await update.message.reply_text("Usage: <code>/osint example.com</code>", parse_mode=ParseMode.HTML)
        return

    await update.message.chat.send_action(ChatAction.TYPING)
    osint = OSINTEngine()
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, lambda: osint.full_scan(domain))
        report = osint.format_report(result)
        for chunk in split_message(report):
            await update.message.reply_text(format_html(chunk), parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"❌ OSINT error: {e}")


async def cmd_compliance(bot: "HackBotTelegram", update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = bot._get_session(update.effective_user.id)
    if not session.agent_mode or not session.agent_mode.findings:
        await update.message.reply_text("No findings to map. Run an agent assessment first.")
        return

    findings = [f.to_dict() for f in session.agent_mode.findings]
    mapper = ComplianceMapper()
    loop = asyncio.get_event_loop()
    try:
        mappings = await loop.run_in_executor(None, lambda: mapper.map_findings(findings))
        report = mapper.format_report(mappings)
        for chunk in split_message(report):
            await update.message.reply_text(format_html(chunk), parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"❌ Compliance error: {e}")


async def cmd_attack(bot: "HackBotTelegram", update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /attack — MITRE ATT&CK mapping."""
    session = bot._get_session(update.effective_user.id)
    args = " ".join(context.args) if context.args else ""
    parts = args.split(maxsplit=1)
    subcmd = parts[0].lower() if parts else "map"
    sub_args = parts[1] if len(parts) > 1 else ""

    mapper = AttackMapper()

    if subcmd == "map":
        agent = session.agent_mode
        if not agent or not agent.findings:
            await update.message.reply_text("No findings to map. Run an agent assessment first.")
            return
        findings = [f.to_dict() for f in agent.findings]
        tool_history = [r.to_dict() for r in agent.runner.history]
        target_name = agent.target
        loop = asyncio.get_event_loop()
        try:
            report = await loop.run_in_executor(
                None, lambda: mapper.map_findings(findings, target=target_name, tool_history=tool_history),
            )
            text = mapper.format_summary(report)
            await update.message.reply_text(format_html(text), parse_mode=ParseMode.HTML)
        except Exception as e:
            await update.message.reply_text(f"❌ ATT&CK mapping error: {e}")

    elif subcmd == "full":
        agent = session.agent_mode
        if not agent or not agent.findings:
            await update.message.reply_text("No findings to map. Run an agent assessment first.")
            return
        findings = [f.to_dict() for f in agent.findings]
        tool_history = [r.to_dict() for r in agent.runner.history]
        target_name = agent.target
        loop = asyncio.get_event_loop()
        try:
            report = await loop.run_in_executor(
                None, lambda: mapper.map_findings(findings, target=target_name, tool_history=tool_history),
            )
            text = mapper.format_report(report)
            for chunk in split_message(text):
                await update.message.reply_text(format_html(chunk), parse_mode=ParseMode.HTML)
        except Exception as e:
            await update.message.reply_text(f"❌ ATT&CK mapping error: {e}")

    elif subcmd == "tactics":
        tactics = AttackMapper.list_tactics()
        lines = ["<b>MITRE ATT&CK Tactics</b>\n"]
        for tac in tactics:
            lines.append(f"<code>{tac['id']}</code> — {tac['name']}")
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

    elif subcmd == "tool":
        tool_name = sub_args.strip()
        if not tool_name:
            await update.message.reply_text("Usage: /attack tool <tool_name>")
            return
        techs = AttackMapper.get_tool_techniques(tool_name)
        if not techs:
            await update.message.reply_text(f"No ATT&CK mappings for tool: {tool_name}")
            return
        lines = [f"<b>ATT&CK Techniques: {format_html(tool_name)}</b>\n"]
        for item in techs:
            tech_dict: Dict[str, Any] = dict(item["technique"])
            lines.append(f"<code>{tech_dict['id']}</code> {tech_dict['name']} ({item['confidence']})")
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

    elif subcmd == "lookup":
        tech_id = sub_args.strip().upper()
        if not tech_id:
            await update.message.reply_text("Usage: /attack lookup <technique_id>")
            return
        tech_info: Optional[Dict[str, Any]] = AttackMapper.get_technique(tech_id)
        if not tech_info:
            await update.message.reply_text(f"Technique not found: {tech_id}")
            return
        await update.message.reply_text(
            f"<b>{tech_info['id']}</b> — {tech_info['name']}\n"
            f"Tactics: {', '.join(tech_info['tactic_ids'])}\n"
            f"URL: {tech_info['url']}",
            parse_mode=ParseMode.HTML,
        )

    else:
        await update.message.reply_text(
            "<b>/attack</b> — MITRE ATT&CK Mapping\n\n"
            "/attack map — Map agent findings (summary)\n"
            "/attack full — Full ATT&CK report\n"
            "/attack tactics — List all tactics\n"
            "/attack tool &lt;name&gt; — Tool technique map\n"
            "/attack lookup &lt;id&gt; — Look up technique",
            parse_mode=ParseMode.HTML,
        )


# ── Settings ─────────────────────────────────────────────────────────────────

async def cmd_model(bot: "HackBotTelegram", update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    model = " ".join(context.args) if context.args else ""
    if not model:
        preset = PROVIDERS.get(bot.config.ai.provider, {})
        models = preset.get("models", [])
        if models:
            lines = [f"<b>Models for {bot.config.ai.provider}:</b>\n"]
            for m in models:
                current = " ◀" if m["id"] == bot.config.ai.model else ""
                lines.append(f"<code>{m['id']}</code> — {m['name']}{current}")
            await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text("No model list available for current provider.")
        return

    from hackbot.core.engine import AIEngine
    bot.config.ai.model = model
    bot.engine = AIEngine(bot.config.ai)
    bot._refresh_all_sessions()
    save_config(bot.config)
    await update.message.reply_text(f"✅ Model set to: <code>{model}</code>", parse_mode=ParseMode.HTML)


async def cmd_provider(bot: "HackBotTelegram", update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    provider = " ".join(context.args).lower() if context.args else ""
    if not provider:
        lines = ["<b>Available providers:</b>\n"]
        for key, p in PROVIDERS.items():
            current = " ◀" if key == bot.config.ai.provider else ""
            lines.append(f"<code>{key}</code> — {p['name']}{current}")
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)
        return

    if provider not in PROVIDERS:
        await update.message.reply_text(f"❌ Unknown provider: {provider}")
        return

    from hackbot.core.engine import AIEngine
    bot.config.ai.provider = provider
    preset = PROVIDERS[provider]
    if preset["models"]:
        bot.config.ai.model = preset["models"][0]["id"]
    bot.engine = AIEngine(bot.config.ai)
    bot._refresh_all_sessions()
    save_config(bot.config)
    await update.message.reply_text(
        f"✅ Provider: <code>{preset['name']}</code>\n"
        f"Model: <code>{bot.config.ai.model}</code>",
        parse_mode=ParseMode.HTML,
    )


async def cmd_language(bot: "HackBotTelegram", update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = " ".join(context.args) if context.args else ""
    if not lang:
        current = bot.config.ui.language
        lines = [f"Current: <b>{current}</b>\n\n<b>Available:</b>\n"]
        for name, native in sorted(SUPPORTED_LANGUAGES.items()):
            marker = " ◀" if name == current else ""
            lines.append(f"<code>{name}</code> ({native}){marker}")
        text = "\n".join(lines)
        for chunk in split_message(text):
            await update.message.reply_text(chunk, parse_mode=ParseMode.HTML)
        return

    matched = None
    for name in SUPPORTED_LANGUAGES:
        if name.lower() == lang.lower():
            matched = name
            break
    if not matched:
        for name in SUPPORTED_LANGUAGES:
            if name.lower().startswith(lang.lower()):
                matched = name
                break
    if not matched:
        await update.message.reply_text(f"❌ Unknown language: {lang}\nUse /language to see all options.")
        return

    bot.config.ui.language = matched
    save_config(bot.config)
    bot._refresh_all_sessions()
    native = SUPPORTED_LANGUAGES[matched]
    await update.message.reply_text(
        f"✅ Language set to: <b>{matched}</b> ({native})", parse_mode=ParseMode.HTML
    )


async def cmd_config(bot: "HackBotTelegram", update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    preset = PROVIDERS.get(bot.config.ai.provider, {})
    provider_name = preset.get("name", bot.config.ai.provider)
    tools = detect_tools(bot.config.agent.allowed_tools)
    installed = sum(1 for v in tools.values() if v)
    total = len(tools)
    sample_tools = ", ".join(bot.config.agent.allowed_tools[:10])
    text = (
        f"⚙️ <b>HackBot Configuration</b>\n\n"
        f"<b>Provider:</b> {provider_name}\n"
        f"<b>Model:</b> <code>{bot.config.ai.model}</code>\n"
        f"<b>API Key:</b> {'✅ Set' if bot.config.ai.api_key else '❌ Not set'}\n"
        f"<b>Language:</b> {bot.config.ui.language}\n"
        f"<b>Safe Mode:</b> {'✅' if bot.config.agent.safe_mode else '❌'}\n"
        f"<b>Max Steps:</b> {bot.config.agent.max_steps}\n"
        f"<b>Temperature:</b> {bot.config.ai.temperature}\n"
        f"<b>Allowed Tools:</b> {installed}/{total} installed\n"
        f"<b>Tool Sample:</b> <code>{sample_tools}</code>\n"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_tools(bot: "HackBotTelegram", update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /tools — show installed/missing tools from allowed list."""
    view = " ".join(context.args).strip().lower() if context.args else "installed"
    if view not in ("installed", "missing", "all"):
        await update.message.reply_text(
            "Usage: /tools [installed|missing|all]",
            parse_mode=ParseMode.HTML,
        )
        return

    tools = detect_tools(bot.config.agent.allowed_tools)
    installed = [name for name, path in tools.items() if path]
    missing = [name for name, path in tools.items() if not path]

    if view == "installed":
        lines = [f"🧰 <b>Installed Tools</b> ({len(installed)}/{len(tools)})\n"]
        lines.extend(f"✅ <code>{name}</code>" for name in installed)
    elif view == "missing":
        lines = [f"🧰 <b>Missing Tools</b> ({len(missing)}/{len(tools)})\n"]
        lines.extend(f"❌ <code>{name}</code>" for name in missing)
    else:
        lines = [f"🧰 <b>Tool Inventory</b> ({len(installed)}/{len(tools)} installed)\n"]
        lines.append("<b>Installed:</b>")
        lines.extend(f"✅ <code>{name}</code>" for name in installed)
        lines.append("\n<b>Missing:</b>")
        lines.extend(f"❌ <code>{name}</code>" for name in missing)

    text = "\n".join(lines)
    for chunk in split_message(text):
        await update.message.reply_text(chunk, parse_mode=ParseMode.HTML)


# ── Session management ───────────────────────────────────────────────────────

async def cmd_reset(bot: "HackBotTelegram", update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bot._reset_session(update.effective_user.id)
    await update.message.reply_text("🔄 Session reset. Fresh start!")


async def cmd_logout(bot: "HackBotTelegram", update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /logout — disconnect the Telegram user from this HackBot instance."""
    user_id = update.effective_user.id
    if bot.pairing.revoke(user_id):
        bot.pairing.save()
        # Also clear their in-memory session
        if user_id in bot.sessions:
            del bot.sessions[user_id]
        await update.message.reply_text(
            "🚪 <b>Logged out successfully.</b>\n\n"
            "You've been disconnected from HackBot.\n"
            "To reconnect, run <code>hackbot telegram</code> on your "
            "machine and scan the QR code again.",
            parse_mode=ParseMode.HTML,
        )
    else:
        await update.message.reply_text(
            "You're not currently connected. Use /start to begin pairing."
        )


async def cmd_export(bot: "HackBotTelegram", update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = bot._get_session(update.effective_user.id)
    if not session.agent_mode or not session.agent_mode.findings:
        await update.message.reply_text("No findings to export.")
        return

    findings = [f.to_dict() for f in session.agent_mode.findings]
    tool_history = [r.to_dict() for r in session.agent_mode.runner.history]
    scripts = [s.to_dict() for s in session.agent_mode.scripts]

    reporter = ReportGenerator(report_format="markdown")
    report = reporter.generate(
        target=session.agent_mode.target,
        findings=findings,
        tool_history=tool_history,
        scripts=scripts,
    )

    buf = io.BytesIO(report.encode("utf-8"))
    buf.name = f"hackbot_report_{int(time.time())}.md"
    await update.message.reply_document(
        document=buf, caption=f"📊 HackBot Report — {session.agent_mode.target}"
    )


async def cmd_version(bot: "HackBotTelegram", update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    plat = detect_platform()
    await update.message.reply_text(
        f"🤖 <b>HackBot</b> v{__version__}\n"
        f"Developer: Yashab Alam\n"
        f"Platform: {plat['system']} {plat['machine']}\n"
        f"Python: {plat['python']}",
        parse_mode=ParseMode.HTML,
    )


async def cmd_status(bot: "HackBotTelegram", update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = bot._get_session(update.effective_user.id)
    tools = detect_tools(bot.config.agent.allowed_tools)
    installed = sum(1 for v in tools.values() if v)
    total = len(tools)

    await update.message.reply_text(
        f"📡 <b>HackBot Status</b>\n\n"
        f"🟢 Bot: Connected\n"
        f"Mode: <b>{session.mode.upper()}</b>\n"
        f"Provider: {bot.config.ai.provider}/{bot.config.ai.model}\n"
        f"API Key: {'✅' if bot.engine.is_configured() else '❌'}\n"
        f"Language: {bot.config.ui.language}\n"
        f"Tools: {installed}/{total} installed\n"
        f"Agent: {'🟢 Running' if session.agent_mode and session.agent_mode.is_running else '⚪ Idle'}\n"
        f"Findings: {len(session.agent_mode.findings) if session.agent_mode else 0}",
        parse_mode=ParseMode.HTML,
    )


async def cmd_vulndb(bot: "HackBotTelegram", update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /vulndb — query the vulnerability database."""
    args = " ".join(context.args) if context.args else ""
    parts = args.split(maxsplit=1)
    subcmd = parts[0].lower() if parts else "stats"
    sub_args = parts[1] if len(parts) > 1 else ""

    db = VulnDB()

    if subcmd == "stats":
        stats = db.get_stats(sub_args)
        sev_lines = []
        for sev in ("Critical", "High", "Medium", "Low", "Info"):
            c = stats.by_severity.get(sev, 0)
            if c > 0:
                icon = {"Critical": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🔵", "Info": "⚪"}.get(sev, "•")
                sev_lines.append(f"  {icon} {sev}: {c}")
        sev_text = "\n".join(sev_lines) if sev_lines else "  None"

        await update.message.reply_text(
            f"📊 <b>Vulnerability Database</b>\n\n"
            f"Assessments: {stats.total_assessments}\n"
            f"Targets: {stats.unique_targets}\n"
            f"Findings: {stats.total_findings}\n"
            f"Risk Score: {stats.overall_risk_score:.1f}\n\n"
            f"<b>By Severity:</b>\n{sev_text}\n\n"
            f"🔓 Open: {stats.open_findings}\n"
            f"🔧 In Progress: {stats.in_progress_findings}\n"
            f"✅ Resolved: {stats.resolved_findings}\n\n"
            f"DB Size: {db.db_size}",
            parse_mode=ParseMode.HTML,
        )

    elif subcmd == "search":
        if not sub_args:
            await update.message.reply_text("Usage: /vulndb search <query>")
            return
        results = db.search_findings(query=sub_args, limit=20)
        if not results:
            await update.message.reply_text(f"No findings matching '{sub_args}'")
            return
        lines = [f"🔍 <b>Search: {format_html(sub_args)}</b> ({len(results)} results)\n"]
        icons = {"Critical": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🔵", "Info": "⚪"}
        for f in results[:20]:
            icon = icons.get(f.severity, "•")
            lines.append(f"{icon} #{f.id} <b>{format_html(f.title)}</b> [{f.severity}] — {f.status}")
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

    elif subcmd == "open":
        results = db.search_findings(status="open", limit=20)
        if not results:
            await update.message.reply_text("✅ No open findings!")
            return
        lines = [f"🔓 <b>Open Findings</b> ({len(results)})\n"]
        icons = {"Critical": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🔵", "Info": "⚪"}
        for f in results:
            icon = icons.get(f.severity, "•")
            lines.append(f"{icon} #{f.id} <b>{format_html(f.title)}</b> [{f.severity}] — {f.target}")
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

    elif subcmd == "status" and sub_args:
        status_parts = sub_args.split(maxsplit=2)
        if len(status_parts) < 2 or not status_parts[0].isdigit():
            await update.message.reply_text(
                "Usage: /vulndb status <id> <open|in_progress|resolved|accepted|false_positive>"
            )
            return
        fid = int(status_parts[0])
        new_status = status_parts[1]
        note = status_parts[2] if len(status_parts) > 2 else ""
        try:
            ok = db.update_status(fid, new_status, note=note, changed_by="telegram")
            if ok:
                await update.message.reply_text(f"✅ Finding #{fid} → <b>{new_status}</b>", parse_mode=ParseMode.HTML)
            else:
                await update.message.reply_text(f"❌ Finding #{fid} not found")
        except ValueError as e:
            await update.message.reply_text(f"❌ {e}")

    else:
        await update.message.reply_text(
            "📊 <b>Vulnerability Database</b>\n\n"
            "<b>Commands:</b>\n"
            "/vulndb stats — Statistics\n"
            "/vulndb search &lt;query&gt; — Search\n"
            "/vulndb open — Open findings\n"
            "/vulndb status &lt;id&gt; &lt;state&gt; — Update status",
            parse_mode=ParseMode.HTML,
        )


# ── Inline keyboard callback ────────────────────────────────────────────────

async def callback_handler(bot: "HackBotTelegram", update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    if not bot.pairing.is_authorized(user_id):
        await query.edit_message_text("🔒 Not authorized.")
        return

    data = query.data
    session = bot._get_session(user_id)

    if data == "mode_chat":
        session.mode = "chat"
        await query.edit_message_text("💬 Switched to <b>Chat Mode</b>", parse_mode=ParseMode.HTML)
    elif data == "mode_agent":
        session.mode = "agent"
        await query.edit_message_text(
            "🤖 <b>Agent Mode</b>\nSend /agent &lt;target&gt; to start an assessment.",
            parse_mode=ParseMode.HTML,
        )
    elif data == "mode_plan":
        session.mode = "plan"
        await query.edit_message_text(
            "📋 <b>Plan Mode</b>\nSend /plan &lt;target&gt; to generate a plan.",
            parse_mode=ParseMode.HTML,
        )
    elif data == "settings":
        await query.edit_message_text(
            f"⚙️ <b>Settings</b>\n\n"
            f"Provider: {bot.config.ai.provider}\n"
            f"Model: {bot.config.ai.model}\n"
            f"Language: {bot.config.ui.language}\n\n"
            f"Use /model, /provider, /language to change.",
            parse_mode=ParseMode.HTML,
        )
    elif data == "help":
        await query.edit_message_text("Type /help to see all available commands.")
    elif data == "logout":
        bot.pairing.revoke(user_id)
        bot.pairing.save()
        if user_id in bot.sessions:
            del bot.sessions[user_id]
        await query.edit_message_text(
            "🚪 <b>Logged out.</b>\n\n"
            "Run <code>hackbot telegram</code> on your machine "
            "and scan the QR code to reconnect.",
            parse_mode=ParseMode.HTML,
        )


# ── Free-text message handler ────────────────────────────────────────────────

async def message_handler(bot: "HackBotTelegram", update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route plain text to the active mode (chat / agent / plan)."""
    user_id = update.effective_user.id
    if not bot.pairing.is_authorized(user_id):
        await update.message.reply_text(
            "🔒 Not authorized. Run <code>hackbot telegram</code> on your "
            "machine and scan the QR code.",
            parse_mode=ParseMode.HTML,
        )
        return

    session = bot._get_session(user_id)
    text = update.message.text.strip()
    if not text:
        return

    if not bot.engine.is_configured():
        await update.message.reply_text(
            "❌ API key not configured.\n"
            "Set HACKBOT_API_KEY on your machine or use /config."
        )
        return

    await update.message.chat.send_action(ChatAction.TYPING)
    loop = asyncio.get_event_loop()

    try:
        chat_mode = session.chat_mode or ChatMode(engine=bot.engine, config=bot.config)
        session.chat_mode = chat_mode
        plan_mode = session.plan_mode or PlanMode(engine=bot.engine, config=bot.config)
        session.plan_mode = plan_mode
        agent_mode = session.agent_mode

        if session.mode == "chat":
            response = await loop.run_in_executor(
                None, lambda: chat_mode.ask(text, stream=False)
            )
        elif session.mode == "agent":
            if agent_mode and agent_mode.is_running:
                response, is_complete = await loop.run_in_executor(
                    None, lambda: agent_mode.step(text)
                )
                if is_complete:
                    response += "\n\n✅ Assessment complete!"
            else:
                response = await loop.run_in_executor(
                    None, lambda: chat_mode.ask(text, stream=False)
                )
        elif session.mode == "plan":
            response = await loop.run_in_executor(
                None, lambda: plan_mode.ask(text, stream=False)
            )
        else:
            response = await loop.run_in_executor(
                None, lambda: chat_mode.ask(text, stream=False)
            )

        for chunk in split_message(response):
            await update.message.reply_text(format_html(chunk), parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error("Message handler error: %s", e)
        await update.message.reply_text(f"❌ Error: {e}")
