package com.agentdroid.app

import com.agentdroid.app.ui.navigation.Screen
import com.agentdroid.app.ui.navigation.bottomNavItems
import org.junit.Assert.*
import org.junit.Test

class NavigationTest {

    // Simulated backstack implementing MainActivity's navigation logic
    private class SimulatedNavHost(val startDestination: String = Screen.Dashboard.route) {
        val backStack = mutableListOf<String>(startDestination)
        val savedStates = mutableMapOf<String, Any>()

        val currentDestination: String
            get() = backStack.last()

        fun navigate(route: String, saveState: Boolean = true, restoreState: Boolean = true, launchSingleTop: Boolean = true) {
            if (launchSingleTop && currentDestination == route) {
                return // No-op if already on top
            }

            if (route == startDestination) {
                // Popping back to dashboard pops all screens off backstack
                val popped = popBackStack(startDestination, inclusive = false)
                if (!popped) {
                    backStack.clear()
                    backStack.add(startDestination)
                }
            } else {
                // Pop up to start destination saving state
                if (saveState) {
                    while (backStack.size > 1) {
                        val removed = backStack.removeAt(backStack.lastIndex)
                        savedStates[removed] = "state_of_$removed"
                    }
                }
                backStack.add(route)
            }
        }

        fun popBackStack(targetRoute: String, inclusive: Boolean): Boolean {
            val targetIdx = backStack.lastIndexOf(targetRoute)
            if (targetIdx == -1) return false
            val removeCount = backStack.size - (if (inclusive) targetIdx else targetIdx + 1)
            repeat(removeCount) {
                backStack.removeAt(backStack.lastIndex)
            }
            return true
        }

        fun pressBack(): Boolean {
            return if (backStack.size > 1) {
                backStack.removeAt(backStack.lastIndex)
                true
            } else {
                false
            }
        }
    }

    @Test
    fun testBottomNavItemsContainAllRequiredScreens() {
        assertEquals("Bottom navigation must have exactly 6 primary items", 6, bottomNavItems.size)
        val routes = bottomNavItems.map { it.route }
        assertTrue("Must contain Dashboard (Home)", routes.contains(Screen.Dashboard.route))
        assertTrue("Must contain Chat (CommandCenter)", routes.contains(Screen.CommandCenter.route))
        assertTrue("Must contain Agents", routes.contains(Screen.Agents.route))
        assertTrue("Must contain Automations", routes.contains(Screen.Automation.route))
        assertTrue("Must contain Activity", routes.contains(Screen.Activity.route))
        assertTrue("Must contain Settings", routes.contains(Screen.Settings.route))

        // Verify footer tab labels are concise to prevent clipping/wrapping on compact screens
        bottomNavItems.forEach { screen ->
            assertTrue(
                "Tab label '${screen.tabLabel}' for ${screen.route} must not exceed 8 characters to prevent truncation",
                screen.tabLabel.length <= 8
            )
        }
        assertEquals("Automate", Screen.Automation.tabLabel)
        assertEquals("Automations", Screen.Automation.title)
    }

    @Test
    fun testHomeToChatToHome() {
        val nav = SimulatedNavHost()
        assertEquals(Screen.Dashboard.route, nav.currentDestination)

        nav.navigate(Screen.CommandCenter.route)
        assertEquals(Screen.CommandCenter.route, nav.currentDestination)

        nav.navigate(Screen.Dashboard.route)
        assertEquals(Screen.Dashboard.route, nav.currentDestination)
        assertEquals(1, nav.backStack.size)
    }

    @Test
    fun testChatToAgentsToHome() {
        val nav = SimulatedNavHost()
        nav.navigate(Screen.CommandCenter.route)
        nav.navigate(Screen.Agents.route)
        assertEquals(Screen.Agents.route, nav.currentDestination)

        nav.navigate(Screen.Dashboard.route)
        assertEquals(Screen.Dashboard.route, nav.currentDestination)
        assertEquals(1, nav.backStack.size)
    }

    @Test
    fun testHomeToSettingsToHome() {
        val nav = SimulatedNavHost()
        assertEquals(Screen.Dashboard.route, nav.currentDestination)

        nav.navigate(Screen.Settings.route)
        assertEquals(Screen.Settings.route, nav.currentDestination)

        nav.navigate(Screen.Dashboard.route)
        assertEquals("Must return to Home", Screen.Dashboard.route, nav.currentDestination)
        assertEquals("Backstack must only have Dashboard", 1, nav.backStack.size)
    }

