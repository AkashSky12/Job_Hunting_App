package com.jobhunter.app.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable

private val DarkColors = darkColorScheme(
    primary = Brand,
    onPrimary = Ink0,
    secondary = Brand2,
    onSecondary = Ink0,
    tertiary = Accent,
    background = Ink0,
    onBackground = TextHi,
    surface = Surface1,
    onSurface = TextHi,
    surfaceVariant = Surface2,
    onSurfaceVariant = TextMuted,
    outline = Stroke,
)

private val LightColors = lightColorScheme(
    primary = BrandDark,
    onPrimary = TextHi,
    secondary = Brand2,
)

@Composable
fun JobHunterTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    MaterialTheme(
        colorScheme = if (darkTheme) DarkColors else LightColors,
        typography = AppTypography,
        content = content,
    )
}
