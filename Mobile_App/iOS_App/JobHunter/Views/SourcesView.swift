import SwiftUI

struct SourcesView: View {
    @EnvironmentObject var vm: AppViewModel
    @State private var query = ""
    @State private var location = ""
    @State private var keywords = ""
    @State private var exclude = ""
    @Environment(\.openURL) private var openURL

    var body: some View {
        NavigationStack {
            List {
                Section {
                    TextField("Keywords, comma-separated", text: $keywords)
                    TextField("Exclude e.g. intern, staff", text: $exclude)
                    Button("Run auto-search") {
                        vm.autoSearch(keywords: keywords, exclude: exclude, location: location)
                    }
                    .tint(Palette.brand)
                    .disabled(vm.loading || keywords.trimmingCharacters(in: .whitespaces).isEmpty)
                    if let r = vm.autoSearchResult {
                        ForEach(r.perBoard.keys.sorted(), id: \.self) { board in
                            HStack {
                                Text(board).font(.subheadline)
                                Spacer()
                                if r.errors[board] != nil {
                                    Text("failed").font(.subheadline).foregroundStyle(.red)
                                } else {
                                    Text("\(r.perBoard[board] ?? 0)").font(.subheadline).foregroundStyle(Palette.brand)
                                }
                            }
                        }
                    }
                } header: {
                    Text("Auto-search")
                } footer: {
                    Text("Searches company boards on Greenhouse, Lever and Ashby (ATS_BOARDS on the server). Uses the location below.")
                }
                .listRowBackground(Palette.surface.opacity(0.6))

                Section {
                    TextField("Role e.g. python developer", text: $query)
                    TextField("Location e.g. bangalore", text: $location)
                    Button("Update search links") { vm.loadSources(query: query, location: location) }
                        .tint(Palette.brand)
                }
                .listRowBackground(Palette.surface.opacity(0.6))

                Section {
                    ForEach(vm.sources) { source in
                        SourceRow(source: source) { url in openURL(url) }
                            .listRowBackground(Color.clear)
                            .listRowSeparator(.hidden)
                    }
                } header: {
                    Text("Platforms")
                } footer: {
                    Text("Deep-link platforms open their own job search — no scraping. API sources are ingested into your feed.")
                }
            }
            .scrollContentBackground(.hidden)
            .background(ScreenBackground())
            .navigationTitle("Sources")
            .refreshable { vm.loadSources(query: query, location: location) }
        }
        .onAppear { if vm.sources.isEmpty { vm.loadSources() } }
    }
}

struct SourceRow: View {
    let source: JobSource
    let onOpen: (URL) -> Void

    private var badge: String {
        if source.kind == "deeplink" { return "deep link" }
        return source.enabled ? "ingested" : "needs key"
    }
    private var initials: String { String(source.name.trimmingCharacters(in: .whitespaces).prefix(2)).uppercased() }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 12) {
                GradientChip(text: initials, size: 42)
                Text(source.name).font(.headline)
                Spacer()
                Text(badge).font(.caption).foregroundStyle(Palette.brand)
            }
            Text(source.note).font(.subheadline).foregroundStyle(.secondary)
            if let urlStr = source.searchUrl, let url = URL(string: urlStr) {
                Button("Open search →") { onOpen(url) }
                    .font(.callout.weight(.semibold))
                    .buttonStyle(.borderless)
                    .tint(Palette.brand)
            }
        }
        .cardStyle()
        .padding(.vertical, 4)
    }
}
