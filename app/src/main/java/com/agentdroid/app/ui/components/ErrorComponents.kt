package com.agentdroid.app.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.agentdroid.app.ai.connection.ConnectionState
import com.agentdroid.app.ai.error.AiError
import com.agentdroid.app.ai.error.ErrorCategory
import com.agentdroid.app.ui.theme.*

/**
 * AIConnectionErrorCard: Displayed when Master Agent or any agent cannot connect to a real AI model.
 */
@Composable
fun AIConnectionErrorCard(
    error: AiError,
    onNavigateToSettings: () -> Unit,
    onRetry: (() -> Unit)? = null,
    modifier: Modifier = Modifier
) {
    ObsidianCard(
        modifier = modifier,
        borderColor = ErrorRed.copy(alpha = 0.5f),
        backgroundColor = CardBackground
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(36.dp)
                        .clip(RoundedCornerShape(8.dp))
                        .background(ErrorRed.copy(alpha = 0.15f)),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        Icons.Default.CloudOff,
                        contentDescription = null,
                        tint = ErrorRed,
                        modifier = Modifier.size(20.dp)
                    )
                }
                Spacer(modifier = Modifier.width(10.dp))
                Column {
                    Text(
                        text = error.userFriendlyTitle,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        color = TextPrimary
                    )
                    Text(
                        text = "STRICT REAL AI ENFORCEMENT",
                        style = MaterialTheme.typography.labelSmall,
                        fontSize = 9.sp,
                        letterSpacing = 1.sp,
                        fontFamily = FontFamily.Monospace,
                        color = ErrorRed
                    )
                }
            }

            Surface(
                color = ErrorRed.copy(alpha = 0.15f),
                shape = RoundedCornerShape(4.dp)
            ) {
                Text(
                    text = error.errorCode,
                    style = MaterialTheme.typography.labelSmall,
                    fontSize = 9.sp,
                    fontFamily = FontFamily.Monospace,
                    fontWeight = FontWeight.Bold,
                    color = ErrorRed,
                    modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                )
            }
        }

        Spacer(modifier = Modifier.height(10.dp))
        Text(
            text = error.userFriendlyMessage,
            style = MaterialTheme.typography.bodyMedium,
            color = TextSecondary,
            lineHeight = 20.sp
        )

        if (error.technicalDetails.isNotBlank()) {
            Spacer(modifier = Modifier.height(8.dp))
            Surface(
                color = SurfaceVariantDark,
                shape = RoundedCornerShape(6.dp),
                border = androidx.compose.foundation.BorderStroke(1.dp, BorderDark)
            ) {
                Text(
                    text = error.technicalDetails,
                    style = MaterialTheme.typography.labelSmall,
                    fontSize = 10.sp,
                    fontFamily = FontFamily.Monospace,
                    color = TextMuted,
                    modifier = Modifier.padding(8.dp),
                    maxLines = 3
                )
            }
        }

        Spacer(modifier = Modifier.height(14.dp))
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.End,
            verticalAlignment = Alignment.CenterVertically
        ) {
            if (onRetry != null && error.retryAvailable) {
                RetryButton(onClick = onRetry)
                Spacer(modifier = Modifier.width(8.dp))
            }
            ConnectProviderButton(onClick = onNavigateToSettings)
        }
    }
}

/**
 * ProviderErrorCard: Shows provider validation failure in Settings or inspector.
 */
@Composable
fun ProviderErrorCard(
    providerName: String,
    state: ConnectionState,
    error: AiError?,
    onTestConnection: () -> Unit,
    onEditKey: () -> Unit,
    modifier: Modifier = Modifier
) {
    val stateColor = when (state) {
        ConnectionState.CONNECTED -> SuccessGreen
        ConnectionState.AUTHENTICATION_FAILED, ConnectionState.INVALID_API_KEY -> ErrorRed
        ConnectionState.RATE_LIMITED -> WarningAmber
        ConnectionState.NETWORK_ERROR, ConnectionState.REQUEST_TIMEOUT -> WarningAmber
        else -> TextMuted
    }

    ObsidianCard(
        modifier = modifier,
        borderColor = stateColor.copy(alpha = 0.4f),
        backgroundColor = SurfaceVariantDark
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = providerName,
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.Bold,
                color = TextPrimary
            )
            Surface(
                color = stateColor.copy(alpha = 0.15f),
                shape = RoundedCornerShape(4.dp)
            ) {
                Text(
                    text = state.name.replace("_", " "),
                    color = stateColor,
                    style = MaterialTheme.typography.labelSmall,
                    fontSize = 9.sp,
                    fontFamily = FontFamily.Monospace,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                )
            }
        }

        if (error != null) {
            Spacer(modifier = Modifier.height(6.dp))
            Text(
                text = error.userFriendlyMessage,
                style = MaterialTheme.typography.bodySmall,
                color = TextSecondary
            )
        }

        Spacer(modifier = Modifier.height(10.dp))
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.End
        ) {
            OutlinedButton(
                onClick = onEditKey,
                shape = RoundedCornerShape(6.dp),
                colors = ButtonDefaults.outlinedButtonColors(contentColor = PrimaryAccent),
                contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp),
                modifier = Modifier.height(32.dp)
            ) {
                Text("Update Key", fontSize = 11.sp)
            }
            Spacer(modifier = Modifier.width(8.dp))
            Button(
                onClick = onTestConnection,
                shape = RoundedCornerShape(6.dp),
                colors = ButtonDefaults.buttonColors(containerColor = PrimaryAccent, contentColor = BackgroundDark),
                contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp),
                modifier = Modifier.height(32.dp)
            ) {
                Text("Test Connection", fontSize = 11.sp, fontWeight = FontWeight.Bold)
            }
        }
    }
}

