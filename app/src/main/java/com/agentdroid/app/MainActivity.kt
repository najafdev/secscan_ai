package com.agentdroid.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.animateDpAsState
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavType
import androidx.navigation.compose.*
import androidx.navigation.navArgument
import com.agentdroid.app.AgentDroidApplication
import com.agentdroid.app.ui.navigation.Screen
import com.agentdroid.app.ui.navigation.bottomNavItems
import com.agentdroid.app.ui.screens.activity.ActivityCenterScreen
import com.agentdroid.app.ui.screens.agents.AgentsDashboardScreen
import com.agentdroid.app.ui.screens.automation.AutomationCenterScreen
import com.agentdroid.app.ui.screens.builder.CustomAgentBuilderScreen
import com.agentdroid.app.ui.screens.command.CommandCenterScreen
import com.agentdroid.app.ui.screens.dashboard.DashboardScreen
import com.agentdroid.app.ui.screens.details.AgentDetailsScreen
import com.agentdroid.app.ui.screens.legal.LegalViewerScreen
import com.agentdroid.app.ui.screens.permissions.FirstTimePermissionsDialog
import com.agentdroid.app.ui.screens.settings.SettingsScreen
import com.agentdroid.app.ui.screens.social.SocialMediaCenterScreen
import com.agentdroid.app.ui.theme.*

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            AgentDroidTheme {
                MainAppNavigation()
            }
        }
    }
}

