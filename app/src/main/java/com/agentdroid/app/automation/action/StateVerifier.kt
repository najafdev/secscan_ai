package com.agentdroid.app.automation.action

import com.agentdroid.app.automation.accessibility.AgentDroidAccessibilityService
import kotlinx.coroutines.delay
import java.io.File

class StateVerifier {

    suspend fun verifyPackageForeground(expectedPackage: String, maxWaitMs: Long = 3000): Boolean {
        val start = System.currentTimeMillis()
        while (System.currentTimeMillis() - start < maxWaitMs) {
            val current = AgentDroidAccessibilityService.currentPackage.value
            if (current.equals(expectedPackage, ignoreCase = true) || current.contains(expectedPackage, ignoreCase = true)) {
                return true
            }
            delay(200)
        }
        return false
    }

    suspend fun verifyScreenContainsText(expectedText: String, maxWaitMs: Long = 3000): Boolean {
        val start = System.currentTimeMillis()
        while (System.currentTimeMillis() - start < maxWaitMs) {
            val service = AgentDroidAccessibilityService.instance
            if (service != null) {
                val nodes = service.inspectVisibleHierarchy()
                if (nodes.any { it.contains(expectedText, ignoreCase = true) }) {
                    return true
                }
            }
            delay(300)
        }
        return false
    }

    fun verifyFileCreated(filePath: String): Boolean {
        val file = File(filePath)
        return file.exists() && file.isFile
    }
}
