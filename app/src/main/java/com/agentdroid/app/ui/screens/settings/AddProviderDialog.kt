package com.agentdroid.app.ui.screens.settings

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
import com.agentdroid.app.ai.connection.NetworkSecurityValidator
import com.agentdroid.app.data.local.entity.ApiProviderEntity
import com.agentdroid.app.ui.components.ObsidianCard
import com.agentdroid.app.ui.theme.*
import java.util.UUID

data class ProviderTemplate(
    val templateId: String,
    val name: String,
    val type: String,
    val defaultBaseUrl: String,
    val isLocal: Boolean,
    val keyRequired: Boolean = true,
    val description: String
)

val cloudTemplates = listOf(
    ProviderTemplate("openai", "OpenAI", "OPENAI", "https://api.openai.com/v1", false, true, "GPT-4o, GPT-4o Mini, o1 reasoning models"),
    ProviderTemplate("gemini", "Google Gemini", "GEMINI", "https://generativelanguage.googleapis.com", false, true, "Gemini 1.5 Pro, 1.5 Flash, 2.0 Flash"),
    ProviderTemplate("anthropic", "Anthropic Claude", "ANTHROPIC", "https://api.anthropic.com/v1", false, true, "Claude 3.5 Sonnet v2, Claude 3.5 Haiku"),
    ProviderTemplate("openrouter", "OpenRouter", "OPENROUTER", "https://openrouter.ai/api/v1", false, true, "Unified gateway to 100+ open & commercial models"),
    ProviderTemplate("groq", "Groq Cloud", "GROQ", "https://api.groq.com/openai/v1", false, true, "Ultra-fast LPU inference (Llama 3.3, Mixtral)"),
    ProviderTemplate("together", "Together AI", "TOGETHER", "https://api.together.xyz/v1", false, true, "Open source LLMs at production scale"),
    ProviderTemplate("mistral", "Mistral AI", "OPENAI_COMPATIBLE", "https://api.mistral.ai/v1", false, true, "Mistral Large, Codestral, Pixtral"),
    ProviderTemplate("deepseek", "DeepSeek", "OPENAI_COMPATIBLE", "https://api.deepseek.com/v1", false, true, "DeepSeek-V3, DeepSeek-R1 reasoning"),
    ProviderTemplate("custom_cloud", "Custom Cloud API", "OPENAI_COMPATIBLE", "https://api.my-domain.com/v1", false, true, "Any OpenAI-compatible hosted endpoint")
)

val localTemplates = listOf(
    ProviderTemplate("ollama", "Ollama Local Daemon", "OLLAMA", "http://10.0.2.2:11434", true, false, "Local models: Llama 3.2, Mistral, Qwen, DeepSeek"),
    ProviderTemplate("lmstudio", "LM Studio", "OPENAI_COMPATIBLE", "http://10.0.2.2:1234/v1", true, false, "Local desktop server with OpenAI compatibility"),
    ProviderTemplate("vllm", "vLLM Server", "OPENAI_COMPATIBLE", "http://10.0.2.2:8000/v1", true, false, "High-throughput GPU inference engine"),
    ProviderTemplate("localai", "LocalAI", "OPENAI_COMPATIBLE", "http://10.0.2.2:8080/v1", true, false, "Self-hosted, community OpenAI drop-in replacement"),
    ProviderTemplate("llamacpp", "llama.cpp Server", "OPENAI_COMPATIBLE", "http://10.0.2.2:8080/v1", true, false, "Lightweight C++ GGUF inference server"),
    ProviderTemplate("custom_local", "Custom Local LLM", "OPENAI_COMPATIBLE", "http://192.168.1.100:8000/v1", true, false, "Any self-hosted LAN / home server inference endpoint")
)

