package com.agentdroid.app.ui.screens.social

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
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
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.agentdroid.app.AgentDroidApplication
import com.agentdroid.app.data.local.entity.ConnectedAccountEntity
import com.agentdroid.app.domain.model.PlatformType
import com.agentdroid.app.ui.components.ObsidianCard
import com.agentdroid.app.ui.theme.*
import org.json.JSONObject

@Composable
fun ConnectSocialAccountDialog(
    initialPlatform: PlatformType = PlatformType.TWITTER,
    existingAccount: ConnectedAccountEntity? = null,
    onDismiss: () -> Unit,
    onSave: (
        platform: PlatformType,
        username: String,
        displayName: String,
        token: String,
        autoDraft: Boolean,
        requireApproval: Boolean
    ) -> Unit,
    onDisconnect: ((accountId: String) -> Unit)? = null
) {
    val app = AgentDroidApplication.instance
    var selectedPlatform by remember {
        mutableStateOf(
            if (existingAccount != null) {
                try {
                    PlatformType.valueOf(existingAccount.platform)
                } catch (e: Exception) {
                    initialPlatform
                }
            } else {
                initialPlatform
            }
        )
    }

    var username by remember { mutableStateOf(existingAccount?.username ?: "") }
    var displayName by remember { mutableStateOf(existingAccount?.displayName ?: "") }

    val savedToken = remember(selectedPlatform) {
        app.securePreferences.getSocialToken(selectedPlatform.name)
    }
    var token by remember { mutableStateOf(savedToken) }
    var showToken by remember { mutableStateOf(false) }

    // Parse permissionsJson
    var autoDraft by remember {
        val json = existingAccount?.permissionsJson ?: "{}"
        val parsed = try { JSONObject(json).optBoolean("autoDraft", true) } catch (e: Exception) { true }
        mutableStateOf(parsed)
    }
    var requireApproval by remember {
        val json = existingAccount?.permissionsJson ?: "{}"
        val parsed = try { JSONObject(json).optBoolean("requireApproval", true) } catch (e: Exception) { true }
        mutableStateOf(parsed)
    }

    var validationError by remember { mutableStateOf<String?>(null) }

    Dialog(
        onDismissRequest = onDismiss,
        properties = DialogProperties(usePlatformDefaultWidth = false)
    ) {
        Surface(
            modifier = Modifier
                .fillMaxWidth(0.95f)
                .fillMaxHeight(0.90f)
                .clip(RoundedCornerShape(16.dp))
                .border(1.dp, BorderDark, RoundedCornerShape(16.dp)),
            color = BackgroundDark
        ) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(18.dp)
            ) {
                // Header
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text(
                            text = if (existingAccount != null) "MANAGE SOCIAL CHANNEL" else "LINK SOCIAL CHANNEL",
                            style = MaterialTheme.typography.labelSmall,
                            letterSpacing = 1.5.sp,
                            fontFamily = FontFamily.Monospace,
                            fontWeight = FontWeight.Bold,
                            color = PrimaryAccent
                        )
                        Text(
                            text = if (existingAccount != null) "Channel Configuration" else "Connect Social Media Account",
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.Bold,
                            color = TextPrimary
                        )
                    }
                    IconButton(onClick = onDismiss, modifier = Modifier.size(32.dp)) {
                        Icon(Icons.Default.Close, contentDescription = "Close", tint = TextMuted)
                    }
                }

                Spacer(modifier = Modifier.height(14.dp))

                LazyColumn(
                    modifier = Modifier
                        .weight(1f)
                        .fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(14.dp)
                ) {
                    // Platform Selection
                    item {
                        Text(
                            text = "SELECT PLATFORM",
                            style = MaterialTheme.typography.labelSmall,
                            fontFamily = FontFamily.Monospace,
                            color = TextMuted,
                            letterSpacing = 1.sp
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        LazyRow(
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            items(PlatformType.entries.toTypedArray()) { platform ->
                                val isSelected = platform == selectedPlatform
                                val platformColor = when (platform) {
                                    PlatformType.TWITTER -> ElectricBlue
                                    PlatformType.LINKEDIN -> Color(0xFF38BDF8)
                                    PlatformType.INSTAGRAM -> SocialAgentColor
                                    PlatformType.TELEGRAM -> Color(0xFF60A5FA)
                                    PlatformType.DISCORD -> PrimaryAccent
                                    PlatformType.FACEBOOK -> Color(0xFF818CF8)
                                    PlatformType.YOUTUBE -> ErrorRed
                                    PlatformType.REDDIT -> ContentAgentColor
                                }
                                Surface(
                                    modifier = Modifier.clickable {
                                        selectedPlatform = platform
                                        token = app.securePreferences.getSocialToken(platform.name)
                                    },
                                    color = if (isSelected) platformColor.copy(alpha = 0.2f) else SurfaceVariantDark,
                                    shape = RoundedCornerShape(10.dp),
                                    border = androidx.compose.foundation.BorderStroke(
                                        1.dp,
                                        if (isSelected) platformColor else BorderDark
                                    )
                                ) {
                                    Text(
                                        text = platform.displayName,
                                        style = MaterialTheme.typography.labelSmall,
                                        fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal,
                                        color = if (isSelected) platformColor else TextSecondary,
                                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp)
                                    )
                                }
                            }
                        }
                    }

                    // Account Profile Details
                    item {
                        ObsidianCard {
                            Text(
                                text = "PROFILE IDENTIFIERS",
                                style = MaterialTheme.typography.labelSmall,
                                fontFamily = FontFamily.Monospace,
                                color = TextMuted,
                                letterSpacing = 1.sp
                            )
                            Spacer(modifier = Modifier.height(10.dp))

                            OutlinedTextField(
                                value = username,
                                onValueChange = {
                                    username = it
                                    validationError = null
                                },
                                label = { Text("Handle / Username / Channel ID") },
                                placeholder = { Text(if (selectedPlatform == PlatformType.TWITTER) "@username" else "Channel or user ID") },
                                singleLine = true,
                                modifier = Modifier.fillMaxWidth(),
                                colors = OutlinedTextFieldDefaults.colors(
                                    focusedBorderColor = PrimaryAccent,
                                    unfocusedBorderColor = BorderDark,
                                    focusedTextColor = TextPrimary,
                                    unfocusedTextColor = TextPrimary,
                                    focusedLabelColor = PrimaryAccent,
                                    unfocusedLabelColor = TextMuted
                                )
                            )

                            Spacer(modifier = Modifier.height(10.dp))

                            OutlinedTextField(
                                value = displayName,
                                onValueChange = { displayName = it },
                                label = { Text("Display Name") },
                                placeholder = { Text("e.g. AgentDroid Official") },
                                singleLine = true,
                                modifier = Modifier.fillMaxWidth(),
                                colors = OutlinedTextFieldDefaults.colors(
                                    focusedBorderColor = PrimaryAccent,
                                    unfocusedBorderColor = BorderDark,
                                    focusedTextColor = TextPrimary,
                                    unfocusedTextColor = TextPrimary,
                                    focusedLabelColor = PrimaryAccent,
                                    unfocusedLabelColor = TextMuted
                                )
                            )
                        }
                    }

                    // API & Security Credentials
                    item {
                        ObsidianCard {
                            Text(
                                text = "API TOKEN / INTEGRATION KEY (OPTIONAL)",
                                style = MaterialTheme.typography.labelSmall,
                                fontFamily = FontFamily.Monospace,
                                color = TextMuted,
                                letterSpacing = 1.sp
                            )
                            Spacer(modifier = Modifier.height(6.dp))
                            Text(
                                text = "Encrypted in Android Keystore (AES-256). Used for automated publishing via platform API.",
                                style = MaterialTheme.typography.bodySmall,
                                color = TextSecondary,
                                fontSize = 11.5.sp
                            )
                            Spacer(modifier = Modifier.height(10.dp))

                            OutlinedTextField(
                                value = token,
                                onValueChange = { token = it },
                                label = { Text("Access Token / Webhook URL") },
                                placeholder = { Text("Bearer token, bot key, or webhook") },
                                singleLine = true,
                                visualTransformation = if (showToken) VisualTransformation.None else PasswordVisualTransformation(),
                                trailingIcon = {
                                    IconButton(onClick = { showToken = !showToken }) {
                                        Icon(
                                            if (showToken) Icons.Default.VisibilityOff else Icons.Default.Visibility,
                                            contentDescription = if (showToken) "Hide" else "Show",
                                            tint = TextMuted
                                        )
                                    }
                                },
                                modifier = Modifier.fillMaxWidth(),
                                colors = OutlinedTextFieldDefaults.colors(
                                    focusedBorderColor = PrimaryAccent,
                                    unfocusedBorderColor = BorderDark,
                                    focusedTextColor = TextPrimary,
                                    unfocusedTextColor = TextPrimary,
                                    focusedLabelColor = PrimaryAccent,
                                    unfocusedLabelColor = TextMuted
                                )
                            )
                        }
                    }

                    // Autonomy & Safety Governance
                    item {
                        ObsidianCard {
                            Text(
                                text = "AUTONOMOUS GOVERNANCE & SAFETY",
                                style = MaterialTheme.typography.labelSmall,
                                fontFamily = FontFamily.Monospace,
                                color = TextMuted,
                                letterSpacing = 1.sp
                            )
                            Spacer(modifier = Modifier.height(10.dp))

                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Column(modifier = Modifier.weight(1f)) {
                                    Text(
                                        text = "AI Post Drafting",
                                        style = MaterialTheme.typography.bodyMedium,
                                        fontWeight = FontWeight.SemiBold,
                                        color = TextPrimary
                                    )
                                    Text(
                                        text = "Allow Social Agent to autonomously prepare posts & campaigns",
                                        style = MaterialTheme.typography.bodySmall,
                                        color = TextSecondary,
                                        fontSize = 11.sp
                                    )
                                }
                                Switch(
                                    checked = autoDraft,
                                    onCheckedChange = { autoDraft = it },
                                    colors = SwitchDefaults.colors(
                                        checkedThumbColor = BackgroundDark,
                                        checkedTrackColor = PrimaryAccent,
                                        uncheckedTrackColor = SurfaceVariantDark,
                                        uncheckedThumbColor = TextMuted
                                    )
                                )
                            }

                            Spacer(modifier = Modifier.height(10.dp))
                            HorizontalDivider(color = BorderDark.copy(alpha = 0.5f), thickness = 0.8.dp)
                            Spacer(modifier = Modifier.height(10.dp))

                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Column(modifier = Modifier.weight(1f)) {
                                    Text(
                                        text = "Require User Approval",
                                        style = MaterialTheme.typography.bodyMedium,
                                        fontWeight = FontWeight.SemiBold,
                                        color = TextPrimary
                                    )
                                    Text(
                                        text = "Require explicit user confirmation before any live broadcast",
                                        style = MaterialTheme.typography.bodySmall,
                                        color = TextSecondary,
                                        fontSize = 11.sp
                                    )
                                }
                                Switch(
                                    checked = requireApproval,
                                    onCheckedChange = { requireApproval = it },
                                    colors = SwitchDefaults.colors(
                                        checkedThumbColor = BackgroundDark,
                                        checkedTrackColor = PrimaryAccent,
                                        uncheckedTrackColor = SurfaceVariantDark,
                                        uncheckedThumbColor = TextMuted
                                    )
                                )
                            }
                        }
                    }

                    // Validation Error Banner
                    if (validationError != null) {
                        item {
                            Surface(
                                color = ErrorRed.copy(alpha = 0.15f),
                                shape = RoundedCornerShape(8.dp),
                                border = androidx.compose.foundation.BorderStroke(1.dp, ErrorRed.copy(alpha = 0.5f))
                            ) {
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(12.dp),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Icon(Icons.Default.Error, contentDescription = null, tint = ErrorRed, modifier = Modifier.size(18.dp))
                                    Spacer(modifier = Modifier.width(8.dp))
                                    Text(text = validationError ?: "", style = MaterialTheme.typography.bodySmall, color = ErrorRed)
                                }
                            }
                        }
                    }
                }

                Spacer(modifier = Modifier.height(14.dp))

                // Action Buttons
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    if (existingAccount != null && onDisconnect != null) {
                        Button(
                            onClick = {
                                onDisconnect(existingAccount.id)
                                onDismiss()
                            },
                            colors = ButtonDefaults.buttonColors(containerColor = ErrorRed.copy(alpha = 0.2f), contentColor = ErrorRed),
                            border = androidx.compose.foundation.BorderStroke(1.dp, ErrorRed.copy(alpha = 0.6f)),
                            shape = RoundedCornerShape(10.dp),
                            modifier = Modifier.weight(1f)
                        ) {
                            Text("Disconnect", fontWeight = FontWeight.Bold, fontSize = 12.sp)
                        }
                    }

                    OutlinedButton(
                        onClick = onDismiss,
                        border = androidx.compose.foundation.BorderStroke(1.dp, BorderDark),
                        shape = RoundedCornerShape(10.dp),
                        modifier = Modifier.weight(1f)
                    ) {
                        Text("Cancel", color = TextSecondary, fontSize = 12.sp)
                    }

                    Button(
                        onClick = {
                            if (username.isBlank()) {
                                validationError = "Please enter an account username or handle."
                                return@Button
                            }
                            onSave(
                                selectedPlatform,
                                username.trim(),
                                if (displayName.isBlank()) username.trim() else displayName.trim(),
                                token.trim(),
                                autoDraft,
                                requireApproval
                            )
                            onDismiss()
                        },
                        colors = ButtonDefaults.buttonColors(containerColor = PrimaryAccent, contentColor = BackgroundDark),
                        shape = RoundedCornerShape(10.dp),
                        modifier = Modifier.weight(1.3f)
                    ) {
                        Text("Save Channel", fontWeight = FontWeight.Bold, fontSize = 12.sp)
                    }
                }
            }
        }
    }
}
