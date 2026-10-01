package com.jobhunter.app.ui

import android.content.Intent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.net.toUri
import com.jobhunter.app.data.JobSource

@Composable
fun SourcesScreen(vm: AppViewModel, state: UiState) {
    var query by remember { mutableStateOf("") }
    var location by remember { mutableStateOf("") }
    var keywords by remember { mutableStateOf("") }
    var exclude by remember { mutableStateOf("") }
    val context = LocalContext.current

    LaunchedEffect(Unit) { vm.loadSources() }

    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item { Text("Auto-search", style = MaterialTheme.typography.headlineSmall) }
        item {
            GlassCard {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text(
                        "Searches company boards on Greenhouse, Lever and Ashby (ATS_BOARDS on the server).",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    OutlinedTextField(
                        value = keywords, onValueChange = { keywords = it },
                        label = { Text("Keywords, comma-separated") },
                        modifier = Modifier.fillMaxWidth(), singleLine = true,
                    )
                    OutlinedTextField(
                        value = exclude, onValueChange = { exclude = it },
                        label = { Text("Exclude e.g. intern, staff") },
                        modifier = Modifier.fillMaxWidth(), singleLine = true,
                    )
                    Button(
                        onClick = { vm.autoSearch(keywords, exclude, location) },
                        enabled = !state.loading && keywords.isNotBlank(),
                        modifier = Modifier.fillMaxWidth(),
                    ) { Text("Run auto-search") }
                    state.autoSearch?.let { r ->
                        r.perBoard.forEach { (board, count) ->
                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                Text(board, style = MaterialTheme.typography.bodyMedium)
                                Text(
                                    r.errors[board]?.let { "failed" } ?: "$count",
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = if (board in r.errors) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary,
                                )
                            }
                        }
                    }
                }
            }
        }
        item { Text("Job sources", style = MaterialTheme.typography.headlineSmall) }
        item {
            OutlinedTextField(
                value = query, onValueChange = { query = it },
                label = { Text("Role e.g. python developer") },
                modifier = Modifier.fillMaxWidth(), singleLine = true,
            )
        }
        item {
            OutlinedTextField(
                value = location, onValueChange = { location = it },
                label = { Text("Location e.g. bangalore") },
                modifier = Modifier.fillMaxWidth(), singleLine = true,
            )
        }
        item {
            Button(
                onClick = { vm.loadSources(query, location) },
                modifier = Modifier.fillMaxWidth(),
            ) { Text("Update search links") }
        }
        items(state.sources) { source ->
            SourceCard(source) { url ->
                runCatching { context.startActivity(Intent(Intent.ACTION_VIEW, url.toUri())) }
            }
        }
    }
}

@Composable
private fun SourceCard(source: JobSource, onOpen: (String) -> Unit) {
    val initials = source.name.trim().take(2).uppercase()
    GlassCard {
        Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Row(Modifier.weight(1f), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
                    GradientChip(initials, sizeDp = 42)
                    Text(source.name, fontWeight = FontWeight.SemiBold, style = MaterialTheme.typography.titleMedium)
                }
                val badge = when {
                    source.kind == "deeplink" -> "deep link"
                    source.enabled -> "ingested"
                    else -> "needs key"
                }
                Text(badge, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.primary)
            }
            Text(source.note, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            source.searchUrl?.let { url ->
                Button(onClick = { onOpen(url) }, shape = RoundedCornerShape(12.dp)) { Text("Open search →") }
            }
        }
    }
}
