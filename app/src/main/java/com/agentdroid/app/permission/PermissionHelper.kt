package com.agentdroid.app.permission

import android.Manifest
import android.app.NotificationManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.os.PowerManager
import android.provider.Settings
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import com.agentdroid.app.automation.accessibility.AgentDroidAccessibilityService

data class PermissionItem(
    val id: String,
    val name: String,
    val androidPermission: String?,
    val description: String,
    val agentRoles: List<String>,
    val isGranted: Boolean,
    val isSpecialAccess: Boolean = false,
    val isEssential: Boolean = true
)

object PermissionHelper {

    fun getRequiredRuntimePermissions(): Array<String> {
        val permissions = mutableListOf<String>()

        // 1. Notifications (Android 13+)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            permissions.add(Manifest.permission.POST_NOTIFICATIONS)
        }

        // 2. Messaging & SMS
        permissions.add(Manifest.permission.SEND_SMS)
        permissions.add(Manifest.permission.READ_SMS)
        permissions.add(Manifest.permission.RECEIVE_SMS)

        // 3. Telephony & Calls
        permissions.add(Manifest.permission.CALL_PHONE)
        permissions.add(Manifest.permission.READ_PHONE_STATE)
        permissions.add(Manifest.permission.READ_CALL_LOG)

        // 4. Contacts
        permissions.add(Manifest.permission.READ_CONTACTS)
        permissions.add(Manifest.permission.WRITE_CONTACTS)

        // 5. Camera for Vision/OCR
        permissions.add(Manifest.permission.CAMERA)

        // 6. Audio / Microphone for Voice Control
        permissions.add(Manifest.permission.RECORD_AUDIO)

        // 7. Location for Geofence and Context
        permissions.add(Manifest.permission.ACCESS_FINE_LOCATION)
        permissions.add(Manifest.permission.ACCESS_COARSE_LOCATION)

