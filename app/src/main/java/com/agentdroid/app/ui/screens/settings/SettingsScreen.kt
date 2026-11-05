package com.agentdroid.app.ui.screens.settings

import android.content.Intent
import android.provider.Settings
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
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
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.agentdroid.app.AgentDroidApplication
import com.agentdroid.app.ai.connection.ConnectionState
import com.agentdroid.app.automation.accessibility.AgentDroidAccessibilityService
import com.agentdroid.app.data.local.entity.ApiProviderEntity
import com.agentdroid.app.data.local.entity.ConnectedAccountEntity
import com.agentdroid.app.data.local.entity.DiscoveredModelEntity
import com.agentdroid.app.domain.model.AgentRole
import com.agentdroid.app.domain.model.MemoryTier
import com.agentdroid.app.domain.model.ModelCapability
import com.agentdroid.app.domain.model.PlatformType
import com.agentdroid.app.domain.model.requiredCapabilities
import com.agentdroid.app.permission.PermissionHelper
import com.agentdroid.app.ui.components.ObsidianCard
import com.agentdroid.app.ui.screens.permissions.PermissionManagementDialog
import com.agentdroid.app.ui.screens.social.ConnectSocialAccountDialog
import com.agentdroid.app.ui.theme.*
import kotlinx.coroutines.launch
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun SettingsScreen(
    onNavigateToLegal: (String) -> Unit = {},
    onNavigateToSocial: () -> Unit = {}
) {
    val app = AgentDroidApplication.instance
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()

    val providers by app.database.settingsDao().getAllProviders().collectAsState(initial = emptyList())
    val memoryRecords by app.memoryManager.getAllRecords().collectAsState(initial = emptyList())
    val isAccessibilityActive by AgentDroidAccessibilityService.isServiceActive.collectAsState()
    val installedPlugins by app.pluginRegistry.installedPlugins.collectAsState()
    val systemStatus by app.aiConnectionManager.systemStatus.collectAsState()
    val providerStatuses by app.aiConnectionManager.providerStatuses.collectAsState()
    val modelConfigs by app.database.settingsDao().getAllModelConfigs().collectAsState(initial = emptyList())
    val allDiscoveredModels by app.database.settingsDao().getAllDiscoveredModels().collectAsState(initial = emptyList())
    val connectedAccounts by app.database.accountDao().getAllAccounts().collectAsState(initial = emptyList())

    var showAddProviderDialog by remember { mutableStateOf(false) }
    var providerToEdit by remember { mutableStateOf<ApiProviderEntity?>(null) }
    var targetAgentForModelPicker by remember { mutableStateOf<Pair<String, String>?>(null) } // (role, title)
    var testingProviderId by remember { mutableStateOf<String?>(null) }
    var refreshingProviderId by remember { mutableStateOf<String?>(null) }

    var platformToConnect by remember { mutableStateOf<PlatformType?>(null) }
    var accountToEdit by remember { mutableStateOf<ConnectedAccountEntity?>(null) }
    var showPermissionManagerDialog by remember { mutableStateOf(false) }

    val timeFormat = remember { SimpleDateFormat("HH:mm:ss", Locale.getDefault()) }

    // Dialog: Add / Edit Provider
    if (showAddProviderDialog || providerToEdit != null) {
        val editing = providerToEdit
        AddProviderDialog(
            initialProvider = editing,
            initialApiKey = editing?.let { app.securePreferences.getApiKey(it.id) } ?: "",
            onDismiss = {
                showAddProviderDialog = false
                providerToEdit = null
            },
            onSave = { newProvider, key ->
                coroutineScope.launch {
                    app.database.settingsDao().insertProvider(newProvider)
                    if (key.isNotBlank()) {
                        app.securePreferences.saveApiKey(newProvider.id, key)
                    }
                    showAddProviderDialog = false
                    providerToEdit = null
                    app.aiConnectionManager.testProviderConnection(newProvider.id)
                    app.aiConnectionManager.refreshAllStatuses()
                }
            }
        )
    }

    // Dialog: Model Picker
    if (targetAgentForModelPicker != null) {
        val target = targetAgentForModelPicker!!
        val currentConfig = modelConfigs.firstOrNull { it.agentRole == target.first }
        ModelPickerDialog(
            targetAgentRole = target.first,
            targetAgentTitle = target.second,
            currentModelName = currentConfig?.modelName ?: "gpt-4o",
            currentProviderId = currentConfig?.providerId ?: (providers.firstOrNull()?.id ?: ""),
            discoveredModels = allDiscoveredModels,
            providers = providers,
            onDismiss = { targetAgentForModelPicker = null },
            onSelectModel = { provId, modelId ->
                coroutineScope.launch {
                    app.aiConnectionManager.assignModelToAgent(target.first, provId, modelId)
                    targetAgentForModelPicker = null
                }
            },
            onManualModelSubmit = { provId, manualModel ->
                coroutineScope.launch {
                    val prov = providers.find { it.id == provId }
                    val isLocal = prov?.providerType == "OLLAMA"
                    val manualEntity = DiscoveredModelEntity(
                        id = "$provId:$manualModel",
                        modelId = manualModel,
                        providerId = provId,
                        displayName = manualModel,
                        modelType = if (isLocal) "LOCAL" else "CLOUD",
                        isManualEntry = true,
                        isAvailable = true,
                        isLocal = isLocal,
                        lastVerified = System.currentTimeMillis()
                    )
                    app.database.settingsDao().insertDiscoveredModel(manualEntity)
                    app.aiConnectionManager.assignModelToAgent(target.first, provId, manualModel)
                    targetAgentForModelPicker = null
                }
            }
        )
    }

    // Dialog: Connect / Edit Social Account
    if (platformToConnect != null) {
        ConnectSocialAccountDialog(
            initialPlatform = platformToConnect ?: PlatformType.TWITTER,
            existingAccount = accountToEdit,
            onDismiss = {
                platformToConnect = null
                accountToEdit = null
            },
            onSave = { platform, username, displayName, token, autoDraft, requireApproval ->
                coroutineScope.launch {
                    val accountId = accountToEdit?.id ?: "acc_${platform.name.lowercase()}_${System.currentTimeMillis()}"
                    val permsJson = JSONObject().apply {
                        put("autoDraft", autoDraft)
                        put("requireApproval", requireApproval)
                    }.toString()
                    app.database.accountDao().insertAccount(
                        ConnectedAccountEntity(
                            id = accountId,
                            platform = platform.name,
                            username = username,
                            displayName = displayName,
                            isConnected = true,
                            permissionsJson = permsJson,
                            lastSyncTime = System.currentTimeMillis()
                        )
                    )
                    if (token.isNotBlank()) {
                        app.securePreferences.saveSocialToken(platform.name, token)
                    } else if (accountToEdit != null && token.isBlank()) {
                        app.securePreferences.removeSocialToken(platform.name)
                    }
                    platformToConnect = null
                    accountToEdit = null
                }
            },
            onDisconnect = { accountId ->
                coroutineScope.launch {
                    app.database.accountDao().deleteAccountById(accountId)
                    platformToConnect?.let { p ->
                        app.securePreferences.removeSocialToken(p.name)
                    }
                    platformToConnect = null
                    accountToEdit = null
                }
            }
        )
    }

    // Dialog: Permissions Manager Window
    if (showPermissionManagerDialog) {
        PermissionManagementDialog(
            onDismiss = { showPermissionManagerDialog = false }
        )
    }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(BackgroundDark)
            .padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Header
        item {
            Spacer(modifier = Modifier.height(16.dp))
            Column {
                Text(
                    text = "SYSTEM PREFERENCES",
                    style = MaterialTheme.typography.labelSmall,
                    letterSpacing = 2.sp,
                    color = PrimaryAccent,
                    fontFamily = FontFamily.Monospace
                )
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = "Settings & AI Infrastructure",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold,
                    color = TextPrimary
                )
            }
        }

        // Global AI System Status Card
        item {
            ObsidianCard(
                borderColor = if (systemStatus.isAnyConnected) SuccessGreen.copy(alpha = 0.5f) else ErrorRed.copy(alpha = 0.5f),
                highlightGlow = systemStatus.isAnyConnected
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text(
                            text = "AI SYSTEM STATUS",
                            style = MaterialTheme.typography.labelSmall,
                            letterSpacing = 1.5.sp,
                            fontFamily = FontFamily.Monospace,
                            fontWeight = FontWeight.Bold,
                            color = if (systemStatus.isAnyConnected) SuccessGreen else ErrorRed
                        )
                        Text(
                            text = if (systemStatus.isAnyConnected) "Real AI Engine Online" else "No AI Provider Connected",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                            color = TextPrimary
                        )
                    }

                    IconButton(
                        onClick = {
                            coroutineScope.launch {
                                app.aiConnectionManager.refreshAllStatuses()
                            }
                        },
                        modifier = Modifier
                            .size(32.dp)
                            .clip(CircleShape)
                            .background(SurfaceVariantDark)
                    ) {
                        Icon(
                            Icons.Default.Refresh,
                            contentDescription = "Refresh Status",
                            tint = PrimaryAccent,
                            modifier = Modifier.size(16.dp)
                        )
                    }
                }

                Spacer(modifier = Modifier.height(12.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Column {
                        Text("Connected", style = MaterialTheme.typography.labelSmall, color = TextMuted)
                        Text(
                            text = "${systemStatus.connectedProviderCount} Active",
                            style = MaterialTheme.typography.bodyMedium,
                            fontWeight = FontWeight.Bold,
                            color = if (systemStatus.connectedProviderCount > 0) SuccessGreen else ErrorRed,
                            fontFamily = FontFamily.Monospace
                        )
                    }
                    Column {
                        Text("Configured", style = MaterialTheme.typography.labelSmall, color = TextMuted)
                        Text(
                            text = "${systemStatus.totalConfiguredCount} Providers",
                            style = MaterialTheme.typography.bodyMedium,
                            fontWeight = FontWeight.Bold,
                            color = TextPrimary,
                            fontFamily = FontFamily.Monospace
                        )
                    }
                    Column {
                        Text("Master Model", style = MaterialTheme.typography.labelSmall, color = TextMuted)
                        Text(
                            text = systemStatus.activeModel ?: "None",
                            style = MaterialTheme.typography.bodyMedium,
                            fontWeight = FontWeight.Bold,
                            color = PrimaryAccent,
                            fontFamily = FontFamily.Monospace
                        )
                    }
                    Column {
                        Text("Last Checked", style = MaterialTheme.typography.labelSmall, color = TextMuted)
                        Text(
                            text = systemStatus.lastCheckTimestamp?.let { timeFormat.format(Date(it)) } ?: "--:--:--",
                            style = MaterialTheme.typography.bodyMedium,
                            fontFamily = FontFamily.Monospace,
                            color = TextSecondary
                        )
                    }
                }
            }
        }

        // Section: Connected Providers
        item {
            ObsidianCard {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text(
                            text = "AI Providers & Inference Engines",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.SemiBold,
                            color = TextPrimary
                        )
                        Text(
                            text = "Hardware Keystore Encryption • Local & Cloud",
                            style = MaterialTheme.typography.labelSmall,
                            fontFamily = FontFamily.Monospace,
                            color = ElectricBlue
                        )
                    }

                    Button(
                        onClick = { showAddProviderDialog = true },
                        colors = ButtonDefaults.buttonColors(
                            containerColor = PrimaryAccent,
                            contentColor = BackgroundDark
                        ),
                        shape = RoundedCornerShape(8.dp),
                        contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp),
                        modifier = Modifier.height(30.dp)
                    ) {
                        Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(14.dp))
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("Add Provider", fontSize = 11.sp, fontWeight = FontWeight.Bold)
                    }
                }

                Spacer(modifier = Modifier.height(14.dp))

                providers.forEachIndexed { index, provider ->
                    val key = app.securePreferences.getApiKey(provider.id)
                    val hasKey = key.isNotBlank()
                    val status = providerStatuses[provider.id]
                    val isLocal = status?.isLocal == true || provider.providerType == "OLLAMA"
                    val connState = status?.state ?: if (hasKey || isLocal) ConnectionState.CONFIGURED else ConnectionState.NOT_CONFIGURED
                    val isTesting = testingProviderId == provider.id
                    val isRefreshing = refreshingProviderId == provider.id
                    val provModels = allDiscoveredModels.filter { it.providerId == provider.id }

                    val stateBadgeColor = when (connState) {
                        ConnectionState.CONNECTED -> SuccessGreen
                        ConnectionState.CONFIGURED -> WarningAmber
                        ConnectionState.NOT_CONFIGURED -> TextMuted
                        ConnectionState.CONNECTING -> PrimaryAccent
                        ConnectionState.INVALID_API_KEY, ConnectionState.AUTHENTICATION_FAILED -> ErrorRed
                        ConnectionState.RATE_LIMITED -> WarningAmber
                        ConnectionState.NETWORK_ERROR, ConnectionState.PROVIDER_UNAVAILABLE, ConnectionState.REQUEST_TIMEOUT -> ErrorRed
                        else -> TextMuted
                    }

                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 6.dp)
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Box(
                                    modifier = Modifier
                                        .size(10.dp)
                                        .clip(CircleShape)
                                        .background(stateBadgeColor)
                                )
                                Spacer(modifier = Modifier.width(8.dp))
                                Column {
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Text(
                                            text = provider.displayName,
                                            style = MaterialTheme.typography.bodyMedium,
                                            fontWeight = FontWeight.SemiBold,
                                            color = TextPrimary
                                        )
                                        Spacer(modifier = Modifier.width(6.dp))
                                        Surface(
                                            color = if (isLocal) ElectricBlue.copy(alpha = 0.15f) else PrimaryAccent.copy(alpha = 0.15f),
                                            shape = RoundedCornerShape(4.dp)
                                        ) {
                                            Text(
                                                text = if (isLocal) "LOCAL" else "CLOUD",
                                                color = if (isLocal) ElectricBlue else PrimaryAccent,
                                                fontSize = 8.sp,
                                                fontFamily = FontFamily.Monospace,
                                                fontWeight = FontWeight.Bold,
                                                modifier = Modifier.padding(horizontal = 4.dp, vertical = 1.dp)
                                            )
                                        }
                                    }
                                    Text(
                                        text = provider.baseUrl,
                                        style = MaterialTheme.typography.labelSmall,
                                        fontFamily = FontFamily.Monospace,
                                        color = TextMuted,
                                        fontSize = 10.sp
                                    )
                                    Text(
                                        text = if (provModels.isNotEmpty()) "${provModels.size} Models Discovered" else "No models cached",
                                        style = MaterialTheme.typography.labelSmall,
                                        fontFamily = FontFamily.Monospace,
                                        color = if (provModels.isNotEmpty()) PrimaryAccent else TextMuted,
                                        fontSize = 10.sp
                                    )
                                }
                            }

                            Surface(
                                color = stateBadgeColor.copy(alpha = 0.15f),
                                shape = RoundedCornerShape(4.dp)
                            ) {
                                Text(
                                    text = if (isTesting) "TESTING..." else if (isRefreshing) "REFRESHING..." else connState.name.replace("_", " "),
                                    color = stateBadgeColor,
                                    style = MaterialTheme.typography.labelSmall,
                                    fontSize = 9.sp,
                                    fontFamily = FontFamily.Monospace,
                                    fontWeight = FontWeight.Bold,
                                    modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                                )
                            }
                        }

                        // Error Banner if present
                        if (status?.lastError != null && connState != ConnectionState.CONNECTED) {
                            Spacer(modifier = Modifier.height(6.dp))
                            Surface(
                                color = ErrorRed.copy(alpha = 0.12f),
                                shape = RoundedCornerShape(6.dp),
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Text(
                                    text = "Error: ${status.lastError.userFriendlyMessage}",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = ErrorRed,
                                    fontSize = 10.sp,
                                    modifier = Modifier.padding(6.dp)
                                )
                            }
                        }

                        Spacer(modifier = Modifier.height(8.dp))

                        // Action Buttons Row
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.End,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            // Remove Button
                            TextButton(
                                onClick = {
                                    coroutineScope.launch {
                                        app.aiConnectionManager.removeProvider(provider.id)
                                    }
                                },
                                contentPadding = PaddingValues(horizontal = 6.dp, vertical = 0.dp)
                            ) {
                                Text("Delete", color = ErrorRed.copy(alpha = 0.8f), fontSize = 11.sp)
                            }

                            Spacer(modifier = Modifier.width(4.dp))

                            // Edit Button
                            OutlinedButton(
                                onClick = { providerToEdit = provider },
                                shape = RoundedCornerShape(6.dp),
                                colors = ButtonDefaults.outlinedButtonColors(contentColor = TextPrimary),
                                border = ButtonDefaults.outlinedButtonBorder.copy(
                                    brush = Brush.linearGradient(listOf(BorderDark, BorderDark))
                                ),
                                contentPadding = PaddingValues(horizontal = 8.dp, vertical = 2.dp),
                                modifier = Modifier.height(28.dp)
                            ) {
                                Text("Edit", fontSize = 11.sp)
                            }

                            Spacer(modifier = Modifier.width(4.dp))

                            // Refresh Models Button
                            OutlinedButton(
                                onClick = {
                                    coroutineScope.launch {
                                        refreshingProviderId = provider.id
                                        app.aiConnectionManager.refreshModelsForProvider(provider.id)
                                        refreshingProviderId = null
                                    }
                                },
                                enabled = !isRefreshing && !isTesting,
                                shape = RoundedCornerShape(6.dp),
                                colors = ButtonDefaults.outlinedButtonColors(contentColor = PrimaryAccent),
                                border = ButtonDefaults.outlinedButtonBorder.copy(
                                    brush = Brush.linearGradient(listOf(BorderDark, BorderDark))
                                ),
                                contentPadding = PaddingValues(horizontal = 8.dp, vertical = 2.dp),
                                modifier = Modifier.height(28.dp)
                            ) {
                                Text("Refresh", fontSize = 11.sp)
                            }

                            Spacer(modifier = Modifier.width(4.dp))

                            // Test Connection Button
                            Button(
                                onClick = {
                                    coroutineScope.launch {
                                        testingProviderId = provider.id
                                        app.aiConnectionManager.testProviderConnection(provider.id)
                                        testingProviderId = null
                                    }
                                },
                                enabled = !isTesting && !isRefreshing,
                                shape = RoundedCornerShape(6.dp),
                                colors = ButtonDefaults.buttonColors(
                                    containerColor = PrimaryAccent,
                                    contentColor = BackgroundDark
                                ),
                                contentPadding = PaddingValues(horizontal = 8.dp, vertical = 2.dp),
                                modifier = Modifier.height(28.dp)
                            ) {
                                Text("Test", fontSize = 11.sp, fontWeight = FontWeight.Bold)
                            }
                        }
                    }

                    if (index < providers.size - 1) {
                        Spacer(modifier = Modifier.height(4.dp))
                        HorizontalDivider(color = BorderDark.copy(alpha = 0.5f), thickness = 0.5.dp)
                        Spacer(modifier = Modifier.height(4.dp))
                    }
                }
            }
        }

        // Section: Agent-Specific Model Assignment & Capability Validation
        item {
            ObsidianCard {
                Column {
                    Text(
                        text = "Agent Model Assignments",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold,
                        color = TextPrimary
                    )
                    Text(
                        text = "Assign distinct models per specialized agent",
                        style = MaterialTheme.typography.labelSmall,
                        fontFamily = FontFamily.Monospace,
                        color = TextSecondary
                    )
                }

                Spacer(modifier = Modifier.height(14.dp))

                val agentList = listOf(
                    "GLOBAL_DEFAULT" to "Global Default Model",
                    AgentRole.MASTER.name to "Master Agent",
                    AgentRole.PHONE_CONTROL.name to "Phone Control Agent",
                    AgentRole.RESEARCH.name to "Research Agent",
                    AgentRole.CONTENT_CREATION.name to "Content Creation Agent",
                    AgentRole.SOCIAL_MEDIA.name to "Social Media Agent",
                    AgentRole.COMMUNICATION.name to "Communication Agent",
                    AgentRole.FILE_MANAGEMENT.name to "File Management Agent",
                    AgentRole.PRODUCTIVITY.name to "Productivity Agent",
                    AgentRole.ANALYTICS.name to "Analytics Agent",
                    AgentRole.BROWSER.name to "Browser Agent",
                    AgentRole.SECURITY.name to "Security Agent"
                )

                agentList.forEachIndexed { index, (roleName, roleTitle) ->
                    val config = modelConfigs.firstOrNull { it.agentRole == roleName }
                        ?: modelConfigs.firstOrNull { it.agentRole == AgentRole.MASTER.name }
                    val assignedProvider = providers.firstOrNull { it.id == config?.providerId }
                    val roleEnum = try { AgentRole.valueOf(roleName) } catch (e: Exception) { null }
                    val requiredCaps = roleEnum?.requiredCapabilities() ?: emptySet()

                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 6.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = roleTitle,
                                style = MaterialTheme.typography.bodyMedium,
                                fontWeight = FontWeight.SemiBold,
                                color = TextPrimary
                            )
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                modifier = Modifier.padding(top = 2.dp)
                            ) {
                                Text(
                                    text = "${assignedProvider?.displayName ?: "Default"}: ",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = TextMuted,
                                    fontSize = 11.sp
                                )
                                Text(
                                    text = config?.modelName ?: "gpt-4o",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = PrimaryAccent,
                                    fontFamily = FontFamily.Monospace,
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 11.sp
                                )
                            }
                            if (requiredCaps.isNotEmpty()) {
                                Row(
                                    modifier = Modifier.padding(top = 4.dp),
                                    horizontalArrangement = Arrangement.spacedBy(4.dp)
                                ) {
                                    requiredCaps.take(2).forEach { cap ->
                                        Surface(
                                            color = SurfaceVariantDark,
                                            shape = RoundedCornerShape(3.dp)
                                        ) {
                                            Text(
                                                text = cap.name.replace("_", " "),
                                                color = TextSecondary,
                                                fontSize = 8.sp,
                                                fontFamily = FontFamily.Monospace,
                                                modifier = Modifier.padding(horizontal = 4.dp, vertical = 1.dp)
                                            )
                                        }
                                    }
                                }
                            }
                        }

                        Button(
                            onClick = {
                                targetAgentForModelPicker = (roleName to roleTitle)
                            },
                            shape = RoundedCornerShape(6.dp),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = SurfaceVariantDark,
                                contentColor = PrimaryAccent
                            ),
                            border = ButtonDefaults.outlinedButtonBorder.copy(
                                brush = Brush.linearGradient(listOf(BorderDark, BorderDark))
                            ),
                            contentPadding = PaddingValues(horizontal = 10.dp, vertical = 2.dp),
                            modifier = Modifier.height(28.dp)
                        ) {
                            Text("Change Model", fontSize = 11.sp, fontWeight = FontWeight.Bold)
                        }
                    }

                    if (index < agentList.size - 1) {
                        HorizontalDivider(color = BorderDark.copy(alpha = 0.3f), thickness = 0.5.dp)
                    }
                }
            }
        }

        // Section: System Permissions & Security Access Management
        item {
            val allPermissions = remember(showPermissionManagerDialog) {
                PermissionHelper.getAllPermissionItems(context)
            }
            val grantedCount = allPermissions.count { it.isGranted }
            val isAllReady = grantedCount == allPermissions.size

            ObsidianCard(
                borderColor = if (isAllReady) SuccessGreen.copy(alpha = 0.5f) else WarningAmber.copy(alpha = 0.5f)
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = "SECURITY & ACCESS CONTROL",
                            style = MaterialTheme.typography.labelSmall,
                            letterSpacing = 1.2.sp,
                            fontFamily = FontFamily.Monospace,
                            fontWeight = FontWeight.Bold,
                            color = if (isAllReady) SuccessGreen else WarningAmber
                        )
                        Spacer(modifier = Modifier.height(2.dp))
                        Text(
                            text = "Permissions & System Access",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                            color = TextPrimary
                        )
                    }

                    Surface(
                        color = if (isAllReady) SuccessGreen.copy(alpha = 0.15f) else WarningAmber.copy(alpha = 0.15f),
                        shape = RoundedCornerShape(8.dp),
                        border = androidx.compose.foundation.BorderStroke(
                            1.dp,
                            if (isAllReady) SuccessGreen.copy(alpha = 0.4f) else WarningAmber.copy(alpha = 0.4f)
                        )
                    ) {
                        Text(
                            text = "$grantedCount of ${allPermissions.size} Ready",
                            style = MaterialTheme.typography.labelSmall,
                            fontWeight = FontWeight.Bold,
                            fontFamily = FontFamily.Monospace,
                            color = if (isAllReady) SuccessGreen else WarningAmber,
                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                        )
                    }
                }

                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = "Manage OS-level permissions for phone automation, notifications, file intelligence, camera OCR, and background execution. Grant missing access anytime.",
                    style = MaterialTheme.typography.bodySmall,
                    color = TextSecondary,
                    fontSize = 11.5.sp
                )

                Spacer(modifier = Modifier.height(12.dp))

                // Summary chips
                LazyRow(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    contentPadding = PaddingValues(horizontal = 2.dp)
                ) {
                    items(allPermissions) { perm ->
                        Surface(
                            color = SurfaceVariantDark,
                            shape = RoundedCornerShape(8.dp),
                            border = androidx.compose.foundation.BorderStroke(
                                1.dp,
                                if (perm.isGranted) SuccessGreen.copy(alpha = 0.4f) else WarningAmber.copy(alpha = 0.4f)
                            )
                        ) {
                            Row(
                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 6.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Box(
                                    modifier = Modifier
                                        .size(6.dp)
                                        .clip(CircleShape)
                                        .background(if (perm.isGranted) SuccessGreen else WarningAmber)
                                )
                                Spacer(modifier = Modifier.width(6.dp))
                                Text(
                                    text = perm.name.replace(" Automation Service", "").replace(" Access", "").replace(" & Visual Intelligence", ""),
                                    style = MaterialTheme.typography.labelSmall,
                                    fontSize = 10.sp,
                                    color = if (perm.isGranted) TextPrimary else WarningAmber
                                )
                            }
                        }
                    }
                }

                Spacer(modifier = Modifier.height(14.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Button(
                        onClick = { showPermissionManagerDialog = true },
                        colors = ButtonDefaults.buttonColors(
                            containerColor = PrimaryAccent,
                            contentColor = BackgroundDark
                        ),
                        shape = RoundedCornerShape(8.dp),
                        modifier = Modifier.weight(1.3f),
                        contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp)
                    ) {
                        Icon(Icons.Default.Security, contentDescription = null, modifier = Modifier.size(15.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Manage Permissions", fontSize = 11.5.sp, fontWeight = FontWeight.Bold)
                    }

                    OutlinedButton(
                        onClick = { PermissionHelper.openAppSettings(context) },
                        border = androidx.compose.foundation.BorderStroke(1.dp, BorderDark),
                        shape = RoundedCornerShape(8.dp),
                        modifier = Modifier.weight(1f),
                        contentPadding = PaddingValues(horizontal = 10.dp, vertical = 6.dp)
                    ) {
                        Icon(Icons.Default.Settings, contentDescription = null, tint = TextSecondary, modifier = Modifier.size(14.dp))
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("OS Settings", color = TextSecondary, fontSize = 11.sp)
                    }
                }
            }
        }

        // Accessibility Automation Service Status Card
        item {
            ObsidianCard(
                borderColor = if (isAccessibilityActive) SuccessGreen.copy(alpha = 0.5f) else WarningAmber.copy(alpha = 0.5f)
            ) {
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
                                .size(36.dp)
                                .clip(RoundedCornerShape(8.dp))
                                .background(
                                    if (isAccessibilityActive) SuccessGreen.copy(alpha = 0.15f)
                                    else WarningAmber.copy(alpha = 0.15f)
                                ),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                if (isAccessibilityActive) Icons.Default.CheckCircle else Icons.Default.Warning,
                                contentDescription = null,
                                tint = if (isAccessibilityActive) SuccessGreen else WarningAmber,
                                modifier = Modifier.size(20.dp)
                            )
                        }

                        Spacer(modifier = Modifier.width(12.dp))

                        Column {
                            Text(
                                text = "Accessibility Automation Engine",
                                style = MaterialTheme.typography.titleSmall,
                                fontWeight = FontWeight.SemiBold,
                                color = TextPrimary
                            )
                            Spacer(modifier = Modifier.height(2.dp))
                            Text(
                                text = if (isAccessibilityActive)
                                    "Active: Autonomous clicking, typing & screen inspection ready"
                                else
                                    "Disabled: Enable service to allow Phone Control Agent actions",
                                style = MaterialTheme.typography.bodySmall,
                                color = if (isAccessibilityActive) SuccessGreen else WarningAmber
                            )
                        }
                    }

                    Spacer(modifier = Modifier.width(8.dp))

                    Button(
                        onClick = {
                            val intent = Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS).apply {
                                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                            }
                            context.startActivity(intent)
                        },
                        colors = ButtonDefaults.buttonColors(
                            containerColor = if (isAccessibilityActive) SurfaceVariantDark else PrimaryAccent,
                            contentColor = if (isAccessibilityActive) TextPrimary else BackgroundDark
                        ),
                        shape = RoundedCornerShape(8.dp),
                        contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp)
                    ) {
                        Text(
                            text = if (isAccessibilityActive) "Settings" else "Enable",
                            fontWeight = FontWeight.Bold,
                            fontSize = 12.sp
                        )
                    }
                }
            }
        }

        // Section: Connected Social Media Accounts & Integrations
        item {
            ObsidianCard(borderColor = SocialAgentColor.copy(alpha = 0.4f)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text(
                            text = "SOCIAL MEDIA ACCOUNTS & INTEGRATIONS",
                            style = MaterialTheme.typography.labelSmall,
                            letterSpacing = 1.2.sp,
                            fontFamily = FontFamily.Monospace,
                            fontWeight = FontWeight.Bold,
                            color = SocialAgentColor
                        )
                        Spacer(modifier = Modifier.height(2.dp))
                        Text(
                            text = "Connected Channels (${connectedAccounts.size})",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                            color = TextPrimary
                        )
                    }

                    Button(
                        onClick = {
                            platformToConnect = PlatformType.TWITTER
                            accountToEdit = null
                        },
                        colors = ButtonDefaults.buttonColors(containerColor = SocialAgentColor, contentColor = BackgroundDark),
                        shape = RoundedCornerShape(8.dp),
                        contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp),
                        modifier = Modifier.height(30.dp)
                    ) {
                        Text("+ Connect", fontSize = 11.sp, fontWeight = FontWeight.Bold)
                    }
                }

                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = "Manage API credentials and permissions for the Social Media Agent across X, LinkedIn, Instagram, Discord, Telegram, and YouTube.",
                    style = MaterialTheme.typography.bodySmall,
                    color = TextSecondary,
                    fontSize = 11.5.sp
                )

                Spacer(modifier = Modifier.height(10.dp))

                if (connectedAccounts.isEmpty()) {
                    Surface(
                        color = SurfaceVariantDark,
                        shape = RoundedCornerShape(8.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(
                            text = "No channels currently linked. Tap '+ Connect' to add your accounts.",
                            style = MaterialTheme.typography.bodySmall,
                            color = TextMuted,
                            modifier = Modifier.padding(12.dp)
                        )
                    }
                } else {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        for (acc in connectedAccounts) {
                            Surface(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clickable {
                                        val p = try { PlatformType.valueOf(acc.platform) } catch (e: Exception) { PlatformType.TWITTER }
                                        platformToConnect = p
                                        accountToEdit = acc
                                    },
                                color = SurfaceVariantDark,
                                shape = RoundedCornerShape(8.dp),
                                border = androidx.compose.foundation.BorderStroke(1.dp, BorderDark)
                            ) {
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(horizontal = 12.dp, vertical = 10.dp),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Box(
                                            modifier = Modifier
                                                .size(8.dp)
                                                .clip(CircleShape)
                                                .background(if (acc.isConnected) SuccessGreen else TextMuted)
                                        )
                                        Spacer(modifier = Modifier.width(10.dp))
                                        Column {
                                            Text(
                                                text = acc.platform,
                                                style = MaterialTheme.typography.labelSmall,
                                                fontWeight = FontWeight.Bold,
                                                color = TextPrimary
                                            )
                                            Text(
                                                text = acc.username,
                                                style = MaterialTheme.typography.bodySmall,
                                                color = SocialAgentColor,
                                                fontSize = 11.sp
                                            )
                                        }
                                    }

                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Text(
                                            text = "Configure",
                                            style = MaterialTheme.typography.labelSmall,
                                            color = PrimaryAccent,
                                            fontSize = 11.sp,
                                            fontWeight = FontWeight.SemiBold
                                        )
                                        Spacer(modifier = Modifier.width(4.dp))
                                        Icon(Icons.Default.ChevronRight, contentDescription = null, tint = TextMuted, modifier = Modifier.size(14.dp))
                                    }
                                }
                            }
                        }
                    }
                }

                Spacer(modifier = Modifier.height(12.dp))
                OutlinedButton(
                    onClick = onNavigateToSocial,
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(8.dp),
                    border = androidx.compose.foundation.BorderStroke(1.dp, SocialAgentColor.copy(alpha = 0.5f))
                ) {
                    Icon(Icons.Default.Share, contentDescription = null, tint = SocialAgentColor, modifier = Modifier.size(14.dp))
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("Open Social Media Hub", color = SocialAgentColor, fontSize = 11.5.sp, fontWeight = FontWeight.Bold)
                }
            }
        }

        // 5-Tier Memory & Context Engine
        item {
            ObsidianCard {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text(
                            text = "Multi-Tier Context Memory",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.SemiBold,
                            color = TextPrimary
                        )
                        Text(
                            text = "${memoryRecords.size} Records Stored Across 5 Tiers",
                            style = MaterialTheme.typography.bodySmall,
                            color = TextSecondary
                        )
                    }

                    TextButton(
                        onClick = {
                            coroutineScope.launch {
                                app.memoryManager.clearAll()
                            }
                        },
                        colors = ButtonDefaults.textButtonColors(contentColor = ErrorRed),
                        contentPadding = PaddingValues(horizontal = 8.dp, vertical = 2.dp)
                    ) {
                        Text("Purge All", fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                    }
                }

                Spacer(modifier = Modifier.height(12.dp))

                for (tier in MemoryTier.entries) {
                    val count = memoryRecords.count { it.tier == tier }
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 4.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = tier.name,
                            style = MaterialTheme.typography.bodyMedium,
                            color = TextPrimary,
                            fontFamily = FontFamily.Monospace,
                            fontSize = 12.sp
                        )

                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(
                                text = "$count items",
                                style = MaterialTheme.typography.labelSmall,
                                color = PrimaryAccent,
                                fontFamily = FontFamily.Monospace
                            )
                            Spacer(modifier = Modifier.width(10.dp))
                            TextButton(
                                onClick = {
                                    coroutineScope.launch {
                                        app.memoryManager.clearTier(tier)
                                    }
                                },
                                contentPadding = PaddingValues(0.dp)
                            ) {
                                Text("Reset", fontSize = 11.sp, color = TextMuted)
                            }
                        }
                    }
                }
            }
        }

        // Modular Extension Plugins (Section 13 SDK)
        item {
            ObsidianCard {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text(
                            text = "Modular Extension Plugins",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.SemiBold,
                            color = TextPrimary
                        )
                        Text(
                            text = "${installedPlugins.size} Active Plugins Loaded",
                            style = MaterialTheme.typography.bodySmall,
                            color = TextSecondary
                        )
                    }

                    Surface(
                        color = SuccessGreen.copy(alpha = 0.15f),
                        shape = RoundedCornerShape(6.dp)
                    ) {
                        Text(
                            text = "SDK v1.0",
                            style = MaterialTheme.typography.labelSmall,
                            color = SuccessGreen,
                            fontFamily = FontFamily.Monospace,
                            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                        )
                    }
                }

                Spacer(modifier = Modifier.height(12.dp))

                installedPlugins.forEachIndexed { index, plugin ->
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 4.dp)
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = "${plugin.name} (v${plugin.version})",
                                style = MaterialTheme.typography.bodyMedium,
                                fontWeight = FontWeight.SemiBold,
                                color = TextPrimary
                            )
                            Surface(
                                color = SuccessGreen.copy(alpha = 0.15f),
                                shape = RoundedCornerShape(4.dp)
                            ) {
                                Text(
                                    text = "ACTIVE",
                                    color = SuccessGreen,
                                    style = MaterialTheme.typography.labelSmall,
                                    fontSize = 9.sp,
                                    fontFamily = FontFamily.Monospace,
                                    fontWeight = FontWeight.Bold,
                                    modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                                )
                            }
                        }
                        Spacer(modifier = Modifier.height(2.dp))
                        Text(
                            text = plugin.description,
                            style = MaterialTheme.typography.bodySmall,
                            color = TextSecondary
                        )
                        Spacer(modifier = Modifier.height(2.dp))
                        Text(
                            text = "Author: ${plugin.author} • Permissions: ${plugin.requiredPermissions.joinToString(", ")}",
                            style = MaterialTheme.typography.labelSmall,
                            fontSize = 10.sp,
                            fontFamily = FontFamily.Monospace,
                            color = PrimaryAccent
                        )
                    }

                    if (index < installedPlugins.size - 1) {
                        Spacer(modifier = Modifier.height(4.dp))
                        HorizontalDivider(color = BorderDark.copy(alpha = 0.5f), thickness = 0.5.dp)
                        Spacer(modifier = Modifier.height(4.dp))
                    }
                }
            }
        }

        // Legal, Privacy & Governance Section
        item {
            ObsidianCard {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text(
                            text = "Legal, Privacy & Governance",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.SemiBold,
                            color = TextPrimary
                        )
                        Text(
                            text = "Data sovereignty, terms of service & disclaimers",
                            style = MaterialTheme.typography.bodySmall,
                            color = TextSecondary
                        )
                    }

                    Surface(
                        color = PrimaryAccent.copy(alpha = 0.15f),
                        shape = RoundedCornerShape(6.dp)
                    ) {
                        Text(
                            text = "COMPLIANCE",
                            style = MaterialTheme.typography.labelSmall,
                            color = PrimaryAccent,
                            fontFamily = FontFamily.Monospace,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                        )
                    }
                }

                Spacer(modifier = Modifier.height(14.dp))

                // Item 1: Privacy Policy Row
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(8.dp))
                        .clickable { onNavigateToLegal("privacy") }
                        .padding(vertical = 8.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier.weight(1f)
                    ) {
                        Box(
                            modifier = Modifier
                                .size(34.dp)
                                .clip(CircleShape)
                                .background(SuccessGreen.copy(alpha = 0.15f)),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                Icons.Default.Shield,
                                contentDescription = null,
                                tint = SuccessGreen,
                                modifier = Modifier.size(18.dp)
                            )
                        }
                        Spacer(modifier = Modifier.width(12.dp))
                        Column {
                            Text(
                                text = "Privacy Policy",
                                style = MaterialTheme.typography.bodyMedium,
                                fontWeight = FontWeight.SemiBold,
                                color = TextPrimary
                            )
                            Text(
                                text = "Zero tracking • Local Keystore • Accessibility disclosure",
                                style = MaterialTheme.typography.bodySmall,
                                color = TextSecondary
                            )
                        }
                    }
                    Icon(
                        Icons.Default.ChevronRight,
                        contentDescription = "Open Privacy Policy",
                        tint = TextMuted,
                        modifier = Modifier.size(20.dp)
                    )
                }

                HorizontalDivider(color = BorderDark.copy(alpha = 0.5f), thickness = 0.5.dp)

                // Item 2: Terms and Conditions Row
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(8.dp))
                        .clickable { onNavigateToLegal("terms") }
                        .padding(vertical = 8.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier.weight(1f)
                    ) {
                        Box(
                            modifier = Modifier
                                .size(34.dp)
                                .clip(CircleShape)
                                .background(PrimaryAccent.copy(alpha = 0.15f)),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                Icons.Default.Description,
                                contentDescription = null,
                                tint = PrimaryAccent,
                                modifier = Modifier.size(18.dp)
                            )
                        }
                        Spacer(modifier = Modifier.width(12.dp))
                        Column {
                            Text(
                                text = "Terms & Conditions",
                                style = MaterialTheme.typography.bodyMedium,
                                fontWeight = FontWeight.SemiBold,
                                color = TextPrimary
                            )
                            Text(
                                text = "Human oversight • Prohibited uses • Apache 2.0 license",
                                style = MaterialTheme.typography.bodySmall,
                                color = TextSecondary
                            )
                        }
                    }
                    Icon(
                        Icons.Default.ChevronRight,
                        contentDescription = "Open Terms",
                        tint = TextMuted,
                        modifier = Modifier.size(20.dp)
                    )
                }

                HorizontalDivider(color = BorderDark.copy(alpha = 0.5f), thickness = 0.5.dp)

                // Item 3: Open Source Licenses
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 8.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier.weight(1f)
                    ) {
                        Box(
                            modifier = Modifier
                                .size(34.dp)
                                .clip(CircleShape)
                                .background(ElectricBlue.copy(alpha = 0.15f)),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                Icons.Default.Info,
                                contentDescription = null,
                                tint = ElectricBlue,
                                modifier = Modifier.size(18.dp)
                            )
                        }
                        Spacer(modifier = Modifier.width(12.dp))
                        Column {
                            Text(
                                text = "Open Source Licensing",
                                style = MaterialTheme.typography.bodyMedium,
                                fontWeight = FontWeight.SemiBold,
                                color = TextPrimary
                            )
                            Text(
                                text = "Licensed under Apache License, Version 2.0",
                                style = MaterialTheme.typography.bodySmall,
                                color = TextSecondary
                            )
                        }
                    }
                    Surface(
                        color = CardBackground,
                        shape = RoundedCornerShape(4.dp),
                        border = androidx.compose.foundation.BorderStroke(0.5.dp, BorderDark)
                    ) {
                        Text(
                            text = "APACHE 2.0",
                            style = MaterialTheme.typography.labelSmall,
                            color = SuccessGreen,
                            fontSize = 9.sp,
                            fontFamily = FontFamily.Monospace,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                        )
                    }
                }
            }
        }

        // About AgentDroid OS Card
        item {
            ObsidianCard {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    androidx.compose.foundation.Image(
                        painter = androidx.compose.ui.res.painterResource(id = com.agentdroid.app.R.drawable.agentdroid_logo),
                        contentDescription = "AgentDroid Logo",
                        modifier = Modifier
                            .size(38.dp)
                            .clip(RoundedCornerShape(8.dp))
                    )
                    Spacer(modifier = Modifier.width(12.dp))
                    Column {
                        Text(
                            text = "AgentDroid AI OS",
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.Bold,
                            color = TextPrimary
                        )
                        Text(
                            text = "Strict Real AI Architecture",
                            style = MaterialTheme.typography.labelSmall,
                            fontFamily = FontFamily.Monospace,
                            color = SuccessGreen
                        )
                    }
                }

                Spacer(modifier = Modifier.height(10.dp))
                Text(
                    text = "Zero mock data policy. Every operation is powered by verified real AI connections, native Accessibility automation, dynamic cloud & Ollama model discovery, and hardware Keystore AES-256 GCM encryption.",
                    style = MaterialTheme.typography.bodySmall,
                    color = TextSecondary,
                    lineHeight = 18.sp
                )
            }
        }

        item { Spacer(modifier = Modifier.height(80.dp)) }
    }
}
