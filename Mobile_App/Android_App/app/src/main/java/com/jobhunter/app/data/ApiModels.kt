package com.jobhunter.app.data

import com.google.gson.annotations.SerializedName

/** Mirrors the FastAPI JSON responses. Field names match the API keys. */

data class Stats(
    val jobs: Int = 0,
    val matches: Int = 0,
    val applications: Int = 0,
    val funnel: Map<String, Int> = emptyMap(),
    @SerializedName("ai_enabled") val aiEnabled: Boolean = false,
    @SerializedName("adzuna_enabled") val adzunaEnabled: Boolean = false,
    @SerializedName("gmail_enabled") val gmailEnabled: Boolean = false,
)

data class TrendPoint(
    val day: String = "",
    val applied: Int = 0,
    val interviews: Int = 0,
    val offers: Int = 0,
)

data class Match(
    val id: String = "",
    val title: String? = null,
    val company: String? = null,
    val location: String? = null,
    val score: Double = 0.0,
    val reasoning: String? = null,
    val source: String? = null,
    val remote: Int? = null,
    @SerializedName("salary_min") val salaryMin: Int? = null,
    @SerializedName("salary_max") val salaryMax: Int? = null,
    @SerializedName("apply_url") val applyUrl: String? = null,
    @SerializedName("app_status") val appStatus: String? = null,
)

data class Application(
    @SerializedName("job_id") val jobId: String = "",
    val status: String = "queued",
    val title: String? = null,
    val company: String? = null,
    val location: String? = null,
    @SerializedName("apply_url") val applyUrl: String? = null,
    @SerializedName("cover_letter") val coverLetter: String? = null,
)

data class Profile(
    @SerializedName("full_name") val fullName: String? = null,
    val email: String? = null,
    val summary: String? = null,
    @SerializedName("parsed_json") val parsedJson: ParsedCv? = null,
)

data class ParsedCv(
    val name: String? = null,
    val email: String? = null,
    val summary: String? = null,
    val skills: List<String> = emptyList(),
)

data class IngestResponse(val ok: Boolean = false, val ingested: Int = 0)
data class MatchResponse(val ok: Boolean = false, val matched: Int = 0)

data class JobSource(
    val key: String = "",
    val name: String = "",
    val kind: String = "",          // "api" | "deeplink"
    val enabled: Boolean = false,
    val note: String = "",
    @SerializedName("search_url") val searchUrl: String? = null,
)

data class ClassifyResult(
    val classification: Classification? = null,
    val updated: UpdatedApp? = null,
)
data class Classification(
    val status: String = "other",
    val company: String? = null,
    @SerializedName("next_action") val nextAction: String? = null,
)
data class UpdatedApp(
    @SerializedName("job_id") val jobId: String? = null,
    val company: String? = null,
    val status: String? = null,
)

data class ApplyRequest(@SerializedName("job_id") val jobId: String)
data class StatusRequest(
    @SerializedName("job_id") val jobId: String,
    val status: String,
)
data class ClassifyRequest(val subject: String, val body: String)

data class AutoSearchRequest(
    val keywords: List<String>,
    val exclude: List<String> = emptyList(),
    val location: String? = null,
)
data class AutoSearchResponse(
    val ok: Boolean = false,
    val ingested: Int = 0,
    @SerializedName("per_board") val perBoard: Map<String, Int> = emptyMap(),
    val errors: Map<String, String> = emptyMap(),
)

data class AutoApplyRequest(
    @SerializedName("job_id") val jobId: String,
    val submit: Boolean = false,
)
data class AutoApplyResponse(val ok: Boolean = false, val headless: Boolean = false)
