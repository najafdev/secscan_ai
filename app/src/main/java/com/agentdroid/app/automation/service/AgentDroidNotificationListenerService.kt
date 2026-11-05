package com.agentdroid.app.automation.service

import android.app.Notification
import android.os.Bundle
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

data class NotificationEvent(
    val id: Int,
    val packageName: String,
    val title: String,
    val text: String,
    val timestamp: Long,
    val isClearable: Boolean
)

class AgentDroidNotificationListenerService : NotificationListenerService() {

    override fun onListenerConnected() {
        super.onListenerConnected()
        instance = this
        _isConnected.value = true
    }

    override fun onListenerDisconnected() {
        super.onListenerDisconnected()
        instance = null
        _isConnected.value = false
    }

    override fun onNotificationPosted(sbn: StatusBarNotification?) {
        sbn ?: return
        val extras = sbn.notification.extras ?: return
        val title = extras.getString(Notification.EXTRA_TITLE)
            ?: extras.getCharSequence(Notification.EXTRA_TITLE)?.toString()
            ?: ""
        val text = extras.getString(Notification.EXTRA_TEXT)
            ?: extras.getCharSequence(Notification.EXTRA_TEXT)?.toString()
            ?: ""

        val event = NotificationEvent(
            id = sbn.id,
            packageName = sbn.packageName,
            title = title,
            text = text,
            timestamp = sbn.postTime,
            isClearable = sbn.isClearable
        )

        _lastNotification.value = event
        _recentNotifications.value = (listOf(event) + _recentNotifications.value).take(30)
    }

    companion object {
        var instance: AgentDroidNotificationListenerService? = null
            private set

        private val _isConnected = MutableStateFlow(false)
        val isConnected: StateFlow<Boolean> = _isConnected.asStateFlow()

        private val _lastNotification = MutableStateFlow<NotificationEvent?>(null)
        val lastNotification: StateFlow<NotificationEvent?> = _lastNotification.asStateFlow()

        private val _recentNotifications = MutableStateFlow<List<NotificationEvent>>(emptyList())
        val recentNotifications: StateFlow<List<NotificationEvent>> = _recentNotifications.asStateFlow()
    }
}
