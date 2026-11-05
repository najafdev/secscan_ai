package com.agentdroid.app.ui.screens.legal

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.widget.Toast
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
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
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.agentdroid.app.ui.components.ObsidianCard
import com.agentdroid.app.ui.theme.*

enum class LegalTab(val title: String, val icon: ImageVector) {
    PRIVACY_POLICY("Privacy Policy", Icons.Default.PrivacyTip),
    TERMS_AND_CONDITIONS("Terms & Conditions", Icons.Default.Description)
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LegalViewerScreen(
    initialTab: String = "privacy",
    onBack: () -> Unit
) {
    val context = LocalContext.current
    var currentTab by remember {
        mutableStateOf(
            if (initialTab.equals("terms", ignoreCase = true)) {
                LegalTab.TERMS_AND_CONDITIONS
            } else {
                LegalTab.PRIVACY_POLICY
            }
        )
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        androidx.compose.foundation.Image(
                            painter = androidx.compose.ui.res.painterResource(id = com.agentdroid.app.R.drawable.agentdroid_logo),
                            contentDescription = "AgentDroid Logo",
                            modifier = Modifier
                                .size(28.dp)
                                .clip(RoundedCornerShape(6.dp))
                        )
                        Spacer(modifier = Modifier.width(10.dp))
                        Column {
                            Text(
                                text = "Legal & Compliance",
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold,
                                color = TextPrimary
                            )
                            Text(
                                text = "AgentDroid AI Operating System • v1.0.0",
                                style = MaterialTheme.typography.labelSmall,
                                fontFamily = FontFamily.Monospace,
                                color = PrimaryAccent
                            )
                        }
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(
                            Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "Back",
                            tint = TextPrimary
                        )
                    }
                },
                actions = {
                    IconButton(
                        onClick = {
                            val textToCopy = if (currentTab == LegalTab.PRIVACY_POLICY) {
                                FULL_PRIVACY_POLICY_TEXT
                            } else {
                                FULL_TERMS_TEXT
                            }
                            val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                            val clip = ClipData.newPlainText("AgentDroid Legal Text", textToCopy)
                            clipboard.setPrimaryClip(clip)
                            Toast.makeText(context, "${currentTab.title} copied to clipboard", Toast.LENGTH_SHORT).show()
                        }
                    ) {
                        Icon(
                            Icons.Default.ContentCopy,
                            contentDescription = "Copy Document",
                            tint = TextSecondary
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = BackgroundDark,
                    titleContentColor = TextPrimary,
                    navigationIconContentColor = TextPrimary
                )
            )
        },
        containerColor = BackgroundDark
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .background(BackgroundDark)
        ) {
            // Segmented Tab Selector
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 8.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .background(CardBackground)
                    .border(0.5.dp, BorderDark, RoundedCornerShape(12.dp))
                    .padding(4.dp),
                horizontalArrangement = Arrangement.spacedBy(4.dp)
            ) {
                LegalTab.values().forEach { tab ->
                    val isSelected = currentTab == tab
                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .clip(RoundedCornerShape(8.dp))
                            .background(if (isSelected) PrimaryAccent.copy(alpha = 0.2f) else Color.Transparent)
                            .clickable { currentTab = tab }
                            .padding(vertical = 10.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.Center
                        ) {
                            Icon(
                                imageVector = tab.icon,
                                contentDescription = null,
                                tint = if (isSelected) PrimaryAccent else TextMuted,
                                modifier = Modifier.size(16.dp)
                            )
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(
                                text = tab.title,
                                style = MaterialTheme.typography.labelMedium,
                                fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
                                color = if (isSelected) TextPrimary else TextSecondary
                            )
                        }
                    }
                }
            }

            // Animated Tab Content
            AnimatedContent(
                targetState = currentTab,
                transitionSpec = { fadeIn() togetherWith fadeOut() },
                modifier = Modifier.weight(1f)
            ) { tab ->
                when (tab) {
                    LegalTab.PRIVACY_POLICY -> PrivacyPolicyContent()
                    LegalTab.TERMS_AND_CONDITIONS -> TermsAndConditionsContent()
                }
            }
        }
    }
}

