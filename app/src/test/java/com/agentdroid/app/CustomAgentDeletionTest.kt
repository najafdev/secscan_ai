package com.agentdroid.app

import com.agentdroid.app.data.local.entity.AgentEntity
import org.junit.Assert.*
import org.junit.Test

class CustomAgentDeletionTest {

    private fun isUserCreatedCustomAgent(agent: AgentEntity): Boolean {
        return agent.isCustom && !agent.id.startsWith("plugin_")
    }

    @Test
    fun testCoreAgentsAreNotMarkedAsUserDeletable() {
        val master = AgentEntity("agent_master", "Master Agent", "MASTER", "...", isCustom = false)
        val phone = AgentEntity("agent_phone", "Phone Control Agent", "PHONE_CONTROL", "...", isCustom = false)
        val social = AgentEntity("agent_social", "Social Media Agent", "SOCIAL_MEDIA", "...", isCustom = false)

        assertFalse(isUserCreatedCustomAgent(master))
        assertFalse(isUserCreatedCustomAgent(phone))
        assertFalse(isUserCreatedCustomAgent(social))
    }

    @Test
    fun testBuiltinPluginsAreNotMarkedAsUserDeletable() {
        val ocrPlugin = AgentEntity("plugin_vision_ocr", "OCR Agent", "CUSTOM", "...", isCustom = true)
        val codingPlugin = AgentEntity("plugin_coding_agent", "Coding Agent", "CUSTOM", "...", isCustom = true)
        val meetingPlugin = AgentEntity("plugin_meeting_assistant", "Meeting Agent", "CUSTOM", "...", isCustom = true)

        assertFalse(isUserCreatedCustomAgent(ocrPlugin))
        assertFalse(isUserCreatedCustomAgent(codingPlugin))
        assertFalse(isUserCreatedCustomAgent(meetingPlugin))
    }

    @Test
    fun testUserCreatedCustomAgentsAreDeletable() {
        val custom1 = AgentEntity("agent_custom_a1b2c3d4", "Crypto Analyst", "CUSTOM", "...", isCustom = true)
        val custom2 = AgentEntity("agent_custom_99887766", "Travel Planner", "CUSTOM", "...", isCustom = true)

        assertTrue(isUserCreatedCustomAgent(custom1))
        assertTrue(isUserCreatedCustomAgent(custom2))
    }

    @Test
    fun testFleetListAfterCustomAgentDeletion() {
        val initialFleet = mutableListOf(
            AgentEntity("agent_master", "Master", "MASTER", "..."),
            AgentEntity("plugin_vision_ocr", "Vision", "CUSTOM", "...", isCustom = true),
            AgentEntity("agent_custom_user1", "My Personal Assistant", "CUSTOM", "...", isCustom = true)
        )

        assertEquals(3, initialFleet.size)

        // Delete user custom agent
        val target = initialFleet.first { it.id == "agent_custom_user1" }
        assertTrue(isUserCreatedCustomAgent(target))
        initialFleet.remove(target)

        assertEquals(2, initialFleet.size)
        assertNull(initialFleet.firstOrNull { it.id == "agent_custom_user1" })
        assertNotNull(initialFleet.firstOrNull { it.id == "agent_master" })
        assertNotNull(initialFleet.firstOrNull { it.id == "plugin_vision_ocr" })
    }
}
