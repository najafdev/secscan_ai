package com.agentdroid.app.domain.workflow

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.agentdroid.app.AgentDroidApplication

class AgentDroidWorker(
    appContext: Context,
    params: WorkerParameters
) : CoroutineWorker(appContext, params) {

    override suspend fun doWork(): Result {
        val workflowId = inputData.getString(KEY_WORKFLOW_ID) ?: return Result.failure()
        val app = applicationContext as? AgentDroidApplication ?: return Result.failure()

        val workflow = app.database.workflowDao().getWorkflowById(workflowId) ?: return Result.failure()
        if (!workflow.isEnabled) return Result.success()

        // Execute workflow prompt via Orchestrator
        try {
            app.orchestrator.startGoalExecution(workflow.prompt).collect {
                // Collect updates until completion
            }
            app.database.workflowDao().recordExecution(workflow.id, System.currentTimeMillis())
            return Result.success()
        } catch (e: Exception) {
            return Result.retry()
        }
    }

    companion object {
        const val KEY_WORKFLOW_ID = "workflow_id"
    }
}
