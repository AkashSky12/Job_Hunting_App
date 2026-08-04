package com.jobhunter.app.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.jobhunter.app.data.Application

@Composable
fun ApplicationsScreen(vm: AppViewModel, state: UiState) {
    LaunchedEffect(Unit) { vm.loadApplications() }
    val columns = vm.statusColumns

    if (state.applications.isEmpty()) {
        EmptyState("No applications yet.\nAuto-apply to a match to start tracking.")
        return
    }

    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        item { Text("Applications", style = MaterialTheme.typography.headlineSmall) }
        columns.forEach { status ->
            val items = state.applications.filter { it.status == status }
            if (items.isNotEmpty()) {
                item {
                    Text(
                        "${status.replace('_', ' ')} (${items.size})",
                        style = MaterialTheme.typography.titleMedium,
                    )
                }
                items(items.size) { i ->
                    val app = items[i]
                    val idx = columns.indexOf(status)
                    ApplicationCard(
                        app = app,
                        prev = columns.getOrNull(idx - 1),
                        next = columns.getOrNull(idx + 1),
                        onMove = { target -> vm.moveApplication(app.jobId, target) },
                    )
                }
            }
        }
    }
}

@Composable
private fun ApplicationCard(
    app: Application,
    prev: String?,
    next: String?,
    onMove: (String) -> Unit,
) {
    GlassCard {
        Column(Modifier.fillMaxWidth().padding(16.dp)) {
            Text(app.title ?: "Untitled", fontWeight = FontWeight.SemiBold, style = MaterialTheme.typography.titleMedium)
            Text(
                app.company ?: "",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp), modifier = Modifier.padding(top = 4.dp)) {
                prev?.let {
                    TextButton(onClick = { onMove(it) }) { Text("← ${it.replace('_', ' ')}") }
                }
                next?.let {
                    TextButton(onClick = { onMove(it) }) { Text("→ ${it.replace('_', ' ')}", color = MaterialTheme.colorScheme.primary) }
                }
            }
        }
    }
}
