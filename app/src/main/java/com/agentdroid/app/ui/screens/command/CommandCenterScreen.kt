package com.agentdroid.app.ui.screens.command

import android.app.Activity
import android.content.Intent
import android.speech.RecognizerIntent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateContentSize
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.agentdroid.app.AgentDroidApplication
import com.agentdroid.app.ai.connection.ConnectionState
import com.agentdroid.app.ai.error.AiError
import com.agentdroid.app.data.local.entity.MessageEntity
import com.agentdroid.app.domain.model.*
import com.agentdroid.app.domain.orchestrator.OrchestrationUpdate
import com.agentdroid.app.ui.components.*
import com.agentdroid.app.ui.theme.*
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch
import java.util.UUID

@Composable
fun CommandCenterScreen(
    initialPrompt: String? = null,
    onNavigateToSettings: (() -> Unit)? = null,
    onBack: (() -> Unit)? = null
) {
    val app = AgentDroidApplication.instance
    val clipboardManager = LocalClipboardManager.current
    val coroutineScope = rememberCoroutineScope()
    val listState = rememberLazyListState()

    var inputText by remember { mutableStateOf(initialPrompt ?: "") }
    var isExecuting by remember { mutableStateOf(false) }
    var activeAiError by remember { mutableStateOf<AiError?>(null) }
    var lastSubmittedPrompt by remember { mutableStateOf("") }

    val systemStatus by app.aiConnectionManager.systemStatus.collectAsState()
    val currentPlan by app.orchestrator.currentPlan.collectAsState()
    val messages by app.database.conversationDao().getMessagesForConversation("conv_welcome").collectAsState(initial = emptyList())

    val speechRecognizerLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == Activity.RESULT_OK) {
            val spokenText = result.data?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)?.firstOrNull()
            if (!spokenText.isNullOrBlank()) {
                inputText = spokenText
            }
        }
    }

    // Auto-scroll on new messages or error
    LaunchedEffect(messages.size, currentPlan?.tasks?.size, activeAiError) {
        if (messages.isNotEmpty()) {
            listState.animateScrollToItem(messages.size)
        }
    }

    // Auto-trigger if initial prompt was provided
    LaunchedEffect(initialPrompt) {
        if (!initialPrompt.isNullOrBlank()) {
            val prompt = initialPrompt
            inputText = ""
            lastSubmittedPrompt = prompt
            coroutineScope.launch {
                sendMessage(
                    prompt = prompt,
                    app = app,
                    setExecuting = { isExecuting = it },
                    onError = { activeAiError = it }
                )
            }
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BackgroundDark)
    ) {
        // Top Command Bar with Live AI Model Status & Actions
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(BackgroundSecondary)
                .border(1.dp, BorderDark)
                .padding(horizontal = 12.dp, vertical = 10.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                if (onBack != null) {
                    IconButton(onClick = onBack, modifier = Modifier.size(32.dp)) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back", tint = TextPrimary, modifier = Modifier.size(18.dp))
                    }
                    Spacer(modifier = Modifier.width(4.dp))
                }
                MasterAgentVisualizer(
                    state = if (isExecuting) AgentExecutionState.RUNNING else AgentExecutionState.IDLE,
                    size = 32.dp
                )
                Spacer(modifier = Modifier.width(10.dp))
                Column {
                    Text(
                        text = "AI CHAT & COMMAND CENTER",
                        style = MaterialTheme.typography.labelSmall,
                        letterSpacing = 1.2.sp,
                        color = PrimaryAccent,
                        fontFamily = FontFamily.Monospace,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        text = "Talk to Master Agent & Fleet",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        color = TextPrimary
                    )
                }
            }

            Row(verticalAlignment = Alignment.CenterVertically) {
                // New Chat / Clear history button
                IconButton(
                    onClick = {
                        coroutineScope.launch {
                            app.database.conversationDao().clearMessages("conv_welcome")
                            app.orchestrator.cancelExecution()
                            isExecuting = false
                            activeAiError = null
                            app.database.conversationDao().insertMessage(
                                MessageEntity(
                                    id = "msg_welcome_${System.currentTimeMillis()}",
                                    conversationId = "conv_welcome",
                                    senderRole = "MASTER",
                                    content = "Welcome to AgentDroid OS. I am your Master Agent. I coordinate your specialized agents across Phone Control, Social Media, Content, Research, Files, and Automation. What would you like us to achieve today?"
                                )
                            )
                        }
                    },
                    modifier = Modifier.size(32.dp)
                ) {
                    Icon(
                        Icons.Default.AddComment,
                        contentDescription = "New Chat",
                        tint = PrimaryAccent,
                        modifier = Modifier.size(18.dp)
                    )
                }

                Spacer(modifier = Modifier.width(4.dp))

                ModelStatusIndicator(
                    modelName = systemStatus.activeModel ?: "No Model",
                    state = systemStatus.currentMasterState
                )

                if (isExecuting) {
                    Spacer(modifier = Modifier.width(8.dp))
                    Button(
                        onClick = {
                            app.orchestrator.cancelExecution()
                            isExecuting = false
                        },
                        colors = ButtonDefaults.buttonColors(containerColor = ErrorRed.copy(alpha = 0.15f), contentColor = ErrorRed),
                        shape = RoundedCornerShape(8.dp),
                        border = androidx.compose.foundation.BorderStroke(1.dp, ErrorRed.copy(alpha = 0.4f)),
                        contentPadding = PaddingValues(horizontal = 8.dp, vertical = 2.dp),
                        modifier = Modifier.height(28.dp)
                    ) {
                        Icon(Icons.Default.Stop, contentDescription = null, modifier = Modifier.size(12.dp))
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("ABORT", fontSize = 10.sp, fontWeight = FontWeight.Bold)
                    }
                }
            }
        }

        // Conversation & Multi-Agent Execution Feed
        LazyColumn(
            state = listState,
            modifier = Modifier
                .weight(1f)
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            item { Spacer(modifier = Modifier.height(8.dp)) }

            // Starter Suggestions when chat is fresh
            if (messages.size <= 1 && !isExecuting) {
                item {
                    ObsidianCard(borderColor = PrimaryAccent.copy(alpha = 0.35f)) {
                        Text(
                            text = "ASSIGN WORK TO SPECIALIZED AGENTS",
                            style = MaterialTheme.typography.labelSmall,
                            color = PrimaryAccent,
                            letterSpacing = 1.2.sp,
                            fontFamily = FontFamily.Monospace,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(modifier = Modifier.height(6.dp))
                        Text(
                            text = "Tap any suggested goal to immediately dispatch to Master Agent and the specialized AI fleet:",
                            style = MaterialTheme.typography.bodySmall,
                            color = TextSecondary,
                            fontSize = 11.5.sp
                        )
                        Spacer(modifier = Modifier.height(10.dp))
                        val suggestions = listOf(
                            "📱 Automate device actions, check notifications & summarize daily agenda",
                            "🌐 Prepare 3 cross-platform post drafts for X and LinkedIn",
                            "🔍 Research latest autonomous AI agent frameworks and summarize findings",
                            "📁 Scan storage and report duplicate or large PDF documents",
                            "⚡ Organize today's productivity checklist and calendar tasks"
                        )
                        Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            for (s in suggestions) {
                                Surface(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .clickable {
                                            inputText = ""
                                            lastSubmittedPrompt = s
                                            activeAiError = null
                                            coroutineScope.launch {
                                                sendMessage(
                                                    prompt = s,
                                                    app = app,
                                                    setExecuting = { isExecuting = it },
                                                    onError = { activeAiError = it }
                                                )
                                            }
                                        },
                                    color = SurfaceVariantDark,
                                    shape = RoundedCornerShape(8.dp),
                                    border = androidx.compose.foundation.BorderStroke(1.dp, BorderDark)
                                ) {
                                    Text(
                                        text = s,
                                        style = MaterialTheme.typography.bodySmall,
                                        color = TextPrimary,
                                        fontSize = 11.5.sp,
                                        modifier = Modifier.padding(10.dp)
                                    )
                                }
                            }
                        }
                    }
                }
            }

            // Render Messages
            items(messages) { msg ->
                val isUser = msg.senderRole == "USER"

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start
                ) {
                    val bubbleShape = RoundedCornerShape(
                        topStart = 14.dp,
                        topEnd = 14.dp,
                        bottomStart = if (isUser) 14.dp else 4.dp,
                        bottomEnd = if (isUser) 4.dp else 14.dp
                    )

                    Surface(
                        color = if (isUser) SurfaceVariantDark else CardBackground,
                        shape = bubbleShape,
                        border = androidx.compose.foundation.BorderStroke(
                            1.dp,
                            if (isUser) PrimaryAccent.copy(alpha = 0.35f) else BorderDark
                        ),
                        modifier = Modifier
                            .widthIn(max = 330.dp)
                            .animateContentSize()
                    ) {
                        Column(modifier = Modifier.padding(14.dp)) {
                            if (!isUser) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Box(
                                            modifier = Modifier
                                                .size(6.dp)
                                                .clip(CircleShape)
                                                .background(PrimaryAccent)
                                        )
                                        Spacer(modifier = Modifier.width(6.dp))
                                        Text(
                                            text = "MASTER AGENT",
                                            style = MaterialTheme.typography.labelSmall,
                                            fontFamily = FontFamily.Monospace,
                                            fontWeight = FontWeight.Bold,
                                            color = PrimaryAccent,
                                            fontSize = 10.sp
                                        )
                                    }
                                    IconButton(
                                        onClick = {
                                            clipboardManager.setText(AnnotatedString(msg.content))
                                        },
                                        modifier = Modifier.size(20.dp)
                                    ) {
                                        Icon(
                                            Icons.Default.ContentCopy,
                                            contentDescription = "Copy Response",
                                            tint = TextMuted,
                                            modifier = Modifier.size(13.dp)
                                        )
                                    }
                                }
                                Spacer(modifier = Modifier.height(6.dp))
                            }

                            Text(
                                text = msg.content,
                                style = MaterialTheme.typography.bodyMedium,
                                color = TextPrimary,
                                lineHeight = 21.sp
                            )
                        }
                    }
                }
            }

            // Real AI Connection Error Card (Displayed when no provider is connected or auth failed)
            if (activeAiError != null) {
                item {
                    AIConnectionErrorCard(
                        error = activeAiError!!,
                        onNavigateToSettings = { onNavigateToSettings?.invoke() },
                        onRetry = {
                            val prompt = lastSubmittedPrompt
                            activeAiError = null
                            if (prompt.isNotBlank()) {
                                coroutineScope.launch {
                                    sendMessage(
                                        prompt = prompt,
                                        app = app,
                                        setExecuting = { isExecuting = it },
                                        onError = { activeAiError = it }
                                    )
                                }
                            }
                        }
                    )
                }
            }

            // Interactive Task Graph Visualization (DAG)
            if (currentPlan != null && currentPlan!!.tasks.isNotEmpty()) {
                item {
                    ObsidianCard(
                        borderColor = PrimaryAccent.copy(alpha = 0.35f),
                        backgroundColor = SurfaceVariantDark
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = "MULTI-AGENT TASK GRAPH",
                                style = MaterialTheme.typography.labelSmall,
                                letterSpacing = 1.sp,
                                color = PrimaryAccent,
                                fontFamily = FontFamily.Monospace,
                                fontWeight = FontWeight.Bold
                            )
                            Surface(
                                color = PrimaryAccent.copy(alpha = 0.15f),
                                shape = RoundedCornerShape(4.dp)
                            ) {
                                Text(
                                    text = "${currentPlan!!.tasks.count { it.status == TaskStatus.COMPLETED }}/${currentPlan!!.tasks.size} DONE",
                                    color = PrimaryAccent,
                                    fontSize = 10.sp,
                                    fontFamily = FontFamily.Monospace,
                                    fontWeight = FontWeight.Bold,
                                    modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                                )
                            }
                        }

                        Spacer(modifier = Modifier.height(12.dp))

                        currentPlan!!.tasks.forEachIndexed { index, task ->
                            TaskGraphItem(stepNumber = index + 1, task = task)
                            if (index < currentPlan!!.tasks.size - 1) {
                                Box(
                                    modifier = Modifier
                                        .padding(start = 14.dp)
                                        .width(1.5.dp)
                                        .height(10.dp)
                                        .background(BorderDark)
                                )
                            }
                        }
                    }
                }
            }

            // Typing Indicator during real execution
            if (isExecuting && activeAiError == null) {
                item {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier.padding(vertical = 4.dp)
                    ) {
                        Surface(
                            color = CardBackground,
                            shape = RoundedCornerShape(12.dp),
                            border = androidx.compose.foundation.BorderStroke(1.dp, BorderDark),
                            modifier = Modifier.padding(start = 4.dp)
                        ) {
                            Row(
                                modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(
                                    text = "Agent fleet reasoning",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = TextSecondary,
                                    fontSize = 11.sp
                                )
                                Spacer(modifier = Modifier.width(8.dp))
                                AnimatedTypingIndicator()
                            }
                        }
                    }
                }
            }

            item { Spacer(modifier = Modifier.height(16.dp)) }
        }

        // Quick Agent Delegation Selector
        val delegationChips = listOf(
            Triple("🤖 Master Agent", "", MasterAgentColor),
            Triple("📱 Phone Control", "Assign to Phone Control Agent: ", PhoneAgentColor),
            Triple("🌐 Social Media", "Assign to Social Media Agent: ", SocialAgentColor),
            Triple("🔍 Research", "Assign to Research Agent: ", ResearchAgentColor),
            Triple("✍️ Content", "Assign to Content Creation Agent: ", ContentAgentColor),
            Triple("📁 Files", "Assign to File Management Agent: ", FileAgentColor),
            Triple("⚡ Productivity", "Assign to Productivity Agent: ", ProductivityAgentColor),
            Triple("📊 Analytics", "Assign to Analytics Agent: ", AnalyticsAgentColor),
            Triple("🌐 Browser", "Assign to Browser Agent: ", BrowserAgentColor),
            Triple("🛡️ Security", "Assign to Security Agent: ", SecurityAgentColor)
        )

        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 4.dp)
        ) {
            Text(
                text = "ASSIGN WORK TO AGENT:",
                style = MaterialTheme.typography.labelSmall,
                color = TextMuted,
                fontFamily = FontFamily.Monospace,
                fontSize = 9.sp,
                letterSpacing = 1.sp
            )
            Spacer(modifier = Modifier.height(4.dp))
            LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                items(delegationChips) { (label, prefix, chipColor) ->
                    Surface(
                        modifier = Modifier.clickable {
                            inputText = if (prefix.isNotBlank()) prefix else ""
                        },
                        color = SurfaceVariantDark,
                        shape = RoundedCornerShape(8.dp),
                        border = androidx.compose.foundation.BorderStroke(1.dp, chipColor.copy(alpha = 0.4f))
                    ) {
                        Text(
                            text = label,
                            style = MaterialTheme.typography.labelSmall,
                            color = chipColor,
                            fontWeight = FontWeight.SemiBold,
                            fontSize = 11.sp,
                            modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp)
                        )
                    }
                }
            }
        }

        // Bottom AI Command Dock
        AICommandBar(
            value = inputText,
            onValueChange = { inputText = it },
            onSend = {
                if (inputText.isNotBlank()) {
                    val prompt = inputText.trim()
                    inputText = ""
                    lastSubmittedPrompt = prompt
                    activeAiError = null
                    coroutineScope.launch {
                        sendMessage(
                            prompt = prompt,
                            app = app,
                            setExecuting = { isExecuting = it },
                            onError = { activeAiError = it }
                        )
                    }
                }
            },
            onVoiceClick = {
                val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                    putExtra(RecognizerIntent.EXTRA_PROMPT, "Speak a goal for AgentDroid...")
                }
                try {
                    speechRecognizerLauncher.launch(intent)
                } catch (e: Exception) {
                    // Speech recognition not supported on device
                }
            },
            onAttachClick = {
                inputText = "Audit and organize all downloaded PDF files on device."
            },
            placeholderText = "Message Master Agent or assign work...",
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 10.dp)
        )
    }
}

