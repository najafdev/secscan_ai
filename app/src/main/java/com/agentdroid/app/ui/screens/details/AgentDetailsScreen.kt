package com.agentdroid.app.ui.screens.details

import android.content.Intent
import android.provider.Settings
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
import com.agentdroid.app.AgentDroidApplication
import com.agentdroid.app.data.local.entity.AgentConfigEntity
import com.agentdroid.app.data.local.entity.ConnectedAccountEntity
import com.agentdroid.app.data.local.entity.ModelConfigEntity
import com.agentdroid.app.domain.model.AgentExecutionState
import com.agentdroid.app.domain.model.AgentRole
import com.agentdroid.app.domain.model.PlatformType
import com.agentdroid.app.ui.components.AgentStatusBadge
import com.agentdroid.app.ui.components.ObsidianCard
import com.agentdroid.app.ui.screens.settings.ModelPickerDialog
import com.agentdroid.app.ui.screens.social.ConnectSocialAccountDialog
import com.agentdroid.app.ui.theme.*
import kotlinx.coroutines.launch
import org.json.JSONObject

@Composable
fun AgentDetailsScreen(
    agentId: String,
    onBack: () -> Unit,
    onNavigateToSocialHub: () -> Unit = {},
    onNavigateToChat: ((String) -> Unit)? = null
) {
    val app = AgentDroidApplication.instance
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()

    var agentEntity by remember { mutableStateOf<com.agentdroid.app.data.local.entity.AgentEntity?>(null) }
    var modelConfig by remember { mutableStateOf<ModelConfigEntity?>(null) }
    var agentConfig by remember { mutableStateOf<AgentConfigEntity?>(null) }

    var temperature by remember { mutableFloatStateOf(0.7f) }
    var maxTokens by remember { mutableIntStateOf(4096) }
    var systemPrompt by remember { mutableStateOf("") }
    var isSavedToast by remember { mutableStateOf(false) }
    var showDeleteConfirmation by remember { mutableStateOf(false) }

    // Dialog states
    var showModelPicker by remember { mutableStateOf(false) }
    var platformToConnect by remember { mutableStateOf<PlatformType?>(null) }
    var accountToEdit by remember { mutableStateOf<ConnectedAccountEntity?>(null) }

    val discoveredModels by app.database.settingsDao().getAllDiscoveredModels().collectAsState(initial = emptyList())
    val providers by app.database.settingsDao().getAllProviders().collectAsState(initial = emptyList())
    val connectedAccounts by app.database.accountDao().getAllAccounts().collectAsState(initial = emptyList())

    val registeredAgent = app.agentsMap.values.firstOrNull { it.id == agentId } ?: app.masterAgent

    LaunchedEffect(agentId) {
        val entity = app.database.agentDao().getAgentById(agentId)
        agentEntity = entity
        val role = entity?.role ?: "MASTER"
        val cfg = app.database.settingsDao().getConfigForRole(role)
        modelConfig = cfg
        temperature = cfg?.temperature ?: 0.7f
        maxTokens = cfg?.maxTokens ?: 4096

        val aCfg = app.database.agentDao().getConfigForAgent(agentId)
        agentConfig = aCfg
        systemPrompt = aCfg?.systemPrompt ?: (entity?.description ?: registeredAgent.description)
    }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(BackgroundDark)
            .padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        // Navigation Header
        item {
            val isUserCreatedCustom = agentEntity?.isCustom == true && !agentId.startsWith("plugin_")
            Spacer(modifier = Modifier.height(14.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.weight(1f)
                ) {
                    IconButton(
                        onClick = onBack,
                        modifier = Modifier.size(36.dp)
                    ) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back", tint = TextPrimary, modifier = Modifier.size(18.dp))
                    }
                    Spacer(modifier = Modifier.width(8.dp))
                    Column {
                        Text(
                            text = if (isUserCreatedCustom) "CUSTOM AGENT INSPECTOR" else "AGENT INSPECTOR & SETTINGS",
                            style = MaterialTheme.typography.labelSmall,
                            letterSpacing = 1.5.sp,
                            color = PrimaryAccent
                        )
                        Text(
                            text = agentEntity?.name ?: registeredAgent.name,
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.Bold,
                            color = TextPrimary
                        )
                    }
                }

                if (isUserCreatedCustom) {
                    IconButton(
                        onClick = { showDeleteConfirmation = true },
                        modifier = Modifier.size(36.dp)
                    ) {
                        Icon(
                            Icons.Default.DeleteOutline,
                            contentDescription = "Delete Custom Agent",
                            tint = ErrorRed,
                            modifier = Modifier.size(20.dp)
                        )
                    }
                }
            }
        }

        // Operational Status & Enable/Disable Card
        item {
            ObsidianCard(borderColor = PrimaryAccent.copy(alpha = 0.35f)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text(
                            text = "OPERATIONAL STATUS",
                            style = MaterialTheme.typography.labelSmall,
                            color = TextMuted,
                            letterSpacing = 0.8.sp
                        )
                        Text(
                            text = if (agentEntity?.isEnabled == true) "Active & Standing By" else "Disabled / Standby",
                            style = MaterialTheme.typography.titleMedium,
                            color = if (agentEntity?.isEnabled == true) SuccessGreen else TextMuted,
                            fontWeight = FontWeight.SemiBold
                        )
                    }
                    Switch(
                        checked = agentEntity?.isEnabled ?: true,
                        onCheckedChange = { checked ->
                            coroutineScope.launch {
                                app.database.agentDao().setAgentEnabled(agentId, checked)
                                agentEntity = agentEntity?.copy(isEnabled = checked)
                            }
                        },
                        colors = SwitchDefaults.colors(
                            checkedThumbColor = BackgroundDark,
                            checkedTrackColor = PrimaryAccent,
                            uncheckedTrackColor = SurfaceVariantDark,
                            uncheckedThumbColor = TextMuted
                        )
                    )
                }
                Spacer(modifier = Modifier.height(10.dp))
                Text(
                    text = agentEntity?.description ?: registeredAgent.description,
                    style = MaterialTheme.typography.bodyLarge,
                    color = TextSecondary,
                    lineHeight = 20.sp
                )

                if (onNavigateToChat != null) {
                    Spacer(modifier = Modifier.height(14.dp))
                    Button(
                        onClick = {
                            val name = agentEntity?.name ?: registeredAgent.name
                            onNavigateToChat("Assign task to $name: ")
                        },
                        colors = ButtonDefaults.buttonColors(
                            containerColor = PrimaryAccent,
                            contentColor = BackgroundDark
                        ),
                        shape = RoundedCornerShape(10.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Icon(Icons.Default.Forum, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Chat & Assign Work to this Agent", fontWeight = FontWeight.Bold, fontSize = 12.sp)
                    }
                }
            }
        }

        // Model & Inference Configuration Card
        item {
            ObsidianCard {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "AI MODEL ASSIGNMENT",
                        style = MaterialTheme.typography.labelSmall,
                        color = TextSecondary,
                        letterSpacing = 1.sp
                    )
                    TextButton(onClick = { showModelPicker = true }) {
                        Icon(Icons.Default.Tune, contentDescription = null, tint = PrimaryAccent, modifier = Modifier.size(14.dp))
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("Change Model", color = PrimaryAccent, fontSize = 11.5.sp, fontWeight = FontWeight.Bold)
                    }
                }
                Spacer(modifier = Modifier.height(4.dp))
                Surface(
                    color = SurfaceVariantDark,
                    shape = RoundedCornerShape(10.dp),
                    border = androidx.compose.foundation.BorderStroke(1.dp, BorderDark),
                    modifier = Modifier.fillMaxWidth().clickable { showModelPicker = true }
                ) {
                    Row(
                        modifier = Modifier.padding(12.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text(
                                text = modelConfig?.modelName ?: "Autonomous Default",
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold,
                                color = PrimaryAccent
                            )
                            Text(
                                text = "Provider: ${modelConfig?.providerId ?: "Autonomous Router"}",
                                style = MaterialTheme.typography.bodySmall,
                                color = TextMuted,
                                fontSize = 11.sp
                            )
                        }
                        Icon(Icons.Default.ArrowDropDown, contentDescription = null, tint = PrimaryAccent)
                    }
                }

                Spacer(modifier = Modifier.height(14.dp))

                // Inference Temperature Slider
                Text(
                    text = "Inference Temperature: ${String.format("%.2f", temperature)}",
                    style = MaterialTheme.typography.bodyMedium,
                    color = TextSecondary
                )
                Slider(
                    value = temperature,
                    onValueChange = {
                        temperature = it
                        isSavedToast = false
                    },
                    valueRange = 0.0f..1.0f,
                    colors = SliderDefaults.colors(
                        thumbColor = PrimaryAccent,
                        activeTrackColor = PrimaryAccent,
                        inactiveTrackColor = BorderDark
                    )
                )

                Spacer(modifier = Modifier.height(8.dp))

                // Max Tokens Selector
                Text(
                    text = "Max Tokens: $maxTokens",
                    style = MaterialTheme.typography.bodyMedium,
                    color = TextSecondary
                )
                Spacer(modifier = Modifier.height(6.dp))
                LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    items(listOf(1024, 2048, 4096, 8192)) { tokens ->
                        val isSelected = maxTokens == tokens
                        FilterChip(
                            selected = isSelected,
                            onClick = {
                                maxTokens = tokens
                                isSavedToast = false
                            },
                            label = { Text("$tokens", fontSize = 11.sp) },
                            colors = FilterChipDefaults.filterChipColors(
                                selectedContainerColor = PrimaryAccent,
                                selectedLabelColor = BackgroundDark,
                                containerColor = SurfaceVariantDark,
                                labelColor = TextSecondary
                            )
                        )
                    }
                }

                Spacer(modifier = Modifier.height(12.dp))
                Button(
                    onClick = {
                        coroutineScope.launch {
                            val role = agentEntity?.role ?: "MASTER"
                            val entity = modelConfig?.copy(temperature = temperature, maxTokens = maxTokens)
                                ?: ModelConfigEntity(
                                    id = "cfg_${role.lowercase()}",
                                    agentRole = role,
                                    providerId = "prov_openai",
                                    modelName = "gpt-4o",
                                    temperature = temperature,
                                    maxTokens = maxTokens
                                )
                            app.database.settingsDao().insertModelConfig(entity)
                            modelConfig = entity
                            isSavedToast = true
                        }
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = PrimaryAccent, contentColor = BackgroundDark),
                    shape = RoundedCornerShape(8.dp),
                    contentPadding = PaddingValues(horizontal = 16.dp, vertical = 6.dp),
                    modifier = Modifier.height(34.dp)
                ) {
                    Text(if (isSavedToast) "Saved ✓" else "Save Inference Settings", fontSize = 11.5.sp, fontWeight = FontWeight.Bold)
                }
            }
        }

        // Custom System Persona / Prompt Card
        item {
            ObsidianCard {
                Text(
                    text = "SYSTEM PROMPT & PERSONA INSTRUCTIONS",
                    style = MaterialTheme.typography.labelSmall,
                    color = TextSecondary,
                    letterSpacing = 1.sp
                )
                Spacer(modifier = Modifier.height(8.dp))
                OutlinedTextField(
                    value = systemPrompt,
                    onValueChange = { systemPrompt = it },
                    label = { Text("Agent Instructions") },
                    modifier = Modifier.fillMaxWidth(),
                    minLines = 3,
                    maxLines = 6,
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = PrimaryAccent,
                        unfocusedBorderColor = BorderDark,
                        focusedTextColor = TextPrimary,
                        unfocusedTextColor = TextPrimary,
                        focusedLabelColor = PrimaryAccent,
                        unfocusedLabelColor = TextMuted
                    )
                )
                Spacer(modifier = Modifier.height(8.dp))
                Button(
                    onClick = {
                        coroutineScope.launch {
                            val existingCfg = agentConfig
                            val newCfg = existingCfg?.copy(systemPrompt = systemPrompt)
                                ?: AgentConfigEntity(
                                    id = "cfg_agent_$agentId",
                                    agentId = agentId,
                                    assignedModel = modelConfig?.modelName ?: "gpt-4o",
                                    providerId = modelConfig?.providerId ?: "prov_openai",
                                    systemPrompt = systemPrompt,
                                    temperature = temperature
                                )
                            app.database.agentDao().insertConfig(newCfg)
                            agentConfig = newCfg
                            isSavedToast = true
                        }
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = SurfaceVariantDark, contentColor = PrimaryAccent),
                    border = androidx.compose.foundation.BorderStroke(1.dp, PrimaryAccent.copy(alpha = 0.5f)),
                    shape = RoundedCornerShape(8.dp),
                    contentPadding = PaddingValues(horizontal = 14.dp, vertical = 6.dp),
                    modifier = Modifier.height(32.dp)
                ) {
                    Text("Save Persona Instructions", fontSize = 11.sp, fontWeight = FontWeight.SemiBold)
                }
            }
        }

        // SPECIAL SECTION: Connected Social Accounts (If SOCIAL_MEDIA Agent)
        if (agentEntity?.role == "SOCIAL_MEDIA") {
            item {
                ObsidianCard(
                    borderColor = SocialAgentColor.copy(alpha = 0.5f),
                    highlightGlow = true
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text(
                                text = "SOCIAL MEDIA CHANNELS & ACCOUNTS",
                                style = MaterialTheme.typography.labelSmall,
                                color = SocialAgentColor,
                                letterSpacing = 1.sp,
                                fontWeight = FontWeight.Bold
                            )
                            Text(
                                text = "${connectedAccounts.size} Channels Configured",
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
                            Text("+ Connect Channel", fontSize = 10.5.sp, fontWeight = FontWeight.Bold)
                        }
                    }

                    Spacer(modifier = Modifier.height(10.dp))

                    if (connectedAccounts.isEmpty()) {
                        Text(
                            text = "No social media accounts linked yet. Click '+ Connect Channel' to link X, LinkedIn, Instagram, Discord, Telegram, or YouTube.",
                            style = MaterialTheme.typography.bodySmall,
                            color = TextMuted
                        )
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
                                    shape = RoundedCornerShape(10.dp),
                                    border = androidx.compose.foundation.BorderStroke(1.dp, BorderDark)
                                ) {
                                    Row(
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .padding(10.dp),
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
                                            Spacer(modifier = Modifier.width(8.dp))
                                            Column {
                                                Text(
                                                    text = acc.platform,
                                                    style = MaterialTheme.typography.labelMedium,
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
                                                text = "Edit / Unlink",
                                                style = MaterialTheme.typography.labelSmall,
                                                color = TextSecondary,
                                                fontSize = 10.5.sp
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
                        onClick = onNavigateToSocialHub,
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(8.dp),
                        border = androidx.compose.foundation.BorderStroke(1.dp, SocialAgentColor.copy(alpha = 0.5f))
                    ) {
                        Icon(Icons.Default.Share, contentDescription = null, tint = SocialAgentColor, modifier = Modifier.size(14.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Open Full Social Media Hub", color = SocialAgentColor, fontSize = 11.5.sp, fontWeight = FontWeight.Bold)
                    }
                }
            }
        }

        // SPECIAL SECTION: Accessibility Service (If PHONE_CONTROL Agent)
        if (agentEntity?.role == "PHONE_CONTROL") {
            item {
                ObsidianCard(borderColor = PhoneAgentColor.copy(alpha = 0.5f)) {
                    Text(
                        text = "ANDROID ACCESSIBILITY AUTOMATION",
                        style = MaterialTheme.typography.labelSmall,
                        color = PhoneAgentColor,
                        letterSpacing = 1.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(modifier = Modifier.height(6.dp))
                    Text(
                        text = "Allows AgentDroid to perform automated taps, typing, app navigation, and UI tree inspection on device.",
                        style = MaterialTheme.typography.bodySmall,
                        color = TextSecondary
                    )
                    Spacer(modifier = Modifier.height(10.dp))
                    Button(
                        onClick = {
                            try {
                                context.startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS).apply {
                                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                                })
                            } catch (e: Exception) {
                                // Ignore
                            }
                        },
                        colors = ButtonDefaults.buttonColors(containerColor = PhoneAgentColor, contentColor = BackgroundDark),
                        shape = RoundedCornerShape(8.dp),
                        contentPadding = PaddingValues(horizontal = 14.dp, vertical = 6.dp),
                        modifier = Modifier.height(34.dp)
                    ) {
                        Icon(Icons.Default.SettingsAccessibility, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Open Android Accessibility Settings", fontSize = 11.sp, fontWeight = FontWeight.Bold)
                    }
                }
            }
        }

        // Capabilities List Card
        item {
            ObsidianCard {
                Text(
                    text = "CAPABILITIES (${registeredAgent.capabilities.size})",
                    style = MaterialTheme.typography.labelSmall,
                    color = TextSecondary,
                    letterSpacing = 1.sp
                )
                Spacer(modifier = Modifier.height(10.dp))
                for (cap in registeredAgent.capabilities) {
                    Row(
                        modifier = Modifier.padding(vertical = 4.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Box(
                            modifier = Modifier
                                .size(6.dp)
                                .clip(CircleShape)
                                .background(SuccessGreen)
                        )
                        Spacer(modifier = Modifier.width(10.dp))
                        Text(text = cap, style = MaterialTheme.typography.bodyMedium, color = TextPrimary)
                    }
                }
            }
        }

        // Available Tools Card
        item {
            ObsidianCard {
                Text(
                    text = "AVAILABLE TOOLS & APIS",
                    style = MaterialTheme.typography.labelSmall,
                    color = TextSecondary,
                    letterSpacing = 1.sp
                )
                Spacer(modifier = Modifier.height(10.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    for (tool in registeredAgent.availableTools) {
                        Surface(
                            color = SurfaceVariantDark,
                            shape = RoundedCornerShape(8.dp),
                            border = androidx.compose.foundation.BorderStroke(1.dp, BorderDark)
                        ) {
                            Text(
                                text = tool,
                                style = MaterialTheme.typography.labelSmall,
                                color = PrimaryAccent,
                                modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp)
                            )
                        }
                    }
                }
            }
        }

        // Security Boundaries
        item {
            ObsidianCard {
                Text(
                    text = "PERMISSIONS & BOUNDARIES",
                    style = MaterialTheme.typography.labelSmall,
                    color = TextSecondary,
                    letterSpacing = 1.sp
                )
                Spacer(modifier = Modifier.height(8.dp))
                if (registeredAgent.requiredPermissions.isEmpty()) {
                    Text(
                        text = "Sandbox Isolated: No elevated Android system permissions required.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = TextSecondary
                    )
                } else {
                    for (perm in registeredAgent.requiredPermissions) {
                        Text(
                            text = "• $perm",
                            style = MaterialTheme.typography.bodyMedium,
                            color = WarningAmber
                        )
                    }
                }
            }
        }

        // Custom Agent Danger Zone: Delete Option
        if (agentEntity?.isCustom == true && !agentId.startsWith("plugin_")) {
            item {
                ObsidianCard(borderColor = ErrorRed.copy(alpha = 0.4f)) {
                    Text(
                        text = "CUSTOM AGENT MANAGEMENT",
                        style = MaterialTheme.typography.labelSmall,
                        color = ErrorRed,
                        letterSpacing = 1.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "Delete Custom Agent",
                        style = MaterialTheme.typography.titleMedium,
                        color = TextPrimary,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(modifier = Modifier.height(6.dp))
                    Text(
                        text = "Permanently remove this custom agent, its assigned AI model, custom tools, and persona instructions from your device.",
                        style = MaterialTheme.typography.bodySmall,
                        color = TextSecondary
                    )
                    Spacer(modifier = Modifier.height(12.dp))
                    Button(
                        onClick = { showDeleteConfirmation = true },
                        colors = ButtonDefaults.buttonColors(containerColor = ErrorRed, contentColor = BackgroundDark),
                        shape = RoundedCornerShape(8.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Icon(Icons.Default.Delete, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Delete Custom Agent", fontWeight = FontWeight.Bold, fontSize = 12.sp)
                    }
                }
            }
        }

        item { Spacer(modifier = Modifier.height(80.dp)) }
    }

    // Model Picker Dialog
    if (showModelPicker) {
        val role = agentEntity?.role ?: "MASTER"
        ModelPickerDialog(
            targetAgentRole = role,
            targetAgentTitle = agentEntity?.name ?: registeredAgent.name,
            currentModelName = modelConfig?.modelName ?: "",
            currentProviderId = modelConfig?.providerId ?: "",
            discoveredModels = discoveredModels,
            providers = providers,
            onDismiss = { showModelPicker = false },
            onSelectModel = { providerId, modelName ->
                coroutineScope.launch {
                    val existing = app.database.settingsDao().getConfigForRole(role)
                    val newEntity = existing?.copy(providerId = providerId, modelName = modelName)
                        ?: ModelConfigEntity(
                            id = "cfg_${role.lowercase()}",
                            agentRole = role,
                            providerId = providerId,
                            modelName = modelName,
                            temperature = temperature,
                            maxTokens = maxTokens
                        )
                    app.database.settingsDao().insertModelConfig(newEntity)
                    modelConfig = newEntity
                    showModelPicker = false
                }
            },
            onManualModelSubmit = { providerId, manualModelId ->
                coroutineScope.launch {
                    val existing = app.database.settingsDao().getConfigForRole(role)
                    val newEntity = existing?.copy(providerId = providerId, modelName = manualModelId)
                        ?: ModelConfigEntity(
                            id = "cfg_${role.lowercase()}",
                            agentRole = role,
                            providerId = providerId,
                            modelName = manualModelId,
                            temperature = temperature,
                            maxTokens = maxTokens
                        )
                    app.database.settingsDao().insertModelConfig(newEntity)
                    modelConfig = newEntity
                    showModelPicker = false
                }
            }
        )
    }

    // Connect Social Account Dialog
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

    // Delete Custom Agent Dialog
    if (showDeleteConfirmation) {
        AlertDialog(
            onDismissRequest = { showDeleteConfirmation = false },
            title = {
                Text(
                    text = "Delete Custom Agent",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    color = TextPrimary
                )
            },
            text = {
                Text(
                    text = "Are you sure you want to delete '${agentEntity?.name}'? This will permanently remove this custom agent from your fleet.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = TextSecondary
                )
            },
            confirmButton = {
                Button(
                    onClick = {
                        coroutineScope.launch {
                            app.database.agentDao().deleteAgentById(agentId)
                            showDeleteConfirmation = false
                            onBack()
                        }
                    },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = ErrorRed,
                        contentColor = BackgroundDark
                    ),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Text("Delete Agent", fontWeight = FontWeight.Bold)
                }
            },
            dismissButton = {
                OutlinedButton(
                    onClick = { showDeleteConfirmation = false },
                    border = androidx.compose.foundation.BorderStroke(1.dp, BorderDark),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Text("Cancel", color = TextSecondary)
                }
            },
            containerColor = BackgroundDark,
            shape = RoundedCornerShape(16.dp)
        )
    }
}