    @Test
    fun testHomeToAgentsToHome() {
        val nav = SimulatedNavHost()
        nav.navigate(Screen.Agents.route)
        assertEquals(Screen.Agents.route, nav.currentDestination)

        nav.navigate(Screen.Dashboard.route)
        assertEquals(Screen.Dashboard.route, nav.currentDestination)
        assertEquals(1, nav.backStack.size)
    }

    @Test
    fun testHomeToActivityToHome() {
        val nav = SimulatedNavHost()
        nav.navigate(Screen.Activity.route)
        assertEquals(Screen.Activity.route, nav.currentDestination)

        nav.navigate(Screen.Dashboard.route)
        assertEquals(Screen.Dashboard.route, nav.currentDestination)
        assertEquals(1, nav.backStack.size)
    }

    @Test
    fun testHomeToAutomationsToHome() {
        val nav = SimulatedNavHost()
        nav.navigate(Screen.Automation.route)
        assertEquals(Screen.Automation.route, nav.currentDestination)

        nav.navigate(Screen.Dashboard.route)
        assertEquals(Screen.Dashboard.route, nav.currentDestination)
        assertEquals(1, nav.backStack.size)
    }

    @Test
    fun testSettingsToAgentsToHome() {
        val nav = SimulatedNavHost()
        nav.navigate(Screen.Settings.route)
        nav.navigate(Screen.Agents.route)
        assertEquals(Screen.Agents.route, nav.currentDestination)

        nav.navigate(Screen.Dashboard.route)
        assertEquals(Screen.Dashboard.route, nav.currentDestination)
        assertEquals(1, nav.backStack.size)
    }

    @Test
    fun testActivityToSettingsToHome() {
        val nav = SimulatedNavHost()
        nav.navigate(Screen.Activity.route)
        nav.navigate(Screen.Settings.route)
        assertEquals(Screen.Settings.route, nav.currentDestination)

        nav.navigate(Screen.Dashboard.route)
        assertEquals(Screen.Dashboard.route, nav.currentDestination)
        assertEquals(1, nav.backStack.size)
    }

    @Test
    fun testAutomationsToActivityToHome() {
        val nav = SimulatedNavHost()
        nav.navigate(Screen.Automation.route)
        nav.navigate(Screen.Activity.route)
        assertEquals(Screen.Activity.route, nav.currentDestination)

        nav.navigate(Screen.Dashboard.route)
        assertEquals(Screen.Dashboard.route, nav.currentDestination)
        assertEquals(1, nav.backStack.size)
    }

    @Test
    fun testRepeatedHomeClicksDoNotDuplicateBackstack() {
        val nav = SimulatedNavHost()
        assertEquals(Screen.Dashboard.route, nav.currentDestination)

        nav.navigate(Screen.Dashboard.route)
        nav.navigate(Screen.Dashboard.route)
        nav.navigate(Screen.Dashboard.route)

        assertEquals(Screen.Dashboard.route, nav.currentDestination)
        assertEquals(1, nav.backStack.size)
    }

    @Test
    fun testBackNavigationPopsToHome() {
        val nav = SimulatedNavHost()
        nav.navigate(Screen.Settings.route)
        assertTrue(nav.pressBack())
        assertEquals(Screen.Dashboard.route, nav.currentDestination)
        assertFalse("At root, back should not pop further", nav.pressBack())
    }

    @Test
    fun testLegalScreenRoutesAndNavigation() {
        assertEquals("legal?tab={tab}", Screen.Legal.route)
        assertEquals("legal?tab=privacy", Screen.Legal.createRoute("privacy"))
        assertEquals("legal?tab=terms", Screen.Legal.createRoute("terms"))

        val nav = SimulatedNavHost()
        nav.navigate(Screen.Legal.createRoute("privacy"))
        assertEquals("legal?tab=privacy", nav.currentDestination)

        nav.navigate(Screen.Legal.createRoute("terms"))
        assertEquals("legal?tab=terms", nav.currentDestination)

        // Navigating back home works
        nav.navigate(Screen.Dashboard.route)
        assertEquals(Screen.Dashboard.route, nav.currentDestination)
        assertEquals(1, nav.backStack.size)
    }
}
