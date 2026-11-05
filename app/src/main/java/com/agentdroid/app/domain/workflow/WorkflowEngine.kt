package com.agentdroid.app.domain.workflow

import android.content.Context
import androidx.work.Constraints
import androidx.work.Data
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import com.agentdroid.app.data.local.dao.WorkflowDao
import com.agentdroid.app.data.local.entity.WorkflowEntity
import com.agentdroid.app.domain.model.TriggerType
import com.agentdroid.app.domain.model.Workflow
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import java.util.UUID
import java.util.concurrent.TimeUnit

class WorkflowEngine(
    private val context: Context,
    private val workflowDao: WorkflowDao
) {
    private val workManager = WorkManager.getInstance(context)

    fun getAllWorkflows(): Flow<List<Workflow>> {
        return workflowDao.getAllWorkflows().map { entities ->
            entities.map { it.toDomain() }
        }
    }

    suspend fun createWorkflow(
        title: String,
        prompt: String,
        triggerType: TriggerType = TriggerType.MANUAL,
        cronSchedule: String? = null
    ): Workflow {
        val id = UUID.randomUUID().toString()
        val entity = WorkflowEntity(
            id = id,
            title = title,
            prompt = prompt,
            triggerType = triggerType.name,
            cronSchedule = cronSchedule,
            isEnabled = true
        )
        workflowDao.insertWorkflow(entity)

        if (triggerType == TriggerType.SCHEDULED) {
            schedulePeriodicWork(id)
        }

        return entity.toDomain()
    }

    suspend fun toggleWorkflow(id: String, enabled: Boolean) {
        workflowDao.setWorkflowEnabled(id, enabled)
        if (!enabled) {
            workManager.cancelAllWorkByTag("workflow_$id")
        } else {
            schedulePeriodicWork(id)
        }
    }

    suspend fun deleteWorkflow(id: String) {
        val entity = workflowDao.getWorkflowById(id) ?: return
        workManager.cancelAllWorkByTag("workflow_$id")
        workflowDao.deleteWorkflow(entity)
    }

    private fun schedulePeriodicWork(workflowId: String) {
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()

        val inputData = Data.Builder()
            .putString(AgentDroidWorker.KEY_WORKFLOW_ID, workflowId)
            .build()

        val workRequest = PeriodicWorkRequestBuilder<AgentDroidWorker>(24, TimeUnit.HOURS)
            .setConstraints(constraints)
            .setInputData(inputData)
            .addTag("workflow_$workflowId")
            .build()

        workManager.enqueue(workRequest)
    }

    private fun WorkflowEntity.toDomain(): Workflow {
        val triggerEnum = try { TriggerType.valueOf(triggerType) } catch (e: Exception) { TriggerType.MANUAL }
        return Workflow(
            id = id,
            title = title,
            prompt = prompt,
            triggerType = triggerEnum,
            cronSchedule = cronSchedule,
            isEnabled = isEnabled,
            lastRun = lastRun,
            nextRun = nextRun,
            executionCount = executionCount
        )
    }
}