@Composable
private fun PrivacyPolicyContent() {
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        item { Spacer(modifier = Modifier.height(4.dp)) }

        // Core Guarantee Banner
        item {
            ObsidianCard(borderColor = SuccessGreen.copy(alpha = 0.4f)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .size(36.dp)
                            .clip(CircleShape)
                            .background(SuccessGreen.copy(alpha = 0.15f)),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            Icons.Default.Shield,
                            contentDescription = null,
                            tint = SuccessGreen,
                            modifier = Modifier.size(20.dp)
                        )
                    }
                    Spacer(modifier = Modifier.width(12.dp))
                    Column {
                        Text(
                            text = "USER DATA SOVEREIGNTY GUARANTEE",
                            style = MaterialTheme.typography.labelSmall,
                            fontFamily = FontFamily.Monospace,
                            fontWeight = FontWeight.Bold,
                            color = SuccessGreen
                        )
                        Text(
                            text = "Zero tracking • Local storage • Hardware encryption",
                            style = MaterialTheme.typography.bodySmall,
                            color = TextSecondary
                        )
                    }
                }
                Spacer(modifier = Modifier.height(10.dp))
                Text(
                    text = "AgentDroid does not operate centralized servers, does not track analytics or location, and never sells user data. All chats, task plans, and settings reside on your device.",
                    style = MaterialTheme.typography.bodySmall,
                    color = TextPrimary,
                    lineHeight = 18.sp
                )
            }
        }

        // Section 1: Information We Do NOT Collect
        item {
            LegalSectionCard(
                sectionNumber = "1",
                title = "Information We Do NOT Collect",
                badge = "ZERO TRACKING",
                badgeColor = ElectricBlue
            ) {
                LegalBullet("No Advertising SDKs", "AgentDroid contains zero third-party advertising or commercial marketing beacons.")
                LegalBullet("No Location Tracking", "The application never requests or records your physical GPS or network coordinates.")
                LegalBullet("No Contact or SMS Harvesting", "AgentDroid does not scan or upload your contacts, phone logs, or personal messages.")
                LegalBullet("No Central Telemetry", "Prompts and conversations are never routed to any centralized telemetry server operated by AgentDroid maintainers.")
            }
        }

        // Section 2: Prominent Accessibility Service Disclosure
        item {
            LegalSectionCard(
                sectionNumber = "2",
                title = "Prominent Accessibility Service Disclosure",
                badge = "ANDROID ACCESSIBILITY",
                badgeColor = WarningAmber
            ) {
                Text(
                    text = "AgentDroid features an optional Android Accessibility Service (AgentDroidAccessibilityService) utilized by the Phone Control Agent for autonomous task execution:",
                    style = MaterialTheme.typography.bodySmall,
                    color = TextSecondary,
                    lineHeight = 18.sp
                )
                Spacer(modifier = Modifier.height(8.dp))
                LegalBullet(
                    "Purpose of Service",
                    "Permits simulated user actions (clicking buttons, typing text, scrolling, navigating home/back) on installed applications to fulfill user-directed goals."
                )
                LegalBullet(
                    "Scope of Data Accessed",
                    "Inspects visible on-screen text and view node identifiers strictly during active, user-initiated automated workflows."
                )
                LegalBullet(
                    "Local In-Memory Evaluation",
                    "Screen content is evaluated ephemerally in RAM. It is NEVER recorded continuously, never stored on disk, and never transmitted to developer servers."
                )
                LegalBullet(
                    "Revocation & Control",
                    "Accessibility is strictly optional and can be enabled or revoked at any time via Android Settings → Accessibility → AgentDroid."
                )
            }
        }

        // Section 3: Information Processed On-Device
        item {
            LegalSectionCard(
                sectionNumber = "3",
                title = "Information Stored Locally On-Device",
                badge = "AES-256 GCM",
                badgeColor = PrimaryAccent
            ) {
                LegalBullet("Hardware Keystore Encryption", "API keys and auth tokens are encrypted using AES-256 GCM via AndroidX MasterKey and stored in private hardware-backed storage.")
                LegalBullet("Local SQLite Database", "Conversational histories, workflow definitions, and task states reside in your phone's encrypted SQLite database (agentdroid.db).")
                LegalBullet("Multi-Tier Context Memory", "Working context and long-term user preferences are retained locally and can be purged at any time.")
                LegalBullet("On-Device Audit Logs", "Activity logs of executed agent actions are stored locally for verification and auto-pruned after 30 days.")
            }
        }

        // Section 4: AI Providers & Network Boundaries
        item {
            LegalSectionCard(
                sectionNumber = "4",
                title = "AI Providers & Network Transmission",
                badge = "DIRECT CLIENT",
                badgeColor = ElectricBlue
            ) {
                LegalBullet(
                    "Cloud AI Providers (OpenAI, Gemini, Anthropic, Groq)",
                    "If you configure cloud models, prompts are transmitted directly via encrypted HTTPS from your device to the chosen vendor. Interactions are governed by that provider's commercial terms."
                )
                LegalBullet(
                    "Local Private LLMs (Ollama, LM Studio)",
                    "When connected to local inference servers over home Wi-Fi or loopback, zero prompt bytes leave your private local network."
                )
            }
        }

        // Section 5: User Rights & Deletion
        item {
            LegalSectionCard(
                sectionNumber = "5",
                title = "Data Retention, Purging & User Rights",
                badge = "COMPLETE CONTROL",
                badgeColor = SuccessGreen
            ) {
                LegalBullet("Granular Memory Reset", "Wipe active context, session history, or learned facts independently in Settings → Data & Memory.")
                LegalBullet("Credential Deletion", "Disconnecting an AI provider immediately wipes the associated encryption key from the hardware Keystore.")
                LegalBullet("Total App Purge", "Clearing storage in Android Settings or uninstalling AgentDroid permanently destroys all local databases, ciphertexts, and memories.")
            }
        }

        // Section 6: Contact & Jurisdiction
        item {
            LegalSectionCard(
                sectionNumber = "6",
                title = "Contact & Legal Governance",
                badge = "OPEN SOURCE",
                badgeColor = TextSecondary
            ) {
                Text(
                    text = "AgentDroid is developed as an open-source initiative under the Apache 2.0 license.\n\n" +
                            "• Effective Date: November 1, 2026\n" +
                            "• Contact Email: [OFFICIAL CONTACT EMAIL - e.g. privacy@agentdroid.org]\n" +
                            "• Repository: https://github.com/[PROJECT_OWNER]/agentdroid\n" +
                            "• Applicable Jurisdiction: [APPLICABLE JURISDICTION]",
                    style = MaterialTheme.typography.bodySmall,
                    color = TextSecondary,
                    lineHeight = 18.sp
                )
            }
        }

        item { Spacer(modifier = Modifier.height(40.dp)) }
    }
}

