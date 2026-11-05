package com.agentdroid.app

import com.agentdroid.app.data.local.preferences.SecurePreferencesManager
import com.agentdroid.app.permission.PermissionHelper
import com.agentdroid.app.permission.PermissionItem
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

class PermissionManagerTest {

    private lateinit var securePrefs: SecurePreferencesManager

    @Before
    fun setUp() {
        securePrefs = SecurePreferencesManager(null)
    }

    @Test
    fun testFirstLaunchPreferenceLifecycle() {
        // Initially first launch is not completed
        assertFalse(securePrefs.isFirstLaunchCompleted())

        // Mark as completed
        securePrefs.setFirstLaunchCompleted(true)
        assertTrue(securePrefs.isFirstLaunchCompleted())

        // Toggle back to false
        securePrefs.setFirstLaunchCompleted(false)
        assertFalse(securePrefs.isFirstLaunchCompleted())
    }

    @Test
    fun testRequiredRuntimePermissionsArray() {
        val perms = PermissionHelper.getRequiredRuntimePermissions()
        assertTrue(perms.isNotEmpty())
        assertTrue("Must request camera", perms.any { it.contains("CAMERA") })
        assertTrue("Must request storage/media", perms.any { it.contains("STORAGE") || it.contains("MEDIA") })
        assertTrue("Must request SMS permissions for messaging", perms.any { it.contains("SEND_SMS") })
        assertTrue("Must request Call phone permissions", perms.any { it.contains("CALL_PHONE") })
        assertTrue("Must request Contacts permissions for contact resolution", perms.any { it.contains("READ_CONTACTS") })
        assertTrue("Must request Audio permissions for voice control", perms.any { it.contains("RECORD_AUDIO") })
        assertTrue("Must request Location permissions for location context", perms.any { it.contains("ACCESS_FINE_LOCATION") })
    }

    @Test
    fun testDeviceControlActionTypesExist() {
        val actions = com.agentdroid.app.domain.model.ActionType.entries
        assertTrue("Must have SEND_WHATSAPP action", actions.contains(com.agentdroid.app.domain.model.ActionType.SEND_WHATSAPP))
        assertTrue("Must have SEND_SMS action", actions.contains(com.agentdroid.app.domain.model.ActionType.SEND_SMS))
        assertTrue("Must have MAKE_CALL action", actions.contains(com.agentdroid.app.domain.model.ActionType.MAKE_CALL))
        assertTrue("Must have CONTROL_SYSTEM action", actions.contains(com.agentdroid.app.domain.model.ActionType.CONTROL_SYSTEM))
        assertTrue("Must have READ_CONTACTS action", actions.contains(com.agentdroid.app.domain.model.ActionType.READ_CONTACTS))
    }

    private class FakeContext : android.content.ContextWrapper(null)

    @Test
    fun testAgentCapabilitiesAndPermissions() {
        val actionDispatcher = com.agentdroid.app.automation.action.ActionDispatcher(FakeContext())
        val dummyDao = object : com.agentdroid.app.data.local.dao.ActivityLogDao {
            override fun getRecentLogs(): kotlinx.coroutines.flow.Flow<List<com.agentdroid.app.data.local.entity.ActivityLogEntity>> = kotlinx.coroutines.flow.flowOf(emptyList())
            override fun getLogsForAgent(role: String): kotlinx.coroutines.flow.Flow<List<com.agentdroid.app.data.local.entity.ActivityLogEntity>> = kotlinx.coroutines.flow.flowOf(emptyList())
            override suspend fun insertLog(log: com.agentdroid.app.data.local.entity.ActivityLogEntity) {}
            override suspend fun clearLogs() {}
        }

        val phoneAgent = com.agentdroid.app.domain.agent.PhoneControlAgent(actionDispatcher, dummyDao)
        assertTrue(phoneAgent.capabilities.any { it.contains("WhatsApp") })
        assertTrue(phoneAgent.capabilities.any { it.contains("SMS") })
        assertTrue(phoneAgent.capabilities.any { it.contains("phone call") || it.contains("Phone call") })
        assertTrue(phoneAgent.capabilities.any { it.contains("system") || it.contains("System") })
        assertTrue(phoneAgent.requiredPermissions.contains("android.permission.SEND_SMS"))
        assertTrue(phoneAgent.requiredPermissions.contains("android.permission.CALL_PHONE"))
        assertTrue(phoneAgent.requiredPermissions.contains("android.permission.READ_CONTACTS"))
        assertTrue(phoneAgent.requiredPermissions.contains("android.permission.BIND_ACCESSIBILITY_SERVICE"))
    }

    @Test
    fun testPermissionItemModelStructure() {
        val item = PermissionItem(
            id = "perm_accessibility_test",
            name = "Accessibility Service",
            androidPermission = null,
            description = "Automates taps and typing",
            agentRoles = listOf("Phone Control Agent"),
            isGranted = false,
            isSpecialAccess = true,
            isEssential = true
        )

        assertEquals("perm_accessibility_test", item.id)
        assertEquals("Accessibility Service", item.name)
        assertNull(item.androidPermission)
        assertFalse(item.isGranted)
        assertTrue(item.isSpecialAccess)
        assertTrue(item.isEssential)
        assertEquals(listOf("Phone Control Agent"), item.agentRoles)
    }
}
