package com.jobhunter.app.ui

import android.content.Intent
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.FilterChip
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp
import androidx.core.net.toUri
import com.jobhunter.app.data.Match

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun MatchesScreen(vm: AppViewModel, state: UiState) {
    LaunchedEffect(Unit) { vm.loadMatches() }
    val context = LocalContext.current

    var role by remember { mutableStateOf("") }
    var country by remember { mutableStateOf("") }
    var minSalary by remember { mutableStateOf("") }
    var remoteOnly by remember { mutableStateOf(false) }

    if (state.matches.isEmpty()) {
        EmptyState("No matches yet.\nUpload a CV, ingest jobs, then run matching.")
        return
    }

    fun isRemote(m: Match): Boolean =
        (m.remote ?: 0) == 1 || (m.location?.contains("remote", ignoreCase = true) == true)

    val salaryFloor = minSalary.toIntOrNull() ?: 0
    val filtered = state.matches.filter { m ->
        if (role.isNotBlank() && !"${m.title ?: ""} ${m.company ?: ""}".contains(role, ignoreCase = true)) return@filter false
        if (country.isNotBlank() && !(m.location ?: "").contains(country, ignoreCase = true)) return@filter false
        if (remoteOnly && !isRemote(m)) return@filter false
        if (salaryFloor > 0) {
            val jobMax = m.salaryMax ?: m.salaryMin ?: 0
            if (jobMax < salaryFloor) return@filter false
        }
        true
    }

    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item { Text("Matches", style = MaterialTheme.typography.headlineSmall) }
        item {
            GlassCard {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    OutlinedTextField(
                        value = role, onValueChange = { role = it },
                        label = { Text("Role or company") },
                        modifier = Modifier.fillMaxWidth(), singleLine = true,
                    )
                    OutlinedTextField(
                        value = country, onValueChange = { country = it },
                        label = { Text("Country or location") },
                        modifier = Modifier.fillMaxWidth(), singleLine = true,
                    )
                    OutlinedTextField(
                        value = minSalary, onValueChange = { minSalary = it.filter(Char::isDigit) },
                        label = { Text("Min salary") },
                        modifier = Modifier.fillMaxWidth(), singleLine = true,
                    )
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        FilterChip(
                            selected = remoteOnly,
                            onClick = { remoteOnly = !remoteOnly },
                            label = { Text("Remote only") },
                        )
                        Text(
                            "${filtered.size} of ${state.matches.size}",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                        if (role.isNotBlank() || country.isNotBlank() || minSalary.isNotBlank() || remoteOnly) {
                            TextButton(onClick = { role = ""; country = ""; minSalary = ""; remoteOnly = false }) {
                                Text("Clear")
                            }
                        }
                    }
                }
            }
        }
        items(filtered) { m ->
            MatchCard(
                match = m,
                isRemote = isRemote(m),
                onApply = { vm.applyToJob(m.id) },
                onView = {
                    m.applyUrl?.let {
                        runCatching {
                            context.startActivity(Intent(Intent.ACTION_VIEW, it.toUri()))
                        }
                    }
                },
            )
        }
    }
}

private fun formatSalary(min: Int?, max: Int?): String? {
    fun k(n: Int) = "$" + (n / 1000) + "k"
    return when {
        min != null && max != null -> "${k(min)}–${k(max)}"
        min != null -> "${k(min)}+"
        max != null -> "up to ${k(max)}"
        else -> null
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun MatchCard(match: Match, isRemote: Boolean, onApply: () -> Unit, onView: () -> Unit) {
    val pct = (match.score * 100).toInt().coerceIn(0, 100)
    val initials = (match.company ?: "?").trim().take(2).uppercase()
    val salary = formatSalary(match.salaryMin, match.salaryMax)
    GlassCard {
        Column(Modifier.padding(18.dp)) {
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.Top,
            ) {
                Row(Modifier.weight(1f), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    GradientChip(initials, sizeDp = 44)
                    Column {
                        Text(
                            match.title ?: "Untitled",
                            fontWeight = FontWeight.SemiBold,
                            style = MaterialTheme.typography.titleMedium,
                            color = if (match.applyUrl != null) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface,
                            textDecoration = if (match.applyUrl != null) TextDecoration.Underline else TextDecoration.None,
                            modifier = if (match.applyUrl != null) Modifier.clickable { onView() } else Modifier,
                        )
                        Text(
                            "${match.company ?: ""} · ${match.location ?: ""}",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
                Text("$pct%", fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.primary)
            }
            FlowRow(horizontalArrangement = Arrangement.spacedBy(6.dp), modifier = Modifier.padding(top = 8.dp)) {
                salary?.let { Badge(it, MaterialTheme.colorScheme.primary) }
                if (isRemote) Badge("remote", com.jobhunter.app.ui.theme.Brand2)
                match.source?.let { Badge(it, MaterialTheme.colorScheme.onSurfaceVariant) }
            }
            LinearProgressIndicator(
                progress = { pct / 100f },
                modifier = Modifier.fillMaxWidth().padding(vertical = 10.dp).height(8.dp).clip(RoundedCornerShape(999.dp)),
                color = MaterialTheme.colorScheme.primary,
                trackColor = MaterialTheme.colorScheme.surfaceVariant,
            )
            match.reasoning?.let {
                Text(
                    it,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Row(
                Modifier.padding(top = 12.dp),
                horizontalArrangement = Arrangement.spacedBy(10.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Button(onClick = onApply, shape = RoundedCornerShape(12.dp)) { Text("Auto-apply") }
                OutlinedButton(onClick = onView, shape = RoundedCornerShape(12.dp)) { Text("View job →") }
                match.appStatus?.let {
                    Text(it, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.primary)
                }
            }
        }
    }
}

@Composable
private fun Badge(text: String, color: androidx.compose.ui.graphics.Color) {
    Text(
        text,
        style = MaterialTheme.typography.bodySmall,
        color = color,
        modifier = Modifier
            .clip(RoundedCornerShape(6.dp))
            .background(color.copy(alpha = 0.14f))
            .padding(horizontal = 8.dp, vertical = 3.dp),
    )
}
