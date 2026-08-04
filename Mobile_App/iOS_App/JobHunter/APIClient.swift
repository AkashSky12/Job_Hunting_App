import Foundation

/// Lightweight async/await REST client for the AI Job Hunter backend.
///
/// The iOS Simulator shares the host's network, so `localhost` reaches a
/// backend started with `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
/// For a physical device, change `baseURL` to your machine's LAN IP.
struct APIClient {
    static let shared = APIClient()

    // Change to "http://<your-lan-ip>:8000" for a physical device.
    let baseURL = URL(string: "http://127.0.0.1:8000")!

    private let decoder: JSONDecoder = {
        let d = JSONDecoder()
        return d
    }()

    enum APIError: LocalizedError {
        case http(Int, String)
        case invalidResponse
        var errorDescription: String? {
            switch self {
            case .http(let code, let detail): return detail.isEmpty ? "HTTP \(code)" : detail
            case .invalidResponse: return "Invalid server response"
            }
        }
    }

    // MARK: - Core requests

    private func request(_ path: String, method: String = "GET", body: Data? = nil) async throws -> Data {
        var req = URLRequest(url: baseURL.appendingPathComponent(path))
        req.httpMethod = method
        if let body {
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
            req.httpBody = body
        }
        let (data, resp) = try await URLSession.shared.data(for: req)
        guard let http = resp as? HTTPURLResponse else { throw APIError.invalidResponse }
        guard (200..<300).contains(http.statusCode) else {
            let detail = (try? JSONDecoder().decode([String: String].self, from: data))?["detail"] ?? ""
            throw APIError.http(http.statusCode, detail)
        }
        return data
    }

    private func get<T: Decodable>(_ path: String) async throws -> T {
        try decoder.decode(T.self, from: try await request(path))
    }

    private func post<T: Decodable>(_ path: String, body: Encodable? = nil) async throws -> T {
        let data = try body.map { try JSONEncoder().encode(AnyEncodable($0)) }
        return try decoder.decode(T.self, from: try await request(path, method: "POST", body: data))
    }

    private func patch<T: Decodable>(_ path: String, body: Encodable) async throws -> T {
        let data = try JSONEncoder().encode(AnyEncodable(body))
        return try decoder.decode(T.self, from: try await request(path, method: "PATCH", body: data))
    }

    // MARK: - Endpoints

    func stats() async throws -> Stats { try await get("api/stats") }
    func trend(days: Int = 30) async throws -> [TrendPoint] { try await get("api/stats/trend?days=\(days)") }
    func matches() async throws -> [Match] { try await get("api/matches") }
    func applications() async throws -> [Application] { try await get("api/applications") }
    func profile() async throws -> Profile { try await get("api/profile") }

    func sources(query: String = "", location: String = "") async throws -> [JobSource] {
        let q = query.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? ""
        let loc = location.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? ""
        return try await get("api/sources?query=\(q)&location=\(loc)")
    }

    @discardableResult
    func ingest() async throws -> IngestResponse { try await post("api/jobs/ingest") }
    @discardableResult
    func runMatch() async throws -> MatchResponse { try await post("api/match") }

    @discardableResult
    func apply(jobId: String) async throws -> [String: AnyCodable] {
        try await post("api/applications", body: ["job_id": jobId])
    }
    @discardableResult
    func updateStatus(jobId: String, status: String) async throws -> [String: AnyCodable] {
        try await patch("api/applications/status", body: ["job_id": jobId, "status": status])
    }
    func classify(subject: String, body: String) async throws -> ClassifyResult {
        try await post("api/inbox/classify", body: ["subject": subject, "body": body])
    }

    // MARK: - Multipart CV upload

    func uploadCV(fileURL: URL) async throws {
        let boundary = "Boundary-\(UUID().uuidString)"
        var req = URLRequest(url: baseURL.appendingPathComponent("api/profile/upload"))
        req.httpMethod = "POST"
        req.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        let needsStop = fileURL.startAccessingSecurityScopedResource()
        defer { if needsStop { fileURL.stopAccessingSecurityScopedResource() } }
        let fileData = try Data(contentsOf: fileURL)
        let filename = fileURL.lastPathComponent

        var data = Data()
        data.append("--\(boundary)\r\n".data(using: .utf8)!)
        data.append("Content-Disposition: form-data; name=\"file\"; filename=\"\(filename)\"\r\n".data(using: .utf8)!)
        data.append("Content-Type: application/octet-stream\r\n\r\n".data(using: .utf8)!)
        data.append(fileData)
        data.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)

        let (respData, resp) = try await URLSession.shared.upload(for: req, from: data)
        guard let http = resp as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            let detail = (try? JSONDecoder().decode([String: String].self, from: respData))?["detail"] ?? "Upload failed"
            throw APIError.http((resp as? HTTPURLResponse)?.statusCode ?? -1, detail)
        }
    }
}

/// Type-erased Encodable so heterogeneous bodies can be sent.
struct AnyEncodable: Encodable {
    private let encodeFunc: (Encoder) throws -> Void
    init(_ wrapped: Encodable) { encodeFunc = wrapped.encode }
    func encode(to encoder: Encoder) throws { try encodeFunc(encoder) }
}

/// Decodes arbitrary JSON values (used for endpoints returning loose maps).
struct AnyCodable: Codable {
    let value: Any
    init(from decoder: Decoder) throws {
        let c = try decoder.singleValueContainer()
        if let v = try? c.decode(Bool.self) { value = v }
        else if let v = try? c.decode(Int.self) { value = v }
        else if let v = try? c.decode(Double.self) { value = v }
        else if let v = try? c.decode(String.self) { value = v }
        else { value = "" }
    }
    func encode(to encoder: Encoder) throws {
        var c = encoder.singleValueContainer()
        switch value {
        case let v as Bool: try c.encode(v)
        case let v as Int: try c.encode(v)
        case let v as Double: try c.encode(v)
        case let v as String: try c.encode(v)
        default: try c.encodeNil()
        }
    }
}