/**
 * TaskFailureCard: Summarizes failed agent subtasks in DAG or reports.
 */
@Composable
fun TaskFailureCard(
    taskTitle: String,
    agentRole: String,
    errorMessage: String,
    onRetry: (() -> Unit)? = null,
    modifier: Modifier = Modifier
) {
    ObsidianCard(
        modifier = modifier,
        borderColor = ErrorRed.copy(alpha = 0.4f),
        backgroundColor = CardBackground
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "TASK FAILED • $agentRole",
                style = MaterialTheme.typography.labelSmall,
                fontSize = 10.sp,
                fontFamily = FontFamily.Monospace,
                color = ErrorRed,
                fontWeight = FontWeight.Bold
            )
            Icon(Icons.Default.ErrorOutline, contentDescription = null, tint = ErrorRed, modifier = Modifier.size(16.dp))
        }

        Spacer(modifier = Modifier.height(6.dp))
        Text(text = taskTitle, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold, color = TextPrimary)
        Spacer(modifier = Modifier.height(4.dp))
        Text(text = errorMessage, style = MaterialTheme.typography.bodySmall, color = TextSecondary)

        if (onRetry != null) {
            Spacer(modifier = Modifier.height(10.dp))
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                RetryButton(onClick = onRetry)
            }
        }
    }
}

/**
 * NetworkErrorBanner: Compact offline banner.
 */
@Composable
fun NetworkErrorBanner(
    message: String = "Network Offline: Real AI model requests unavailable",
    onRetry: () -> Unit,
    modifier: Modifier = Modifier
) {
    Surface(
        modifier = modifier.fillMaxWidth(),
        color = ErrorRed.copy(alpha = 0.15f),
        border = androidx.compose.foundation.BorderStroke(1.dp, ErrorRed.copy(alpha = 0.4f)),
        shape = RoundedCornerShape(8.dp)
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.WifiOff, contentDescription = null, tint = ErrorRed, modifier = Modifier.size(16.dp))
                Spacer(modifier = Modifier.width(8.dp))
                Text(text = message, style = MaterialTheme.typography.bodySmall, color = TextPrimary, fontSize = 11.sp)
            }
            TextButton(
                onClick = onRetry,
                contentPadding = PaddingValues(horizontal = 6.dp, vertical = 2.dp)
            ) {
                Text("Retry", color = ErrorRed, fontSize = 11.sp, fontWeight = FontWeight.Bold)
            }
        }
    }
}

/**
 * ModelStatusIndicator: Status badge displaying model connectivity.
 */
@Composable
fun ModelStatusIndicator(
    modelName: String,
    state: ConnectionState,
    modifier: Modifier = Modifier
) {
    val (dotColor, statusText) = when (state) {
        ConnectionState.CONNECTED -> SuccessGreen to "ONLINE"
        ConnectionState.CONNECTING -> PrimaryAccent to "CONNECTING"
        ConnectionState.CONFIGURED -> WarningAmber to "UNVERIFIED"
        ConnectionState.NOT_CONFIGURED -> TextMuted to "NOT CONNECTED"
        ConnectionState.INVALID_API_KEY, ConnectionState.AUTHENTICATION_FAILED -> ErrorRed to "AUTH FAILED"
        ConnectionState.RATE_LIMITED -> WarningAmber to "RATE LIMITED"
        ConnectionState.NETWORK_ERROR -> ErrorRed to "NETWORK ERROR"
        ConnectionState.PROVIDER_UNAVAILABLE, ConnectionState.REQUEST_TIMEOUT -> ErrorRed to "OFFLINE"
        else -> TextMuted to "OFFLINE"
    }

    Surface(
        modifier = modifier,
        color = SurfaceVariantDark,
        shape = RoundedCornerShape(20.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, BorderDark)
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(6.dp)
                    .clip(CircleShape)
                    .background(dotColor)
            )
            Spacer(modifier = Modifier.width(6.dp))
            Text(
                text = "$modelName • $statusText",
                style = MaterialTheme.typography.labelSmall,
                fontSize = 10.sp,
                fontFamily = FontFamily.Monospace,
                color = TextPrimary
            )
        }
    }
}

/**
 * RetryButton: Reusable retry action button.
 */
@Composable
fun RetryButton(
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    OutlinedButton(
        onClick = onClick,
        shape = RoundedCornerShape(8.dp),
        colors = ButtonDefaults.outlinedButtonColors(contentColor = PrimaryAccent),
        border = androidx.compose.foundation.BorderStroke(1.dp, BorderDark),
        contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp),
        modifier = modifier.height(34.dp)
    ) {
        Icon(Icons.Default.Refresh, contentDescription = null, modifier = Modifier.size(14.dp))
        Spacer(modifier = Modifier.width(4.dp))
        Text("Retry", fontSize = 11.sp, fontWeight = FontWeight.SemiBold)
    }
}

/**
 * ConnectProviderButton: Navigates user to AI Provider Settings.
 */
@Composable
fun ConnectProviderButton(
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Button(
        onClick = onClick,
        shape = RoundedCornerShape(8.dp),
        colors = ButtonDefaults.buttonColors(containerColor = PrimaryAccent, contentColor = BackgroundDark),
        contentPadding = PaddingValues(horizontal = 12.dp, vertical = 4.dp),
        modifier = modifier.height(34.dp)
    ) {
        Icon(Icons.Default.Settings, contentDescription = null, modifier = Modifier.size(14.dp))
        Spacer(modifier = Modifier.width(6.dp))
        Text("Connect AI Provider", fontSize = 11.sp, fontWeight = FontWeight.Bold)
    }
}
