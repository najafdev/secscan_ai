package com.agentdroid.app.ui.screens.dashboard

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateContentSize
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.agentdroid.app.AgentDroidApplication
import com.agentdroid.app.ai.error.AiError
import com.agentdroid.app.domain.model.AgentExecutionState
import com.agentdroid.app.domain.model.AgentRole
import com.agentdroid.app.domain.model.TaskStatus
import com.agentdroid.app.ui.components.*
import com.agentdroid.app.ui.theme.*
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun DashboardScreen(
    onNavigateToCommand: (String) -> Unit,
    onNavigateToAgents: () -> Unit,
    onNavigateToAgentDetails: (String) -> Unit,
    onNavigateToActivity: () -> Unit,
    onNavigateToSettings: (() -> Unit)? = null,
    onNavigateToLegal: ((String) -> Unit)? = null
) {
    val app = AgentDroidApplication.instance
    val coroutineScope = rememberCoroutineScope()

    val orchestratorStatus by app.orchestrator.orchestratorStatus.collectAsState()
    val systemStatus by app.aiConnectionManager.systemStatus.collectAsState()
    val currentPlan by app.orchestrator.currentPlan.collectAsState()
    val allAgents by app.database.agentDao().getAllAgents().collectAsState(initial = emptyList())
    val pendingApprovals by app.database.approvalDao().getPendingApprovals().collectAsState(initial = emptyList())
    val recentLogs by app.database.activityLogDao().getRecentLogs().collectAsState(initial = emptyList())
    val memoryRecords by app.memoryManager.getAllRecords().collectAsState(initial = emptyList())

    var commandText by remember { mutableStateOf("") }

    val activeState = when {
        orchestratorStatus == "Planning" -> AgentExecutionState.PLANNING
        orchestratorStatus == "Running" || orchestratorStatus.contains("Executing", ignoreCase = true) -> AgentExecutionState.RUNNING
        orchestratorStatus.contains("Waiting", ignoreCase = true) -> AgentExecutionState.WAITING_FOR_APPROVAL
        orchestratorStatus == "Completed" -> AgentExecutionState.COMPLETED
        orchestratorStatus == "Failed" -> AgentExecutionState.FAILED
        else -> AgentExecutionState.IDLE
    }

    val runningTasksCount = currentPlan?.tasks?.count { it.status == TaskStatus.RUNNING } ?: 0
    val activeAgentsCount = allAgents.count { it.isEnabled }

    val quickActions = listOf(
        "Organize my entire workday." to "Schedule, emails, and pending documents",
        "Research five competitors." to "Market trends & comparison report",
        "Manage my social media today." to "Content, posts, analytics, replies",
        "Audit device storage & security." to "Check files, permissions, and links"
    )

    val timeFormat = remember { SimpleDateFormat("HH:mm:ss", Locale.getDefault()) }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(BackgroundDark)
            .padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // 1. Top Section: Minimalist Branding, Greeting & Shortcuts
        item {
            Spacer(modifier = Modifier.height(14.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    androidx.compose.foundation.Image(
                        painter = androidx.compose.ui.res.painterResource(id = com.agentdroid.app.R.drawable.agentdroid_logo),
                        contentDescription = "AgentDroid Logo",
                        modifier = Modifier
                            .size(32.dp)
                            .clip(RoundedCornerShape(8.dp))
                    )
                    Spacer(modifier = Modifier.width(10.dp))
                    Column {
                        Text(
                            text = "AGENTDROID OS",
                            style = MaterialTheme.typography.labelSmall,
                            letterSpacing = 2.sp,
                            color = PrimaryAccent,
                            fontWeight = FontWeight.Bold
                        )
                        Text(
                            text = "System Online • Operator Session",
                            style = MaterialTheme.typography.bodySmall,
                            color = TextSecondary
                        )
                    }
                }

                Row(verticalAlignment = Alignment.CenterVertically) {
                    // Emergency Halt Button
                    Button(
                        onClick = { app.orchestrator.triggerEmergencyStop() },
                        colors = ButtonDefaults.buttonColors(containerColor = ErrorRed.copy(alpha = 0.15f), contentColor = ErrorRed),
                        shape = RoundedCornerShape(8.dp),
                        border = androidx.compose.foundation.BorderStroke(1.dp, ErrorRed.copy(alpha = 0.4f)),
                        contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp),
                        modifier = Modifier.height(30.dp)
                    ) {
                        Icon(Icons.Default.Warning, contentDescription = "Emergency Stop", modifier = Modifier.size(14.dp))
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("HALT", fontSize = 11.sp, fontWeight = FontWeight.Bold)
                    }

                    if (onNavigateToSettings != null) {
                        Spacer(modifier = Modifier.width(8.dp))
                        IconButton(
                            onClick = onNavigateToSettings,
                            modifier = Modifier.size(32.dp)
                        ) {
                            Icon(Icons.Default.Settings, contentDescription = "Settings", tint = TextSecondary, modifier = Modifier.size(18.dp))
                        }
                    }
                }
            }
        }

        // 2. Main Section: Master Agent Hero Card with Animated AI Core
        item {
            MasterAgentHeroCard(
                status = if (!systemStatus.isAnyConnected) "AI Model Disconnected" else orchestratorStatus,
                activeAgentsCount = activeAgentsCount,
                runningTasksCount = runningTasksCount,
                executionState = if (!systemStatus.isAnyConnected) AgentExecutionState.FAILED else activeState,
                onChatClick = { onNavigateToCommand("") }
            )
        }

        // Strict Real AI Guard Banner
        if (!systemStatus.isAnyConnected) {
            item {
                AIConnectionErrorCard(
                    error = AiError.notConfigured(modelName = systemStatus.activeModel),
                    onNavigateToSettings = { onNavigateToSettings?.invoke() }
                )
            }
        }

        // 3. Prominent Futuristic AI Command Bar
        item {
            Column {
                Text(
                    text = "DISPATCH INSTRUCTION",
                    style = MaterialTheme.typography.labelSmall,
                    color = TextSecondary,
                    letterSpacing = 1.sp
                )
                Spacer(modifier = Modifier.height(6.dp))
                AICommandBar(
                    value = commandText,
                    onValueChange = { commandText = it },
                    onSend = {
                        if (commandText.isNotBlank()) {
                            val cmd = commandText
                            commandText = ""
                            onNavigateToCommand(cmd)
                        }
                    },
                    onVoiceClick = {
                        commandText = "Manage my social media today. Create content, prepare posts, analyze engagement, and organize my replies."
                    },
                    onAttachClick = {
                        commandText = "Analyze document /Documents/Project_Brief.pdf and prepare an executive summary."
                    },
                    placeholderText = "Command AgentDroid OS..."
                )
            }
        }

        // 4. Pending Approvals Section (Human-in-the-Loop Gate)
        if (pendingApprovals.isNotEmpty()) {
            item {
                ObsidianCard(
                    borderColor = WarningAmber.copy(alpha = 0.7f),
                    highlightGlow = true
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.Security, contentDescription = null, tint = WarningAmber, modifier = Modifier.size(18.dp))
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = "Action Approvals Required (${pendingApprovals.size})",
                                style = MaterialTheme.typography.titleMedium,
                                color = WarningAmber,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }
                    Spacer(modifier = Modifier.height(8.dp))
                    for (approval in pendingApprovals.take(3)) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 4.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text(approval.title, style = MaterialTheme.typography.bodyLarge, fontWeight = FontWeight.SemiBold)
                                Text(approval.actionDetails, style = MaterialTheme.typography.bodySmall, color = TextMuted)
                            }
                            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                OutlinedButton(
                                    onClick = { coroutineScope.launch { app.orchestrator.rejectTask(approval.taskId) } },
                                    colors = ButtonDefaults.outlinedButtonColors(contentColor = ErrorRed),
                                    shape = RoundedCornerShape(6.dp),
                                    contentPadding = PaddingValues(horizontal = 8.dp, vertical = 2.dp),
                                    modifier = Modifier.height(28.dp)
                                ) {
                                    Text("Deny", fontSize = 11.sp)
                                }
                                Button(
                                    onClick = { coroutineScope.launch { app.orchestrator.approveTask(approval.taskId) } },
                                    colors = ButtonDefaults.buttonColors(containerColor = PrimaryAccent, contentColor = BackgroundDark),
                                    shape = RoundedCornerShape(6.dp),
                                    contentPadding = PaddingValues(horizontal = 10.dp, vertical = 2.dp),
                                    modifier = Modifier.height(28.dp)
                                ) {
                                    Text("Approve", fontSize = 11.sp, fontWeight = FontWeight.Bold)
                                }
                            }
                        }
                    }
                }
            }
        }

        // 5. Quick Workflow Accelerators (Preset Prompts)
        item {
            Column {
                Text(
                    text = "QUICK DISPATCH WORKFLOWS",
                    style = MaterialTheme.typography.labelSmall,
                    color = TextSecondary,
                    letterSpacing = 1.sp
                )
                Spacer(modifier = Modifier.height(8.dp))
                LazyRow(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    items(quickActions) { (prompt, subtitle) ->
                        ObsidianCard(
                            modifier = Modifier
                                .width(200.dp)
                                .clickable { onNavigateToCommand(prompt) },
                            borderColor = BorderDark
                        ) {
                            Text(
                                text = prompt,
                                style = MaterialTheme.typography.bodyLarge,
                                fontWeight = FontWeight.SemiBold,
                                maxLines = 1,
                                color = TextPrimary
                            )
                            Spacer(modifier = Modifier.height(3.dp))
                            Text(
                                text = subtitle,
                                style = MaterialTheme.typography.bodySmall,
                                color = TextMuted,
                                maxLines = 1
                            )
                        }
                    }
                }
            }
        }

        // 6. Active Agents Fleet Overview
        item {
            Column {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "SPECIALIZED FLEET (${allAgents.size})",
                        style = MaterialTheme.typography.labelSmall,
                        color = TextSecondary,
                        letterSpacing = 1.sp
                    )
                    Text(
                        text = "Manage All",
                        style = MaterialTheme.typography.labelSmall,
                        color = PrimaryAccent,
                        modifier = Modifier.clickable(onClick = onNavigateToAgents)
                    )
                }
                Spacer(modifier = Modifier.height(8.dp))
                LazyRow(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    items(allAgents) { agent ->
                        val roleEnum = AgentRole.fromId(agent.id)
                        val roleColor = when (roleEnum) {
                            AgentRole.MASTER -> MasterAgentColor
                            AgentRole.PHONE_CONTROL -> PhoneAgentColor
                            AgentRole.SOCIAL_MEDIA -> SocialAgentColor
                            AgentRole.CONTENT_CREATION -> ContentAgentColor
                            AgentRole.RESEARCH -> ResearchAgentColor
                            AgentRole.COMMUNICATION -> CommAgentColor
                            AgentRole.FILE_MANAGEMENT -> FileAgentColor
                            AgentRole.PRODUCTIVITY -> ProductivityAgentColor
                            AgentRole.ANALYTICS -> AnalyticsAgentColor
                            AgentRole.BROWSER -> BrowserAgentColor
                            AgentRole.SECURITY -> SecurityAgentColor
                            AgentRole.CUSTOM -> CustomAgentColor
                        }

                        ObsidianCard(
                            modifier = Modifier
                                .width(155.dp)
                                .clickable { onNavigateToAgentDetails(agent.id) },
                            borderColor = BorderDark
                        ) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Box(
                                    modifier = Modifier
                                        .size(7.dp)
                                        .clip(CircleShape)
                                        .background(roleColor)
                                )
                                Spacer(modifier = Modifier.width(6.dp))
                                Text(
                                    text = agent.role,
                                    style = MaterialTheme.typography.labelSmall,
                                    color = roleColor,
                                    fontSize = 9.sp
                                )
                            }
                            Spacer(modifier = Modifier.height(6.dp))
                            Text(
                                text = agent.name,
                                style = MaterialTheme.typography.bodyLarge,
                                fontWeight = FontWeight.Bold,
                                maxLines = 1,
                                color = TextPrimary
                            )
                            Spacer(modifier = Modifier.height(8.dp))
                            AgentStatusBadge(state = if (agent.isEnabled) AgentExecutionState.IDLE else AgentExecutionState.CANCELLED)
                        }
                    }
                }
            }
        }

        // 7. System Telemetry & Statistics Cards
        item {
            Column {
                Text(
                    text = "SYSTEM TELEMETRY",
                    style = MaterialTheme.typography.labelSmall,
                    color = TextSecondary,
                    letterSpacing = 1.sp
                )
                Spacer(modifier = Modifier.height(8.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    MetricCard(
                        title = "Context Memory",
                        value = "${memoryRecords.size}",
                        subtitle = "5 tiers active",
                        accentColor = PrimaryAccent,
                        modifier = Modifier.weight(1f)
                    )
                    MetricCard(
                        title = "Security Gate",
                        value = "Zero-Trust",
                        subtitle = "Hardware Keystore",
                        accentColor = SuccessGreen,
                        modifier = Modifier.weight(1f)
                    )
                    MetricCard(
                        title = "Concurrency",
                        value = "4x Max",
                        subtitle = "DAG parallel limits",
                        accentColor = ElectricBlue,
                        modifier = Modifier.weight(1f)
                    )
                }
            }
        }

        // 8. Recent System Activity Timeline
        item {
            Column {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "REAL-TIME AUDIT STREAM",
                        style = MaterialTheme.typography.labelSmall,
                        color = TextSecondary,
                        letterSpacing = 1.sp
                    )
                    Text(
                        text = "Full History",
                        style = MaterialTheme.typography.labelSmall,
                        color = PrimaryAccent,
                        modifier = Modifier.clickable(onClick = onNavigateToActivity)
                    )
                }
                Spacer(modifier = Modifier.height(8.dp))
                for (log in recentLogs.take(4)) {
                    ObsidianCard(
                        modifier = Modifier.padding(vertical = 3.dp),
                        borderColor = BorderDark
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = log.agentRole,
                                style = MaterialTheme.typography.labelSmall,
                                color = PrimaryAccent,
                                fontSize = 9.sp
                            )
                            Text(
                                text = timeFormat.format(Date(log.timestamp)),
                                style = MaterialTheme.typography.labelSmall,
                                color = TextMuted,
                                fontSize = 9.sp
                            )
                        }
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = log.description,
                            style = MaterialTheme.typography.bodyMedium,
                            color = TextPrimary
                        )
                    }
                }
            }

            // 9. Legal & Compliance Footer Links
            Spacer(modifier = Modifier.height(16.dp))
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 8.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Row(
                    horizontalArrangement = Arrangement.Center,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "Privacy Policy",
                        style = MaterialTheme.typography.labelSmall,
                        color = TextSecondary,
                        modifier = Modifier.clickable { onNavigateToLegal?.invoke("privacy") }
                    )
                    Text(
                        text = "  •  ",
                        style = MaterialTheme.typography.labelSmall,
                        color = TextMuted
                    )
                    Text(
                        text = "Terms & Conditions",
                        style = MaterialTheme.typography.labelSmall,
                        color = TextSecondary,
                        modifier = Modifier.clickable { onNavigateToLegal?.invoke("terms") }
                    )
                    Text(
                        text = "  •  ",
                        style = MaterialTheme.typography.labelSmall,
                        color = TextMuted
                    )
                    Text(
                        text = "v1.0.0",
                        style = MaterialTheme.typography.labelSmall,
                        fontFamily = FontFamily.Monospace,
                        color = PrimaryAccent
                    )
                }
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = "AgentDroid Sovereign Multi-Agent AI OS • Apache 2.0",
                    style = MaterialTheme.typography.labelSmall,
                    fontSize = 10.sp,
                    color = TextMuted
                )
            }
            Spacer(modifier = Modifier.height(70.dp))
        }
    }
}