@Composable
private fun TaskGraphItem(stepNumber: Int, task: TaskItem) {
    val isComplete = task.status == TaskStatus.COMPLETED
    val isRunning = task.status == TaskStatus.RUNNING
    val isFailed = task.status == TaskStatus.FAILED

    val statusColor = when {
        isFailed -> ErrorRed
        isComplete -> SuccessGreen
        isRunning -> PrimaryAccent
        else -> TextMuted
    }

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(8.dp))
            .background(CardBackground)
            .border(1.dp, if (isRunning) PrimaryAccent.copy(alpha = 0.5f) else BorderDark, RoundedCornerShape(8.dp))
            .padding(10.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.weight(1f)) {
            Box(
                modifier = Modifier
                    .size(24.dp)
                    .clip(CircleShape)
                    .background(statusColor.copy(alpha = 0.15f)),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    text = "$stepNumber",
                    style = MaterialTheme.typography.labelSmall,
                    fontSize = 10.sp,
                    fontFamily = FontFamily.Monospace,
                    fontWeight = FontWeight.Bold,
                    color = statusColor
                )
            }
            Spacer(modifier = Modifier.width(10.dp))
            Column {
                Text(
                    text = task.title,
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.SemiBold,
                    color = TextPrimary,
                    maxLines = 1
                )
                Text(
                    text = "${task.agentRole.displayName} • ${task.status.name}",
                    style = MaterialTheme.typography.labelSmall,
                    fontSize = 10.sp,
                    fontFamily = FontFamily.Monospace,
                    color = statusColor
                )
            }
        }

        RiskBadge(task.riskLevel)
    }
}

