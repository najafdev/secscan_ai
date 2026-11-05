package com.agentdroid.app.ui.components

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.agentdroid.app.domain.model.*
import com.agentdroid.app.ui.theme.*

/**
 * ObsidianCard: Core surface container for AgentDroid UI.
 * Inspired by Linear & Nothing OS: deep graphite solid background, fine charcoal border,
 * optional subtle ambient violet highlight.
 */
@Composable
fun ObsidianCard(
    modifier: Modifier = Modifier,
    borderColor: Color = BorderDark,
    backgroundColor: Color = CardBackground,
    highlightGlow: Boolean = false,
    onClick: (() -> Unit)? = null,
    content: @Composable ColumnScope.() -> Unit
) {
    val shape = RoundedCornerShape(14.dp)
    val cardModifier = if (onClick != null) {
        modifier
            .fillMaxWidth()
            .clip(shape)
            .clickable(onClick = onClick)
            .background(backgroundColor)
            .border(
                1.dp,
                if (highlightGlow) PrimaryAccent.copy(alpha = 0.5f) else borderColor,
                shape
            )
    } else {
        modifier
            .fillMaxWidth()
            .clip(shape)
            .background(backgroundColor)
            .border(
                1.dp,
                if (highlightGlow) PrimaryAccent.copy(alpha = 0.5f) else borderColor,
                shape
            )
    }

    Column(
        modifier = cardModifier.padding(16.dp),
        content = content
    )
}

// Backward compatible alias
@Composable
fun GlassCard(
    modifier: Modifier = Modifier,
    borderColor: Color = BorderDark,
    backgroundColor: Color = CardBackground,
    content: @Composable ColumnScope.() -> Unit
) {
    ObsidianCard(
        modifier = modifier,
        borderColor = borderColor,
        backgroundColor = backgroundColor,
        content = content
    )
}

/**
 * AgentStatusBadge: Minimal status pill with pulsing breathing dot.
 */
@Composable
fun AgentStatusBadge(
    state: AgentExecutionState,
    modifier: Modifier = Modifier
) {
    val (color, text) = when (state) {
        AgentExecutionState.IDLE -> TextSecondary to "IDLE"
        AgentExecutionState.THINKING -> PrimaryAccent to "THINKING"
        AgentExecutionState.PLANNING -> ElectricBlue to "PLANNING"
        AgentExecutionState.ASSIGNED -> PrimaryAccent to "ASSIGNED"
        AgentExecutionState.RUNNING -> SecondaryAccent to "RUNNING"
        AgentExecutionState.WAITING_FOR_APPROVAL -> WarningAmber to "APPROVAL"
        AgentExecutionState.COMPLETED -> SuccessGreen to "DONE"
        AgentExecutionState.FAILED -> ErrorRed to "FAILED"
        AgentExecutionState.CANCELLED -> TextMuted to "HALTED"
    }

    val infiniteTransition = rememberInfiniteTransition(label = "badge_pulse")
    val dotAlpha by infiniteTransition.animateFloat(
        initialValue = 0.35f,
        targetValue = 1.0f,
        animationSpec = infiniteRepeatable(
            animation = tween(900, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "dot_alpha"
    )

    Surface(
        color = color.copy(alpha = 0.12f),
        shape = RoundedCornerShape(16.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, color.copy(alpha = 0.28f)),
        modifier = modifier
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp)
        ) {
            Box(
                modifier = Modifier
                    .size(5.dp)
                    .clip(CircleShape)
                    .background(color.copy(alpha = if (state == AgentExecutionState.RUNNING || state == AgentExecutionState.THINKING) dotAlpha else 0.85f))
            )
            Spacer(modifier = Modifier.width(6.dp))
            Text(
                text = text,
                style = MaterialTheme.typography.labelSmall,
                color = color,
                fontSize = 9.5.sp,
                letterSpacing = 0.5.sp
            )
        }
    }
}

/**
 * RiskBadge: Human-in-the-loop security risk tier pill.
 */
@Composable
fun RiskBadge(riskLevel: RiskLevel) {
    val (color, label) = when (riskLevel) {
        RiskLevel.LOW -> SuccessGreen to "LOW RISK"
        RiskLevel.MEDIUM -> WarningAmber to "MEDIUM RISK"
        RiskLevel.HIGH -> ErrorRed to "HIGH RISK"
    }
    Surface(
        color = color.copy(alpha = 0.10f),
        shape = RoundedCornerShape(4.dp),
        border = androidx.compose.foundation.BorderStroke(0.8.dp, color.copy(alpha = 0.35f))
    ) {
        Text(
            text = label,
            color = color,
            style = MaterialTheme.typography.labelSmall,
            fontSize = 9.sp,
            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
        )
    }
}

