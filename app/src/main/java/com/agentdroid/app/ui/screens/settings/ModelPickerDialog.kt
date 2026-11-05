package com.agentdroid.app.ui.screens.settings

import androidx.compose.animation.AnimatedVisibility
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.agentdroid.app.data.local.entity.ApiProviderEntity
import com.agentdroid.app.data.local.entity.DiscoveredModelEntity
import com.agentdroid.app.domain.model.AgentRole
import com.agentdroid.app.domain.model.ModelCapability
import com.agentdroid.app.domain.model.requiredCapabilities
import com.agentdroid.app.ui.theme.*
import org.json.JSONArray

@Composable
fun ModelPickerDialog(
    targetAgentRole: String,
    targetAgentTitle: String,
    currentModelName: String,
    currentProviderId: String,
    discoveredModels: List<DiscoveredModelEntity>,
    providers: List<ApiProviderEntity>,
    onDismiss: () -> Unit,
    onSelectModel: (providerId: String, modelName: String) -> Unit,
    onManualModelSubmit: (providerId: String, manualModelId: String) -> Unit
) {
    var searchQuery by remember { mutableStateOf("") }
    var selectedProviderFilter by remember { mutableStateOf<String?>(null) } // null = All
    var selectedCapabilityFilter by remember { mutableStateOf<ModelCapability?>(null) }
    var filterLocalOnly by remember { mutableStateOf(false) }
    var filterCloudOnly by remember { mutableStateOf(false) }

    var showManualEntry by remember { mutableStateOf(false) }
    var manualModelId by remember { mutableStateOf("") }
    var manualProviderId by remember { mutableStateOf(providers.firstOrNull()?.id ?: "") }

    val roleEnum = try { AgentRole.valueOf(targetAgentRole) } catch (e: Exception) { null }
    val requiredCaps = roleEnum?.requiredCapabilities() ?: emptySet()

    // Filter models
    val filteredModels = discoveredModels.filter { model ->
        val matchesSearch = searchQuery.isBlank() ||
                model.modelId.contains(searchQuery, ignoreCase = true) ||
                model.displayName.contains(searchQuery, ignoreCase = true)

        val matchesProvider = selectedProviderFilter == null || model.providerId == selectedProviderFilter

        val matchesLocalCloud = when {
            filterLocalOnly -> model.isLocal
            filterCloudOnly -> !model.isLocal
            else -> true
        }

        val matchesCapability = if (selectedCapabilityFilter == null) {
            true
        } else {
            try {
                val jsonArr = JSONArray(model.capabilitiesJson)
                val caps = (0 until jsonArr.length()).map { jsonArr.getString(it) }
                caps.contains(selectedCapabilityFilter!!.name)
            } catch (e: Exception) {
                false
            }
        }

        matchesSearch && matchesProvider && matchesLocalCloud && matchesCapability
    }.sortedBy { it.displayName.lowercase() }

    Dialog(
        onDismissRequest = onDismiss,
        properties = DialogProperties(usePlatformDefaultWidth = false)
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
                            text = "ASSIGN AI MODEL",
                            style = MaterialTheme.typography.labelSmall,
                            letterSpacing = 1.5.sp,
                            color = PrimaryAccent,
                            fontFamily = FontFamily.Monospace,
                            fontWeight = FontWeight.Bold
                        )
                        Text(
                            text = targetAgentTitle,
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                            color = TextPrimary
                        )
                    }

                    IconButton(onClick = onDismiss) {
                        Icon(Icons.Default.Close, contentDescription = "Close", tint = TextMuted)
                    }
                }

                if (requiredCaps.isNotEmpty()) {
                    Spacer(modifier = Modifier.height(6.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "Required: ",
                            style = MaterialTheme.typography.labelSmall,
                            color = TextMuted,
                            fontSize = 10.sp
                        )
                        requiredCaps.forEach { cap ->
                            Surface(
                                color = SurfaceVariantDark,
                                shape = RoundedCornerShape(4.dp),
                                modifier = Modifier.padding(end = 4.dp)
                            ) {
                                Text(
                                    text = cap.displayName,
                                    fontSize = 9.sp,
                                    color = PrimaryAccent,
                                    fontFamily = FontFamily.Monospace,
                                    modifier = Modifier.padding(horizontal = 4.dp, vertical = 2.dp)
                                )
                            }
                        }
                    }
                }

                Spacer(modifier = Modifier.height(10.dp))

                // Search Bar
                OutlinedTextField(
                    value = searchQuery,
                    onValueChange = { searchQuery = it },
                    placeholder = { Text("Search by model name or ID...", color = TextMuted) },
                    leadingIcon = { Icon(Icons.Default.Search, contentDescription = null, tint = TextMuted) },
                    trailingIcon = {
                        if (searchQuery.isNotBlank()) {
                            IconButton(onClick = { searchQuery = "" }) {
                                Icon(Icons.Default.Clear, contentDescription = "Clear", tint = TextMuted)
                            }
                        }
                    },
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(8.dp),
                    singleLine = true,
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedContainerColor = CardBackground,
                        unfocusedContainerColor = CardBackground,
                        focusedBorderColor = PrimaryAccent,
                        unfocusedBorderColor = BorderDark,
                        focusedTextColor = TextPrimary,
                        unfocusedTextColor = TextPrimary
                    )
                )

                Spacer(modifier = Modifier.height(8.dp))

                // Filter Rows
                // 1. Provider Chips
                LazyRow(
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    item {
                        FilterChip(
                            selected = selectedProviderFilter == null,
                            onClick = { selectedProviderFilter = null },
                            label = { Text("All Providers (${discoveredModels.size})", fontSize = 10.sp) },
                            colors = FilterChipDefaults.filterChipColors(
                                selectedContainerColor = PrimaryAccent,
                                selectedLabelColor = BackgroundDark
                            )
                        )
                    }
                    items(providers) { prov ->
                        val count = discoveredModels.count { it.providerId == prov.id }
                        FilterChip(
                            selected = selectedProviderFilter == prov.id,
                            onClick = {
                                selectedProviderFilter = if (selectedProviderFilter == prov.id) null else prov.id
                            },
                            label = { Text("${prov.displayName} ($count)", fontSize = 10.sp) },
                            colors = FilterChipDefaults.filterChipColors(
                                selectedContainerColor = PrimaryAccent,
                                selectedLabelColor = BackgroundDark
                            )
                        )
                    }
                }

                Spacer(modifier = Modifier.height(4.dp))

                // 2. Capabilities & Type Chips
                LazyRow(
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    item {
                        FilterChip(
                            selected = filterCloudOnly,
                            onClick = {
                                filterCloudOnly = !filterCloudOnly
                                if (filterCloudOnly) filterLocalOnly = false
                            },
                            label = { Text("Cloud", fontSize = 10.sp) },
                            colors = FilterChipDefaults.filterChipColors(
                                selectedContainerColor = PrimaryAccent,
                                selectedLabelColor = BackgroundDark
                            )
                        )
                    }
                    item {
                        FilterChip(
                            selected = filterLocalOnly,
                            onClick = {
                                filterLocalOnly = !filterLocalOnly
                                if (filterLocalOnly) filterCloudOnly = false
                            },
                            label = { Text("Local LLMs", fontSize = 10.sp) },
                            colors = FilterChipDefaults.filterChipColors(
                                selectedContainerColor = ElectricBlue,
                                selectedLabelColor = BackgroundDark
                            )
                        )
                    }
                    items(listOf(ModelCapability.TOOL_CALLING, ModelCapability.VISION, ModelCapability.REASONING)) { cap ->
                        FilterChip(
                            selected = selectedCapabilityFilter == cap,
                            onClick = {
                                selectedCapabilityFilter = if (selectedCapabilityFilter == cap) null else cap
                            },
                            label = { Text(cap.displayName, fontSize = 10.sp) },
                            colors = FilterChipDefaults.filterChipColors(
                                selectedContainerColor = SurfaceVariantDark,
                                selectedLabelColor = PrimaryAccent
                            )
                        )
                    }
                }

                Spacer(modifier = Modifier.height(10.dp))

                // Model List
                LazyColumn(
                    modifier = Modifier.weight(1f),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    if (filteredModels.isEmpty()) {
                        item {
                            Surface(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(vertical = 20.dp),
                                color = SurfaceVariantDark.copy(alpha = 0.5f),
                                shape = RoundedCornerShape(10.dp)
                            ) {
                                Column(
                                    modifier = Modifier.padding(16.dp),
                                    horizontalAlignment = Alignment.CenterHorizontally
                                ) {
                                    Icon(Icons.Default.SearchOff, contentDescription = null, tint = TextMuted, modifier = Modifier.size(32.dp))
                                    Spacer(modifier = Modifier.height(8.dp))
                                    Text(
                                        "No models found matching current filters.",
                                        style = MaterialTheme.typography.bodyMedium,
                                        color = TextSecondary
                                    )
                                    Spacer(modifier = Modifier.height(4.dp))
                                    Text(
                                        "Use the Manual Model Entry below to connect any custom model ID.",
                                        style = MaterialTheme.typography.bodySmall,
                                        color = TextMuted,
                                        fontSize = 11.sp
                                    )
                                }
                            }
                        }
                    }

                    items(filteredModels) { model ->
                        val isAssigned = model.modelId == currentModelName && model.providerId == currentProviderId
                        val provider = providers.firstOrNull { it.id == model.providerId }

                        Surface(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clip(RoundedCornerShape(10.dp))
                                .border(
                                    width = 1.dp,
                                    color = if (isAssigned) PrimaryAccent else BorderDark,
                                    shape = RoundedCornerShape(10.dp)
                                )
                                .clickable {
                                    onSelectModel(model.providerId, model.modelId)
                                },
                            color = if (isAssigned) SurfaceVariantDark else CardBackground
                        ) {
                            Column(modifier = Modifier.padding(12.dp)) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Column(modifier = Modifier.weight(1f)) {
                                        Text(
                                            text = model.displayName,
                                            style = MaterialTheme.typography.bodyMedium,
                                            fontWeight = FontWeight.Bold,
                                            color = TextPrimary
                                        )
                                        Text(
                                            text = "${provider?.displayName ?: model.providerId} • ${model.modelId}",
                                            style = MaterialTheme.typography.labelSmall,
                                            fontFamily = FontFamily.Monospace,
                                            color = TextSecondary,
                                            fontSize = 10.sp
                                        )
                                    }

                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        // Local vs Cloud badge
                                        Surface(
                                            color = if (model.isLocal) ElectricBlue.copy(alpha = 0.15f) else PrimaryAccent.copy(alpha = 0.15f),
                                            shape = RoundedCornerShape(4.dp)
                                        ) {
                                            Text(
                                                text = if (model.isLocal) "LOCAL" else "CLOUD",
                                                color = if (model.isLocal) ElectricBlue else PrimaryAccent,
                                                style = MaterialTheme.typography.labelSmall,
                                                fontSize = 9.sp,
                                                fontFamily = FontFamily.Monospace,
                                                fontWeight = FontWeight.Bold,
                                                modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                                            )
                                        }

                                        Spacer(modifier = Modifier.width(6.dp))

                                        // Cached vs Verified badge
                                        Surface(
                                            color = if (model.isCached) TextMuted.copy(alpha = 0.2f) else SuccessGreen.copy(alpha = 0.15f),
                                            shape = RoundedCornerShape(4.dp)
                                        ) {
                                            Text(
                                                text = if (model.isCached) "CACHED" else "VERIFIED",
                                                color = if (model.isCached) TextMuted else SuccessGreen,
                                                style = MaterialTheme.typography.labelSmall,
                                                fontSize = 9.sp,
                                                fontFamily = FontFamily.Monospace,
                                                fontWeight = FontWeight.Bold,
                                                modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                                            )
                                        }

                                        if (isAssigned) {
                                            Spacer(modifier = Modifier.width(8.dp))
                                            Icon(Icons.Default.CheckCircle, contentDescription = "Active", tint = PrimaryAccent, modifier = Modifier.size(18.dp))
                                        }
                                    }
                                }

                                Spacer(modifier = Modifier.height(6.dp))

                                // Capability badges & Context window
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Row(
                                        horizontalArrangement = Arrangement.spacedBy(4.dp),
                                        verticalAlignment = Alignment.CenterVertically
                                    ) {
                                        if (model.capabilitiesJson.contains("TOOL_CALLING")) {
                                            CapsuleBadge("TOOLS", PrimaryAccent)
                                        }
                                        if (model.capabilitiesJson.contains("VISION")) {
                                            CapsuleBadge("VISION", ElectricBlue)
                                        }
                                        if (model.capabilitiesJson.contains("REASONING")) {
                                            CapsuleBadge("REASONING", WarningAmber)
                                        }
                                    }

                                    if (model.contextWindow != null && model.contextWindow > 0) {
                                        val displayCtx = if (model.contextWindow >= 1000000) {
                                            "${model.contextWindow / 1000000}M ctx"
                                        } else {
                                            "${model.contextWindow / 1000}k ctx"
                                        }
                                        Text(
                                            text = displayCtx,
                                            style = MaterialTheme.typography.labelSmall,
                                            color = TextMuted,
                                            fontFamily = FontFamily.Monospace,
                                            fontSize = 10.sp
                                        )
                                    }
                                }
                            }
                        }
                    }
                }

                Spacer(modifier = Modifier.height(10.dp))

                // Manual Model ID Entry Section
                Surface(
                    color = SurfaceVariantDark,
                    shape = RoundedCornerShape(10.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(modifier = Modifier.padding(10.dp)) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable { showManualEntry = !showManualEntry },
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Icon(Icons.Default.Edit, contentDescription = null, tint = PrimaryAccent, modifier = Modifier.size(16.dp))
                                Spacer(modifier = Modifier.width(6.dp))
                                Text("Manual Model ID Entry", style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Bold, color = TextPrimary)
                            }
                            Icon(
                                if (showManualEntry) Icons.Default.ExpandLess else Icons.Default.ExpandMore,
                                contentDescription = null,
                                tint = TextMuted
                            )
                        }

                        AnimatedVisibility(visible = showManualEntry) {
                            Column(modifier = Modifier.padding(top = 8.dp)) {
                                Text("Enter custom or fine-tuned model ID (e.g. ft:gpt-4o:org:... or llama3.2:3b):", fontSize = 10.sp, color = TextSecondary)
                                Spacer(modifier = Modifier.height(4.dp))
                                OutlinedTextField(
                                    value = manualModelId,
                                    onValueChange = { manualModelId = it },
                                    placeholder = { Text("Model ID string", color = TextMuted) },
                                    modifier = Modifier.fillMaxWidth(),
                                    shape = RoundedCornerShape(6.dp),
                                    singleLine = true,
                                    colors = OutlinedTextFieldDefaults.colors(
                                        focusedContainerColor = CardBackground,
                                        unfocusedContainerColor = CardBackground,
                                        focusedBorderColor = PrimaryAccent,
                                        unfocusedBorderColor = BorderDark,
                                        focusedTextColor = TextPrimary,
                                        unfocusedTextColor = TextPrimary
                                    )
                                )

                                Spacer(modifier = Modifier.height(6.dp))

                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.End
                                ) {
                                    Button(
                                        onClick = {
                                            if (manualModelId.isNotBlank() && manualProviderId.isNotBlank()) {
                                                onManualModelSubmit(manualProviderId, manualModelId.trim())
                                            }
                                        },
                                        enabled = manualModelId.isNotBlank(),
                                        shape = RoundedCornerShape(6.dp),
                                        colors = ButtonDefaults.buttonColors(containerColor = PrimaryAccent, contentColor = BackgroundDark),
                                        contentPadding = PaddingValues(horizontal = 12.dp, vertical = 4.dp),
                                        modifier = Modifier.height(32.dp)
                                    ) {
                                        Text("Assign Manual Model", fontSize = 11.sp, fontWeight = FontWeight.Bold)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun CapsuleBadge(text: String, color: Color) {
    Surface(
        color = color.copy(alpha = 0.12f),
        shape = RoundedCornerShape(3.dp)
    ) {
        Text(
            text = text,
            color = color,
            fontSize = 8.sp,
            fontFamily = FontFamily.Monospace,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(horizontal = 4.dp, vertical = 1.dp)
        )
    }
}
