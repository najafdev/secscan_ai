package com.agentdroid.app

import com.agentdroid.app.automation.action.EmergencyKillswitch
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

class EmergencyKillswitchTest {

    @Before
    fun setUp() {
        EmergencyKillswitch.resetKillswitch()
    }

    @Test
    fun testKillswitchTriggersException() {
        assertFalse(EmergencyKillswitch.isEngaged.value)
        // CheckStatus should not throw when reset
        EmergencyKillswitch.checkStatus()

        // Engage killswitch
        EmergencyKillswitch.triggerEmergencyStop()
        assertTrue(EmergencyKillswitch.isEngaged.value)

        // CheckStatus must throw SecurityException
        try {
            EmergencyKillswitch.checkStatus()
            fail("Expected SecurityException when Emergency Killswitch is engaged.")
        } catch (e: SecurityException) {
            assertTrue(e.message?.contains("EMERGENCY KILLSWITCH ENGAGED") == true)
        }

        // Reset killswitch
        EmergencyKillswitch.resetKillswitch()
        assertFalse(EmergencyKillswitch.isEngaged.value)
        EmergencyKillswitch.checkStatus()
    }
}
