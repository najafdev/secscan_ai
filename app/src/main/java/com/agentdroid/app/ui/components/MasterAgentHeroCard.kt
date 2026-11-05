package com.agentdroid.app.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Forum
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.agentdroid.app.domain.model.AgentExecutionState
import com.agentdroid.app.ui.theme.*

@Composable
fun MasterAgentHeroCard(
    status: String,
    activeAgentsCount: Int,
    runningTasksCount: Int,
    executionState: AgentExecutionState,
    onChatClick: (() -> Unit)? = null,
    modifier: Modifier = Modifier
) {
    val shape = RoundedCornerShape(18.dp)

    Box(
        modifier = modifier
            .fillMaxWidth()
            .clip(shape)
            .background(
                Brush.verticalGradient(
                    colors = listOf(
                        SurfaceVariantDark,
                        CardBackground
                    )
                )
            )
            .border(1.dp, BorderDark, shape)
            .then(
                if (onChatClick != null) Modifier.clickable { onChatClick() }
                else Modifier
            )
            .padding(18.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = "CORE ORCHESTRATOR",
                        style = MaterialTheme.typography.labelSmall,
                        color = PrimaryAccent,
                        letterSpacing = 1.2.sp
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    AgentStatusBadge(state = executionState)
                }

                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = "Master Agent",
                    style = MaterialTheme.typography.headlineMedium,
                    fontWeight = FontWeight.Bold,
                    color = TextPrimary
                )
                Spacer(modifier = Modifier.height(3.dp))
                Text(
                    text = if (status == "Idle") "Monitoring device state. Ready for goal delegation." else "Status: $status",
                    style = MaterialTheme.typography.bodyMedium,
                    color = TextSecondary,
                    maxLines = 2
                )

                Spacer(modifier = Modifier.height(14.dp))

                // Telemetry mini-badges
                Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                    Column {
                        Text(
                            text = "$activeAgentsCount",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                            color = PrimaryAccent
                        )
                        Text(
                            text = "Agents Online",
                            style = MaterialTheme.typography.labelSmall,
                            color = TextMuted,
                            fontSize = 9.sp
                        )
                    }

                    Column {
                        Text(
                            text = "$runningTasksCount",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                            color = if (runningTasksCount > 0) SuccessGreen else TextSecondary
                        )
                        Text(
                            text = "Active Tasks",
                            style = MaterialTheme.typography.labelSmall,
                            color = TextMuted,
                            fontSize = 9.sp
                        )
                    }
                }

                if (onChatClick != null) {
                    Spacer(modifier = Modifier.height(14.dp))
                    Button(
                        onClick = onChatClick,
                        colors = ButtonDefaults.buttonColors(
                            containerColor = PrimaryAccent,
                            contentColor = BackgroundDark
                        ),
                        shape = RoundedCornerShape(10.dp),
                        contentPadding = PaddingValues(horizontal = 14.dp, vertical = 6.dp),
                        modifier = Modifier.height(34.dp)
                    ) {
                        Icon(Icons.Default.Forum, contentDescription = null, modifier = Modifier.size(15.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Chat with Master Agent", fontSize = 11.5.sp, fontWeight = FontWeight.Bold)
                    }
                }
            }

            Spacer(modifier = Modifier.width(12.dp))

            // Cinematic AI Core Visualizer Orb
            MasterAgentVisualizer(
                state = executionState,
                size = 96.dp
            )
        }
    }
}
