package com.agentdroid.app.data.local.preferences

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

open class SecurePreferencesManager(context: Context? = null) {

    private val inMemoryMap = mutableMapOf<String, Any>()

    private val sharedPreferences: SharedPreferences? = if (context != null) {
        try {
            val masterKey = MasterKey.Builder(context)
                .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
                .build()
            EncryptedSharedPreferences.create(
                context,
                "agentdroid_secure_prefs",
                masterKey,
                EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
                EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
            )
        } catch (e: Exception) {
            context.getSharedPreferences("agentdroid_secure_prefs_fallback", Context.MODE_PRIVATE)
        }
    } else null

    open fun saveApiKey(providerId: String, apiKey: String) {
        if (sharedPreferences != null) {
            sharedPreferences.edit().putString("api_key_$providerId", apiKey).apply()
        } else {
            inMemoryMap["api_key_$providerId"] = apiKey
        }
    }

    open fun getApiKey(providerId: String): String {
        return if (sharedPreferences != null) {
            sharedPreferences.getString("api_key_$providerId", "") ?: ""
        } else {
            inMemoryMap["api_key_$providerId"] as? String ?: ""
        }
    }

    open fun removeApiKey(providerId: String) {
        if (sharedPreferences != null) {
            sharedPreferences.edit().remove("api_key_$providerId").apply()
        } else {
            inMemoryMap.remove("api_key_$providerId")
        }
    }

    open fun saveSocialToken(platform: String, token: String) {
        if (sharedPreferences != null) {
            sharedPreferences.edit().putString("social_token_$platform", token).apply()
        } else {
            inMemoryMap["social_token_$platform"] = token
        }
    }

    open fun getSocialToken(platform: String): String {
        return if (sharedPreferences != null) {
            sharedPreferences.getString("social_token_$platform", "") ?: ""
        } else {
            inMemoryMap["social_token_$platform"] as? String ?: ""
        }
    }

    open fun removeSocialToken(platform: String) {
        if (sharedPreferences != null) {
            sharedPreferences.edit().remove("social_token_$platform").apply()
        } else {
            inMemoryMap.remove("social_token_$platform")
        }
    }

    open fun setEmergencyKillswitchEngaged(engaged: Boolean) {
        if (sharedPreferences != null) {
            sharedPreferences.edit().putBoolean("emergency_killswitch", engaged).apply()
        } else {
            inMemoryMap["emergency_killswitch"] = engaged
        }
    }

    open fun isEmergencyKillswitchEngaged(): Boolean {
        return if (sharedPreferences != null) {
            sharedPreferences.getBoolean("emergency_killswitch", false)
        } else {
            inMemoryMap["emergency_killswitch"] as? Boolean ?: false
        }
    }

    open fun setAccessibilityEnabled(enabled: Boolean) {
        if (sharedPreferences != null) {
            sharedPreferences.edit().putBoolean("accessibility_enabled", enabled).apply()
        } else {
            inMemoryMap["accessibility_enabled"] = enabled
        }
    }

    open fun isAccessibilityEnabled(): Boolean {
        return if (sharedPreferences != null) {
            sharedPreferences.getBoolean("accessibility_enabled", false)
        } else {
            inMemoryMap["accessibility_enabled"] as? Boolean ?: false
        }
    }

    open fun isFirstLaunchCompleted(): Boolean {
        return if (sharedPreferences != null) {
            sharedPreferences.getBoolean("first_launch_completed", false)
        } else {
            inMemoryMap["first_launch_completed"] as? Boolean ?: false
        }
    }

    open fun setFirstLaunchCompleted(completed: Boolean = true) {
        if (sharedPreferences != null) {
            sharedPreferences.edit().putBoolean("first_launch_completed", completed).apply()
        } else {
            inMemoryMap["first_launch_completed"] = completed
        }
    }
}
