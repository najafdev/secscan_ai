package com.agentdroid.app.ai.provider

import com.agentdroid.app.domain.model.ActionType
import com.agentdroid.app.domain.model.AgentRole
import com.agentdroid.app.domain.model.RiskLevel
import com.agentdroid.app.domain.model.TaskItem
import com.agentdroid.app.domain.model.TaskStatus
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import java.util.UUID

@Deprecated(
    message = "Development and test fixture only. Strict Real AI Mode prohibits mock AI in production.",
    level = DeprecationLevel.WARNING
)
class AutonomousMockProvider : AiProvider {
    override val providerId: String = "prov_autonomous"
    override val displayName: String = "AgentDroid Autonomous Engine"

    override suspend fun generateResponse(
        prompt: String,
        systemPrompt: String,
        model: String,
        temperature: Float,
        maxTokens: Int
    ): AiResponse {
        val lowerPrompt = prompt.lowercase()
        val content = when {
            lowerPrompt.contains("social") || lowerPrompt.contains("post") || lowerPrompt.contains("twitter") || lowerPrompt.contains("linkedin") -> {
                "AgentDroid Social Intelligence generated 3 targeted campaigns across X, LinkedIn, and Instagram focusing on autonomous AI agents, enterprise automation, and user privacy."
            }
            lowerPrompt.contains("competitor") || lowerPrompt.contains("research") -> {
                "Conducted competitive landscape analysis across 5 mobile AI assistants. Key differentiators identified: Local accessibility automation, multi-agent DAG orchestration, and zero-trust human-in-the-loop governance."
            }
            lowerPrompt.contains("schedule") || lowerPrompt.contains("productivity") || lowerPrompt.contains("calendar") -> {
                "Synthesized dynamic workday schedule: 09:00 Deep Work (AI Architecture), 11:30 Standup & Sprint Sync, 14:00 Agent Evaluation, 16:30 Automated Social Review."
            }
            lowerPrompt.contains("file") || lowerPrompt.contains("pdf") || lowerPrompt.contains("clean") -> {
                "Catalogued 42 device documents, tagged 3 duplicate PDF downloads, and indexed storage usage into /Documents/AgentDroid_Audit.txt."
            }
            lowerPrompt.contains("security") || lowerPrompt.contains("permission") || lowerPrompt.contains("phish") -> {
                "Security Audit Complete: Accessibility service permissions verified within safe boundaries. Zero prompt injection vectors detected in untrusted inputs. All high-risk actions queued for human authorization."
            }
            else -> {
                "AgentDroid AI Engine evaluated command: \"$prompt\". Multi-agent execution strategy optimized across agent roles."
            }
        }

        return AiResponse(
            content = content,
            promptTokens = prompt.length / 4,
            completionTokens = content.length / 4,
            totalTokens = (prompt.length + content.length) / 4,
            modelUsed = "agentdroid-autonomous-v1"
        )
    }

    override fun streamResponse(
        prompt: String,
        systemPrompt: String,
        model: String,
        temperature: Float
    ): Flow<String> = flow {
        val tokens = listOf(
            "AgentDroid ", "Master ", "Agent ", "activated. ",
            "Analyzing ", "intent: ", "\"$prompt\". ",
            "Formulating ", "multi-agent ", "execution ", "graph...\n\n",
            "Agents ", "dispatched ", "to ", "shared ", "context. ",
            "All ", "subtasks ", "orchestrated ", "successfully."
        )
        for (token in tokens) {
            delay(50)
            emit(token)
        }
    }

