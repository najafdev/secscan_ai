package com.agentdroid.app.ui.components

import androidx.compose.animation.core.*
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.agentdroid.app.domain.model.AgentExecutionState
import com.agentdroid.app.ui.theme.*
import kotlin.math.cos
import kotlin.math.sin

@Composable
fun MasterAgentVisualizer(
    state: AgentExecutionState,
    modifier: Modifier = Modifier,
    size: Dp = 100.dp
) {
    val infiniteTransition = rememberInfiniteTransition(label = "ai_core_anim")

    // Slow breathing animation (used for Idle and baseline glow)
    val breathingPulse by infiniteTransition.animateFloat(
        initialValue = 0.82f,
        targetValue = 1.05f,
        animationSpec = infiniteRepeatable(
            animation = tween(2800, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "pulse"
    )

    // Smooth rotation angle for outer orbitals
    val rotationAngle by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 360f,
        animationSpec = infiniteRepeatable(
            animation = tween(if (state == AgentExecutionState.RUNNING) 3200 else 8000, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "rotation"
    )

    // Counter-rotation angle for inner core rings
    val counterRotation by infiniteTransition.animateFloat(
        initialValue = 360f,
        targetValue = 0f,
        animationSpec = infiniteRepeatable(
            animation = tween(if (state == AgentExecutionState.THINKING) 2400 else 6000, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "counter_rotation"
    )

    // Expanding ripple waves (used for Listening / Working)
    val waveRadiusFraction by infiniteTransition.animateFloat(
        initialValue = 0.2f,
        targetValue = 1.0f,
        animationSpec = infiniteRepeatable(
            animation = tween(1800, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "wave"
    )

    // State-driven core theme colors
    val (coreColor, accentGlow) = when (state) {
        AgentExecutionState.IDLE -> PrimaryAccent to SecondaryAccent
        AgentExecutionState.THINKING -> PrimaryAccent to ElectricBlue
        AgentExecutionState.PLANNING -> ElectricBlue to SecondaryAccent
        AgentExecutionState.RUNNING -> SecondaryAccent to PrimaryAccent
        AgentExecutionState.WAITING_FOR_APPROVAL -> WarningAmber to WarningAmber.copy(alpha = 0.6f)
        AgentExecutionState.COMPLETED -> SuccessGreen to SuccessGreen.copy(alpha = 0.5f)
        AgentExecutionState.FAILED -> ErrorRed to ErrorRed.copy(alpha = 0.6f)
        AgentExecutionState.CANCELLED -> TextMuted to BorderDark
        else -> PrimaryAccent to SecondaryAccent
    }

    Box(
        modifier = modifier.size(size)
    ) {
        Canvas(modifier = Modifier.fillMaxSize()) {
            val center = Offset(size.toPx() / 2f, size.toPx() / 2f)
            val maxRadius = size.toPx() / 2f * 0.95f
            val baseRadius = maxRadius * 0.45f

            // 1. Ambient Background Radial Glow
            val glowRadius = maxRadius * (if (state == AgentExecutionState.RUNNING) 1.2f else breathingPulse)
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(
                        accentGlow.copy(alpha = if (state == AgentExecutionState.RUNNING) 0.35f else 0.20f),
                        coreColor.copy(alpha = 0.08f),
                        Color.Transparent
                    ),
                    center = center,
                    radius = glowRadius
                ),
                radius = glowRadius,
                center = center
            )

            // 2. State-specific wave expansions (Listening / Working)
            if (state == AgentExecutionState.RUNNING || state == AgentExecutionState.ASSIGNED) {
                val waveR = baseRadius + (maxRadius - baseRadius) * waveRadiusFraction
                val waveAlpha = (1f - waveRadiusFraction).coerceIn(0f, 0.8f)
                drawCircle(
                    color = coreColor.copy(alpha = waveAlpha * 0.4f),
                    radius = waveR,
                    center = center,
                    style = Stroke(width = 1.5.dp.toPx())
                )
            }

            // 3. Outer Segmented Orbitals / Rotating Rings
            rotate(rotationAngle, pivot = center) {
                drawArc(
                    color = coreColor.copy(alpha = 0.7f),
                    startAngle = 0f,
                    sweepAngle = 110f,
                    useCenter = false,
                    topLeft = Offset(center.x - maxRadius * 0.85f, center.y - maxRadius * 0.85f),
                    size = androidx.compose.ui.geometry.Size(maxRadius * 1.7f, maxRadius * 1.7f),
                    style = Stroke(width = 1.8.dp.toPx(), cap = StrokeCap.Round)
                )
                drawArc(
                    color = accentGlow.copy(alpha = 0.5f),
                    startAngle = 180f,
                    sweepAngle = 90f,
                    useCenter = false,
                    topLeft = Offset(center.x - maxRadius * 0.85f, center.y - maxRadius * 0.85f),
                    size = androidx.compose.ui.geometry.Size(maxRadius * 1.7f, maxRadius * 1.7f),
                    style = Stroke(width = 1.8.dp.toPx(), cap = StrokeCap.Round)
                )

                // Orbital particle dot
                val dotX = center.x + maxRadius * 0.85f * cos(Math.toRadians(0.0)).toFloat()
                val dotY = center.y + maxRadius * 0.85f * sin(Math.toRadians(0.0)).toFloat()
                drawCircle(
                    color = Color.White,
                    radius = 2.dp.toPx(),
                    center = Offset(dotX, dotY)
                )
            }

            // 4. Inner Orbitals / Counter-rotating Ring
            rotate(counterRotation, pivot = center) {
                drawArc(
                    color = coreColor.copy(alpha = 0.45f),
                    startAngle = 60f,
                    sweepAngle = 140f,
                    useCenter = false,
                    topLeft = Offset(center.x - maxRadius * 0.65f, center.y - maxRadius * 0.65f),
                    size = androidx.compose.ui.geometry.Size(maxRadius * 1.3f, maxRadius * 1.3f),
                    style = Stroke(width = 1.2.dp.toPx(), cap = StrokeCap.Round)
                )
                drawArc(
                    color = accentGlow.copy(alpha = 0.35f),
                    startAngle = 240f,
                    sweepAngle = 70f,
                    useCenter = false,
                    topLeft = Offset(center.x - maxRadius * 0.65f, center.y - maxRadius * 0.65f),
                    size = androidx.compose.ui.geometry.Size(maxRadius * 1.3f, maxRadius * 1.3f),
                    style = Stroke(width = 1.2.dp.toPx(), cap = StrokeCap.Round)
                )
            }

            // 5. Central AI Orb Core with Radial Gradient & Specular Center
            val innerCoreRadius = baseRadius * (if (state == AgentExecutionState.IDLE) breathingPulse else 1.0f)
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(
                        Color.White.copy(alpha = 0.95f),
                        coreColor,
                        accentGlow.copy(alpha = 0.85f),
                        CardBackground
                    ),
                    center = Offset(center.x - innerCoreRadius * 0.2f, center.y - innerCoreRadius * 0.2f),
                    radius = innerCoreRadius
                ),
                radius = innerCoreRadius,
                center = center
            )

            // Inner Core Fine Rim
            drawCircle(
                color = coreColor.copy(alpha = 0.8f),
                radius = innerCoreRadius,
                center = center,
                style = Stroke(width = 1.dp.toPx())
            )
        }
    }
}
