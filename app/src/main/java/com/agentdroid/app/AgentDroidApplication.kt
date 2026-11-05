package com.agentdroid.app

import android.app.Application
import com.agentdroid.app.ai.connection.AiConnectionManager
import com.agentdroid.app.ai.router.AiModelRouter
import com.agentdroid.app.automation.action.ActionDispatcher
import com.agentdroid.app.data.local.database.AgentDroidDatabase
import com.agentdroid.app.data.local.preferences.SecurePreferencesManager
import com.agentdroid.app.domain.agent.*
import com.agentdroid.app.domain.memory.AgentMemoryManager
import com.agentdroid.app.domain.model.AgentRole
import com.agentdroid.app.domain.orchestrator.AgentOrchestrator
import com.agentdroid.app.domain.workflow.WorkflowEngine
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class AgentDroidApplication : Application() {

    lateinit var database: AgentDroidDatabase
        private set

    lateinit var securePreferences: SecurePreferencesManager
        private set

    lateinit var aiConnectionManager: AiConnectionManager
        private set

    lateinit var aiModelRouter: AiModelRouter
        private set

    lateinit var actionDispatcher: ActionDispatcher
        private set

    lateinit var masterAgent: MasterAgent
        private set

    lateinit var agentsMap: Map<AgentRole, Agent>
        private set

    lateinit var orchestrator: AgentOrchestrator
        private set

    lateinit var memoryManager: AgentMemoryManager
        private set

    lateinit var workflowEngine: WorkflowEngine
        private set

    lateinit var pluginRegistry: com.agentdroid.app.sdk.PluginRegistry
        private set

    override fun onCreate() {
        super.onCreate()
        instance = this

        database = AgentDroidDatabase.getInstance(this)
        securePreferences = SecurePreferencesManager(this)
        aiConnectionManager = AiConnectionManager(database.settingsDao(), securePreferences)
        aiModelRouter = AiModelRouter(database.settingsDao(), securePreferences, aiConnectionManager)
        actionDispatcher = ActionDispatcher(this)

        val activityLogDao = database.activityLogDao()

        masterAgent = MasterAgent(actionDispatcher, activityLogDao, aiModelRouter)
        val phoneAgent = PhoneControlAgent(actionDispatcher, activityLogDao)
        val socialAgent = SocialMediaAgent(actionDispatcher, activityLogDao, aiModelRouter)
        val contentAgent = ContentCreationAgent(actionDispatcher, activityLogDao, aiModelRouter)
        val researchAgent = ResearchAgent(actionDispatcher, activityLogDao, aiModelRouter)
        val commAgent = CommunicationAgent(actionDispatcher, activityLogDao, aiModelRouter)
        val fileAgent = FileManagementAgent(actionDispatcher, activityLogDao)
        val productivityAgent = ProductivityAgent(actionDispatcher, activityLogDao, aiModelRouter)
        val analyticsAgent = AnalyticsAgent(actionDispatcher, activityLogDao, aiModelRouter)
        val browserAgent = BrowserAgent(actionDispatcher, activityLogDao)
        val securityAgent = SecurityAgent(actionDispatcher, activityLogDao)

        agentsMap = mapOf(
            AgentRole.MASTER to masterAgent,
            AgentRole.PHONE_CONTROL to phoneAgent,
            AgentRole.SOCIAL_MEDIA to socialAgent,
            AgentRole.CONTENT_CREATION to contentAgent,
            AgentRole.RESEARCH to researchAgent,
            AgentRole.COMMUNICATION to commAgent,
            AgentRole.FILE_MANAGEMENT to fileAgent,
            AgentRole.PRODUCTIVITY to productivityAgent,
            AgentRole.ANALYTICS to analyticsAgent,
            AgentRole.BROWSER to browserAgent,
            AgentRole.SECURITY to securityAgent
        )

        orchestrator = AgentOrchestrator(
            context = this,
            masterAgent = masterAgent,
            agentsMap = agentsMap,
            taskDao = database.taskDao(),
            approvalDao = database.approvalDao(),
            activityLogDao = activityLogDao,
            aiConnectionManager = aiConnectionManager
        )

        memoryManager = AgentMemoryManager(database.memoryDao())
        workflowEngine = WorkflowEngine(this, database.workflowDao())

        pluginRegistry = com.agentdroid.app.sdk.PluginRegistry(this).apply {
            registerPlugin(com.agentdroid.app.sdk.extensions.VisionOcrAgentPlugin())
            registerPlugin(com.agentdroid.app.sdk.extensions.CodingAgentPlugin())
            registerPlugin(com.agentdroid.app.sdk.extensions.MeetingAssistantPlugin())
        }

        CoroutineScope(Dispatchers.IO).launch {
            AgentDroidDatabase.ensureDefaultDataSeeded(database)
            aiConnectionManager.refreshAllStatuses()
        }
    }

    companion object {
        lateinit var instance: AgentDroidApplication
            private set
    }
}
