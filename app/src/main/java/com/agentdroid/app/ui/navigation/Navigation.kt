package com.agentdroid.app.ui.navigation

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.ui.graphics.vector.ImageVector

sealed class Screen(
    val route: String,
    val title: String,
    val icon: ImageVector,
    val tabLabel: String = title
) {
    object Dashboard : Screen("dashboard", "Home", Icons.Default.Dashboard, tabLabel = "Home")
    object CommandCenter : Screen("command", "Chat", Icons.Default.Forum, tabLabel = "Chat")
    object Agents : Screen("agents", "Agents", Icons.Default.Group, tabLabel = "Agents")
    object Automation : Screen("automation", "Automations", Icons.Default.Autorenew, tabLabel = "Automate")
    object Social : Screen("social", "Social", Icons.Default.Share, tabLabel = "Social")
    object Activity : Screen("activity", "Activity", Icons.Default.History, tabLabel = "Activity")
    object Settings : Screen("settings", "Settings", Icons.Default.Settings, tabLabel = "Settings")
    object CustomAgentBuilder : Screen("builder", "Agent Builder", Icons.Default.Add)
    object AgentDetails : Screen("details/{agentId}", "Agent Details", Icons.Default.Info) {
        fun createRoute(agentId: String) = "details/$agentId"
    }
    object Legal : Screen("legal?tab={tab}", "Legal & Policies", Icons.Default.Gavel) {
        fun createRoute(tab: String = "privacy") = "legal?tab=$tab"
    }
}

val bottomNavItems = listOf(
    Screen.Dashboard,
    Screen.CommandCenter,
    Screen.Agents,
    Screen.Automation,
    Screen.Activity,
    Screen.Settings
)
