package com.jobhunter.app.ui

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun ProfileScreen(vm: AppViewModel, state: UiState) {
    LaunchedEffect(Unit) { vm.loadProfile() }
    val context = LocalContext.current

    val picker = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.GetContent(),
    ) { uri -> uri?.let { vm.uploadCv(context, it) } }

    Column(
        modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Profile", style = MaterialTheme.typography.headlineSmall)
        Button(onClick = { picker.launch("*/*") }, shape = RoundedCornerShape(12.dp)) { Text("Upload CV (PDF / DOCX / TXT)") }

        val parsed = state.profile?.parsedJson
        if (parsed == null) {
            Text(
                "No CV uploaded yet.",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        } else {
            GlassCard {
                Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(parsed.name ?: state.profile?.fullName ?: "", fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleLarge)
                    Text(
                        parsed.email ?: state.profile?.email ?: "",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    parsed.summary?.takeIf { it.isNotBlank() }?.let {
                        Text(it, style = MaterialTheme.typography.bodyMedium)
                    }
                    if (parsed.skills.isNotEmpty()) {
                        FlowRow(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            parsed.skills.forEach { skill ->
                                AssistChip(onClick = {}, label = { Text(skill) })
                            }
                        }
                    }
                }
            }
        }

        GlassCard {
            Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text("Server status", style = MaterialTheme.typography.titleMedium)
                val s = state.stats
                Text("AI matching: ${if (s.aiEnabled) "on (LLM)" else "fallback (TF-IDF)"}",
                    color = MaterialTheme.colorScheme.onSurfaceVariant)
                Text("Adzuna: ${if (s.adzunaEnabled) "enabled" else "off"}",
                    color = MaterialTheme.colorScheme.onSurfaceVariant)
                Text("Gmail sync: ${if (s.gmailEnabled) "configured" else "off"}",
                    color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}
