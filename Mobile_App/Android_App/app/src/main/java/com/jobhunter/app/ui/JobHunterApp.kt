package com.jobhunter.app.ui

import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Dashboard
import androidx.compose.material.icons.filled.Email
import androidx.compose.material.icons.filled.Hub
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Work
import androidx.compose.material.icons.filled.ViewKanban
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController

private data class Tab(val route: String, val label: String, val icon: ImageVector)

private val tabs = listOf(
    Tab("overview", "Overview", Icons.Filled.Dashboard),
    Tab("matches", "Matches", Icons.Filled.Work),
    Tab("applications", "Apps", Icons.Filled.ViewKanban),
    Tab("inbox", "Inbox", Icons.Filled.Email),
    Tab("sources", "Sources", Icons.Filled.Hub),
    Tab("profile", "Profile", Icons.Filled.Person),
)

@Composable
fun JobHunterApp(vm: AppViewModel = viewModel()) {
    val navController = rememberNavController()
    val state by vm.state.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }

    LaunchedEffect(state.message) {
        state.message?.let {
            snackbar.showSnackbar(it)
            vm.clearMessage()
        }
    }

    Scaffold(
        containerColor = androidx.compose.ui.graphics.Color.Transparent,
        snackbarHost = { SnackbarHost(snackbar) },
        bottomBar = {
            val navBackStackEntry by navController.currentBackStackEntryAsState()
            val currentDestination = navBackStackEntry?.destination
            NavigationBar(
                containerColor = com.jobhunter.app.ui.theme.Surface1.copy(alpha = 0.92f),
                tonalElevation = 0.dp,
            ) {
                tabs.forEach { tab ->
                    val selected = currentDestination?.hierarchy?.any { it.route == tab.route } == true
                    NavigationBarItem(
                        selected = selected,
                        onClick = {
                            navController.navigate(tab.route) {
                                popUpTo(navController.graph.findStartDestination().id) { saveState = true }
                                launchSingleTop = true
                                restoreState = true
                            }
                        },
                        icon = { Icon(tab.icon, contentDescription = tab.label, modifier = Modifier.size(26.dp)) },
                        label = { Text(tab.label, style = MaterialTheme.typography.labelLarge) },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = com.jobhunter.app.ui.theme.Brand,
                            selectedTextColor = com.jobhunter.app.ui.theme.Brand,
                            indicatorColor = com.jobhunter.app.ui.theme.Brand.copy(alpha = 0.16f),
                            unselectedIconColor = com.jobhunter.app.ui.theme.TextMuted,
                            unselectedTextColor = com.jobhunter.app.ui.theme.TextMuted,
                        ),
                    )
                }
            }
        },
    ) { padding ->
        ScreenBackground {
            NavHost(
                navController = navController,
                startDestination = "overview",
                modifier = Modifier.padding(padding),
            ) {
                composable("overview") { OverviewScreen(vm, state) }
                composable("matches") { MatchesScreen(vm, state) }
                composable("applications") { ApplicationsScreen(vm, state) }
                composable("inbox") { InboxScreen(vm, state) }
                composable("sources") { SourcesScreen(vm, state) }
                composable("profile") { ProfileScreen(vm, state) }
            }
        }
    }
}