@Composable
fun AddProviderDialog(
    initialProvider: ApiProviderEntity? = null,
    initialApiKey: String = "",
    onDismiss: () -> Unit,
    onSave: (provider: ApiProviderEntity, apiKey: String) -> Unit
) {
    var selectedCategory by remember { mutableStateOf(if (initialProvider?.providerType == "OLLAMA") 1 else 0) }
    var selectedTemplate by remember { mutableStateOf<ProviderTemplate?>(null) }

    var providerName by remember { mutableStateOf(initialProvider?.displayName ?: "") }
    var baseUrl by remember { mutableStateOf(initialProvider?.baseUrl ?: "") }
    var providerType by remember { mutableStateOf(initialProvider?.providerType ?: "OPENAI") }
    var apiKey by remember { mutableStateOf(initialApiKey) }
    var showPassword by remember { mutableStateOf(false) }
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
                            text = if (initialProvider != null) "EDIT AI PROVIDER" else "CONNECT AI PROVIDER",
                            style = MaterialTheme.typography.labelSmall,
                            letterSpacing = 1.5.sp,
                            color = PrimaryAccent,
                            fontFamily = FontFamily.Monospace,
                            fontWeight = FontWeight.Bold
                        )
                        Text(
                            text = if (initialProvider != null) initialProvider.displayName else "Add Cloud or Local Server",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                            color = TextPrimary
                        )
                    }

                    IconButton(onClick = onDismiss) {
                        Icon(Icons.Default.Close, contentDescription = "Close", tint = TextMuted)
                    }
                }

                Spacer(modifier = Modifier.height(12.dp))

                // Category Tabs (Cloud vs Local)
                TabRow(
                    selectedTabIndex = selectedCategory,
                    containerColor = SurfaceVariantDark,
                    contentColor = PrimaryAccent,
                    modifier = Modifier.clip(RoundedCornerShape(8.dp))
                ) {
                    Tab(
                        selected = selectedCategory == 0,
                        onClick = { selectedCategory = 0 },
                        text = {
                            Text(
                                "CLOUD PROVIDERS",
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                fontFamily = FontFamily.Monospace,
                                color = if (selectedCategory == 0) PrimaryAccent else TextMuted
                            )
                        }
                    )
                    Tab(
                        selected = selectedCategory == 1,
                        onClick = { selectedCategory = 1 },
                        text = {
                            Text(
                                "LOCAL / LAN SERVERS",
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                fontFamily = FontFamily.Monospace,
                                color = if (selectedCategory == 1) ElectricBlue else TextMuted
                            )
                        }
                    )
                }

                Spacer(modifier = Modifier.height(14.dp))

                LazyColumn(
                    modifier = Modifier.weight(1f),
                    verticalArrangement = Arrangement.spacedBy(14.dp)
                ) {
                    // Quick Template Picker
                    item {
                        Text(
                            text = if (selectedCategory == 0) "SELECT CLOUD PRESET" else "SELECT LOCAL PRESET",
                            style = MaterialTheme.typography.labelSmall,
                            color = TextSecondary,
                            fontFamily = FontFamily.Monospace
                        )
                        Spacer(modifier = Modifier.height(6.dp))

                        val templates = if (selectedCategory == 0) cloudTemplates else localTemplates
                        LazyRow(
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            items(templates) { template ->
                                val isSelected = template.templateId == selectedTemplate?.templateId ||
                                        (selectedTemplate == null && template.name == providerName)
                                Surface(
                                    modifier = Modifier
                                        .clickable {
                                            selectedTemplate = template
                                            providerName = template.name
                                            baseUrl = template.defaultBaseUrl
                                            providerType = template.type
                                            validationError = null
                                        }
                                        .clip(RoundedCornerShape(8.dp))
                                        .border(
                                            width = 1.dp,
                                            color = if (isSelected) (if (template.isLocal) ElectricBlue else PrimaryAccent) else BorderDark,
                                            shape = RoundedCornerShape(8.dp)
                                        ),
                                    color = if (isSelected) SurfaceVariantDark else CardBackground
                                ) {
                                    Column(modifier = Modifier.padding(10.dp)) {
                                        Text(
                                            text = template.name,
                                            fontWeight = FontWeight.Bold,
                                            fontSize = 12.sp,
                                            color = if (isSelected) TextPrimary else TextSecondary
                                        )
                                        Text(
                                            text = if (template.isLocal) "LOCAL" else "CLOUD",
                                            fontSize = 9.sp,
                                            fontFamily = FontFamily.Monospace,
                                            color = if (template.isLocal) ElectricBlue else PrimaryAccent
                                        )
                                    }
                                }
                            }
                        }
                    }

                    // Form Fields
                    item {
                        // Provider Display Name
                        Text("Provider Name", style = MaterialTheme.typography.labelSmall, color = TextSecondary)
                        Spacer(modifier = Modifier.height(4.dp))
                        OutlinedTextField(
                            value = providerName,
                            onValueChange = { providerName = it; validationError = null },
                            placeholder = { Text("e.g. Ollama Local or OpenAI") },
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
                    }

                    item {
                        // Base URL
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text("Server Base URL", style = MaterialTheme.typography.labelSmall, color = TextSecondary)
                            if (selectedCategory == 1) {
                                Text(
                                    "Android Local Network",
                                    style = MaterialTheme.typography.labelSmall,
                                    fontSize = 10.sp,
                                    color = ElectricBlue,
                                    fontFamily = FontFamily.Monospace
                                )
                            }
                        }
                        Spacer(modifier = Modifier.height(4.dp))
                        OutlinedTextField(
                            value = baseUrl,
                            onValueChange = { baseUrl = it; validationError = null },
                            placeholder = { Text(if (selectedCategory == 1) "http://10.0.2.2:11434" else "https://api.openai.com/v1") },
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

                        // Helper note for local servers
                        if (selectedCategory == 1) {
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                text = "• Emulator Host: http://10.0.2.2:11434\n• Wi-Fi / Local PC: http://192.168.x.x:11434\n• Device-local: http://127.0.0.1:11434",
                                style = MaterialTheme.typography.bodySmall,
                                fontSize = 10.sp,
                                color = TextMuted,
                                fontFamily = FontFamily.Monospace
                            )
                        }
                    }

                    item {
                        // API Key
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text("API Key / Bearer Token", style = MaterialTheme.typography.labelSmall, color = TextSecondary)
                            if (selectedCategory == 1) {
                                Text(
                                    "Optional for Local",
                                    style = MaterialTheme.typography.labelSmall,
                                    fontSize = 10.sp,
                                    color = SuccessGreen,
                                    fontFamily = FontFamily.Monospace
                                )
                            }
                        }
                        Spacer(modifier = Modifier.height(4.dp))
                        OutlinedTextField(
                            value = apiKey,
                            onValueChange = { apiKey = it; validationError = null },
                            placeholder = { Text(if (selectedCategory == 1) "Optional (leave empty for Ollama / LM Studio)" else "sk-...") },
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(8.dp),
                            singleLine = true,
                            visualTransformation = if (showPassword) VisualTransformation.None else PasswordVisualTransformation(),
                            trailingIcon = {
                                IconButton(onClick = { showPassword = !showPassword }) {
                                    Icon(
                                        imageVector = if (showPassword) Icons.Default.VisibilityOff else Icons.Default.Visibility,
                                        contentDescription = "Toggle key visibility",
                                        tint = TextMuted
                                    )
                                }
                            },
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedContainerColor = CardBackground,
                                unfocusedContainerColor = CardBackground,
                                focusedBorderColor = PrimaryAccent,
                                unfocusedBorderColor = BorderDark,
                                focusedTextColor = TextPrimary,
                                unfocusedTextColor = TextPrimary
                            )
                        )
                    }

                    if (validationError != null) {
                        item {
                            Surface(
                                color = ErrorRed.copy(alpha = 0.15f),
                                shape = RoundedCornerShape(8.dp),
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Text(
                                    text = validationError!!,
                                    style = MaterialTheme.typography.bodySmall,
                                    color = ErrorRed,
                                    modifier = Modifier.padding(10.dp)
                                )
                            }
                        }
                    }
                }

                Spacer(modifier = Modifier.height(14.dp))

                // Action Buttons
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.End,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    TextButton(onClick = onDismiss) {
                        Text("Cancel", color = TextSecondary)
                    }

                    Spacer(modifier = Modifier.width(10.dp))

                    Button(
                        onClick = {
                            val trimmedName = providerName.trim()
                            val trimmedUrl = baseUrl.trim()
                            if (trimmedName.isBlank()) {
                                validationError = "Provider name is required."
                                return@Button
                            }
                            if (trimmedUrl.isBlank()) {
                                validationError = "Base URL is required."
                                return@Button
                            }

                            val validation = NetworkSecurityValidator.validateEndpointUrl(trimmedUrl)
                            if (!validation.isValid) {
                                validationError = validation.errorMessage ?: "Invalid URL."
                                return@Button
                            }

                            val isLocal = validation.isLocal || selectedCategory == 1 || providerType == "OLLAMA"
                            if (!isLocal && apiKey.trim().isBlank()) {
                                validationError = "Cloud providers require a valid API key."
                                return@Button
                            }

                            val provId = initialProvider?.id ?: "prov_${providerType.lowercase()}_${UUID.randomUUID().toString().take(6)}"
                            val entity = ApiProviderEntity(
                                id = provId,
                                providerType = providerType,
                                displayName = trimmedName,
                                baseUrl = validation.sanitizedUrl ?: trimmedUrl,
                                isEnabled = true
                            )
                            onSave(entity, apiKey.trim())
                        },
                        colors = ButtonDefaults.buttonColors(
                            containerColor = PrimaryAccent,
                            contentColor = BackgroundDark
                        ),
                        shape = RoundedCornerShape(8.dp)
                    ) {
                        Icon(Icons.Default.Check, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Save & Connect", fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
    }
}
