package com.jobhunter.app.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.jobhunter.app.data.ClassifyResult

@Composable
fun InboxScreen(vm: AppViewModel, state: UiState) {
    var subject by remember { mutableStateOf("") }
    var body by remember { mutableStateOf("") }
    var result by remember { mutableStateOf<ClassifyResult?>(null) }

    Column(
        modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Inbox", style = MaterialTheme.typography.headlineSmall)
        Text(
            if (state.stats.gmailEnabled) "Gmail configured on server"
            else "Paste a recruiter email to classify and auto-update the matching application.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        OutlinedTextField(
            value = subject,
            onValueChange = { subject = it },
            label = { Text("Subject") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
        )
        OutlinedTextField(
            value = body,
            onValueChange = { body = it },
            label = { Text("Email body") },
            modifier = Modifier.fillMaxWidth(),
            minLines = 5,
        )
        Button(
            onClick = { vm.classifyEmail(subject, body) { result = it } },
            enabled = subject.isNotBlank() || body.isNotBlank(),
            shape = RoundedCornerShape(12.dp),
        ) { Text("Classify & update") }

        result?.let { r ->
            GlassCard {
                Column(Modifier.padding(16.dp)) {
                    Text("Status: ${r.classification?.status}", fontWeight = FontWeight.SemiBold, style = MaterialTheme.typography.titleMedium)
                    Text(
                        "Company: ${r.classification?.company ?: "—"}",
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    r.classification?.nextAction?.takeIf { it.isNotBlank() }?.let {
                        Text("Next: $it", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    Text(
                        if (r.updated != null) "Updated ${r.updated.company} → ${r.updated.status}"
                        else "No matching application found",
                        style = MaterialTheme.typography.bodyMedium,
                        color = if (r.updated != null) MaterialTheme.colorScheme.primary
                        else MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(top = 6.dp),
                    )
                }
            }
        }
    }
}
