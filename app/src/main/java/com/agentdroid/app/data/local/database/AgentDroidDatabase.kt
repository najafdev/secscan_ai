package com.agentdroid.app.data.local.database

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.sqlite.db.SupportSQLiteDatabase
import com.agentdroid.app.data.local.dao.*
import com.agentdroid.app.data.local.entity.*
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

@Database(
    entities = [
        AgentEntity::class,
        AgentConfigEntity::class,
        TaskEntity::class,
        TaskDependencyEntity::class,
        AgentExecutionEntity::class,
        ConversationEntity::class,
        MessageEntity::class,
        MemoryRecordEntity::class,
        WorkflowEntity::class,
        WorkflowStepEntity::class,
        ConnectedAccountEntity::class,
        ApiProviderEntity::class,
        ModelConfigEntity::class,
        DiscoveredModelEntity::class,
        PermissionEntity::class,
        ApprovalRequestEntity::class,
        ActivityLogEntity::class
    ],
    version = 2,
    exportSchema = false
)
abstract class AgentDroidDatabase : RoomDatabase() {

    abstract fun agentDao(): AgentDao
    abstract fun taskDao(): TaskDao
    abstract fun conversationDao(): ConversationDao
    abstract fun memoryDao(): MemoryDao
    abstract fun workflowDao(): WorkflowDao
    abstract fun approvalDao(): ApprovalDao
    abstract fun activityLogDao(): ActivityLogDao
    abstract fun accountDao(): AccountDao
    abstract fun settingsDao(): SettingsDao

