package com.agentdroid.app.automation.accessibility

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.graphics.Path
import android.graphics.Rect
import android.os.Bundle
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

class AgentDroidAccessibilityService : AccessibilityService() {

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
        _isServiceActive.value = true
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        event?.let {
            if (it.packageName != null) {
                _currentPackage.value = it.packageName.toString()
            }
        }
    }

    override fun onInterrupt() {
        // Accessibility service interrupted
    }

    override fun onDestroy() {
        super.onDestroy()
        instance = null
        _isServiceActive.value = false
    }

    fun inspectVisibleHierarchy(): List<String> {
        val root = rootInActiveWindow ?: return emptyList()
        val nodes = mutableListOf<String>()
        collectNodeText(root, nodes, 0)
        return nodes
    }

    private fun collectNodeText(node: AccessibilityNodeInfo, list: MutableList<String>, depth: Int) {
        val text = node.text?.toString()
        val desc = node.contentDescription?.toString()
        val viewId = node.viewIdResourceName

        if (!text.isNullOrBlank() || !desc.isNullOrBlank() || !viewId.isNullOrBlank()) {
            val label = buildString {
                append(" ".repeat(depth * 2))
                if (!text.isNullOrBlank()) append("text=\"$text\" ")
                if (!desc.isNullOrBlank()) append("desc=\"$desc\" ")
                if (!viewId.isNullOrBlank()) append("id=\"$viewId\" ")
                append("[clickable=${node.isClickable}, editable=${node.isEditable}]")
            }
            list.add(label)
        }

        for (i in 0 until node.childCount) {
            val child = node.getChild(i) ?: continue
            collectNodeText(child, list, depth + 1)
        }
    }

    fun clickElement(target: String): Boolean {
        val root = rootInActiveWindow ?: return false
        val node = findNodeMatching(root, target) ?: return false

        // Try direct click action
        if (node.isClickable && node.performAction(AccessibilityNodeInfo.ACTION_CLICK)) {
            return true
        }

        // Parent click fallback
        var parent = node.parent
        while (parent != null) {
            if (parent.isClickable && parent.performAction(AccessibilityNodeInfo.ACTION_CLICK)) {
                return true
            }
            parent = parent.parent
        }

        // Gesture click fallback based on node bounds
        val bounds = Rect()
        node.getBoundsInScreen(bounds)
        if (!bounds.isEmpty) {
            return clickAtCoordinates(bounds.centerX().toFloat(), bounds.centerY().toFloat())
        }
        return false
    }

    fun typeText(target: String, textToType: String): Boolean {
        val root = rootInActiveWindow ?: return false
        val node = findNodeMatching(root, target) ?: return false

        val args = Bundle().apply {
            putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, textToType)
        }
        return node.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)
    }

    fun scroll(forward: Boolean): Boolean {
        val root = rootInActiveWindow ?: return false
        val action = if (forward) AccessibilityNodeInfo.ACTION_SCROLL_FORWARD else AccessibilityNodeInfo.ACTION_SCROLL_BACKWARD
        return root.performAction(action)
    }

    fun clickAtCoordinates(x: Float, y: Float): Boolean {
        val path = Path().apply { moveTo(x, y) }
        val gesture = GestureDescription.Builder()
            .addStroke(GestureDescription.StrokeDescription(path, 0, 100))
            .build()
        return dispatchGesture(gesture, null, null)
    }

    fun goBack(): Boolean {
        return performGlobalAction(GLOBAL_ACTION_BACK)
    }

    fun goHome(): Boolean {
        return performGlobalAction(GLOBAL_ACTION_HOME)
    }

    private fun findNodeMatching(node: AccessibilityNodeInfo, target: String): AccessibilityNodeInfo? {
        val lowerTarget = target.lowercase()
        val text = node.text?.toString()?.lowercase()
        val desc = node.contentDescription?.toString()?.lowercase()
        val viewId = node.viewIdResourceName?.lowercase()

        if (text?.contains(lowerTarget) == true || desc?.contains(lowerTarget) == true || viewId?.contains(lowerTarget) == true) {
            return node
        }

        for (i in 0 until node.childCount) {
            val child = node.getChild(i) ?: continue
            val match = findNodeMatching(child, target)
            if (match != null) return match
        }
        return null
    }

    companion object {
        var instance: AgentDroidAccessibilityService? = null
            private set

        private val _isServiceActive = MutableStateFlow(false)
        val isServiceActive: StateFlow<Boolean> = _isServiceActive.asStateFlow()

        private val _currentPackage = MutableStateFlow("")
        val currentPackage: StateFlow<String> = _currentPackage.asStateFlow()
    }
}
