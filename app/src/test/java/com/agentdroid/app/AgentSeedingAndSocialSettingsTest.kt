package com.agentdroid.app

import com.agentdroid.app.data.local.entity.AgentEntity
import com.agentdroid.app.data.local.entity.ConnectedAccountEntity
import com.agentdroid.app.data.local.preferences.SecurePreferencesManager
import com.agentdroid.app.domain.model.PlatformType
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

class AgentSeedingAndSocialSettingsTest {

    private lateinit var securePrefs: SecurePreferencesManager

    @Before
    fun setUp() {
        // SecurePreferencesManager without context operates on its internal thread-safe in-memory map
        securePrefs = SecurePreferencesManager(null)
    }

    @Test
    fun testPlatformTypeEnumCompleteness() {
        val platforms = PlatformType.entries.map { it.name }.toSet()
        val expectedPlatforms = setOf(
            "TWITTER", "INSTAGRAM", "FACEBOOK", "LINKEDIN",
            "TELEGRAM", "DISCORD", "YOUTUBE", "REDDIT"
        )
        assertEquals(expectedPlatforms, platforms)
        assertEquals("X (Twitter)", PlatformType.TWITTER.displayName)
        assertEquals("LinkedIn", PlatformType.LINKEDIN.displayName)
        assertEquals("Discord", PlatformType.DISCORD.displayName)
    }

    @Test
    fun testSocialTokenSecureStorage() {
        // Initially empty
        assertEquals("", securePrefs.getSocialToken("TWITTER"))
        assertEquals("", securePrefs.getSocialToken("LINKEDIN"))

        // Save tokens
        securePrefs.saveSocialToken("TWITTER", "x_bearer_secret_token_12345")
        securePrefs.saveSocialToken("LINKEDIN", "li_oauth2_access_token_67890")
        securePrefs.saveSocialToken("DISCORD", "https://discord.com/api/webhooks/123/abc")

        // Retrieve tokens
        assertEquals("x_bearer_secret_token_12345", securePrefs.getSocialToken("TWITTER"))
        assertEquals("li_oauth2_access_token_67890", securePrefs.getSocialToken("LINKEDIN"))
        assertEquals("https://discord.com/api/webhooks/123/abc", securePrefs.getSocialToken("DISCORD"))

        // Remove token
        securePrefs.removeSocialToken("TWITTER")
        assertEquals("", securePrefs.getSocialToken("TWITTER"))
        assertEquals("li_oauth2_access_token_67890", securePrefs.getSocialToken("LINKEDIN"))
    }

    @Test
    fun testConnectedAccountEntityAndPermissionsJson() {
        val json = JSONObject().apply {
            put("autoDraft", true)
            put("requireApproval", false)
        }.toString()

        val account = ConnectedAccountEntity(
            id = "acc_twitter_test",
            platform = "TWITTER",
            username = "@agentdroid_official",
            displayName = "AgentDroid Core",
            isConnected = true,
            permissionsJson = json
        )

        assertEquals("TWITTER", account.platform)
        assertEquals("@agentdroid_official", account.username)
        assertEquals("AgentDroid Core", account.displayName)
        assertTrue(account.isConnected)

        val parsed = JSONObject(account.permissionsJson)
        assertTrue(parsed.getBoolean("autoDraft"))
        assertFalse(parsed.getBoolean("requireApproval"))
    }

    @Test
    fun testTotalAgentCountIncludesPluginExtensions() {
        val defaultAgents = listOf(
            AgentEntity("agent_master", "Master Agent", "MASTER", "..."),
            AgentEntity("agent_phone", "Phone Control Agent", "PHONE_CONTROL", "..."),
            AgentEntity("agent_social", "Social Media Agent", "SOCIAL_MEDIA", "..."),
            AgentEntity("agent_content", "Content Creation Agent", "CONTENT_CREATION", "..."),
            AgentEntity("agent_research", "Research Agent", "RESEARCH", "..."),
            AgentEntity("agent_comm", "Communication Agent", "COMMUNICATION", "..."),
            AgentEntity("agent_file", "File Management Agent", "FILE_MANAGEMENT", "..."),
            AgentEntity("agent_productivity", "Productivity Agent", "PRODUCTIVITY", "..."),
            AgentEntity("agent_analytics", "Analytics Agent", "ANALYTICS", "..."),
            AgentEntity("agent_browser", "Browser Agent", "BROWSER", "..."),
            AgentEntity("agent_security", "Security Agent", "SECURITY", "..."),
            AgentEntity("plugin_vision_ocr", "Computer Vision & OCR Agent", "CUSTOM", "...", isCustom = true),
            AgentEntity("plugin_coding_agent", "Coding & Shell Agent", "CUSTOM", "...", isCustom = true),
            AgentEntity("plugin_meeting_assistant", "Meeting & Calendar Assistant", "CUSTOM", "...", isCustom = true)
        )

        assertEquals(14, defaultAgents.size)
        val customAgents = defaultAgents.filter { it.isCustom }
        assertEquals(3, customAgents.size)
        val coreAgents = defaultAgents.filter { !it.isCustom }
        assertEquals(11, coreAgents.size)
    }
}
