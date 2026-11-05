package com.agentdroid.app.ui.screens.permissions

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.LifecycleOwner
import com.agentdroid.app.permission.PermissionHelper
import com.agentdroid.app.ui.components.ObsidianCard
import com.agentdroid.app.ui.theme.*

@Composable
fun PermissionManagementDialog(
    onDismiss: () -> Unit
) {
    val context = LocalContext.current
    var permissionItems by remember { mutableStateOf(PermissionHelper.getAllPermissionItems(context)) }

    fun refreshPermissions() {
        permissionItems = PermissionHelper.getAllPermissionItems(context)
    }

    val lifecycleOwner = context as? LifecycleOwner
    DisposableEffect(lifecycleOwner) {
        if (lifecycleOwner == null) return@DisposableEffect onDispose {}
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                refreshPermissions()
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose {
            lifecycleOwner.lifecycle.removeObserver(observer)
        }
    }

    val runtimeLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestMultiplePermissions()
    ) {
        refreshPermissions()
    }

    Dialog(
        onDismissRequest = onDismiss,
        properties = DialogProperties(
            dismissOnBackPress = true,
            dismissOnClickOutside = true,
            usePlatformDefaultWidth = false
        )
    ) {
        Surface(
            modifier = Modifier
                .fillMaxWidth(0.95f)
                .fillMaxHeight(0.92f)
                .clip(RoundedCornerShape(16.dp))
                .border(1.dp, BorderDark, RoundedCornerShape(16.dp)),
            color = BackgroundDark
        ) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(20.dp)
            ) {
                // Header
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text(
                            text = "SECURITY & ACCESS CONTROL",
                            style = MaterialTheme.typography.labelSmall,
                            letterSpacing = 1.5.sp,
                            fontFamily = FontFamily.Monospace,
                            fontWeight = FontWeight.Bold,
                            color = PrimaryAccent
                        )
                        Text(
                            text = "Permissions Manager",
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.Bold,
                            color = TextPrimary
                        )
                    }
                    IconButton(onClick = onDismiss, modifier = Modifier.size(32.dp)) {
                        Icon(Icons.Default.Close, contentDescription = "Close", tint = TextMuted)
                    }
                }

                Spacer(modifier = Modifier.height(10.dp))
                Text(
                    text = "Inspect and manage Android OS runtime and special access permissions for your AI fleet. You can grant missing capabilities or revoke them in Android System Settings at any time.",
                    style = MaterialTheme.typography.bodySmall,
                    color = TextSecondary,
                    lineHeight = 16.sp
                )

                Spacer(modifier = Modifier.height(14.dp))

                // Batch Request Card for pending runtime permissions
                val pendingRuntimeCount = permissionItems.count { !it.isGranted && it.androidPermission != null }
                if (pendingRuntimeCount > 0) {
                    Surface(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(bottom = 12.dp),
                        color = PrimaryAccent.copy(alpha = 0.12f),
                        shape = RoundedCornerShape(10.dp),
                        border = androidx.compose.foundation.BorderStroke(1.dp, PrimaryAccent.copy(alpha = 0.35f))
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(12.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text(
                                    text = "$pendingRuntimeCount Standard Permissions Pending",
                                    style = MaterialTheme.typography.titleSmall,
                                    fontWeight = FontWeight.Bold,
                                    color = PrimaryAccent
                                )
                                Text(
                                    text = "SMS, Phone Calls, Contacts, Audio, Storage & Camera",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = TextSecondary,
                                    fontSize = 11.sp
                                )
                            }
                            Spacer(modifier = Modifier.width(8.dp))
                            Button(
                                onClick = {
                                    val runtimePermissions = PermissionHelper.getRequiredRuntimePermissions()
                                    runtimeLauncher.launch(runtimePermissions)
                                },
                                colors = ButtonDefaults.buttonColors(
                                    containerColor = PrimaryAccent,
                                    contentColor = BackgroundDark
                                ),
                                shape = RoundedCornerShape(8.dp),
                                contentPadding = PaddingValues(horizontal = 12.dp, vertical = 4.dp),
                                modifier = Modifier.height(30.dp)
                            ) {
                                Text("Grant All", fontSize = 11.sp, fontWeight = FontWeight.Bold)
                            }
                        }
                    }
                }

                // Permissions List
                LazyColumn(
                    modifier = Modifier
                        .weight(1f)
                        .fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    items(permissionItems) { item ->
                        val isGranted = item.isGranted
                        Surface(
                            color = SurfaceVariantDark,
                            shape = RoundedCornerShape(10.dp),
                            border = androidx.compose.foundation.BorderStroke(
                                1.dp,
                                if (isGranted) SuccessGreen.copy(alpha = 0.4f) else BorderDark
                            )
                        ) {
                            Column(modifier = Modifier.padding(14.dp)) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Row(
                                        verticalAlignment = Alignment.CenterVertically,
                                        modifier = Modifier.weight(1f)
                                    ) {
                                        Box(
                                            modifier = Modifier
                                                .size(8.dp)
                                                .clip(CircleShape)
                                                .background(if (isGranted) SuccessGreen else WarningAmber)
                                        )
                                        Spacer(modifier = Modifier.width(10.dp))
                                        Column {
                                            Text(
                                                text = item.name,
                                                style = MaterialTheme.typography.titleSmall,
                                                fontWeight = FontWeight.Bold,
                                                color = TextPrimary
                                            )
                                            if (item.androidPermission != null) {
                                                Text(
                                                    text = item.androidPermission.substringAfterLast("."),
                                                    style = MaterialTheme.typography.labelSmall,
                                                    fontFamily = FontFamily.Monospace,
                                                    color = TextMuted,
                                                    fontSize = 9.sp
                                                )
                                            }
                                        }
                                    }

                                    Surface(
                                        color = if (isGranted) SuccessGreen.copy(alpha = 0.15f) else WarningAmber.copy(alpha = 0.15f),
                                        shape = RoundedCornerShape(6.dp)
                                    ) {
                                        Text(
                                            text = if (isGranted) "AUTHORIZED" else "MISSING",
                                            style = MaterialTheme.typography.labelSmall,
                                            fontSize = 9.sp,
                                            fontFamily = FontFamily.Monospace,
                                            fontWeight = FontWeight.Bold,
                                            color = if (isGranted) SuccessGreen else WarningAmber,
                                            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                                        )
                                    }
                                }

                                Spacer(modifier = Modifier.height(8.dp))
                                Text(
                                    text = item.description,
                                    style = MaterialTheme.typography.bodySmall,
                                    color = TextSecondary,
                                    fontSize = 11.5.sp,
                                    lineHeight = 15.sp
                                )

                                Spacer(modifier = Modifier.height(8.dp))
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Text(
                                        text = "Agents: ${item.agentRoles.joinToString(", ")}",
                                        style = MaterialTheme.typography.labelSmall,
                                        color = PrimaryAccent.copy(alpha = 0.8f),
                                        fontSize = 10.sp
                                    )

                                    if (!isGranted) {
                                        Button(
                                            onClick = {
                                                when (item.id) {
                                                    "perm_accessibility" -> PermissionHelper.openAccessibilitySettings(context)
                                                    "perm_battery" -> PermissionHelper.requestIgnoreBatteryOptimization(context)
                                                    "perm_notification_listener" -> PermissionHelper.openNotificationListenerSettings(context)
                                                    "perm_system_settings" -> PermissionHelper.openWriteSettings(context)
                                                    "perm_overlay" -> PermissionHelper.openOverlaySettings(context)
                                                    "perm_dnd" -> PermissionHelper.openDndSettings(context)
                                                    "perm_all_files" -> PermissionHelper.openAllFilesAccessSettings(context)
                                                    else -> {
                                                        if (item.androidPermission != null) {
                                                            runtimeLauncher.launch(arrayOf(item.androidPermission))
                                                        } else {
                                                            PermissionHelper.openAppSettings(context)
                                                        }
                                                    }
                                                }
                                            },
                                            colors = ButtonDefaults.buttonColors(
                                                containerColor = PrimaryAccent,
                                                contentColor = BackgroundDark
                                            ),
                                            shape = RoundedCornerShape(6.dp),
                                            contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp),
                                            modifier = Modifier.height(28.dp)
                                        ) {
                                            Text("Grant Access", fontSize = 10.5.sp, fontWeight = FontWeight.Bold)
                                        }
                                    } else {
                                        TextButton(
                                            onClick = {
                                                when (item.id) {
                                                    "perm_accessibility" -> PermissionHelper.openAccessibilitySettings(context)
                                                    "perm_notification_listener" -> PermissionHelper.openNotificationListenerSettings(context)
                                                    "perm_system_settings" -> PermissionHelper.openWriteSettings(context)
                                                    "perm_overlay" -> PermissionHelper.openOverlaySettings(context)
                                                    "perm_dnd" -> PermissionHelper.openDndSettings(context)
                                                    "perm_all_files" -> PermissionHelper.openAllFilesAccessSettings(context)
                                                    else -> PermissionHelper.openAppSettings(context)
                                                }
                                            },
                                            contentPadding = PaddingValues(horizontal = 6.dp, vertical = 0.dp),
                                            modifier = Modifier.height(26.dp)
                                        ) {
                                            Text("System Settings", color = TextMuted, fontSize = 10.sp)
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // System App Settings Helper Card
                    item {
                        ObsidianCard {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Column(modifier = Modifier.weight(1f)) {
                                    Text(
                                        text = "Android OS Application Settings",
                                        style = MaterialTheme.typography.titleSmall,
                                        fontWeight = FontWeight.SemiBold,
                                        color = TextPrimary
                                    )
                                    Text(
                                        text = "Open device settings for AgentDroid to manage all system permissions, notifications, and battery usage.",
                                        style = MaterialTheme.typography.bodySmall,
                                        color = TextSecondary,
                                        fontSize = 11.sp
                                    )
                                }
                                Spacer(modifier = Modifier.width(8.dp))
                                OutlinedButton(
                                    onClick = { PermissionHelper.openAppSettings(context) },
                                    border = androidx.compose.foundation.BorderStroke(1.dp, BorderDark),
                                    shape = RoundedCornerShape(8.dp),
                                    contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp),
                                    modifier = Modifier.height(30.dp)
                                ) {
                                    Icon(Icons.Default.Settings, contentDescription = null, tint = TextPrimary, modifier = Modifier.size(14.dp))
                                    Spacer(modifier = Modifier.width(4.dp))
                                    Text("Open", color = TextPrimary, fontSize = 11.sp)
                                }
                            }
                        }
                    }
                }

                Spacer(modifier = Modifier.height(14.dp))

                // Dismiss Button
                Button(
                    onClick = onDismiss,
                    colors = ButtonDefaults.buttonColors(
                        containerColor = PrimaryAccent,
                        contentColor = BackgroundDark
                    ),
                    shape = RoundedCornerShape(10.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Done", fontWeight = FontWeight.Bold, fontSize = 13.sp)
                }
            }
        }
    }
}
