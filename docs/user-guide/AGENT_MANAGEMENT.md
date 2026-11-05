---
title: Agent Management & Custom Agent Builder
purpose: Guide to inspecting the agent fleet, toggling agents, and building custom agents
scope: AgentsDashboardScreen and CustomAgentBuilderScreen
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/architecture/MULTI_AGENT_ARCHITECTURE.md
  - docs/user-guide/MODEL_SELECTION.md
---

# Agent Management & Custom Agent Builder

## 1. Inspecting the Agent Fleet

Tap **Agents** in the bottom navigation bar to open the **Agents Dashboard**:
* Shows all 11 agents in your system.
* Displays their current state (`IDLE`, `RUNNING`, `WAITING`), their assigned AI model, and their capability tags.
* Tap any agent card to open the **Agent Details Inspector**, which displays:
  * Full system description
  * Tool suite
  * Required Android permissions
  * Execution history and recent activity logs

---

## 2. Enabling or Disabling Agents

If you do not want the Master Agent to delegate tasks to a particular agent (for example, disabling `Social Media Agent` during quiet hours):
1. In the **Agents Dashboard**, locate the target agent card.
2. Toggle the switch to **Disabled**.
3. When the Master Agent decomposes future goals, it excludes disabled agents from its delegation roster.

---

## 3. Creating a Custom Agent

AgentDroid allows you to build custom specialized agents without writing code:
1. In the **Agents Dashboard**, tap **Create Custom Agent** (`+` button).
2. Enter the **Agent Name** (e.g. *"Python Code Auditor"*).
3. Select an **Icon** and **Color** theme.
4. Define the **Custom System Prompt** (e.g. *"You are an expert Python security auditor. Review code snippets for OWASP vulnerabilities and suggest PEP 8 refactorings."*).
5. Select the required **Capabilities** (`Text Generation`, `Tool Calling`, `Reasoning`).
6. Tap **Create Agent**. Your custom agent is instantly saved to Room DB and made available to the Master Agent.
