package com.jobhunter.app.ui

import android.content.Context
import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.jobhunter.app.data.Application
import com.jobhunter.app.data.ApplyRequest
import com.jobhunter.app.data.AutoApplyRequest
import com.jobhunter.app.data.AutoSearchRequest
import com.jobhunter.app.data.AutoSearchResponse
import com.jobhunter.app.data.ClassifyRequest
import com.jobhunter.app.data.ClassifyResult
import com.jobhunter.app.data.JobSource
import com.jobhunter.app.data.Match
import com.jobhunter.app.data.Network
import com.jobhunter.app.data.Profile
import com.jobhunter.app.data.Stats
import com.jobhunter.app.data.StatusRequest
import com.jobhunter.app.data.TrendPoint
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class UiState(
    val loading: Boolean = false,
    val message: String? = null,
    val stats: Stats = Stats(),
    val trend: List<TrendPoint> = emptyList(),
    val matches: List<Match> = emptyList(),
    val applications: List<Application> = emptyList(),
    val profile: Profile? = null,
    val sources: List<JobSource> = emptyList(),
    val autoSearch: AutoSearchResponse? = null,
)

class AppViewModel : ViewModel() {

    private val api = Network.api
    private val _state = MutableStateFlow(UiState())
    val state: StateFlow<UiState> = _state.asStateFlow()

    val statusColumns = listOf("applied", "viewed", "phone_screen", "interview", "offer", "rejected")

    private inline fun launch(crossinline block: suspend () -> Unit) {
        viewModelScope.launch {
            _state.update { it.copy(loading = true) }
            try {
                block()
            } catch (e: Exception) {
                _state.update { it.copy(message = e.message ?: "Network error") }
            } finally {
                _state.update { it.copy(loading = false) }
            }
        }
    }

    fun clearMessage() = _state.update { it.copy(message = null) }

    private fun splitTerms(s: String) = s.split(',').map { it.trim() }.filter { it.isNotEmpty() }

    fun loadOverview() = launch {
        val stats = api.stats()
        val trend = api.trend(30)
        _state.update { it.copy(stats = stats, trend = trend) }
    }

    fun loadMatches() = launch {
        _state.update { it.copy(matches = api.matches()) }
    }

    fun loadApplications() = launch {
        _state.update { it.copy(applications = api.applications()) }
    }

    fun loadProfile() = launch {
        _state.update { it.copy(profile = api.profile()) }
    }

    fun loadSources(query: String = "", location: String = "") = launch {
        _state.update { it.copy(sources = api.sources(query, location)) }
    }

    fun ingest() = launch {
        val r = api.ingest()
        _state.update { it.copy(message = "Ingested ${r.ingested} jobs") }
    }

    fun autoSearch(keywords: String, exclude: String, location: String) = launch {
        val kw = splitTerms(keywords)
        if (kw.isEmpty()) {
            _state.update { it.copy(message = "Enter at least one keyword") }
            return@launch
        }
        val r = api.autoSearch(AutoSearchRequest(kw, splitTerms(exclude), location.trim().ifEmpty { null }))
        val failed = if (r.errors.isEmpty()) "" else " (${r.errors.size} board(s) failed)"
        _state.update { it.copy(autoSearch = r, message = "Auto-search stored ${r.ingested} jobs$failed") }
    }

    fun autoApply(jobId: String) = launch {
        val r = api.autoApply(AutoApplyRequest(jobId))
        val where = if (r.headless) "in the background" else "in a browser on your computer"
        _state.update { it.copy(message = "Pre-filling application $where. Review and submit there.") }
    }

    fun runMatching() = launch {
        val r = api.runMatch()
        _state.update { it.copy(message = "Ranked ${r.matched} jobs") }
        _state.update { it.copy(matches = api.matches()) }
    }

    fun applyToJob(jobId: String) = launch {
        api.apply(ApplyRequest(jobId))
        _state.update { it.copy(message = "Applied + cover letter generated") }
        _state.update { it.copy(matches = api.matches()) }
    }

    fun moveApplication(jobId: String, status: String) = launch {
        api.updateStatus(StatusRequest(jobId, status))
        _state.update { it.copy(applications = api.applications()) }
    }

    fun uploadCv(context: Context, uri: Uri) = launch {
        val part = Network.filePart(context, uri)
        api.uploadCv(part)
        _state.update { it.copy(message = "CV parsed", profile = api.profile()) }
    }

    fun classifyEmail(subject: String, body: String, onResult: (ClassifyResult) -> Unit) = launch {
        val result = api.classify(ClassifyRequest(subject, body))
        val updated = result.updated
        _state.update {
            it.copy(
                message = if (updated != null) "Updated ${updated.company} → ${updated.status}"
                else "Classified as ${result.classification?.status}"
            )
        }
        onResult(result)
    }
}
