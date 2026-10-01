import Foundation
import SwiftUI

/// Single source of truth for UI state, backed by the REST client.
@MainActor
final class AppViewModel: ObservableObject {
    @Published var loading = false
    @Published var message: String?
    @Published var stats = Stats()
    @Published var trend: [TrendPoint] = []
    @Published var matches: [Match] = []
    @Published var applications: [Application] = []
    @Published var profile: Profile?
    @Published var sources: [JobSource] = []
    @Published var autoSearchResult: AutoSearchResponse?

    let statusColumns = ["applied", "viewed", "phone_screen", "interview", "offer", "rejected"]

    private let api = APIClient.shared

    private func run(_ block: @escaping () async throws -> Void) {
        Task {
            loading = true
            defer { loading = false }
            do { try await block() }
            catch { message = error.localizedDescription }
        }
    }

    func loadOverview() {
        run {
            async let s = self.api.stats()
            async let t = self.api.trend(days: 30)
            self.stats = try await s
            self.trend = try await t
        }
    }

    func loadMatches() { run { self.matches = try await self.api.matches() } }
    func loadApplications() { run { self.applications = try await self.api.applications() } }
    func loadProfile() { run { self.profile = try await self.api.profile() } }

    func loadSources(query: String = "", location: String = "") {
        run { self.sources = try await self.api.sources(query: query, location: location) }
    }

    func ingest() {
        run {
            let r = try await self.api.ingest()
            self.message = "Ingested \(r.ingested) jobs"
        }
    }

    private func splitTerms(_ s: String) -> [String] {
        s.split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces) }.filter { !$0.isEmpty }
    }

    func autoSearch(keywords: String, exclude: String, location: String) {
        let kw = splitTerms(keywords)
        guard !kw.isEmpty else { message = "Enter at least one keyword"; return }
        let loc = location.trimmingCharacters(in: .whitespaces)
        let req = AutoSearchRequest(keywords: kw, exclude: splitTerms(exclude), location: loc.isEmpty ? nil : loc)
        run {
            let r = try await self.api.autoSearch(req)
            self.autoSearchResult = r
            let failed = r.errors.isEmpty ? "" : " (\(r.errors.count) board(s) failed)"
            self.message = "Auto-search stored \(r.ingested) jobs\(failed)"
        }
    }

    func autoApply(_ jobId: String) {
        run {
            let r = try await self.api.autoApply(jobId: jobId)
            let place = r.headless ? "in the background" : "in a browser on your computer"
            self.message = "Pre-filling application \(place). Review and submit there."
        }
    }

    func runMatching() {
        run {
            let r = try await self.api.runMatch()
            self.message = "Ranked \(r.matched) jobs"
            self.matches = try await self.api.matches()
        }
    }

    func applyToJob(_ jobId: String) {
        run {
            _ = try await self.api.apply(jobId: jobId)
            self.message = "Applied + cover letter generated"
            self.matches = try await self.api.matches()
        }
    }

    func moveApplication(_ jobId: String, to status: String) {
        run {
            _ = try await self.api.updateStatus(jobId: jobId, status: status)
            self.applications = try await self.api.applications()
        }
    }

    func uploadCV(_ url: URL) {
        run {
            try await self.api.uploadCV(fileURL: url)
            self.message = "CV parsed"
            self.profile = try await self.api.profile()
        }
    }

    func classifyEmail(subject: String, body: String, onResult: @escaping (ClassifyResult) -> Void) {
        run {
            let result = try await self.api.classify(subject: subject, body: body)
            if let u = result.updated {
                self.message = "Updated \(u.company ?? "") → \(u.status ?? "")"
            } else {
                self.message = "Classified as \(result.classification?.status ?? "other")"
            }
            onResult(result)
        }
    }
}
