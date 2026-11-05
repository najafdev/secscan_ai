---
title: Master Agent Architecture
purpose: Detailed specification of the central Master Agent controller, prompting strategy, and coordination mechanics
scope: MasterAgent class and orchestration subsystem
applicable_version: v1.0.0
last_updated: 2026-11-01
status: IMPLEMENTED
cross_references:
  - docs/architecture/MULTI_AGENT_ARCHITECTURE.md
  - docs/architecture/TASK_ORCHESTRATION.md
---

# Master Agent Architecture

## Responsibilities

The **Master Agent** (`com.agentdroid.app.domain.agent.MasterAgent`) acts as the central brain of AgentDroid OS. It is responsible for:
1. **Natural Language Understanding (NLU)**: Parsing ambiguous user requests into structured intents.
2. **Task Decomposition**: Breaking user goals into discrete, logical subtasks assigned to specialized agent roles.
3. **Dependency Graph Construction**: Determining execution order and data dependencies (`dependsOn`).
4. **Risk Categorization**: Assigning initial risk levels (`LOW`, `MEDIUM`, `HIGH`) to each subtask.
5. **Execution Supervision**: Monitoring progress updates emitted by executing agents.
6. **Executive Report Synthesis**: Aggregating outputs from all completed subtasks into a unified executive summary for the user.

---

## Decomposition Prompt Structure

When the user submits a goal, `MasterAgent.decomposeGoal()` injects the available agent roles into a structured system prompt, mandating a strict JSON array response:

```json
[
  {
    "title": "Analyze Competitor Pricing",
    "agentRole": "RESEARCH",
    "description": "Extract pricing tiers for competitor X and competitor Y.",
    "riskLevel": "LOW",
    "actionType": "EXECUTE_CUSTOM_TOOL"
  },
  {
    "title": "Draft Strategic Comparison",
    "agentRole": "CONTENT_CREATION",
    "description": "Draft a side-by-side pricing analysis based on research outputs.",
    "riskLevel": "LOW",
    "actionType": "EXECUTE_CUSTOM_TOOL"
  },
  {
    "title": "Publish Pricing Note to Team",
    "agentRole": "COMMUNICATION",
    "description": "Send drafted comparison note to team channel via email.",
    "riskLevel": "HIGH",
    "actionType": "SEND_EMAIL"
  }
]
```

`HttpAiProvider.parseTasksFromJson()` transforms this JSON into strongly-typed `TaskItem` domain objects, automatically linking consecutive dependent IDs (`task_plan_1` $\rightarrow$ `task_plan_2`).

---

## Synthesis Reporting

Upon plan completion, `MasterAgent.synthesizeReport()` compiles all subtask output summaries:

$$\text{Task Summaries} = \sum_{i=1}^{N} \left( \text{AgentRole}_i + \text{Title}_i + \text{OutputData}_i \right)$$

This context is passed to the resolved AI model with instructions to generate a concise, professional executive briefing formatted in GitHub-flavored Markdown.