@Composable
private fun TermsAndConditionsContent() {
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        item { Spacer(modifier = Modifier.height(4.dp)) }

        // Terms Summary Banner
        item {
            ObsidianCard(borderColor = PrimaryAccent.copy(alpha = 0.4f)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .size(36.dp)
                            .clip(CircleShape)
                            .background(PrimaryAccent.copy(alpha = 0.15f)),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            Icons.Default.Gavel,
                            contentDescription = null,
                            tint = PrimaryAccent,
                            modifier = Modifier.size(20.dp)
                        )
                    }
                    Spacer(modifier = Modifier.width(12.dp))
                    Column {
                        Text(
                            text = "TERMS OF USE & RESPONSIBILITY",
                            style = MaterialTheme.typography.labelSmall,
                            fontFamily = FontFamily.Monospace,
                            fontWeight = FontWeight.Bold,
                            color = PrimaryAccent
                        )
                        Text(
                            text = "Apache 2.0 License • Human-in-the-Loop Oversight",
                            style = MaterialTheme.typography.bodySmall,
                            color = TextSecondary
                        )
                    }
                }
                Spacer(modifier = Modifier.height(10.dp))
                Text(
                    text = "By installing and operating AgentDroid, you agree to these Terms. You acknowledge that AgentDroid coordinates autonomous AI systems and that you maintain responsibility for validating actions executed on your device.",
                    style = MaterialTheme.typography.bodySmall,
                    color = TextPrimary,
                    lineHeight = 18.sp
                )
            }
        }

        // Section 1: Acceptance & License
        item {
            LegalSectionCard(
                sectionNumber = "1",
                title = "Acceptance of Terms & Apache 2.0 License",
                badge = "APACHE 2.0",
                badgeColor = SuccessGreen
            ) {
                Text(
                    text = "AgentDroid is open-source software licensed under the Apache License, Version 2.0. You may freely inspect, fork, and adapt the code subject to retaining original copyright notices, disclaimers, and license declarations.",
                    style = MaterialTheme.typography.bodySmall,
                    color = TextSecondary,
                    lineHeight = 18.sp
                )
            }
        }

        // Section 2: Human-in-the-Loop & Oversight
        item {
            LegalSectionCard(
                sectionNumber = "2",
                title = "User Oversight & Autonomous Actions",
                badge = "HUMAN-IN-THE-LOOP",
                badgeColor = WarningAmber
            ) {
                LegalBullet(
                    "Generative AI Disclaimer",
                    "AI models can hallucinate, produce erroneous interpretations, or misidentify UI buttons. You bear ultimate responsibility for all automated actions executed by the software."
                )
                LegalBullet(
                    "Approval Queue for High-Risk Actions",
                    "High-risk actions (modifying files, sending communications, financial operations) trigger human confirmation prompts. You are responsible for reviewing parameters before tapping Approve."
                )
                LegalBullet(
                    "Emergency Killswitch",
                    "You may halt running automation tasks at any time using the in-app Stop button, persistent notification, or pressing Volume Down three times."
                )
            }
        }

        // Section 3: User API Credentials
        item {
            LegalSectionCard(
                sectionNumber = "3",
                title = "API Credentials & Provider Billing",
                badge = "BYOK (BRING YOUR OWN KEY)",
                badgeColor = ElectricBlue
            ) {
                LegalBullet(
                    "Commercial API Billing",
                    "You are solely responsible for acquiring, managing, and securing your own API keys for third-party cloud services (OpenAI, Gemini, Anthropic, etc.) and paying all vendor usage fees."
                )
                LegalBullet(
                    "Zero Markups or Surcharges",
                    "AgentDroid charges zero fees for API traffic. All network requests travel directly between your phone and your chosen provider."
                )
            }
        }

        // Section 4: Prohibited Uses
        item {
            LegalSectionCard(
                sectionNumber = "4",
                title = "Prohibited Malicious & Harmful Uses",
                badge = "SAFETY POLICY",
                badgeColor = ErrorRed
            ) {
                LegalBullet("Unlawful Conduct", "You may not use AgentDroid to violate local or international laws, conduct harassment, or distribute malware.")
                LegalBullet("Unauthorized Surveillance", "You may not deploy automation to intercept passwords, perform unauthorized keylogging, or spy on third parties.")
                LegalBullet("Terms of Service Violations", "Automating spam, bulk scraping, or abusive bot activity that violates third-party app terms of service is prohibited.")
                LegalBullet("Emergency Systems", "AgentDroid must never be used to automate emergency calls (911/112) or interfere with life-critical software.")
            }
        }

        // Section 5: Warranty & Liability
        item {
            LegalSectionCard(
                sectionNumber = "5",
                title = "Disclaimer of Warranties & Liability Limitation",
                badge = "AS IS",
                badgeColor = TextMuted
            ) {
                Text(
                    text = "THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.\n\n" +
                            "IN NO EVENT SHALL THE AUTHORS, CONTRIBUTORS, OR MAINTAINERS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES (INCLUDING LOSS OF DATA, DEVICE DAMAGE, OR UNINTENDED SOCIAL BROADCASTS) ARISING FROM YOUR USE OF THE APPLICATION.",
                    style = MaterialTheme.typography.bodySmall,
                    color = TextSecondary,
                    lineHeight = 18.sp
                )
            }
        }

        // Section 6: Dispute Resolution
        item {
            LegalSectionCard(
                sectionNumber = "6",
                title = "Governing Law & Legal Entity",
                badge = "GOVERNANCE",
                badgeColor = PrimaryAccent
            ) {
                Text(
                    text = "• Legal Entity: [LEGAL ENTITY NAME / AGENTDROID MAINTAINERS]\n" +
                            "• Governing Jurisdiction: [APPLICABLE JURISDICTION]\n" +
                            "• Contact: [OFFICIAL CONTACT EMAIL - e.g. legal@agentdroid.org]\n" +
                            "• Last Updated: November 1, 2026",
                    style = MaterialTheme.typography.bodySmall,
                    color = TextSecondary,
                    lineHeight = 18.sp
                )
            }
        }

        item { Spacer(modifier = Modifier.height(40.dp)) }
    }
}

