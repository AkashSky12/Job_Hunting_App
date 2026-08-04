package com.jobhunter.app.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.jobhunter.app.ui.theme.Accent
import com.jobhunter.app.ui.theme.Brand
import com.jobhunter.app.ui.theme.Brand2
import com.jobhunter.app.ui.theme.Ink0
import com.jobhunter.app.ui.theme.Ink1
import com.jobhunter.app.ui.theme.Stroke

/** Full-screen gradient mesh background used by every tab. */
@Composable
fun ScreenBackground(content: @Composable () -> Unit) {
    Box(
        Modifier
            .fillMaxSize()
            .background(
                Brush.linearGradient(
                    0.0f to Ink0,
                    0.5f to Ink1,
                    1.0f to Ink0,
                    start = Offset(0f, 0f),
                    end = Offset(1200f, 1600f),
                )
            )
    ) {
        Box(
            Modifier
                .fillMaxSize()
                .background(
                    Brush.radialGradient(
                        colors = listOf(Brand2.copy(alpha = 0.16f), Color.Transparent),
                        center = Offset(120f, 80f),
                        radius = 900f,
                    )
                )
        )
        Box(
            Modifier
                .fillMaxSize()
                .background(
                    Brush.radialGradient(
                        colors = listOf(Accent.copy(alpha = 0.12f), Color.Transparent),
                        center = Offset(1000f, 1700f),
                        radius = 1000f,
                    )
                )
        )
        content()
    }
}

/** Glassy elevated card with a subtle stroke — the standard surface across the app. */
@Composable
fun GlassCard(
    modifier: Modifier = Modifier,
    content: @Composable () -> Unit,
) {
    Card(
        modifier = modifier,
        shape = RoundedCornerShape(22.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.85f)),
        border = BorderStroke(1.dp, Stroke.copy(alpha = 0.7f)),
        elevation = CardDefaults.cardElevation(defaultElevation = 6.dp),
        content = { content() },
    )
}

/** Circular gradient icon chip used for KPIs, avatars and source badges. */
@Composable
fun GradientChip(
    text: String,
    modifier: Modifier = Modifier,
    sizeDp: Int = 48,
) {
    Box(
        modifier
            .size(sizeDp.dp)
            .clip(RoundedCornerShape((sizeDp / 3).dp))
            .background(
                Brush.linearGradient(listOf(Brand.copy(alpha = 0.28f), Brand2.copy(alpha = 0.28f)))
            ),
        contentAlignment = Alignment.Center,
    ) {
        Text(text, fontWeight = FontWeight.Bold, color = Brand, style = MaterialTheme.typography.titleMedium)
    }
}

@Composable
fun EmptyState(message: String) {
    Box(Modifier.fillMaxSize().padding(32.dp), contentAlignment = Alignment.Center) {
        Text(
            message,
            textAlign = TextAlign.Center,
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}
