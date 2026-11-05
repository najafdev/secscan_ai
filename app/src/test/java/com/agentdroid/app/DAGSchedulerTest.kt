package com.agentdroid.app

import com.agentdroid.app.domain.model.*
import com.agentdroid.app.domain.orchestrator.DAGScheduler
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

class DAGSchedulerTest {

    private lateinit var scheduler: DAGScheduler

    @Before
    fun setUp() {
        scheduler = DAGScheduler()
    }

    @Test
    fun testReadyTasksIdentification() {
        val t1 = TaskItem("task_1", "plan_1", AgentRole.RESEARCH, "Research", "Explore topic", status = TaskStatus.PENDING)
        val t2 = TaskItem("task_2", "plan_1", AgentRole.CONTENT_CREATION, "Content", "Write copy", dependsOn = listOf("task_1"), status = TaskStatus.PENDING)
        val t3 = TaskItem("task_3", "plan_1", AgentRole.PRODUCTIVITY, "Schedule", "Add to calendar", dependsOn = listOf("task_2"), status = TaskStatus.PENDING)

        val initialTasks = listOf(t1, t2, t3)

        // Initially, only t1 has no dependencies
        val readyInitially = scheduler.getReadyTasks(initialTasks)
        assertEquals(1, readyInitially.size)
        assertEquals("task_1", readyInitially[0].id)

        // After t1 completes, t2 should become ready
        val afterT1 = listOf(t1.copy(status = TaskStatus.COMPLETED), t2, t3)
        val readyAfterT1 = scheduler.getReadyTasks(afterT1)
        assertEquals(1, readyAfterT1.size)
        assertEquals("task_2", readyAfterT1[0].id)

        // After t2 completes, t3 should become ready
        val afterT2 = listOf(t1.copy(status = TaskStatus.COMPLETED), t2.copy(status = TaskStatus.COMPLETED), t3)
        val readyAfterT2 = scheduler.getReadyTasks(afterT2)
        assertEquals(1, readyAfterT2.size)
        assertEquals("task_3", readyAfterT2[0].id)
    }

    @Test
    fun testParallelTaskDetection() {
        val t1 = TaskItem("task_1", "plan_1", AgentRole.RESEARCH, "Research A", "Topic A", status = TaskStatus.PENDING)
        val t2 = TaskItem("task_2", "plan_1", AgentRole.RESEARCH, "Research B", "Topic B", status = TaskStatus.PENDING)
        val t3 = TaskItem("task_3", "plan_1", AgentRole.CONTENT_CREATION, "Synthesize", "Merge both", dependsOn = listOf("task_1", "task_2"), status = TaskStatus.PENDING)

        val tasks = listOf(t1, t2, t3)
        val ready = scheduler.getReadyTasks(tasks)

        // Both t1 and t2 can run in parallel
        assertEquals(2, ready.size)
        assertTrue(ready.any { it.id == "task_1" })
        assertTrue(ready.any { it.id == "task_2" })
    }

    @Test
    fun testPlanCompletion() {
        val t1 = TaskItem("task_1", "plan_1", AgentRole.RESEARCH, "R", "D", status = TaskStatus.COMPLETED)
        val t2 = TaskItem("task_2", "plan_1", AgentRole.CONTENT_CREATION, "C", "D", status = TaskStatus.COMPLETED)

        assertTrue(scheduler.isPlanComplete(listOf(t1, t2)))

        val incomplete = listOf(t1, t2.copy(status = TaskStatus.RUNNING))
        assertFalse(scheduler.isPlanComplete(incomplete))
    }

    @Test
    fun testSkippingOnUnrecoverableFailure() {
        val t1 = TaskItem("task_1", "plan_1", AgentRole.RESEARCH, "R", "D", status = TaskStatus.FAILED, retryCount = 2, maxRetries = 2)
        val t2 = TaskItem("task_2", "plan_1", AgentRole.CONTENT_CREATION, "C", "D", dependsOn = listOf("task_1"), status = TaskStatus.PENDING)

        val tasks = listOf(t1, t2)
        assertTrue(scheduler.hasUnrecoverableFailure(tasks))

        val updated = scheduler.markSkippedTasks(tasks)
        assertEquals(TaskStatus.SKIPPED, updated[1].status)
    }
}