@Composable
fun MainAppNavigation() {
    val app = AgentDroidApplication.instance
    val navController = rememberNavController()
    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentDestination = navBackStackEntry?.destination

    var forwardedPrompt by remember { mutableStateOf<String?>(null) }
    var showFirstTimePermissions by remember {
        mutableStateOf(!app.securePreferences.isFirstLaunchCompleted())
    }

    Scaffold(
        bottomBar = {
            // Only show bottom navigation on primary screens
            val currentRoute = currentDestination?.route
            val isPrimaryScreen = bottomNavItems.any { it.route == currentRoute }

            if (isPrimaryScreen) {
                Surface(
                    modifier = Modifier
                        .fillMaxWidth()
                        .border(
                            width = 1.dp,
                            color = BorderDark,
                            shape = RoundedCornerShape(topStart = 16.dp, topEnd = 16.dp)
                        ),
                    color = BackgroundSecondary,
                    shape = RoundedCornerShape(topStart = 16.dp, topEnd = 16.dp),
                    tonalElevation = 0.dp
                ) {
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .navigationBarsPadding()
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(62.dp)
                                .padding(horizontal = 2.dp, vertical = 4.dp),
                            horizontalArrangement = Arrangement.SpaceEvenly,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            bottomNavItems.forEach { screen ->
                                val isSelected = currentDestination?.hierarchy?.any { it.route == screen.route } == true

                                val indicatorColor by animateColorAsState(
                                    targetValue = if (isSelected) PrimaryAccent else Color.Transparent,
                                    animationSpec = tween(durationMillis = 200),
                                    label = "nav_indicator_color"
                                )
                                val iconColor by animateColorAsState(
                                    targetValue = if (isSelected) BackgroundDark else TextMuted,
                                    animationSpec = tween(durationMillis = 200),
                                    label = "nav_icon_color"
                                )
                                val textColor by animateColorAsState(
                                    targetValue = if (isSelected) PrimaryAccent else TextMuted,
                                    animationSpec = tween(durationMillis = 200),
                                    label = "nav_text_color"
                                )
                                val pillWidth by animateDpAsState(
                                    targetValue = if (isSelected) 42.dp else 24.dp,
                                    animationSpec = tween(durationMillis = 200),
                                    label = "nav_pill_width"
                                )

                                Column(
                                    modifier = Modifier
                                        .weight(1f)
                                        .fillMaxHeight()
                                        .clip(RoundedCornerShape(12.dp))
                                        .clickable {
                                            val destinationRoute = screen.route
                                            if (currentDestination?.route != destinationRoute) {
                                                if (destinationRoute == Screen.Dashboard.route) {
                                                    val popped = navController.popBackStack(Screen.Dashboard.route, inclusive = false)
                                                    if (!popped) {
                                                        navController.navigate(Screen.Dashboard.route) {
                                                            popUpTo(navController.graph.findStartDestination().id) {
                                                                inclusive = false
                                                            }
                                                            launchSingleTop = true
                                                        }
                                                    }
                                                } else {
                                                    navController.navigate(destinationRoute) {
                                                        popUpTo(navController.graph.findStartDestination().id) {
                                                            saveState = true
                                                        }
                                                        launchSingleTop = true
                                                        restoreState = true
                                                    }
                                                }
                                            }
                                        },
                                    horizontalAlignment = Alignment.CenterHorizontally,
                                    verticalArrangement = Arrangement.Center
                                ) {
                                    Box(
                                        modifier = Modifier
                                            .width(pillWidth)
                                            .height(28.dp)
                                            .background(
                                                color = indicatorColor,
                                                shape = RoundedCornerShape(14.dp)
                                            ),
                                        contentAlignment = Alignment.Center
                                    ) {
                                        Icon(
                                            imageVector = screen.icon,
                                            contentDescription = screen.title,
                                            modifier = Modifier.size(19.dp),
                                            tint = iconColor
                                        )
                                    }
                                    Spacer(modifier = Modifier.height(3.dp))
                                    Text(
                                        text = screen.tabLabel,
                                        fontSize = 9.5.sp,
                                        fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
                                        color = textColor,
                                        maxLines = 1,
                                        softWrap = false,
                                        overflow = TextOverflow.Ellipsis,
                                        textAlign = TextAlign.Center
                                    )
                                }
                            }
                        }
                    }
                }
            }
        },
        containerColor = BackgroundDark
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = Screen.Dashboard.route,
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
        ) {
            // 1. Home Dashboard
            composable(Screen.Dashboard.route) {
                DashboardScreen(
                    onNavigateToCommand = { prompt ->
                        forwardedPrompt = prompt
                        navController.navigate(Screen.CommandCenter.route)
                    },
                    onNavigateToAgents = {
                        navController.navigate(Screen.Agents.route)
                    },
                    onNavigateToAgentDetails = { agentId ->
                        navController.navigate(Screen.AgentDetails.createRoute(agentId))
                    },
                    onNavigateToActivity = {
                        navController.navigate(Screen.Activity.route)
                    },
                    onNavigateToSettings = {
                        navController.navigate(Screen.Settings.route)
                    },
                    onNavigateToLegal = { tab ->
                        navController.navigate(Screen.Legal.createRoute(tab))
                    }
                )
            }

            // 2. AI Command Center
            composable(Screen.CommandCenter.route) {
                val promptToRun = forwardedPrompt
                forwardedPrompt = null
                CommandCenterScreen(
                    initialPrompt = promptToRun,
                    onNavigateToSettings = { navController.navigate(Screen.Settings.route) },
                    onBack = { navController.popBackStack() }
                )
            }

            // 3. Agents Dashboard
            composable(Screen.Agents.route) {
                AgentsDashboardScreen(
                    onNavigateToAgentDetails = { agentId ->
                        navController.navigate(Screen.AgentDetails.createRoute(agentId))
                    },
                    onNavigateToBuilder = {
                        navController.navigate(Screen.CustomAgentBuilder.route)
                    },
                    onNavigateToChat = { prompt ->
                        forwardedPrompt = prompt
                        navController.navigate(Screen.CommandCenter.route)
                    }
                )
            }

            // 4. Agent Details Inspector
            composable(
                route = Screen.AgentDetails.route,
                arguments = listOf(navArgument("agentId") { type = NavType.StringType })
            ) { backStackEntry ->
                val agentId = backStackEntry.arguments?.getString("agentId") ?: "agent_master"
                AgentDetailsScreen(
                    agentId = agentId,
                    onBack = { navController.popBackStack() },
                    onNavigateToSocialHub = { navController.navigate(Screen.Social.route) },
                    onNavigateToChat = { prompt ->
                        forwardedPrompt = prompt
                        navController.navigate(Screen.CommandCenter.route)
                    }
                )
            }

            // 5. Automation Center
            composable(Screen.Automation.route) {
                AutomationCenterScreen(
                    onTriggerWorkflow = { prompt ->
                        forwardedPrompt = prompt
                        navController.navigate(Screen.CommandCenter.route)
                    }
                )
            }

            // 6. Social Media Center
            composable(Screen.Social.route) {
                SocialMediaCenterScreen(
                    onTriggerSocialCampaign = { prompt ->
                        forwardedPrompt = prompt
                        navController.navigate(Screen.CommandCenter.route)
                    }
                )
            }

            // 7. Activity Timeline Center
            composable(Screen.Activity.route) {
                ActivityCenterScreen()
            }

            // 8. Settings
            composable(Screen.Settings.route) {
                SettingsScreen(
                    onNavigateToLegal = { tab ->
                        navController.navigate(Screen.Legal.createRoute(tab))
                    },
                    onNavigateToSocial = {
                        navController.navigate(Screen.Social.route)
                    }
                )
            }

            // 9. Custom Agent Builder
            composable(Screen.CustomAgentBuilder.route) {
                CustomAgentBuilderScreen(
                    onBack = { navController.popBackStack() }
                )
            }

            // 10. Legal & Compliance Viewer (Privacy Policy & Terms and Conditions)
            composable(
                route = Screen.Legal.route,
                arguments = listOf(
                    navArgument("tab") {
                        type = NavType.StringType
                        defaultValue = "privacy"
                    }
                )
            ) { backStackEntry ->
                val initialTab = backStackEntry.arguments?.getString("tab") ?: "privacy"
                LegalViewerScreen(
                    initialTab = initialTab,
                    onBack = { navController.popBackStack() }
                )
            }
        }
    }

    if (showFirstTimePermissions) {
        FirstTimePermissionsDialog(
            onComplete = {
                app.securePreferences.setFirstLaunchCompleted(true)
                showFirstTimePermissions = false
            }
        )
    }
}
