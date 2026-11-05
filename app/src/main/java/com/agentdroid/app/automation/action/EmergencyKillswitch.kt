package com.agentdroid.app.automation.action

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

object EmergencyKillswitch {
    private val _isEngaged = MutableStateFlow(false)
    val isEngaged: StateFlow<Boolean> = _isEngaged.asStateFlow()

    fun triggerEmergencyStop() {
        _isEngaged.value = true
    }

    fun resetKillswitch() {
        _isEngaged.value = false
    }

    fun checkStatus() {
        if (_isEngaged.value) {
            throw SecurityException("EMERGENCY KILLSWITCH ENGAGED! Immediate halt of all agent and automation operations.")
        }
    }
}
