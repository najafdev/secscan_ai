package com.agentdroid.app.domain.orchestrator

import com.agentdroid.app.domain.model.TaskItem
import com.agentdroid.app.domain.model.TaskStatus

class DAGScheduler {

    /**
     * Finds tasks that are PENDING and whose dependencies have all completed successfully.
     */
    fun getReadyTasks(tasks: List<TaskItem>): List<TaskItem> {
        val completedTaskIds = tasks.filter { it.status == TaskStatus.COMPLETED }.map { it.id }.toSet()
        return tasks.filter { task ->
            task.status == TaskStatus.PENDING && task.dependsOn.all { depId -> completedTaskIds.contains(depId) }
        }
    }

    /**
     * Checks if the entire graph has finished executing.
     */
    fun isPlanComplete(tasks: List<TaskItem>): Boolean {
        return tasks.all {
            it.status == TaskStatus.COMPLETED ||
            it.status == TaskStatus.FAILED ||
            it.status == TaskStatus.SKIPPED ||
            it.status == TaskStatus.CANCELLED
        }
    }

    /**
     * Checks if any task has critically failed with no remaining retries, preventing dependent tasks from running.
     */
    fun hasUnrecoverableFailure(tasks: List<TaskItem>): Boolean {
        val failedIds = tasks.filter { it.status == TaskStatus.FAILED && it.retryCount >= it.maxRetries }.map { it.id }.toSet()
        if (failedIds.isEmpty()) return false
        // Check if pending tasks depend on a permanently failed task
        return tasks.any { task ->
            task.status == TaskStatus.PENDING && task.dependsOn.any { failedIds.contains(it) }
        }
    }

    /**
     * Marks pending tasks as SKIPPED if they depend on failed tasks.
     */
    fun markSkippedTasks(tasks: List<TaskItem>): List<TaskItem> {
        val failedOrSkippedIds = tasks.filter { it.status == TaskStatus.FAILED || it.status == TaskStatus.SKIPPED }.map { it.id }.toSet()
        return tasks.map { task ->
            if (task.status == TaskStatus.PENDING && task.dependsOn.any { failedOrSkippedIds.contains(it) }) {
                task.copy(status = TaskStatus.SKIPPED, error = "Dependency failed or skipped.")
            } else {
                task
            }
        }
    }
}
