package com.jobhunter.app.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.jobhunter.app.data.TrendPoint
import com.jobhunter.app.ui.theme.Accent
import com.jobhunter.app.ui.theme.Amber
import com.jobhunter.app.ui.theme.Brand
import com.jobhunter.app.ui.theme.Indigo
import com.jobhunter.app.ui.theme.Stroke

@Composable
fun OverviewScreen(vm: AppViewModel, state: UiState) {
    LaunchedEffect(Unit) { vm.loadOverview() }

    LazyColumn(
        modifier = Modifier.fillMaxWidth().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Text("Overview", style = MaterialTheme.typography.headlineSmall)
        }
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = { vm.ingest() }, modifier = Modifier.weight(1f)) { Text("Ingest jobs") }
                OutlinedButton(onClick = { vm.runMatching() }, modifier = Modifier.weight(1f)) { Text("Run matching") }
            }
        }
        item {
            val s = state.stats
            val interviews = (s.funnel["interview"] ?: 0) + (s.funnel["phone_screen"] ?: 0)
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    KpiCard("Jobs", s.jobs, "⌗", Modifier.weight(1f))
                    KpiCard("Matches", s.matches, "✦", Modifier.weight(1f))
                }
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    KpiCard("Applications", s.applications, "▤", Modifier.weight(1f))
                    KpiCard("Interviews", interviews, "☎", Modifier.weight(1f))
                }
            }
        }
        item {
            GlassCard {
                Column(Modifier.padding(18.dp)) {
                    Text("Activity — last 30 days", style = MaterialTheme.typography.titleMedium)
                    Text(
                        "Applied · Interviews · Offers",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    TrendChart(state.trend, Modifier.fillMaxWidth().height(170.dp).padding(top = 12.dp))
                }
            }
        }
        item {
            GlassCard {
                Column(Modifier.padding(18.dp)) {
                    Text("Application funnel", style = MaterialTheme.typography.titleMedium)
                    if (state.stats.funnel.isEmpty()) {
                        Text(
                            "No applications yet.",
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.padding(top = 8.dp),
                        )
                    } else {
                        state.stats.funnel.forEach { (k, v) ->
                            Row(
                                Modifier.fillMaxWidth().padding(top = 8.dp),
                                horizontalArrangement = Arrangement.SpaceBetween,
                            ) {
                                Text(k.replace('_', ' '), color = MaterialTheme.colorScheme.onSurfaceVariant)
                                Text("$v", fontWeight = FontWeight.SemiBold)
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun KpiCard(label: String, value: Int, icon: String, modifier: Modifier = Modifier) {
    GlassCard(modifier = modifier) {
        Box {
            // top accent bar
            Box(
                Modifier
                    .fillMaxWidth()
                    .height(3.dp)
                    .background(Brush.horizontalGradient(listOf(Brand, Indigo, Accent)))
            )
            Column(Modifier.padding(16.dp)) {
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(label, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    GradientChip(icon, sizeDp = 40)
                }
                Text(
                    "$value",
                    style = MaterialTheme.typography.headlineSmall,
                    fontWeight = FontWeight.ExtraBold,
                    modifier = Modifier.padding(top = 6.dp),
                )
            }
        }
    }
}

@Composable
private fun TrendChart(points: List<TrendPoint>, modifier: Modifier = Modifier) {
    if (points.isEmpty()) {
        Box(modifier, contentAlignment = Alignment.Center) {
            Text("No data yet", color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        return
    }
    val maxVal = (points.maxOf { maxOf(it.applied, it.interviews, it.offers) }).coerceAtLeast(1)
    Canvas(modifier) {
        val w = size.width
        val h = size.height
        fun line(sel: (TrendPoint) -> Int, color: androidx.compose.ui.graphics.Color) {
            val stroke = Path()
            val fill = Path()
            points.forEachIndexed { i, p ->
                val x = if (points.size == 1) 0f else w * i / (points.size - 1)
                val y = h - (h * sel(p) / maxVal)
                if (i == 0) {
                    stroke.moveTo(x, y)
                    fill.moveTo(x, h)
                    fill.lineTo(x, y)
                } else {
                    stroke.lineTo(x, y)
                    fill.lineTo(x, y)
                }
            }
            fill.lineTo(w, h)
            fill.close()
            drawPath(
                fill,
                brush = Brush.verticalGradient(listOf(color.copy(alpha = 0.30f), color.copy(alpha = 0f))),
            )
            drawPath(stroke, color, style = androidx.compose.ui.graphics.drawscope.Stroke(width = 5f))
        }
        drawLine(
            Stroke.copy(alpha = 0.6f),
            Offset(0f, h), Offset(w, h), strokeWidth = 2f,
        )
        line({ it.applied }, Brand)
        line({ it.interviews }, Indigo)
        line({ it.offers }, Amber)
    }
}
