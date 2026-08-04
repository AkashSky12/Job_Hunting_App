package com.jobhunter.app.data

import okhttp3.MultipartBody
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Query

interface ApiService {

    @GET("api/stats")
    suspend fun stats(): Stats

    @GET("api/stats/trend")
    suspend fun trend(@Query("days") days: Int = 30): List<TrendPoint>

    @GET("api/matches")
    suspend fun matches(): List<Match>

    @GET("api/applications")
    suspend fun applications(): List<Application>

    @GET("api/profile")
    suspend fun profile(): Profile

    @GET("api/sources")
    suspend fun sources(
        @Query("query") query: String = "",
        @Query("location") location: String = "",
    ): List<JobSource>

    @POST("api/jobs/ingest")
    suspend fun ingest(): IngestResponse

    @POST("api/match")
    suspend fun runMatch(): MatchResponse

    @POST("api/applications")
    suspend fun apply(@Body req: ApplyRequest): Map<String, Any>

    @PATCH("api/applications/status")
    suspend fun updateStatus(@Body req: StatusRequest): Map<String, Any>

    @POST("api/inbox/classify")
    suspend fun classify(@Body req: ClassifyRequest): ClassifyResult

    @Multipart
    @POST("api/profile/upload")
    suspend fun uploadCv(@Part file: MultipartBody.Part): Map<String, Any>
}