@Composable
private fun LegalSectionCard(
    sectionNumber: String,
    title: String,
    badge: String,
    badgeColor: Color,
    content: @Composable ColumnScope.() -> Unit
) {
    ObsidianCard(modifier = Modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.weight(1f)
            ) {
                Text(
                    text = "$sectionNumber.",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    color = PrimaryAccent
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = title,
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.SemiBold,
                    color = TextPrimary
                )
            }

            Surface(
                color = badgeColor.copy(alpha = 0.15f),
                shape = RoundedCornerShape(4.dp)
            ) {
                Text(
                    text = badge,
                    style = MaterialTheme.typography.labelSmall,
                    color = badgeColor,
                    fontSize = 9.sp,
                    fontFamily = FontFamily.Monospace,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                )
            }
        }

        Spacer(modifier = Modifier.height(10.dp))
        HorizontalDivider(color = BorderDark.copy(alpha = 0.5f), thickness = 0.5.dp)
        Spacer(modifier = Modifier.height(10.dp))

        content()
    }
}

@Composable
private fun LegalBullet(label: String, body: String) {
    Column(modifier = Modifier.padding(vertical = 4.dp)) {
        Row(verticalAlignment = Alignment.Top) {
            Text(
                text = "•",
                color = PrimaryAccent,
                fontWeight = FontWeight.Bold,
                fontSize = 14.sp
            )
            Spacer(modifier = Modifier.width(8.dp))
            Column {
                Text(
                    text = label,
                    style = MaterialTheme.typography.bodySmall,
                    fontWeight = FontWeight.SemiBold,
                    color = TextPrimary
                )
                Spacer(modifier = Modifier.height(2.dp))
                Text(
                    text = body,
                    style = MaterialTheme.typography.bodySmall,
                    color = TextSecondary,
                    lineHeight = 16.sp
                )
            }
        }
    }
}