        // 8. Storage & Media
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            permissions.add(Manifest.permission.READ_MEDIA_IMAGES)
            permissions.add(Manifest.permission.READ_MEDIA_VIDEO)
            permissions.add(Manifest.permission.READ_MEDIA_AUDIO)
        } else {
            permissions.add(Manifest.permission.READ_EXTERNAL_STORAGE)
            permissions.add(Manifest.permission.WRITE_EXTERNAL_STORAGE)
        }

        // 9. Bluetooth Connect (Android 12+)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            permissions.add(Manifest.permission.BLUETOOTH_CONNECT)
        }

        return permissions.toTypedArray()
    }

    fun isPermissionGranted(context: Context, permission: String): Boolean {
        return try {
            ContextCompat.checkSelfPermission(context, permission) == PackageManager.PERMISSION_GRANTED
        } catch (e: Exception) {
            false
        }
    }

    fun areNotificationsGranted(context: Context): Boolean {
        return try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                isPermissionGranted(context, Manifest.permission.POST_NOTIFICATIONS)
            } else {
                NotificationManagerCompat.from(context).areNotificationsEnabled()
            }
        } catch (e: Exception) {
            false
        }
    }

    fun isSmsGranted(context: Context): Boolean {
        return isPermissionGranted(context, Manifest.permission.SEND_SMS)
    }

    fun isCallGranted(context: Context): Boolean {
        return isPermissionGranted(context, Manifest.permission.CALL_PHONE)
    }

    fun isContactsGranted(context: Context): Boolean {
        return isPermissionGranted(context, Manifest.permission.READ_CONTACTS)
    }

    fun isAudioGranted(context: Context): Boolean {
        return isPermissionGranted(context, Manifest.permission.RECORD_AUDIO)
    }

    fun isLocationGranted(context: Context): Boolean {
        return isPermissionGranted(context, Manifest.permission.ACCESS_FINE_LOCATION)
    }

    fun isStorageGranted(context: Context): Boolean {
        return try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                isPermissionGranted(context, Manifest.permission.READ_MEDIA_IMAGES)
            } else {
                isPermissionGranted(context, Manifest.permission.READ_EXTERNAL_STORAGE)
            }
        } catch (e: Exception) {
            false
        }
    }

    fun isAllFilesGranted(context: Context): Boolean {
        return try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                Environment.isExternalStorageManager()
            } else {
                isStorageGranted(context)
            }
        } catch (e: Exception) {
            false
        }
    }

    fun isCameraGranted(context: Context): Boolean {
        return isPermissionGranted(context, Manifest.permission.CAMERA)
    }

    fun isAccessibilityGranted(context: Context): Boolean {
        return try {
            if (AgentDroidAccessibilityService.isServiceActive.value) return true
            val enabledServices = Settings.Secure.getString(
                context.contentResolver,
                Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES
            ) ?: ""
            enabledServices.contains(context.packageName)
        } catch (e: Exception) {
            false
        }
    }

    fun isNotificationListenerGranted(context: Context): Boolean {
        return try {
            val enabledListeners = Settings.Secure.getString(
                context.contentResolver,
                "enabled_notification_listeners"
            ) ?: ""
            enabledListeners.contains(context.packageName)
        } catch (e: Exception) {
            false
        }
    }

    fun isWriteSettingsGranted(context: Context): Boolean {
        return try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                Settings.System.canWrite(context)
            } else {
                true
            }
        } catch (e: Exception) {
            false
        }
    }

    fun isOverlayGranted(context: Context): Boolean {
        return try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                Settings.canDrawOverlays(context)
            } else {
                true
            }
        } catch (e: Exception) {
            false
        }
    }

    fun isDndGranted(context: Context): Boolean {
        return try {
            val nm = context.getSystemService(Context.NOTIFICATION_SERVICE) as? NotificationManager
            nm?.isNotificationPolicyAccessGranted == true
        } catch (e: Exception) {
            false
        }
    }

    fun isBatteryOptimizationIgnored(context: Context): Boolean {
        return try {
            val pm = context.getSystemService(Context.POWER_SERVICE) as? PowerManager
            pm?.isIgnoringBatteryOptimizations(context.packageName) == true
        } catch (e: Exception) {
            false
        }
    }

    fun getAllPermissionItems(context: Context): List<PermissionItem> {
        val items = mutableListOf<PermissionItem>()

        // 1. Accessibility Service (Crucial for WhatsApp automation, clicks, typing)
        items.add(
            PermissionItem(
                id = "perm_accessibility",
                name = "Accessibility Automation Service",
                androidPermission = null,
                description = "Enables automated taps, typing, swipe gestures, and auto-dispatching WhatsApp messages across applications.",
                agentRoles = listOf("Phone Control Agent", "Master Agent"),
                isGranted = isAccessibilityGranted(context),
                isSpecialAccess = true,
                isEssential = true
            )
        )

        // 2. SMS & Direct Messaging
        items.add(
            PermissionItem(
                id = "perm_sms",
                name = "SMS & Text Messaging",
                androidPermission = Manifest.permission.SEND_SMS,
                description = "Enables transmitting direct SMS text messages, reading verification codes, and autonomous text alerts.",
                agentRoles = listOf("Communication Agent", "Phone Control Agent", "Master Agent"),
                isGranted = isSmsGranted(context),
                isSpecialAccess = false,
                isEssential = true
            )
        )

        // 3. Phone Calls & Telephony
        items.add(
            PermissionItem(
                id = "perm_calls",
                name = "Phone Calls & Telephony",
                androidPermission = Manifest.permission.CALL_PHONE,
                description = "Allows placing phone calls directly, inspecting active call states, and managing emergency or scheduled calls.",
                agentRoles = listOf("Phone Control Agent", "Communication Agent"),
                isGranted = isCallGranted(context),
                isSpecialAccess = false,
                isEssential = true
            )
        )

        // 4. Device Contacts
        items.add(
            PermissionItem(
                id = "perm_contacts",
                name = "Device Contacts",
                androidPermission = Manifest.permission.READ_CONTACTS,
                description = "Allows resolving contact names to phone numbers when sending WhatsApp messages, placing calls, or dispatching SMS.",
                agentRoles = listOf("Phone Control Agent", "Communication Agent"),
                isGranted = isContactsGranted(context),
                isSpecialAccess = false,
                isEssential = true
            )
        )

        // 5. System Settings Modification
        items.add(
            PermissionItem(
                id = "perm_system_settings",
                name = "System Settings & Display",
                androidPermission = null,
                description = "Enables adjusting screen brightness, display timeout, system sound levels, and device hardware settings.",
                agentRoles = listOf("Phone Control Agent", "Security Agent"),
                isGranted = isWriteSettingsGranted(context),
                isSpecialAccess = true,
                isEssential = false
            )
        )

        // 6. Notification Listener Service
        items.add(
            PermissionItem(
                id = "perm_notification_listener",
                name = "Notification Triager & Auto-Reply",
                androidPermission = null,
                description = "Enables reading incoming WhatsApp, chat, and system notifications and preparing autonomous smart replies.",
                agentRoles = listOf("Communication Agent", "Master Agent"),
                isGranted = isNotificationListenerGranted(context),
                isSpecialAccess = true,
                isEssential = false
            )
        )

        // 7. Do Not Disturb Mode Control
        items.add(
            PermissionItem(
                id = "perm_dnd",
                name = "Do Not Disturb Control",
                androidPermission = null,
                description = "Allows toggling DND modes and muting interruptions during focused work routines and productivity blocks.",
                agentRoles = listOf("Productivity Agent", "Phone Control Agent"),
                isGranted = isDndGranted(context),
                isSpecialAccess = true,
                isEssential = false
            )
        )

        // 8. Display Over Other Apps (Floating Overlay)
        items.add(
            PermissionItem(
                id = "perm_overlay",
                name = "Display Over Other Apps",
                androidPermission = null,
                description = "Permits floating assistant widgets and emergency stop controls to stay accessible over third-party applications.",
                agentRoles = listOf("Master Agent", "Phone Control Agent"),
                isGranted = isOverlayGranted(context),
                isSpecialAccess = true,
                isEssential = false
            )
        )

        // 9. Real-Time Notifications
        items.add(
            PermissionItem(
                id = "perm_notifications",
                name = "Real-Time Notifications",
                androidPermission = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) Manifest.permission.POST_NOTIFICATIONS else null,
                description = "Delivers execution progress, emergency killswitch status, approval requests, and multi-agent completion alerts.",
                agentRoles = listOf("Master Agent", "Communication Agent", "Social Media Agent"),
                isGranted = areNotificationsGranted(context),
                isSpecialAccess = false,
                isEssential = true
            )
        )

        // 10. Audio & Microphone
        items.add(
            PermissionItem(
                id = "perm_audio",
                name = "Microphone & Voice Input",
                androidPermission = Manifest.permission.RECORD_AUDIO,
                description = "Enables hands-free voice command execution, meeting audio transcription, and voice agent interactions.",
                agentRoles = listOf("Phone Control Agent", "Meeting Assistant Plugin"),
                isGranted = isAudioGranted(context),
                isSpecialAccess = false,
                isEssential = false
            )
        )

        // 11. Location Access
        items.add(
            PermissionItem(
                id = "perm_location",
                name = "Location & Geofence Intelligence",
                androidPermission = Manifest.permission.ACCESS_FINE_LOCATION,
                description = "Enables location-aware automations, local weather briefings, and geofence workflow triggers.",
                agentRoles = listOf("Productivity Agent", "Research Agent"),
                isGranted = isLocationGranted(context),
                isSpecialAccess = false,
                isEssential = false
            )
        )

        // 12. Storage & Media Documents
        items.add(
            PermissionItem(
                id = "perm_storage",
                name = "Storage & Media Access",
                androidPermission = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) Manifest.permission.READ_MEDIA_IMAGES else Manifest.permission.READ_EXTERNAL_STORAGE,
                description = "Allows scanning device storage, indexing documents, summarizing PDFs, and finding duplicate files.",
                agentRoles = listOf("File Management Agent", "Research Agent"),
                isGranted = isStorageGranted(context),
                isSpecialAccess = false,
                isEssential = true
            )
        )

        // 13. All Files Full Management
        items.add(
            PermissionItem(
                id = "perm_all_files",
                name = "All Files Management",
                androidPermission = null,
                description = "Grants unrestricted file management across all shared storage directories for comprehensive organization.",
                agentRoles = listOf("File Management Agent"),
                isGranted = isAllFilesGranted(context),
                isSpecialAccess = true,
                isEssential = false
            )
        )

        // 14. Camera & Visual Intelligence
        items.add(
            PermissionItem(
                id = "perm_camera",
                name = "Camera & Visual Intelligence",
                androidPermission = Manifest.permission.CAMERA,
                description = "Allows Computer Vision & OCR agent to extract text from physical documents, scan QR codes, and capture visual input.",
                agentRoles = listOf("Vision OCR Plugin Agent", "Security Agent"),
                isGranted = isCameraGranted(context),
                isSpecialAccess = false,
                isEssential = false
            )
        )

        // 15. Unrestricted Battery Optimization
        items.add(
            PermissionItem(
                id = "perm_battery",
                name = "Unrestricted Background Execution",
                androidPermission = null,
                description = "Prevents Android DOZE mode from terminating long-running autonomous workflows and scheduled automations.",
                agentRoles = listOf("Master Orchestrator", "Workflow Engine", "Social Media Agent"),
                isGranted = isBatteryOptimizationIgnored(context),
                isSpecialAccess = true,
                isEssential = false
            )
        )

        return items
    }

    fun openAppSettings(context: Context) {
        try {
            val intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                data = Uri.fromParts("package", context.packageName, null)
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            context.startActivity(intent)
        } catch (e: Exception) {
            // Fallback
        }
    }

    fun openAccessibilitySettings(context: Context) {
        try {
            val intent = Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            context.startActivity(intent)
        } catch (e: Exception) {
            openAppSettings(context)
        }
    }

    fun openNotificationSettings(context: Context) {
        try {
            val intent = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS).apply {
                    putExtra(Settings.EXTRA_APP_PACKAGE, context.packageName)
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
            } else {
                Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                    data = Uri.fromParts("package", context.packageName, null)
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
            }
            context.startActivity(intent)
        } catch (e: Exception) {
            openAppSettings(context)
        }
    }

    fun openNotificationListenerSettings(context: Context) {
        try {
            val intent = Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            context.startActivity(intent)
        } catch (e: Exception) {
            openAppSettings(context)
        }
    }

    fun openWriteSettings(context: Context) {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                val intent = Intent(Settings.ACTION_MANAGE_WRITE_SETTINGS).apply {
                    data = Uri.parse("package:${context.packageName}")
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
                context.startActivity(intent)
            } else {
                openAppSettings(context)
            }
        } catch (e: Exception) {
            openAppSettings(context)
        }
    }

    fun openOverlaySettings(context: Context) {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                val intent = Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION).apply {
                    data = Uri.parse("package:${context.packageName}")
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
                context.startActivity(intent)
            } else {
                openAppSettings(context)
            }
        } catch (e: Exception) {
            openAppSettings(context)
        }
    }

    fun openDndSettings(context: Context) {
        try {
            val intent = Intent(Settings.ACTION_NOTIFICATION_POLICY_ACCESS_SETTINGS).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            context.startActivity(intent)
        } catch (e: Exception) {
            openAppSettings(context)
        }
    }

    fun openAllFilesAccessSettings(context: Context) {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                val intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION).apply {
                    data = Uri.parse("package:${context.packageName}")
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
                context.startActivity(intent)
            } else {
                openAppSettings(context)
            }
        } catch (e: Exception) {
            openAppSettings(context)
        }
    }

    fun requestIgnoreBatteryOptimization(context: Context) {
        try {
            val intent = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS).apply {
                data = Uri.parse("package:${context.packageName}")
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            context.startActivity(intent)
        } catch (e: Exception) {
            openAppSettings(context)
        }
    }
}