    companion object {
        @Volatile
        private var INSTANCE: AgentDroidDatabase? = null

        fun getInstance(context: Context): AgentDroidDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    AgentDroidDatabase::class.java,
                    "agentdroid.db"
                )
                    .addCallback(DatabaseCallback())
                    .fallbackToDestructiveMigration()
                    .build()
                INSTANCE = instance
                instance
            }
        }

        suspend fun ensureDefaultDataSeeded(db: AgentDroidDatabase) {
            // Seed Default Master & Specialized Agents
            val defaultAgents = listOf(
                AgentEntity("agent_master", "Master Agent", "MASTER", "Central orchestrator for understanding requests, decomposing tasks, coordinating agents, and synthesizing reports."),
                AgentEntity("agent_phone", "Phone Control Agent", "PHONE_CONTROL", "Automates device actions, UI interactions via Accessibility, apps, and navigation."),
                AgentEntity("agent_social", "Social Media Agent", "SOCIAL_MEDIA", "Manages X, Instagram, LinkedIn, FB, Telegram, Discord, YouTube, Reddit; crafts posts and monitors engagement."),
                AgentEntity("agent_content", "Content Creation Agent", "CONTENT_CREATION", "Generates marketing ideas, articles, scripts, captions, and document summaries."),
                AgentEntity("agent_research", "Research Agent", "RESEARCH", "Conducts web intelligence, competitor analysis, topic investigation, and structured citations."),
                AgentEntity("agent_comm", "Communication Agent", "COMMUNICATION", "Drafts emails, synthesizes conversations, prepares replies, and triages notifications."),
                AgentEntity("agent_file", "File Management Agent", "FILE_MANAGEMENT", "Scans device storage, categorizes docs, detects duplicates, and summarizes PDFs."),
                AgentEntity("agent_productivity", "Productivity Agent", "PRODUCTIVITY", "Organizes tasks, reminders, daily schedules, project plans, and calendar items."),
                AgentEntity("agent_analytics", "Analytics Agent", "ANALYTICS", "Analyzes social media engagement, evaluates campaign performance, and tracks token expenditure."),
                AgentEntity("agent_browser", "Browser Agent", "BROWSER", "Executes multi-step web workflows, form interaction, extraction, and page summaries."),
                AgentEntity("agent_security", "Security Agent", "SECURITY", "Inspects links, audits app permissions, detects phishing, and enforces system security policies."),
                AgentEntity("plugin_vision_ocr", "Computer Vision & OCR Agent", "CUSTOM", "Extracts text from screenshots, analyzes documents, and detects UI elements using vision models.", isCustom = true),
                AgentEntity("plugin_coding_agent", "Coding & Shell Agent", "CUSTOM", "Specializes in Kotlin, Android Jetpack, code inspection, syntax analysis, and architecture debugging.", isCustom = true),
                AgentEntity("plugin_meeting_assistant", "Meeting & Calendar Assistant", "CUSTOM", "Extracts action items, prepares meeting agendas, summarizes audio transcripts, and drafts follow-up emails.", isCustom = true)
            )
            for (agent in defaultAgents) {
                if (db.agentDao().getAgentById(agent.id) == null) {
                    db.agentDao().insertAgent(agent)
                }
            }

            // Seed Default AI Providers (Strict Real AI Mode)
            val defaultProviders = listOf(
                ApiProviderEntity("prov_openai", "OPENAI", "OpenAI", "https://api.openai.com/v1", isEnabled = true),
                ApiProviderEntity("prov_gemini", "GEMINI", "Google Gemini", "https://generativelanguage.googleapis.com", isEnabled = true),
                ApiProviderEntity("prov_anthropic", "ANTHROPIC", "Anthropic Claude", "https://api.anthropic.com/v1", isEnabled = true),
                ApiProviderEntity("prov_ollama", "OLLAMA", "Ollama Local Daemon", "http://10.0.2.2:11434", isEnabled = false)
            )
            if (db.settingsDao().getAllProvidersSync().isEmpty()) {
                for (p in defaultProviders) {
                    db.settingsDao().insertProvider(p)
                }
            }

            // Seed Default Model Configurations mapped to real cloud/local providers
            val defaultConfigs = listOf(
                ModelConfigEntity("cfg_master", "MASTER", "prov_openai", "gpt-4o", 0.7f, 4096),
                ModelConfigEntity("cfg_phone", "PHONE_CONTROL", "prov_openai", "gpt-4o-mini", 0.2f, 2048),
                ModelConfigEntity("cfg_social", "SOCIAL_MEDIA", "prov_anthropic", "claude-3-5-sonnet", 0.8f, 2048),
                ModelConfigEntity("cfg_content", "CONTENT_CREATION", "prov_openai", "gpt-4o", 0.85f, 4096),
                ModelConfigEntity("cfg_research", "RESEARCH", "prov_gemini", "gemini-1.5-pro", 0.3f, 4096),
                ModelConfigEntity("cfg_comm", "COMMUNICATION", "prov_openai", "gpt-4o", 0.5f, 2048),
                ModelConfigEntity("cfg_file", "FILE_MANAGEMENT", "prov_gemini", "gemini-1.5-flash", 0.2f, 2048),
                ModelConfigEntity("cfg_productivity", "PRODUCTIVITY", "prov_anthropic", "claude-3-5-haiku", 0.3f, 2048),
                ModelConfigEntity("cfg_analytics", "ANALYTICS", "prov_openai", "gpt-4o-mini", 0.2f, 2048),
                ModelConfigEntity("cfg_browser", "BROWSER", "prov_openai", "gpt-4o", 0.3f, 2048),
                ModelConfigEntity("cfg_security", "SECURITY", "prov_anthropic", "claude-3-5-sonnet", 0.1f, 2048)
            )
            for (c in defaultConfigs) {
                if (db.settingsDao().getConfigForRole(c.agentRole) == null) {
                    db.settingsDao().insertModelConfig(c)
                }
            }

            // Seed Initial Cached Discovered Models
            val defaultDiscoveredModels = listOf(
                DiscoveredModelEntity("prov_openai:gpt-4o", "gpt-4o", "prov_openai", "GPT-4o Omnimodal", "CLOUD", "[\"TEXT_GENERATION\",\"STREAMING\",\"TOOL_CALLING\",\"STRUCTURED_OUTPUT\",\"VISION\",\"REASONING\"]", 128000, isAvailable = true, isLocal = false, isCached = true),
                DiscoveredModelEntity("prov_openai:gpt-4o-mini", "gpt-4o-mini", "prov_openai", "GPT-4o Mini Fast", "CLOUD", "[\"TEXT_GENERATION\",\"STREAMING\",\"TOOL_CALLING\",\"STRUCTURED_OUTPUT\",\"VISION\"]", 128000, isAvailable = true, isLocal = false, isCached = true),
                DiscoveredModelEntity("prov_openai:o1-preview", "o1-preview", "prov_openai", "o1 Reasoning Preview", "CLOUD", "[\"TEXT_GENERATION\",\"STREAMING\",\"REASONING\",\"STRUCTURED_OUTPUT\"]", 128000, isAvailable = true, isLocal = false, isCached = true),
                DiscoveredModelEntity("prov_gemini:gemini-1.5-pro", "gemini-1.5-pro", "prov_gemini", "Gemini 1.5 Pro Long-Context", "CLOUD", "[\"TEXT_GENERATION\",\"STREAMING\",\"TOOL_CALLING\",\"STRUCTURED_OUTPUT\",\"VISION\",\"REASONING\"]", 2000000, isAvailable = true, isLocal = false, isCached = true),
                DiscoveredModelEntity("prov_gemini:gemini-1.5-flash", "gemini-1.5-flash", "prov_gemini", "Gemini 1.5 Flash High-Speed", "CLOUD", "[\"TEXT_GENERATION\",\"STREAMING\",\"TOOL_CALLING\",\"STRUCTURED_OUTPUT\",\"VISION\"]", 1000000, isAvailable = true, isLocal = false, isCached = true),
                DiscoveredModelEntity("prov_anthropic:claude-3-5-sonnet-20241022", "claude-3-5-sonnet-20241022", "prov_anthropic", "Claude 3.5 Sonnet v2", "CLOUD", "[\"TEXT_GENERATION\",\"STREAMING\",\"TOOL_CALLING\",\"STRUCTURED_OUTPUT\",\"VISION\",\"REASONING\"]", 200000, isAvailable = true, isLocal = false, isCached = true),
                DiscoveredModelEntity("prov_anthropic:claude-3-5-haiku-20241022", "claude-3-5-haiku-20241022", "prov_anthropic", "Claude 3.5 Haiku Ultra-Fast", "CLOUD", "[\"TEXT_GENERATION\",\"STREAMING\",\"TOOL_CALLING\"]", 200000, isAvailable = true, isLocal = false, isCached = true),
                DiscoveredModelEntity("prov_ollama:llama3.2", "llama3.2", "prov_ollama", "Llama 3.2 Local", "LOCAL", "[\"TEXT_GENERATION\",\"STREAMING\",\"TOOL_CALLING\"]", 8192, isAvailable = false, isLocal = true, isCached = true)
            )
            if (db.settingsDao().getAllDiscoveredModelsSync().isEmpty()) {
                db.settingsDao().insertDiscoveredModels(defaultDiscoveredModels)
            }

            // Seed Initial Welcome Conversation
            if (db.conversationDao().getConversationCount() == 0) {
                val conv = ConversationEntity("conv_welcome", "Master AI Initial Session")
                db.conversationDao().insertConversation(conv)
                db.conversationDao().insertMessage(
                    MessageEntity(
                        id = "msg_init_welcome",
                        conversationId = "conv_welcome",
                        senderRole = "MASTER",
                        content = "Welcome to AgentDroid OS. I am your Master Agent. I coordinate your specialized agents across Phone Control, Social Media, Content, Research, Files, and Automation. What would you like us to achieve today?"
                    )
                )
            }

            // Seed Default Connected Social Accounts for demo
            if (db.accountDao().getAccountCount() == 0) {
                db.accountDao().insertAccount(
                    ConnectedAccountEntity(
                        id = "acc_x",
                        platform = "TWITTER",
                        username = "@AgentDroidUser",
                        displayName = "AgentDroid User",
                        isConnected = true
                    )
                )
                db.accountDao().insertAccount(
                    ConnectedAccountEntity(
                        id = "acc_linkedin",
                        platform = "LINKEDIN",
                        username = "ai-systems-lead",
                        displayName = "AI Systems Architect",
                        isConnected = true
                    )
                )
            }
        }
    }

    private class DatabaseCallback : Callback() {
        override fun onCreate(db: SupportSQLiteDatabase) {
            super.onCreate(db)
            CoroutineScope(Dispatchers.IO).launch {
                INSTANCE?.let { database ->
                    ensureDefaultDataSeeded(database)
                }
            }
        }
    }
}
