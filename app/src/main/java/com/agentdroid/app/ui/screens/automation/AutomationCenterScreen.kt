package com.agentdroid.app.ui.screens.automation

import androidx.compose.animation.animateContentSize
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.agentdroid.app.AgentDroidApplication
import com.agentdroid.app.domain.model.TriggerType
import com.agentdroid.app.ui.components.ObsidianCard
import com.agentdroid.app.ui.theme.*
import kotlinx.coroutines.launch

@Composable
fun AutomationCenterScreen(
    onTriggerWorkflow: (String) -> Unit
) {
    val app = AgentDroidApplication.instance
    val coroutineScope = rememberCoroutineScope()

    val workflows by app.workflowEngine.getAllWorkflows().collectAsState(initial = emptyList())

    var workflowTitle by remember { mutableStateOf("") }
    var workflowPrompt by remember { mutableStateOf("") }
    var selectedTrigger by remember { mutableStateOf(TriggerType.SCHEDULED) }

    val templates = listOf(
        "Every morning, summarize important notifications and prioritize emails." to TriggerType.SCHEDULED,
        "Every evening, prepare tomorrow's social media content calendar." to TriggerType.SCHEDULED,
        "Every Sunday, prepare my weekly productivity report and file audit." to TriggerType.SCHEDULED,
        "When sharing an article with AgentDroid, summarize key points." to TriggerType.SHARE_INTENT
    )

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(BackgroundDark)
            .padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        item {
            Spacer(modifier = Modifier.height(14.dp))
            Column {
                Text(
                    text = "WORKFLOW AUTOMATION",
                    style = MaterialTheme.typography.labelSmall,
                    letterSpacing = 1.5.sp,
                    color = PrimaryAccent
                )
                Text(
                    text = "Automation Engine",
                    style = MaterialTheme.typography.headlineMedium,
                    fontWeight = FontWeight.Bold,
                    color = TextPrimary
                )
            }
        }

        // Visual Connected Workflow Pipeline Nodes
        item {
            ObsidianCard(borderColor = PrimaryAccent.copy(alpha = 0.35f)) {
                Text(
                    text = "PIPELINE EXECUTION ARCHITECTURE",
                    style = MaterialTheme.typography.labelSmall,
                    color = TextSecondary,
                    letterSpacing = 1.sp
                )
                Spacer(modifier = Modifier.height(12.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    WorkflowNodeItem(step = "1", title = "Trigger", desc = "WorkManager", color = ElectricBlue)
                    Icon(Icons.AutoMirrored.Filled.ArrowForward, contentDescription = null, tint = TextMuted, modifier = Modifier.size(16.dp))
                    WorkflowNodeItem(step = "2", title = "Plan", desc = "Master Agent", color = PrimaryAccent)
                    Icon(Icons.AutoMirrored.Filled.ArrowForward, contentDescription = null, tint = TextMuted, modifier = Modifier.size(16.dp))
                    WorkflowNodeItem(step = "3", title = "Execute", desc = "DAG Fleet", color = SuccessGreen)
                    Icon(Icons.AutoMirrored.Filled.ArrowForward, contentDescription = null, tint = TextMuted, modifier = Modifier.size(16.dp))
                    WorkflowNodeItem(step = "4", title = "Deliver", desc = "Synthesis", color = PrimaryAccent)
                }
            }
        }

        // Natural Language Workflow Builder Card
        item {
            ObsidianCard {
                Text(
                    text = "NATURAL LANGUAGE BUILDER",
                    style = MaterialTheme.typography.labelSmall,
                    color = TextSecondary,
                    letterSpacing = 1.sp
                )
                Spacer(modifier = Modifier.height(10.dp))
                OutlinedTextField(
                    value = workflowTitle,
                    onValueChange = { workflowTitle = it },
                    placeholder = { Text("Workflow Name (e.g. Daily Executive Sync)", fontSize = 13.sp, color = TextMuted) },
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(10.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = PrimaryAccent,
                        unfocusedBorderColor = BorderDark,
                        focusedContainerColor = SurfaceVariantDark,
                        unfocusedContainerColor = SurfaceVariantDark
                    ),
                    singleLine = true
                )
                Spacer(modifier = Modifier.height(8.dp))
                OutlinedTextField(
                    value = workflowPrompt,
                    onValueChange = { workflowPrompt = it },
                    placeholder = { Text("Instructions (e.g., 'Summarize notifications, triage unread emails, and build daily schedule')", fontSize = 13.sp, color = TextMuted) },
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(10.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = PrimaryAccent,
                        unfocusedBorderColor = BorderDark,
                        focusedContainerColor = SurfaceVariantDark,
                        unfocusedContainerColor = SurfaceVariantDark
                    ),
                    maxLines = 3
                )
                Spacer(modifier = Modifier.height(10.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "Trigger: ${selectedTrigger.name}",
                        style = MaterialTheme.typography.labelSmall,
                        color = PrimaryAccent
                    )
                    Button(
                        onClick = {
                            if (workflowTitle.isNotBlank() && workflowPrompt.isNotBlank()) {
                                coroutineScope.launch {
                                    app.workflowEngine.createWorkflow(
                                        title = workflowTitle.trim(),
                                        prompt = workflowPrompt.trim(),
                                        triggerType = selectedTrigger
                                    )
                                    workflowTitle = ""
                                    workflowPrompt = ""
                                }
                            }
                        },
                        enabled = workflowTitle.isNotBlank() && workflowPrompt.isNotBlank(),
                        colors = ButtonDefaults.buttonColors(containerColor = PrimaryAccent, contentColor = BackgroundDark),
                        shape = RoundedCornerShape(8.dp),
                        contentPadding = PaddingValues(horizontal = 14.dp, vertical = 6.dp),
                        modifier = Modifier.height(32.dp)
                    ) {
                        Text("Save Routine", fontSize = 11.5.sp, fontWeight = FontWeight.Bold)
                    }
                }
            }
        }

        // Preset Templates Carousel
        item {
            Column {
                Text(
                    text = "PRESET AUTOMATION TEMPLATES",
                    style = MaterialTheme.typography.labelSmall,
                    color = TextSecondary,
                    letterSpacing = 1.sp
                )
                Spacer(modifier = Modifier.height(8.dp))
                for ((prompt, trigger) in templates) {
                    ObsidianCard(
                        modifier = Modifier.padding(vertical = 3.dp),
                        borderColor = BorderDark
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text(text = prompt, style = MaterialTheme.typography.bodyMedium, color = TextPrimary)
                                Text(text = "TRIGGER: ${trigger.name}", style = MaterialTheme.typography.labelSmall, color = PrimaryAccent, fontSize = 9.sp)
                            }
                            IconButton(
                                onClick = {
                                    coroutineScope.launch {
                                        app.workflowEngine.createWorkflow(
                                            title = prompt.take(30) + "...",
                                            prompt = prompt,
                                            triggerType = trigger
                                        )
                                    }
                                },
                                modifier = Modifier.size(32.dp)
                            ) {
                                Icon(Icons.Default.AddCircle, contentDescription = "Add Template", tint = PrimaryAccent, modifier = Modifier.size(20.dp))
                            }
                        }
                    }
                }
            }
        }

        // Active Configured Workflows
        item {
            Text(
                text = "CONFIGURED ROUTINES (${workflows.size})",
                style = MaterialTheme.typography.labelSmall,
                color = TextSecondary,
                letterSpacing = 1.sp
            )
        }

        items(workflows) { wf ->
            ObsidianCard(borderColor = if (wf.isEnabled) BorderDark else BorderDark.copy(alpha = 0.4f)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = wf.title,
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.SemiBold,
                            color = TextPrimary
                        )
                        Spacer(modifier = Modifier.height(2.dp))
                        Text(
                            text = wf.prompt,
                            style = MaterialTheme.typography.bodyMedium,
                            color = TextSecondary,
                            maxLines = 2
                        )
                        Spacer(modifier = Modifier.height(6.dp))
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(
                                text = "RUNS: ${wf.executionCount}",
                                style = MaterialTheme.typography.labelSmall,
                                color = TextMuted,
                                fontSize = 9.sp
                            )
                            Spacer(modifier = Modifier.width(10.dp))
                            Text(
                                text = "TRIGGER: ${wf.triggerType.name}",
                                style = MaterialTheme.typography.labelSmall,
                                color = PrimaryAccent,
                                fontSize = 9.sp
                            )
                        }
                    }

                    Column(horizontalAlignment = Alignment.End) {
                        Switch(
                            checked = wf.isEnabled,
                            onCheckedChange = { checked ->
                                coroutineScope.launch {
                                    app.workflowEngine.toggleWorkflow(wf.id, checked)
                                }
                            },
                            colors = SwitchDefaults.colors(
                                checkedThumbColor = BackgroundDark,
                                checkedTrackColor = PrimaryAccent,
                                uncheckedTrackColor = SurfaceVariantDark,
                                uncheckedThumbColor = TextMuted
                            )
                        )
                        IconButton(
                            onClick = { onTriggerWorkflow(wf.prompt) },
                            modifier = Modifier.size(32.dp)
                        ) {
                            Icon(Icons.Default.PlayArrow, contentDescription = "Run Now", tint = SuccessGreen, modifier = Modifier.size(20.dp))
                        }
                    }
                }
            }
        }

        item { Spacer(modifier = Modifier.height(80.dp)) }
    }
}

@Composable
private fun WorkflowNodeItem(
    step: String,
    title: String,
    desc: String,
    color: Color
) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Box(
            modifier = Modifier
                .size(28.dp)
                .clip(CircleShape)
                .background(color.copy(alpha = 0.15f))
                .border(1.dp, color.copy(alpha = 0.5f), CircleShape),
            contentAlignment = Alignment.Center
        ) {
            Text(text = step, style = MaterialTheme.typography.labelSmall, color = color, fontWeight = FontWeight.Bold)
        }
        Spacer(modifier = Modifier.height(4.dp))
        Text(text = title, style = MaterialTheme.typography.labelSmall, color = TextPrimary, fontWeight = FontWeight.SemiBold, fontSize = 10.sp)
        Text(text = desc, style = MaterialTheme.typography.bodySmall, color = TextMuted, fontSize = 8.5.sp)
    }
}