    override suspend fun decomposeUserGoal(
        userGoal: String,
        availableAgents: List<AgentRole>
    ): List<TaskItem> {
        val planId = UUID.randomUUID().toString()
        val lowerGoal = userGoal.lowercase()

        // Core Vision Workflow: "Manage my social media today. Create content, prepare posts, analyze engagement, and organize my replies."
        if (lowerGoal.contains("manage my social") || (lowerGoal.contains("social") && (lowerGoal.contains("replies") || lowerGoal.contains("engagement")))) {
            val t1 = TaskItem(
                id = "task_${planId}_1",
                planId = planId,
                agentRole = AgentRole.CONTENT_CREATION,
                title = "Create Content & Post Hooks",
                description = "Generate high-converting content ideas, hooks, and drafts for daily social publishing.",
                riskLevel = RiskLevel.LOW,
                actionType = ActionType.CREATE_FILE,
                toolName = "CopyDrafter"
            )
            val t2 = TaskItem(
                id = "task_${planId}_2",
                planId = planId,
                agentRole = AgentRole.SOCIAL_MEDIA,
                title = "Prepare Platform-Specific Posts",
                description = "Format posts for X, Instagram, and LinkedIn with hashtag strategies and media formatting.",
                dependsOn = listOf(t1.id),
                riskLevel = RiskLevel.MEDIUM,
                actionType = ActionType.POST_SOCIAL,
                toolName = "SocialComposer"
            )
            val t3 = TaskItem(
                id = "task_${planId}_3",
                planId = planId,
                agentRole = AgentRole.ANALYTICS,
                title = "Analyze Cross-Platform Engagement",
                description = "Synthesize impressions, interactions, follower growth, and optimal timing metrics.",
                dependsOn = listOf(t2.id),
                riskLevel = RiskLevel.LOW,
                actionType = ActionType.EXECUTE_CUSTOM_TOOL,
                toolName = "EngagementAnalyzer"
            )
            val t4 = TaskItem(
                id = "task_${planId}_4",
                planId = planId,
                agentRole = AgentRole.COMMUNICATION,
                title = "Organize & Prepare Replies to Priority Messages",
                description = "Triage mentions and unread direct messages, and prepare drafted replies awaiting user authorization.",
                dependsOn = listOf(t3.id),
                riskLevel = RiskLevel.HIGH,
                actionType = ActionType.SEND_EMAIL,
                toolName = "InboxTriager"
            )
            return listOf(t1, t2, t3, t4)
        }

        // Complex Multi-Agent Workflow Pattern 1: Social Media Campaign & Competitor Research
        if (lowerGoal.contains("competitor") || (lowerGoal.contains("social") && lowerGoal.contains("research"))) {
            val t1 = TaskItem(
                id = "task_${planId}_1",
                planId = planId,
                agentRole = AgentRole.RESEARCH,
                title = "Research Top 5 Competitors & Market Trends",
                description = "Extract key messaging, feature benchmarks, and engagement strategies of rival AI platforms.",
                riskLevel = RiskLevel.LOW,
                actionType = ActionType.OPEN_URL,
                toolName = "WebSearchEngine"
            )
            val t2 = TaskItem(
                id = "task_${planId}_2",
                planId = planId,
                agentRole = AgentRole.CONTENT_CREATION,
                title = "Create Strategic Marketing Copy & Hooks",
                description = "Draft 5 high-converting copy variations based on research findings.",
                dependsOn = listOf(t1.id),
                riskLevel = RiskLevel.LOW,
                actionType = ActionType.CREATE_FILE,
                toolName = "ContentDrafter"
            )
            val t3 = TaskItem(
                id = "task_${planId}_3",
                planId = planId,
                agentRole = AgentRole.SOCIAL_MEDIA,
                title = "Prepare 10 Platform-Specific Social Posts",
                description = "Format posts for X, LinkedIn, and Instagram with hashtags and media hooks.",
                dependsOn = listOf(t2.id),
                riskLevel = RiskLevel.MEDIUM,
                actionType = ActionType.POST_SOCIAL,
                toolName = "SocialComposer"
            )
            val t4 = TaskItem(
                id = "task_${planId}_4",
                planId = planId,
                agentRole = AgentRole.PRODUCTIVITY,
                title = "Organize Posts into Publishing Calendar",
                description = "Schedule posts across the upcoming week at peak engagement windows.",
                dependsOn = listOf(t3.id),
                riskLevel = RiskLevel.LOW,
                actionType = ActionType.CREATE_FILE,
                toolName = "CalendarScheduler"
            )
            return listOf(t1, t2, t3, t4)
        }

        // Pattern 2: Phone Control & Automation
        if (lowerGoal.contains("phone") || lowerGoal.contains("open") || lowerGoal.contains("app") || lowerGoal.contains("click")) {
            val t1 = TaskItem(
                id = "task_${planId}_1",
                planId = planId,
                agentRole = AgentRole.SECURITY,
                title = "Verify Automation Target & Device State",
                description = "Inspect target application safety, check overlay permissions, verify screen state.",
                riskLevel = RiskLevel.LOW,
                actionType = ActionType.READ_SCREEN,
                toolName = "StateInspector"
            )
            val t2 = TaskItem(
                id = "task_${planId}_2",
                planId = planId,
                agentRole = AgentRole.PHONE_CONTROL,
                title = "Automate UI Flow via Accessibility Service",
                description = "Locate target interactive nodes, simulate gestures, navigate requested screens.",
                dependsOn = listOf(t1.id),
                riskLevel = RiskLevel.MEDIUM,
                actionType = ActionType.CLICK_ELEMENT,
                toolName = "AccessibilityDriver"
            )
            val t3 = TaskItem(
                id = "task_${planId}_3",
                planId = planId,
                agentRole = AgentRole.PHONE_CONTROL,
                title = "Verify Resulting Device State & Screenshot",
                description = "Confirm the target state has been achieved and capture execution proof.",
                dependsOn = listOf(t2.id),
                riskLevel = RiskLevel.LOW,
                actionType = ActionType.TAKE_SCREENSHOT,
                toolName = "StateVerifier"
            )
            return listOf(t1, t2, t3)
        }

        // Pattern 3: Workday / Productivity Organization
        if (lowerGoal.contains("workday") || lowerGoal.contains("organize") || lowerGoal.contains("routine") || lowerGoal.contains("productivity")) {
            val t1 = TaskItem(
                id = "task_${planId}_1",
                planId = planId,
                agentRole = AgentRole.COMMUNICATION,
                title = "Triage Important Emails & Unread Messages",
                description = "Filter unread priority emails, extract pending action items and meeting invites.",
                riskLevel = RiskLevel.LOW,
                actionType = ActionType.READ_SCREEN,
                toolName = "InboxTriager"
            )
            val t2 = TaskItem(
                id = "task_${planId}_2",
                planId = planId,
                agentRole = AgentRole.FILE_MANAGEMENT,
                title = "Scan & Categorize Pending Work Documents",
                description = "Check Downloads folder for newly received attachments and sort into Project folders.",
                riskLevel = RiskLevel.LOW,
                actionType = ActionType.SEARCH_DEVICE,
                toolName = "FolderOrganizer"
            )
            val t3 = TaskItem(
                id = "task_${planId}_3",
                planId = planId,
                agentRole = AgentRole.PRODUCTIVITY,
                title = "Construct Optimized Workday Schedule & Tasks",
                description = "Build time-blocked schedule with reminders, focus blocks, and meeting slots.",
                dependsOn = listOf(t1.id, t2.id),
                riskLevel = RiskLevel.LOW,
                actionType = ActionType.CREATE_FILE,
                toolName = "DailyPlanner"
            )
            return listOf(t1, t2, t3)
        }

        // General Multi-Agent Default
        val t1 = TaskItem(
            id = "task_${planId}_1",
            planId = planId,
            agentRole = AgentRole.RESEARCH,
            title = "Analyze Requirements & Gather Context",
            description = "Explore background resources and establish context for: \"$userGoal\".",
            riskLevel = RiskLevel.LOW,
            actionType = ActionType.SEARCH_DEVICE,
            toolName = "ContextCollector"
        )
        val t2 = TaskItem(
            id = "task_${planId}_2",
            planId = planId,
            agentRole = AgentRole.CONTENT_CREATION,
            title = "Synthesize Solution & Generate Artifacts",
            description = "Execute primary work items fulfilling: \"$userGoal\".",
            dependsOn = listOf(t1.id),
            riskLevel = RiskLevel.LOW,
            actionType = ActionType.CREATE_FILE,
            toolName = "SynthesisEngine"
        )
        val t3 = TaskItem(
            id = "task_${planId}_3",
            planId = planId,
            agentRole = AgentRole.SECURITY,
            title = "Policy Compliance & Risk Verification",
            description = "Audit execution outputs against user privacy and security guardrails.",
            dependsOn = listOf(t2.id),
            riskLevel = RiskLevel.LOW,
            actionType = ActionType.READ_SCREEN,
            toolName = "PolicyAuditor"
        )
        return listOf(t1, t2, t3)
    }

    override suspend fun synthesizeReport(
        userGoal: String,
        completedTasks: List<TaskItem>
    ): String {
        val builder = java.lang.StringBuilder()
        builder.append("### AgentDroid Executive Summary\n\n")
        builder.append("**Goal:** $userGoal\n\n")
        builder.append("**Execution Summary:** All ${completedTasks.size} subtasks successfully completed across cooperating agents.\n\n")

        for (task in completedTasks) {
            builder.append("#### [${task.agentRole.displayName}] ${task.title}\n")
            val summary = task.outputData["summary"] ?: task.description
            builder.append("- **Status:** Completed\n")
            builder.append("- **Action:** ${task.actionType ?: "Custom Tool"}\n")
            builder.append("- **Output:** $summary\n\n")
        }

        builder.append("---\n*AgentDroid OS Multi-Agent Collaboration Engine*")
        return builder.toString()
    }

    override suspend fun testConnection(): Boolean = true
}