private suspend fun sendMessage(
    prompt: String,
    app: AgentDroidApplication,
    setExecuting: (Boolean) -> Unit,
    onError: (AiError) -> Unit
) {
    setExecuting(true)

    // 1. Insert User Message into Room DB
    val userMsg = MessageEntity(
        id = UUID.randomUUID().toString(),
        conversationId = "conv_welcome",
        senderRole = "USER",
        content = prompt
    )
    app.database.conversationDao().insertMessage(userMsg)

    // 2. Pre-flight check: Verify Master Agent model connection before creating agent message
    val masterValidation = app.aiConnectionManager.validateAndGetProvider(AgentRole.MASTER)
    if (masterValidation.isFailure) {
        val err = masterValidation.exceptionOrNull() as? AiError
            ?: AiError.notConfigured(modelName = "Master Agent")

        // Report error in conversation
        val errorMsgId = UUID.randomUUID().toString()
        val errorMsg = MessageEntity(
            id = errorMsgId,
            conversationId = "conv_welcome",
            senderRole = "MASTER",
            content = "⚠️ **${err.userFriendlyTitle}**\n\n${err.userFriendlyMessage}\n\nPlease connect an AI provider in Settings → AI Providers.",
            isStreaming = false
        )
        app.database.conversationDao().insertMessage(errorMsg)

        onError(err)
        setExecuting(false)
        return
    }

    // 3. Model is connected: Insert real streaming message
    val masterMsgId = UUID.randomUUID().toString()
    val masterMsg = MessageEntity(
        id = masterMsgId,
        conversationId = "conv_welcome",
        senderRole = "MASTER",
        content = "Validating task requirements and orchestrating specialized agents...",
        isStreaming = true
    )
    app.database.conversationDao().insertMessage(masterMsg)

    // 4. Start Real Multi-Agent Execution Stream
    try {
        app.orchestrator.startGoalExecution(prompt).collectLatest { update ->
            when (update) {
                is OrchestrationUpdate.Validating -> {
                    app.database.conversationDao().updateMessageContent(
                        masterMsgId,
                        update.message,
                        true
                    )
                }
                is OrchestrationUpdate.ProgressLog -> {
                    // Update streaming message
                    app.database.conversationDao().updateMessageContent(
                        masterMsgId,
                        update.message,
                        true
                    )
                }
                is OrchestrationUpdate.PlanCreated -> {
                    app.database.conversationDao().updateMessageContent(
                        masterMsgId,
                        "Plan constructed: ${update.plan.tasks.size} subtasks assigned across cooperating agents. Executing graph...",
                        true
                    )
                }
                is OrchestrationUpdate.PlanCompleted -> {
                    app.database.conversationDao().updateMessageContent(
                        masterMsgId,
                        update.finalReport,
                        false
                    )
                }
                is OrchestrationUpdate.PlanFailed -> {
                    if (update.aiError != null) {
                        onError(update.aiError)
                        app.database.conversationDao().updateMessageContent(
                            masterMsgId,
                            "⚠️ **${update.aiError.userFriendlyTitle}**\n\n${update.aiError.userFriendlyMessage}",
                            false
                        )
                    } else {
                        app.database.conversationDao().updateMessageContent(
                            masterMsgId,
                            "Execution encountered issues: ${update.error}",
                            false
                        )
                    }
                }
                else -> {}
            }
        }
    } catch (e: Exception) {
        val aiErr = if (e is AiError) e else null
        if (aiErr != null) {
            onError(aiErr)
        }
        app.database.conversationDao().updateMessageContent(
            masterMsgId,
            "Execution error: ${e.message}",
            false
        )
    } finally {
        setExecuting(false)
    }
}
