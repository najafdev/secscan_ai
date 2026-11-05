package com.agentdroid.app

import android.content.Context
import com.agentdroid.app.sdk.PluginRegistry
import com.agentdroid.app.sdk.extensions.CodingAgentPlugin
import com.agentdroid.app.sdk.extensions.MeetingAssistantPlugin
import com.agentdroid.app.sdk.extensions.VisionOcrAgentPlugin
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import java.lang.reflect.Proxy

class PluginRegistryTest {

    private lateinit var registry: PluginRegistry

    @Before
    fun setUp() {
        registry = PluginRegistry()
    }

    @Test
    fun testPluginRegistrationAndUnregistration() {
        assertEquals(0, registry.installedPlugins.value.size)

        val visionPlugin = VisionOcrAgentPlugin()
        val codingPlugin = CodingAgentPlugin()
        val meetingPlugin = MeetingAssistantPlugin()

        registry.registerPlugin(visionPlugin)
        registry.registerPlugin(codingPlugin)
        registry.registerPlugin(meetingPlugin)

        val installed = registry.installedPlugins.value
        assertEquals(3, installed.size)

        assertNotNull(registry.getPlugin("plugin_vision_ocr"))
        assertNotNull(registry.getPlugin("plugin_coding_agent"))
        assertNotNull(registry.getPlugin("plugin_meeting_assistant"))

        assertEquals("Computer Vision & OCR Agent", registry.getPlugin("plugin_vision_ocr")?.metadata?.name)

        // Unregister one plugin
        registry.unregisterPlugin("plugin_coding_agent")
        assertEquals(2, registry.installedPlugins.value.size)
        assertNull(registry.getPlugin("plugin_coding_agent"))
    }
}
