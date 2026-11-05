package com.agentdroid.app

import com.agentdroid.app.ai.provider.AutonomousMockProvider
import com.agentdroid.app.domain.model.AgentRole
import com.agentdroid.app.domain.model.TaskItem
import com.agentdroid.app.domain.model.TaskStatus
import kotlinx.coroutines.runBlocking
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

class AutonomousMockProviderTest {

    private lateinit var provider: AutonomousMockProvider

    @Before
    fun setUp() {
        provider = AutonomousMockProvider()
    }

    @Test
    fun testCoreVisionWorkflowSocialAnalyticsAndComm() = runBlocking {
        val userGoal = "Manage my social media today. Create content, prepare posts, analyze engagement, and organize my replies."
        val subtasks = provider.decomposeUserGoal(userGoal, AgentRole.entries)

        assertNotNull(subtasks)
        assertEquals(4, subtasks.size)

        // 1. Content Creation Agent
        assertEquals(AgentRole.CONTENT_CREATION, subtasks[0].agentRole)
        // 2. Social Media Agent
        assertEquals(AgentRole.SOCIAL_MEDIA, subtasks[1].agentRole)
        assertEquals(listOf(subtasks[0].id), subtasks[1].dependsOn)
        // 3. Analytics Agent
        assertEquals(AgentRole.ANALYTICS, subtasks[2].agentRole)
        assertEquals(listOf(subtasks[1].id), subtasks[2].dependsOn)
        // 4. Communication Agent
        assertEquals(AgentRole.COMMUNICATION, subtasks[3].agentRole)
        assertEquals(listOf(subtasks[2].id), subtasks[3].dependsOn)
        // High risk requires authorization
        assertEquals(com.agentdroid.app.domain.model.RiskLevel.HIGH, subtasks[3].riskLevel)
    }

    @Test
    fun testGoalDecompositionSocialAndCompetitor() = runBlocking {
        val userGoal = "Research five competitors, create a marketing strategy, prepare ten social media posts, and organize them into a calendar."
        val availableAgents = listOf(
            AgentRole.MASTER,
            AgentRole.RESEARCH,
            AgentRole.CONTENT_CREATION,
            AgentRole.SOCIAL_MEDIA,
            AgentRole.PRODUCTIVITY
        )

        val subtasks = provider.decomposeUserGoal(userGoal, availableAgents)

        assertNotNull(subtasks)
        assertEquals(4, subtasks.size)

        // Task 1: Research Agent
        assertEquals(AgentRole.RESEARCH, subtasks[0].agentRole)
        assertTrue(subtasks[0].dependsOn.isEmpty())

        // Task 2: Content Creation Agent
        assertEquals(AgentRole.CONTENT_CREATION, subtasks[1].agentRole)
        assertEquals(listOf(subtasks[0].id), subtasks[1].dependsOn)

        // Task 3: Social Media Agent
        assertEquals(AgentRole.SOCIAL_MEDIA, subtasks[2].agentRole)
        assertEquals(listOf(subtasks[1].id), subtasks[2].dependsOn)

        // Task 4: Productivity Agent
        assertEquals(AgentRole.PRODUCTIVITY, subtasks[3].agentRole)
        assertEquals(listOf(subtasks[2].id), subtasks[3].dependsOn)
    }

    @Test
    fun testPhoneAutomationDecomposition() = runBlocking {
        val userGoal = "Open app and click settings to verify state"
        val subtasks = provider.decomposeUserGoal(userGoal, AgentRole.entries)

        assertNotNull(subtasks)
        assertTrue(subtasks.any { it.agentRole == AgentRole.PHONE_CONTROL })
        assertTrue(subtasks.any { it.agentRole == AgentRole.SECURITY })
    }

    @Test
    fun testSynthesizeReport() = runBlocking {
        val completedTasks = listOf(
            TaskItem(
                id = "t1",
                planId = "p1",
                agentRole = AgentRole.RESEARCH,
                title = "Research",
                description = "Analyzed top 5 competitors",
                status = TaskStatus.COMPLETED,
                outputData = mapOf("summary" to "Competitor analysis completed with 5 platforms compared.")
            ),
            TaskItem(
                id = "t2",
                planId = "p1",
                agentRole = AgentRole.SOCIAL_MEDIA,
                title = "Social Posts",
                description = "Drafted 10 posts",
                status = TaskStatus.COMPLETED,
                outputData = mapOf("summary" to "Prepared 10 posts across X, LinkedIn, and Instagram.")
            )
        )

        val report = provider.synthesizeReport("Build social strategy", completedTasks)
        assertNotNull(report)
        assertTrue(report.contains("AgentDroid Executive Summary"))
        assertTrue(report.contains("Research Agent"))
        assertTrue(report.contains("Social Media Agent"))
    }
}
