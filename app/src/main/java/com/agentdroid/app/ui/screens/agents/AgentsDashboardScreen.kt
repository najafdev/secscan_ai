package com.agentdroid.app.ui.screens.agents

import androidx.compose.animation.animateContentSize
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
import androidx.compose.material.icons.automirrored.filled.EventNote
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.agentdroid.app.AgentDroidApplication
import com.agentdroid.app.data.local.entity.AgentEntity
import com.agentdroid.app.data.local.entity.ModelConfigEntity
import com.agentdroid.app.domain.model.AgentExecutionState
import com.agentdroid.app.domain.model.AgentRole
import com.agentdroid.app.ui.components.AgentStatusBadge
import com.agentdroid.app.ui.components.ObsidianCard
import com.agentdroid.app.ui.screens.settings.ModelPickerDialog
import com.agentdroid.app.ui.theme.*
import kotlinx.coroutines.launch

@Composable
fun AgentsDashboardScreen(
    onNavigateToAgentDetails: (String) -> Unit,
    onNavigateToBuilder: () -> Unit,
    onNavigateToChat: ((String) -> Unit)? = null
) {
    val app = AgentDroidApplication.instance
    val coroutineScope = rememberCoroutineScope()
    val allAgents by app.database.agentDao().getAllAgents().collectAsState(initial = emptyList())
    val modelConfigs by app.database.settingsDao().getAllModelConfigs().collectAsState(initial = emptyList())
    val discoveredModels by app.database.settingsDao().getAllDiscoveredModels().collectAsState(initial = emptyList())
    val providers by app.database.settingsDao().getAllProviders().collectAsState(initial = emptyList())
    val connectedAccounts by app.database.accountDao().getAllAccounts().collectAsState(initial = emptyList())

    var searchQuery by remember { mutableStateOf("") }
    var selectedFilter by remember { mutableStateOf("All") }
    var agentForModelPicker by remember { mutableStateOf<Pair<String, String>?>(null) } // role to displayName
    var agentToDelete by remember { mutableStateOf<AgentEntity?>(null) }

    val filteredAgents = allAgents.filter { agent ->
        val matchesSearch = agent.name.contains(searchQuery, ignoreCase = true) ||
                agent.description.contains(searchQuery, ignoreCase = true) ||
                agent.role.contains(searchQuery, ignoreCase = true)
        val matchesFilter = when (selectedFilter) {
            "Core" -> !agent.isCustom
            "Custom" -> agent.isCustom
            "Active" -> agent.isEnabled
            else -> true
        }
        matchesSearch && matchesFilter
    }

    Scaffold(
        floatingActionButton = {
            FloatingActionButton(
                onClick = onNavigateToBuilder,
                containerColor = PrimaryAccent,
                contentColor = BackgroundDark,
                shape = CircleShape,
                modifier = Modifier.padding(bottom = 60.dp)
            ) {
                Icon(Icons.Default.Add, contentDescription = "Create Custom Agent")
            }
        },
        containerColor = BackgroundDark
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            item {
                Spacer(modifier = Modifier.height(14.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text(
                            text = "AGENT DIRECTORY",
                            style = MaterialTheme.typography.labelSmall,
                            letterSpacing = 1.5.sp,
                            color = PrimaryAccent
                        )
                        Text(
                            text = "Specialized AI Fleet",
                            style = MaterialTheme.typography.headlineMedium,
                            fontWeight = FontWeight.Bold,
                            color = TextPrimary
                        )
                    }
                    Surface(
                        color = SurfaceVariantDark,
                        shape = RoundedCornerShape(12.dp),
                        border = androidx.compose.foundation.BorderStroke(1.dp, BorderDark)
                    ) {
                        Text(
                            text = "${allAgents.count { it.isEnabled }} of ${allAgents.size} Active",
                            style = MaterialTheme.typography.labelSmall,
                            color = TextSecondary,
                            modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp)
                        )
                    }
                }
            }

            // Search Bar & Filter Chips
            item {
                OutlinedTextField(
                    value = searchQuery,
                    onValueChange = { searchQuery = it },
                    placeholder = { Text("Search agents by capability or name...", fontSize = 13.sp, color = TextMuted) },
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = PrimaryAccent,
                        unfocusedBorderColor = BorderDark,
                        focusedContainerColor = CardBackground,
                        unfocusedContainerColor = CardBackground
                    ),
                    leadingIcon = {
                        Icon(Icons.Default.Search, contentDescription = null, tint = TextMuted, modifier = Modifier.size(18.dp))
                    },
                    singleLine = true
                )
                Spacer(modifier = Modifier.height(8.dp))
                LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    items(listOf("All", "Core", "Custom", "Active")) { filter ->
                        FilterChip(
                            selected = selectedFilter == filter,
                            onClick = { selectedFilter = filter },
                            label = { Text(filter, fontSize = 11.5.sp) },
                            colors = FilterChipDefaults.filterChipColors(
                                selectedContainerColor = PrimaryAccent,
                                selectedLabelColor = BackgroundDark,
                                containerColor = SurfaceVariantDark,
                                labelColor = TextSecondary
                            ),
                            border = FilterChipDefaults.filterChipBorder(
                                enabled = true,
                                selected = selectedFilter == filter,
                                borderColor = if (selectedFilter == filter) PrimaryAccent else BorderDark
                            )
                        )
                    }
                }
            }

            items(filteredAgents) { agent ->
                val roleEnum = AgentRole.fromId(agent.id)
                val config = modelConfigs.firstOrNull { it.agentRole == agent.role }

                val (roleColor, roleIcon) = getAgentVisuals(roleEnum)

                ObsidianCard(
                    modifier = Modifier.clickable { onNavigateToAgentDetails(agent.id) },
                    borderColor = if (agent.isEnabled) BorderDark else BorderDark.copy(alpha = 0.4f)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(
                                modifier = Modifier
                                    .size(38.dp)
                                    .clip(RoundedCornerShape(10.dp))
                                    .background(roleColor.copy(alpha = 0.14f))
                                    .border(1.dp, roleColor.copy(alpha = 0.35f), RoundedCornerShape(10.dp)),
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(
                                    imageVector = roleIcon,
                                    contentDescription = null,
                                    tint = roleColor,
                                    modifier = Modifier.size(20.dp)
                                )
                            }
                            Spacer(modifier = Modifier.width(12.dp))
                            Column {
                                Text(
                                    text = agent.name,
                                    style = MaterialTheme.typography.titleMedium,
                                    fontWeight = FontWeight.SemiBold,
                                    color = TextPrimary
                                )
                                Text(
                                    text = if (agent.isCustom) "CUSTOM EXTENSION" else agent.role,
                                    style = MaterialTheme.typography.labelSmall,
                                    color = if (agent.isCustom) PrimaryAccent else TextMuted,
                                    fontSize = 9.sp,
                                    letterSpacing = 0.5.sp
                                )
                            }
                        }

                        Row(verticalAlignment = Alignment.CenterVertically) {
                            if (agent.isCustom && !agent.id.startsWith("plugin_")) {
                                IconButton(
                                    onClick = { agentToDelete = agent },
                                    modifier = Modifier.size(32.dp)
                                ) {
                                    Icon(
                                        Icons.Default.DeleteOutline,
                                        contentDescription = "Delete Agent",
                                        tint = ErrorRed.copy(alpha = 0.85f),
                                        modifier = Modifier.size(18.dp)
                                    )
                                }
                                Spacer(modifier = Modifier.width(2.dp))
                            }
                            if (onNavigateToChat != null) {
                                IconButton(
                                    onClick = { onNavigateToChat("Assign task to ${agent.name}: ") },
                                    modifier = Modifier.size(32.dp)
                                ) {
                                    Icon(
                                        Icons.Default.Forum,
                                        contentDescription = "Chat & Assign to ${agent.name}",
                                        tint = PrimaryAccent,
                                        modifier = Modifier.size(18.dp)
                                    )
                                }
                                Spacer(modifier = Modifier.width(2.dp))
                            }
                            IconButton(
                                onClick = { onNavigateToAgentDetails(agent.id) },
                                modifier = Modifier.size(32.dp)
                            ) {
                                Icon(
                                    Icons.Default.Tune,
                                    contentDescription = "Agent Settings",
                                    tint = PrimaryAccent,
                                    modifier = Modifier.size(18.dp)
                                )
                            }
                            Spacer(modifier = Modifier.width(4.dp))
                            Switch(
                                checked = agent.isEnabled,
                                onCheckedChange = { checked ->
                                    coroutineScope.launch {
                                        app.database.agentDao().setAgentEnabled(agent.id, checked)
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
                    }

                    Spacer(modifier = Modifier.height(10.dp))
                    Text(
                        text = agent.description,
                        style = MaterialTheme.typography.bodyMedium,
                        color = TextSecondary,
                        maxLines = 2
                    )

                    Spacer(modifier = Modifier.height(12.dp))
                    HorizontalDivider(color = BorderDark.copy(alpha = 0.6f), thickness = 0.8.dp)
                    Spacer(modifier = Modifier.height(8.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            // Interactive Model Picker Pill
                            Surface(
                                modifier = Modifier.clickable {
                                    agentForModelPicker = agent.role to agent.name
                                },
                                color = SurfaceVariantDark,
                                shape = RoundedCornerShape(6.dp),
                                border = androidx.compose.foundation.BorderStroke(0.8.dp, PrimaryAccent.copy(alpha = 0.4f))
                            ) {
                                Row(
                                    modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Icon(Icons.Default.Memory, contentDescription = null, tint = PrimaryAccent, modifier = Modifier.size(13.dp))
                                    Spacer(modifier = Modifier.width(4.dp))
                                    Text(
                                        text = config?.modelName ?: "Assign Model",
                                        style = MaterialTheme.typography.labelSmall,
                                        color = PrimaryAccent,
                                        fontSize = 9.5.sp,
                                        fontWeight = FontWeight.SemiBold
                                    )
                                    Spacer(modifier = Modifier.width(3.dp))
                                    Icon(Icons.Default.ArrowDropDown, contentDescription = null, tint = PrimaryAccent, modifier = Modifier.size(13.dp))
                                }
                            }

                            // Social Media badge if applicable
                            if (agent.role == "SOCIAL_MEDIA") {
                                Surface(
                                    modifier = Modifier.clickable { onNavigateToAgentDetails(agent.id) },
                                    color = SocialAgentColor.copy(alpha = 0.15f),
                                    shape = RoundedCornerShape(6.dp),
                                    border = androidx.compose.foundation.BorderStroke(0.8.dp, SocialAgentColor.copy(alpha = 0.4f))
                                ) {
                                    Text(
                                        text = "${connectedAccounts.size} Linked",
                                        style = MaterialTheme.typography.labelSmall,
                                        color = SocialAgentColor,
                                        fontSize = 9.5.sp,
                                        fontWeight = FontWeight.SemiBold,
                                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 4.dp)
                                    )
                                }
                            }
                        }

                        Row(verticalAlignment = Alignment.CenterVertically) {
                            AgentStatusBadge(
                                state = if (agent.isEnabled) AgentExecutionState.IDLE else AgentExecutionState.CANCELLED
                            )
                            Spacer(modifier = Modifier.width(6.dp))
                            Icon(Icons.Default.ChevronRight, contentDescription = null, tint = TextMuted, modifier = Modifier.size(16.dp))
                        }
                    }
                }
            }

            item { Spacer(modifier = Modifier.height(80.dp)) }
        }
    }

    // Interactive Model Picker Dialog for any agent from directory
    if (agentForModelPicker != null) {
        val (role, name) = agentForModelPicker!!
        val currentCfg = modelConfigs.firstOrNull { it.agentRole == role }
        ModelPickerDialog(
            targetAgentRole = role,
            targetAgentTitle = name,
            currentModelName = currentCfg?.modelName ?: "",
            currentProviderId = currentCfg?.providerId ?: "",
            discoveredModels = discoveredModels,
            providers = providers,
            onDismiss = { agentForModelPicker = null },
            onSelectModel = { providerId, modelName ->
                coroutineScope.launch {
                    val existing = app.database.settingsDao().getConfigForRole(role)
                    val newEntity = existing?.copy(providerId = providerId, modelName = modelName)
                        ?: ModelConfigEntity(
                            id = "cfg_${role.lowercase()}",
                            agentRole = role,
                            providerId = providerId,
                            modelName = modelName,
                            temperature = 0.7f,
                            maxTokens = 4096
                        )
                    app.database.settingsDao().insertModelConfig(newEntity)
                    agentForModelPicker = null
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
                            temperature = 0.7f,
                            maxTokens = 4096
                        )
                    app.database.settingsDao().insertModelConfig(newEntity)
                    agentForModelPicker = null
                }
            }
        )
    }

    if (agentToDelete != null) {
        val target = agentToDelete!!
        AlertDialog(
            onDismissRequest = { agentToDelete = null },
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
                    text = "Are you sure you want to delete '${target.name}'? This will permanently remove this custom agent and all of its assigned tools and instructions.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = TextSecondary
                )
            },
            confirmButton = {
                Button(
                    onClick = {
                        coroutineScope.launch {
                            app.database.agentDao().deleteAgentById(target.id)
                            agentToDelete = null
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
                    onClick = { agentToDelete = null },
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

private fun getAgentVisuals(role: AgentRole): Pair<Color, ImageVector> {
    return when (role) {
        AgentRole.MASTER -> MasterAgentColor to Icons.Default.SmartToy
        AgentRole.PHONE_CONTROL -> PhoneAgentColor to Icons.Default.Smartphone
        AgentRole.SOCIAL_MEDIA -> SocialAgentColor to Icons.Default.Share
        AgentRole.CONTENT_CREATION -> ContentAgentColor to Icons.Default.EditNote
        AgentRole.RESEARCH -> ResearchAgentColor to Icons.Default.Explore
        AgentRole.COMMUNICATION -> CommAgentColor to Icons.Default.Forum
        AgentRole.FILE_MANAGEMENT -> FileAgentColor to Icons.Default.FolderSpecial
        AgentRole.PRODUCTIVITY -> ProductivityAgentColor to Icons.AutoMirrored.Filled.EventNote
        AgentRole.ANALYTICS -> AnalyticsAgentColor to Icons.Default.Analytics
        AgentRole.BROWSER -> BrowserAgentColor to Icons.Default.Language
        AgentRole.SECURITY -> SecurityAgentColor to Icons.Default.Shield
        AgentRole.CUSTOM -> CustomAgentColor to Icons.Default.Extension
    }
}