private const val FULL_PRIVACY_POLICY_TEXT = """
AGENTDROID PRIVACY POLICY (v1.0.0)
Effective Date: November 1, 2026
Legal Entity: [LEGAL ENTITY NAME / AGENTDROID PROJECT]
Contact: [OFFICIAL CONTACT EMAIL]

1. USER DATA SOVEREIGNTY
AgentDroid does not operate centralized servers, does not track analytics, and does not sell personal data. All data resides on your physical hardware.

2. WHAT WE DO NOT COLLECT
- Zero advertising or marketing beacons
- Zero location tracking
- Zero contacts or SMS harvesting
- Zero prompt telemetry

3. PROMINENT ACCESSIBILITY DISCLOSURE
AgentDroid includes an optional Android Accessibility Service for Phone Automation:
- Purpose: Execute simulated gestures (taps, typing, scrolls) for user goals.
- Data: Inspects visible on-screen text strictly during active user-initiated workflows.
- Handling: Evaluated ephemerally in RAM; never recorded or uploaded.
- Control: Fully revocable in Android Settings -> Accessibility.

4. LOCAL STORAGE & HARDWARE KEYSTORE
API keys are encrypted with AES-256 GCM in Android Keystore. Chats, workflows, and memory reside in local SQLite.

5. AI CLOUD PROVIDERS VS LOCAL OLLAMA
Cloud inference is sent directly over HTTPS to your chosen vendor. Local Ollama inference never leaves your LAN.
"""

private const val FULL_TERMS_TEXT = """
AGENTDROID TERMS AND CONDITIONS (v1.0.0)
Effective Date: November 1, 2026
License: Apache License, Version 2.0
Maintainers: [LEGAL ENTITY NAME / AGENTDROID CONTRIBUTORS]

1. ACCEPTANCE & LICENSE
AgentDroid is open-source software licensed under Apache 2.0. By using the software, you agree to these terms.

2. HUMAN-IN-THE-LOOP OVERSIGHT
AI outputs may contain hallucinations. You maintain ultimate responsibility for automated actions executed on your device. Review high-risk actions before approving. Emergency killswitch stops tasks immediately.

3. API CREDENTIALS
Users bring their own API keys for cloud providers or connect free local Ollama models. You are responsible for provider billing and adherence to their usage policies.

4. PROHIBITED USES
Harassment, malicious surveillance, spam automation, and emergency system disruption are strictly prohibited.

5. DISCLAIMER OF WARRANTIES & LIABILITY
The software is provided AS IS without warranty. Authors and contributors are not liable for direct, indirect, or consequential damages.
"""
