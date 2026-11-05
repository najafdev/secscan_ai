package com.agentdroid.app.ui.screens.builder

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
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Save
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
import com.agentdroid.app.data.local.entity.AgentConfigEntity
import com.agentdroid.app.data.local.entity.AgentEntity
import com.agentdroid.app.ui.components.ObsidianCard
import com.agentdroid.app.ui.theme.*
import kotlinx.coroutines.launch
import java.util.UUID

@Composable
fun CustomAgentBuilderScreen(
    onBack: () -> Unit
) {
    val app = AgentDroidApplication.instance
    val coroutineScope = rememberCoroutineScope()

    var name by remember { mutableStateOf("") }
    var description by remember { mutableStateOf("") }
    var systemPrompt by remember { mutableStateOf("") }
    var assignedModel by remember { mutableStateOf("gpt-4o") }
    var executionLimit by remember { mutableFloatStateOf(120f) }

    val modelOptions = listOf("gpt-4o", "claude-3-5-sonnet", "gemini-1.5-pro", "llama-3-local")
    val availableTools = listOf(
        "WebSearchEngine" to "Live web queries & content scraping",
        "FileScanner" to "Device file search and inspection",
        "AccessibilityDriver" to "Autonomous screen interaction & clicking",
        "SocialComposer" to "Multi-platform post creation",
        "DocumentSummarizer" to "Synthesize text and reports",
        "EmailDrafter" to "Compose email communications"
    )
    val selectedTools = remember { mutableStateListOf<String>("WebSearchEngine", "DocumentSummarizer") }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(BackgroundDark)
            .padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Top Header
        item {
            Spacer(modifier = Modifier.height(16.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                IconButton(
                    onClick = onBack,
                    modifier = Modifier
                        .size(40.dp)
                        .clip(CircleShape)
                        .background(SurfaceVariantDark)
                ) {
                    Icon(
                        Icons.AutoMirrored.Filled.ArrowBack,
                        contentDescription = "Back",
                        tint = TextPrimary,
                        modifier = Modifier.size(18.dp)
                    )
                }
                Spacer(modifier = Modifier.width(12.dp))
                Column {
                    Text(
                        text = "AGENT ARCHITECT",
                        style = MaterialTheme.typography.labelSmall,
                        letterSpacing = 2.sp,
                        color = CustomAgentColor,
                        fontFamily = FontFamily.Monospace
                    )
                    Spacer(modifier = Modifier.height(2.dp))
                    Text(
                        text = "Custom Agent Builder",
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold,
                        color = TextPrimary
                    )
                }
            }
        }

        // Agent Identity Card
        item {
            ObsidianCard(borderColor = CustomAgentColor.copy(alpha = 0.4f)) {
                Text(
                    text = "Agent Identity & Role",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                    color = TextPrimary
                )
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = "Define the name and scope of your autonomous custom agent.",
                    style = MaterialTheme.typography.bodySmall,
                    color = TextSecondary
                )
                Spacer(modifier = Modifier.height(12.dp))

                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    placeholder = { Text("Agent Name (e.g. Legal Research Agent)", color = TextMuted) },
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(10.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = CustomAgentColor,
                        unfocusedBorderColor = BorderDark,
                        focusedContainerColor = SurfaceVariantDark,
                        unfocusedContainerColor = SurfaceVariantDark,
                        focusedTextColor = TextPrimary,
                        unfocusedTextColor = TextPrimary
                    ),
                    singleLine = true
                )

                Spacer(modifier = Modifier.height(10.dp))

                OutlinedTextField(
                    value = description,
                    onValueChange = { description = it },
                    placeholder = { Text("Short description of purpose and domain expertise", color = TextMuted) },
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(10.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = CustomAgentColor,
                        unfocusedBorderColor = BorderDark,
                        focusedContainerColor = SurfaceVariantDark,
                        unfocusedContainerColor = SurfaceVariantDark,
                        focusedTextColor = TextPrimary,
                        unfocusedTextColor = TextPrimary
                    ),
                    maxLines = 2
                )
            }
        }

        // Assigned Foundation Model Card
        item {
            ObsidianCard {
                Text(
                    text = "Inference Model Assignment",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                    color = TextPrimary
                )
                Spacer(modifier = Modifier.height(10.dp))

                LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    items(modelOptions) { model ->
                        val isSelected = assignedModel == model
                        FilterChip(
                            selected = isSelected,
                            onClick = { assignedModel = model },
                            label = {
                                Text(
                                    text = model,
                                    fontSize = 12.sp,
                                    fontFamily = FontFamily.Monospace,
                                    fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal
                                )
                            },
                            colors = FilterChipDefaults.filterChipColors(
                                selectedContainerColor = CustomAgentColor,
                                selectedLabelColor = BackgroundDark,
                                containerColor = SurfaceVariantDark,
                                labelColor = TextSecondary
                            ),
                            border = FilterChipDefaults.filterChipBorder(
                                borderColor = if (isSelected) CustomAgentColor else BorderDark,
                                enabled = true,
                                selected = isSelected
                            ),
                            shape = RoundedCornerShape(8.dp)
                        )
                    }
                }
            }
        }

        // Behavioral System Prompt Editor
        item {
            ObsidianCard {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "System Prompt & Guidelines",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold,
                        color = TextPrimary
                    )
                    Text(
                        text = "${systemPrompt.length} chars",
                        style = MaterialTheme.typography.labelSmall,
                        fontFamily = FontFamily.Monospace,
                        color = TextMuted
                    )
                }
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = "Specify behavioral boundaries, output format, and domain constraints.",
                    style = MaterialTheme.typography.bodySmall,
                    color = TextSecondary
                )
                Spacer(modifier = Modifier.height(10.dp))

                OutlinedTextField(
                    value = systemPrompt,
                    onValueChange = { systemPrompt = it },
                    placeholder = {
                        Text(
                            "You are a specialized agent designed to analyze legal contracts, extract liabilities, and output structured Markdown summaries...",
                            color = TextMuted,
                            fontFamily = FontFamily.Monospace,
                            fontSize = 12.sp
                        )
                    },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(140.dp),
                    shape = RoundedCornerShape(10.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = CustomAgentColor,
                        unfocusedBorderColor = BorderDark,
                        focusedContainerColor = SurfaceVariantDark,
                        unfocusedContainerColor = SurfaceVariantDark,
                        focusedTextColor = TextPrimary,
                        unfocusedTextColor = TextPrimary
                    ),
                    maxLines = 8
                )
            }
        }

        // Sandboxed Tool Allowlists
        item {
            ObsidianCard {
                Text(
                    text = "Sandboxed Tool Allowlists",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                    color = TextPrimary
                )
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = "Select the device capabilities this agent is authorized to call.",
                    style = MaterialTheme.typography.bodySmall,
                    color = TextSecondary
                )
                Spacer(modifier = Modifier.height(10.dp))

                availableTools.forEach { (toolName, toolDesc) ->
                    val isChecked = selectedTools.contains(toolName)
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(8.dp))
                            .clickable {
                                if (isChecked) selectedTools.remove(toolName)
                                else selectedTools.add(toolName)
                            }
                            .padding(vertical = 6.dp, horizontal = 4.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = toolName,
                                style = MaterialTheme.typography.bodyMedium,
                                fontWeight = FontWeight.SemiBold,
                                fontFamily = FontFamily.Monospace,
                                color = if (isChecked) PrimaryAccent else TextPrimary
                            )
                            Text(
                                text = toolDesc,
                                style = MaterialTheme.typography.bodySmall,
                                color = TextSecondary,
                                fontSize = 11.sp
                            )
                        }

                        Checkbox(
                            checked = isChecked,
                            onCheckedChange = { checked ->
                                if (checked) selectedTools.add(toolName)
                                else selectedTools.remove(toolName)
                            },
                            colors = CheckboxDefaults.colors(
                                checkedColor = CustomAgentColor,
                                checkmarkColor = BackgroundDark,
                                uncheckedColor = BorderDark
                            )
                        )
                    }
                    if (toolName != availableTools.last().first) {
                        HorizontalDivider(color = BorderDark.copy(alpha = 0.5f), thickness = 0.5.dp)
                    }
                }
            }
        }

        // Execution Timeout Safeguards
        item {
            ObsidianCard {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "Execution Timeout Limit",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold,
                        color = TextPrimary
                    )
                    Surface(
                        color = PrimaryAccent.copy(alpha = 0.12f),
                        shape = RoundedCornerShape(6.dp)
                    ) {
                        Text(
                            text = "${executionLimit.toInt()}s",
                            style = MaterialTheme.typography.labelSmall,
                            fontFamily = FontFamily.Monospace,
                            fontWeight = FontWeight.Bold,
                            color = PrimaryAccent,
                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp)
                        )
                    }
                }

                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = "Prevents runaway operations or indefinite network hangs.",
                    style = MaterialTheme.typography.bodySmall,
                    color = TextSecondary
                )
                Spacer(modifier = Modifier.height(10.dp))

                Slider(
                    value = executionLimit,
                    onValueChange = { executionLimit = it },
                    valueRange = 30f..300f,
                    steps = 8,
                    colors = SliderDefaults.colors(
                        thumbColor = CustomAgentColor,
                        activeTrackColor = CustomAgentColor,
                        inactiveTrackColor = BorderDark
                    )
                )
            }
        }

        // Deploy Agent Button
        item {
            Button(
                onClick = {
                    if (name.isNotBlank() && description.isNotBlank()) {
                        coroutineScope.launch {
                            val agentId = "agent_custom_${UUID.randomUUID().toString().take(8)}"
                            val entity = AgentEntity(
                                id = agentId,
                                name = name.trim(),
                                role = "CUSTOM",
                                description = description.trim(),
                                isEnabled = true,
                                isCustom = true
                            )
                            app.database.agentDao().insertAgent(entity)

                            val config = AgentConfigEntity(
                                id = "cfg_$agentId",
                                agentId = agentId,
                                assignedModel = assignedModel,
                                providerId = "prov_autonomous",
                                systemPrompt = systemPrompt,
                                executionLimitSeconds = executionLimit.toInt(),
                                toolsJson = selectedTools.joinToString(",", "[", "]") { "\"$it\"" }
                            )
                            app.database.agentDao().insertConfig(config)

                            onBack()
                        }
                    }
                },
                enabled = name.isNotBlank() && description.isNotBlank(),
                colors = ButtonDefaults.buttonColors(
                    containerColor = CustomAgentColor,
                    contentColor = BackgroundDark,
                    disabledContainerColor = SurfaceVariantDark,
                    disabledContentColor = TextMuted
                ),
                shape = RoundedCornerShape(12.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .height(52.dp)
            ) {
                Icon(Icons.Default.Save, contentDescription = null, modifier = Modifier.size(18.dp))
                Spacer(modifier = Modifier.width(8.dp))
                Text("Deploy Custom Agent to Fleet", fontWeight = FontWeight.Bold, fontSize = 14.sp)
            }
            Spacer(modifier = Modifier.height(80.dp))
        }
    }
}
