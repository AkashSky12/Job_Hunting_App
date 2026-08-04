import SwiftUI

struct MatchesView: View {
    @EnvironmentObject var vm: AppViewModel
    @State private var role = ""
    @State private var country = ""
    @State private var minSalary = ""
    @State private var remoteOnly = false

    private func isRemote(_ m: Match) -> Bool {
        (m.remote ?? 0) == 1 || (m.location?.localizedCaseInsensitiveContains("remote") ?? false)
    }

    private var filtered: [Match] {
        let floor = Int(minSalary) ?? 0
        return vm.matches.filter { m in
            if !role.isEmpty,
               !("\(m.title ?? "") \(m.company ?? "")").localizedCaseInsensitiveContains(role) { return false }
            if !country.isEmpty,
               !((m.location ?? "").localizedCaseInsensitiveContains(country)) { return false }
            if remoteOnly, !isRemote(m) { return false }
            if floor > 0 {
                let jobMax = m.salaryMax ?? m.salaryMin ?? 0
                if jobMax < floor { return false }
            }
            return true
        }
    }

    private var filtersActive: Bool {
        !role.isEmpty || !country.isEmpty || !minSalary.isEmpty || remoteOnly
    }

    var body: some View {
        NavigationStack {
            Group {
                if vm.matches.isEmpty {
                    ContentUnavailableView(
                        "No matches yet",
                        systemImage: "sparkles",
                        description: Text("Upload a CV, ingest jobs, then run matching.")
                    )
                } else {
                    ScrollView {
                        LazyVStack(spacing: 14) {
                            filterCard
                            ForEach(filtered) { match in
                                MatchRow(match: match, isRemote: isRemote(match)) { vm.applyToJob(match.id) }
                            }
                        }
                        .padding()
                    }
                }
            }
            .background(ScreenBackground())
            .navigationTitle("Matches")
            .refreshable { vm.loadMatches() }
        }
        .onAppear { vm.loadMatches() }
    }

    private var filterCard: some View {
        VStack(alignment: .leading, spacing: 10) {
            TextField("Role or company", text: $role)
                .textFieldStyle(.roundedBorder)
            TextField("Country or location", text: $country)
                .textFieldStyle(.roundedBorder)
            TextField("Min salary", text: $minSalary)
                .textFieldStyle(.roundedBorder)
                .keyboardType(.numberPad)
            HStack {
                Toggle("Remote only", isOn: $remoteOnly)
                    .toggleStyle(.button)
                    .tint(Palette.brand)
                Spacer()
                Text("\(filtered.count) of \(vm.matches.count)")
                    .font(.caption).foregroundStyle(.secondary)
                if filtersActive {
                    Button("Clear") { role = ""; country = ""; minSalary = ""; remoteOnly = false }
                        .font(.caption).tint(Palette.brand)
                }
            }
        }
        .cardStyle()
    }
}

struct MatchRow: View {
    let match: Match
    var isRemote: Bool = false
    let onApply: () -> Void
    @Environment(\.openURL) private var openURL

    private var pct: Int { min(max(Int(match.score * 100), 0), 100) }
    private var initials: String { String((match.company ?? "?").trimmingCharacters(in: .whitespaces).prefix(2)).uppercased() }

    private func openJob() {
        if let s = match.applyUrl, let url = URL(string: s) { openURL(url) }
    }

    private var salaryText: String? {
        func k(_ n: Int) -> String { "$\(n / 1000)k" }
        switch (match.salaryMin, match.salaryMax) {
        case let (min?, max?): return "\(k(min))–\(k(max))"
        case let (min?, nil): return "\(k(min))+"
        case let (nil, max?): return "up to \(k(max))"
        default: return nil
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .top, spacing: 12) {
                GradientChip(text: initials, size: 44)
                VStack(alignment: .leading, spacing: 2) {
                    Button(action: openJob) {
                        Text(match.title ?? "Untitled")
                            .font(.headline)
                            .multilineTextAlignment(.leading)
                            .foregroundStyle(match.applyUrl != nil ? Palette.brand : Color.primary)
                            .underline(match.applyUrl != nil)
                    }
                    .buttonStyle(.plain)
                    .disabled(match.applyUrl == nil)
                    Text("\(match.company ?? "") · \(match.location ?? "")")
                        .font(.subheadline).foregroundStyle(.secondary)
                }
                Spacer()
                Text("\(pct)%").font(.headline).bold().foregroundStyle(Palette.brand)
            }
            HStack(spacing: 6) {
                if let salaryText { Badge(text: salaryText, color: Palette.brand) }
                if isRemote { Badge(text: "remote", color: Palette.brand2) }
                if let source = match.source { Badge(text: source, color: Palette.textMuted) }
            }
            ProgressView(value: Double(pct), total: 100).tint(Palette.brand)
            if let reasoning = match.reasoning {
                Text(reasoning).font(.subheadline).foregroundStyle(.secondary).lineLimit(2)
            }
            HStack(spacing: 10) {
                Button("Auto-apply", action: onApply).buttonStyle(.borderedProminent)
                if match.applyUrl != nil {
                    Button("View job →") { openJob() }.buttonStyle(.bordered)
                }
                if let status = match.appStatus {
                    Text(status).font(.caption).foregroundStyle(Palette.brand)
                }
            }
        }
        .cardStyle()
    }
}

struct Badge: View {
    let text: String
    let color: Color
    var body: some View {
        Text(text)
            .font(.caption)
            .foregroundStyle(color)
            .padding(.horizontal, 8).padding(.vertical, 3)
            .background(color.opacity(0.15))
            .clipShape(RoundedRectangle(cornerRadius: 6, style: .continuous))
    }
}