/**
 * MetricCard: Clean numerical stat display with subtle telemetry accent.
 */
@Composable
fun MetricCard(
    title: String,
    value: String,
    subtitle: String,
    accentColor: Color = PrimaryAccent,
    modifier: Modifier = Modifier
) {
    ObsidianCard(
        modifier = modifier,
        borderColor = BorderDark
    ) {
        Text(
            text = title.uppercase(),
            style = MaterialTheme.typography.labelSmall,
            color = TextSecondary,
            letterSpacing = 0.8.sp
        )
        Spacer(modifier = Modifier.height(4.dp))
        Text(
            text = value,
            style = MaterialTheme.typography.titleLarge,
            fontWeight = FontWeight.Bold,
            color = accentColor
        )
        Spacer(modifier = Modifier.height(2.dp))
        Text(
            text = subtitle,
            style = MaterialTheme.typography.bodySmall,
            color = TextMuted
        )
    }
}

/**
 * TaskCard: Multi-agent execution DAG item card.
 */
@Composable
fun TaskCard(
    task: TaskItem,
    onApprove: (() -> Unit)? = null,
    onReject: (() -> Unit)? = null,
    modifier: Modifier = Modifier
) {
    val roleColor = when (task.agentRole) {
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

    val isPendingApproval = task.status == TaskStatus.WAITING_APPROVAL

    ObsidianCard(
        modifier = modifier,
        borderColor = if (isPendingApproval) WarningAmber.copy(alpha = 0.7f) else BorderDark,
        highlightGlow = isPendingApproval
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(8.dp)
                        .clip(CircleShape)
                        .background(roleColor)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = task.agentRole.displayName,
                    style = MaterialTheme.typography.labelSmall,
                    color = roleColor,
                    fontWeight = FontWeight.SemiBold
                )
            }
            RiskBadge(task.riskLevel)
        }

        Spacer(modifier = Modifier.height(8.dp))
        Text(
            text = task.title,
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.SemiBold,
            color = TextPrimary
        )
        Spacer(modifier = Modifier.height(3.dp))
        Text(
            text = task.description,
            style = MaterialTheme.typography.bodyMedium,
            color = TextSecondary
        )

        Spacer(modifier = Modifier.height(10.dp))
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                val statusColor = when (task.status) {
                    TaskStatus.COMPLETED -> SuccessGreen
                    TaskStatus.RUNNING -> PrimaryAccent
                    TaskStatus.WAITING_APPROVAL -> WarningAmber
                    TaskStatus.FAILED -> ErrorRed
                    TaskStatus.SKIPPED, TaskStatus.CANCELLED -> TextMuted
                    else -> TextSecondary
                }
                Text(
                    text = "STATUS: ${task.status.name}",
                    style = MaterialTheme.typography.labelSmall,
                    color = statusColor,
                    fontSize = 9.5.sp
                )
                if (task.toolName != null) {
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "• ${task.toolName}",
                        style = MaterialTheme.typography.labelSmall,
                        color = TextMuted,
                        fontSize = 9.5.sp
                    )
                }
            }

            if (isPendingApproval && onApprove != null && onReject != null) {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(
                        onClick = onReject,
                        colors = ButtonDefaults.outlinedButtonColors(contentColor = ErrorRed),
                        shape = RoundedCornerShape(6.dp),
                        contentPadding = PaddingValues(horizontal = 8.dp, vertical = 2.dp),
                        modifier = Modifier.height(28.dp)
                    ) {
                        Text("Deny", fontSize = 11.sp)
                    }
                    Button(
                        onClick = onApprove,
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

/**
 * AnimatedTypingIndicator: Smooth 3-dot wave for AI thinking/streaming states.
 */
@Composable
fun AnimatedTypingIndicator(modifier: Modifier = Modifier) {
    val transition = rememberInfiniteTransition(label = "typing_dots")

    @Composable
    fun dotScale(delayMs: Int): State<Float> = transition.animateFloat(
        initialValue = 0.4f,
        targetValue = 1.0f,
        animationSpec = infiniteRepeatable(
            animation = tween(600, delayMillis = delayMs, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "dot_scale"
    )

    val scale1 by dotScale(0)
    val scale2 by dotScale(150)
    val scale3 by dotScale(300)

    Row(
        modifier = modifier.padding(horizontal = 4.dp, vertical = 6.dp),
        horizontalArrangement = Arrangement.spacedBy(4.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(modifier = Modifier.size(6.dp).scale(scale1).clip(CircleShape).background(PrimaryAccent))
        Box(modifier = Modifier.size(6.dp).scale(scale2).clip(CircleShape).background(PrimaryAccent))
        Box(modifier = Modifier.size(6.dp).scale(scale3).clip(CircleShape).background(PrimaryAccent))
    }
}
