import Foundation

// MARK: - API response models (keys match the FastAPI JSON)

struct Stats: Codable {
    var jobs: Int = 0
    var matches: Int = 0
    var applications: Int = 0
    var funnel: [String: Int] = [:]
    var aiEnabled: Bool = false
    var adzunaEnabled: Bool = false
    var gmailEnabled: Bool = false

    enum CodingKeys: String, CodingKey {
        case jobs, matches, applications, funnel
        case aiEnabled = "ai_enabled"
        case adzunaEnabled = "adzuna_enabled"
        case gmailEnabled = "gmail_enabled"
    }
}

struct TrendPoint: Codable, Identifiable {
    var day: String = ""
    var applied: Int = 0
    var interviews: Int = 0
    var offers: Int = 0
    var id: String { day }
}

struct Match: Codable, Identifiable {
    var id: String = ""
    var title: String?
    var company: String?
    var location: String?
    var score: Double = 0
    var reasoning: String?
    var source: String?
    var remote: Int?
    var salaryMin: Int?
    var salaryMax: Int?
    var applyUrl: String?
    var appStatus: String?

    enum CodingKeys: String, CodingKey {
        case id, title, company, location, score, reasoning, source, remote
        case salaryMin = "salary_min"
        case salaryMax = "salary_max"
        case applyUrl = "apply_url"
        case appStatus = "app_status"
    }
}

struct Application: Codable, Identifiable {
    var jobId: String = ""
    var status: String = "queued"
    var title: String?
    var company: String?
    var location: String?
    var applyUrl: String?
    var coverLetter: String?
    var id: String { jobId }

    enum CodingKeys: String, CodingKey {
        case jobId = "job_id"
        case status, title, company, location
        case applyUrl = "apply_url"
        case coverLetter = "cover_letter"
    }
}

struct Profile: Codable {
    var fullName: String?
    var email: String?
    var summary: String?
    var parsedJson: ParsedCV?

    enum CodingKeys: String, CodingKey {
        case fullName = "full_name"
        case email, summary
        case parsedJson = "parsed_json"
    }
}

struct ParsedCV: Codable {
    var name: String?
    var email: String?
    var summary: String?
    var skills: [String] = []
}

struct IngestResponse: Codable { var ok: Bool = false; var ingested: Int = 0 }
struct MatchResponse: Codable { var ok: Bool = false; var matched: Int = 0 }

struct AutoSearchRequest: Encodable {
    var keywords: [String]
    var exclude: [String] = []
    var location: String?
}

struct AutoSearchResponse: Codable {
    var ok: Bool = false
    var ingested: Int = 0
    var perBoard: [String: Int] = [:]
    var errors: [String: String] = [:]

    enum CodingKeys: String, CodingKey {
        case ok, ingested, errors
        case perBoard = "per_board"
    }
}

struct AutoApplyRequest: Encodable {
    var jobId: String
    var submit = false

    enum CodingKeys: String, CodingKey {
        case submit
        case jobId = "job_id"
    }
}

struct AutoApplyResponse: Codable { var ok: Bool = false; var headless: Bool = false }

struct JobSource: Codable, Identifiable {
    var key: String = ""
    var name: String = ""
    var kind: String = ""            // "api" | "deeplink"
    var enabled: Bool = false
    var note: String = ""
    var searchUrl: String?
    var id: String { key }

    enum CodingKeys: String, CodingKey {
        case key, name, kind, enabled, note
        case searchUrl = "search_url"
    }
}

struct ClassifyResult: Codable {
    var classification: Classification?
    var updated: UpdatedApp?
}
struct Classification: Codable {
    var status: String = "other"
    var company: String?
    var nextAction: String?
    enum CodingKeys: String, CodingKey {
        case status, company
        case nextAction = "next_action"
    }
}
struct UpdatedApp: Codable {
    var jobId: String?
    var company: String?
    var status: String?
    enum CodingKeys: String, CodingKey {
        case jobId = "job_id"
        case company, status
    }
}
