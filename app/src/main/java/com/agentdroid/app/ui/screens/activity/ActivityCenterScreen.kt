package com.agentdroid.app.ui.screens.activity

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import com.agentdroid.app.domain.model.AgentRole
import com.agentdroid.app.domain.model.RiskLevel
import com.agentdroid.app.ui.components.ObsidianCard
import com.agentdroid.app.ui.components.RiskBadge
import com.agentdroid.app.ui.theme.*
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun ActivityCenterScreen() {
    val app = AgentDroidApplication.instance
    val coroutineScope = rememberCoroutineScope()
    val logs by app.database.activityLogDao().getRecentLogs().collectAsState(initial = emptyList())

    val dateFormat = remember { SimpleDateFormat("HH:mm:ss", Locale.getDefault()) }
    var selectedFilter by remember { mutableStateOf("ALL") }

    val filterOptions = listOf("ALL", "PHONE", "SOCIAL", "SECURITY", "ERRORS")

    val filteredLogs = remember(logs, selectedFilter) {
        when (selectedFilter) {
            "PHONE" -> logs.filter { it.agentRole.contains("PHONE", ignoreCase = true) }
            "SOCIAL" -> logs.filter { it.agentRole.contains("SOCIAL", ignoreCase = true) }
            "SECURITY" -> logs.filter { it.agentRole.contains("SECURITY", ignoreCase = true) || it.riskLevel == "HIGH" || it.riskLevel == "CRITICAL" }
            "ERRORS" -> logs.filter { it.status.equals("FAILED", ignoreCase = true) }
            else -> logs
        }
    }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(BackgroundDark)
            .padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        // Top Header
        item {
            Spacer(modifier = Modifier.height(16.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        text = "AUDIT TIMELINE",
                        style = MaterialTheme.typography.labelSmall,
                        letterSpacing = 2.sp,
                        color = ElectricBlue,
                        fontFamily = FontFamily.Monospace
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "System Activity Center",
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold,
                        color = TextPrimary
                    )
                }

                if (logs.isNotEmpty()) {
                    IconButton(
                        onClick = {
                            coroutineScope.launch {
                                app.database.activityLogDao().clearLogs()
                            }
                        },
                        modifier = Modifier
                            .clip(CircleShape)
                            .background(SurfaceVariantDark)
                    ) {
                        Icon(
                            Icons.Default.DeleteSweep,
                            contentDescription = "Clear Logs",
                            tint = TextSecondary,
                            modifier = Modifier.size(20.dp)
                        )
                    }
                }
            }
        }

        // Filter Chips Row
        item {
            LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                items(filterOptions) { filter ->
                    val isSelected = selectedFilter == filter
                    FilterChip(
                        selected = isSelected,
                        onClick = { selectedFilter = filter },
                        label = {
                            Text(
                                text = filter,
                                fontSize = 11.sp,
                                fontFamily = FontFamily.Monospace,
                                fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal
                            )
                        },
                        colors = FilterChipDefaults.filterChipColors(
                            selectedContainerColor = PrimaryAccent,
                            selectedLabelColor = BackgroundDark,
                            containerColor = CardBackground,
                            labelColor = TextSecondary
                        ),
                        border = FilterChipDefaults.filterChipBorder(
                            borderColor = if (isSelected) PrimaryAccent else BorderDark,
                            enabled = true,
                            selected = isSelected
                        ),
                        shape = RoundedCornerShape(8.dp)
                    )
                }
            }
            Spacer(modifier = Modifier.height(4.dp))
        }

        // Empty State
        if (filteredLogs.isEmpty()) {
            item {
                ObsidianCard {
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 24.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Box(
                            modifier = Modifier
                                .size(48.dp)
                                .clip(CircleShape)
                                .background(SurfaceVariantDark),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                Icons.Default.History,
                                contentDescription = null,
                                tint = TextMuted,
                                modifier = Modifier.size(24.dp)
                            )
                        }
                        Spacer(modifier = Modifier.height(12.dp))
                        Text(
                            text = if (logs.isEmpty()) "No activity recorded yet" else "No matching logs for filter",
                            style = MaterialTheme.typography.bodyLarge,
                            fontWeight = FontWeight.SemiBold,
                            color = TextPrimary
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = "Execute commands or workflows to inspect the real-time agent audit stream.",
                            style = MaterialTheme.typography.bodySmall,
                            color = TextSecondary
                        )
                    }
                }
            }
        }

        // Connected Timeline Items
        items(filteredLogs) { log ->
            val roleEnum = try { AgentRole.valueOf(log.agentRole) } catch (e: Exception) { AgentRole.MASTER }
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

            val riskEnum = try { RiskLevel.valueOf(log.riskLevel) } catch (e: Exception) { RiskLevel.LOW }
            val isSuccess = log.status.equals("COMPLETED", ignoreCase = true)
            val isFailed = log.status.equals("FAILED", ignoreCase = true)

            // Timeline Row with vertical connector
            Row(modifier = Modifier.fillMaxWidth()) {
                // Vertical Timeline Spine & Node Dot
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    modifier = Modifier.width(24.dp)
                ) {
                    Box(
                        modifier = Modifier
                            .size(10.dp)
                            .clip(CircleShape)
                            .background(if (isFailed) ErrorRed else roleColor)
                    )
                    Box(
                        modifier = Modifier
                            .width(1.5.dp)
                            .fillMaxHeight()
                            .defaultMinSize(minHeight = 70.dp)
                            .background(BorderDark)
                    )
                }

                Spacer(modifier = Modifier.width(8.dp))

                // Log Detail Obsidian Card
                Box(modifier = Modifier.weight(1f)) {
                    ObsidianCard(
                        borderColor = if (isFailed) ErrorRed.copy(alpha = 0.5f) else BorderDark,
                        backgroundColor = CardBackground
                    ) {
                        // Card Header: Role & Timestamp
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Text(
                                    text = roleEnum.displayName.uppercase(),
                                    style = MaterialTheme.typography.labelSmall,
                                    fontWeight = FontWeight.Bold,
                                    fontFamily = FontFamily.Monospace,
                                    color = roleColor,
                                    fontSize = 11.sp
                                )
                                Spacer(modifier = Modifier.width(8.dp))
                                RiskBadge(riskEnum)
                            }

                            Text(
                                text = dateFormat.format(Date(log.timestamp)),
                                style = MaterialTheme.typography.labelSmall,
                                fontFamily = FontFamily.Monospace,
                                color = TextMuted,
                                fontSize = 11.sp
                            )
                        }

                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = log.description,
                            style = MaterialTheme.typography.bodyMedium,
                            color = TextPrimary,
                            lineHeight = 20.sp
                        )

                        Spacer(modifier = Modifier.height(10.dp))
                        HorizontalDivider(color = BorderDark.copy(alpha = 0.5f), thickness = 0.5.dp)
                        Spacer(modifier = Modifier.height(8.dp))

                        // Footer: Action Type & Status
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = "ACTION: ${log.actionType}",
                                style = MaterialTheme.typography.labelSmall,
                                fontFamily = FontFamily.Monospace,
                                color = TextSecondary,
                                fontSize = 10.sp
                            )

                            Surface(
                                color = when {
                                    isFailed -> ErrorRed.copy(alpha = 0.15f)
                                    isSuccess -> SuccessGreen.copy(alpha = 0.15f)
                                    else -> PrimaryAccent.copy(alpha = 0.15f)
                                },
                                shape = RoundedCornerShape(4.dp)
                            ) {
                                Text(
                                    text = log.status.uppercase(),
                                    style = MaterialTheme.typography.labelSmall,
                                    fontFamily = FontFamily.Monospace,
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 10.sp,
                                    color = when {
                                        isFailed -> ErrorRed
                                        isSuccess -> SuccessGreen
                                        else -> PrimaryAccent
                                    },
                                    modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                                )
                            }
                        }
                    }
                }
            }
        }

        item { Spacer(modifier = Modifier.height(80.dp)) }
    }
}
