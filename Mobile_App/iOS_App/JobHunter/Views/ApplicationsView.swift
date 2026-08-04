import SwiftUI

struct ApplicationsView: View {
    @EnvironmentObject var vm: AppViewModel

    var body: some View {
        NavigationStack {
            Group {
                if vm.applications.isEmpty {
                    ContentUnavailableView(
                        "No applications yet",
                        systemImage: "tray",
                        description: Text("Auto-apply to a match to start tracking.")
                    )
                } else {
                    List {
                        ForEach(vm.statusColumns, id: \.self) { status in
                            let items = vm.applications.filter { $0.status == status }
                            if !items.isEmpty {
                                Section("\(status.humanized.capitalized) (\(items.count))") {
                                    ForEach(items) { app in
                                        ApplicationRow(
                                            app: app,
                                            prev: prevStatus(of: status),
                                            next: nextStatus(of: status),
                                            onMove: { vm.moveApplication(app.jobId, to: $0) }
                                        )
                                        .listRowBackground(Color.clear)
                                        .listRowSeparator(.hidden)
                                    }
                                }
                            }
                        }
                    }
                    .scrollContentBackground(.hidden)
                }
            }
            .background(ScreenBackground())
            .navigationTitle("Applications")
            .refreshable { vm.loadApplications() }
        }
        .onAppear { vm.loadApplications() }
    }

    private func prevStatus(of s: String) -> String? {
        guard let i = vm.statusColumns.firstIndex(of: s), i > 0 else { return nil }
        return vm.statusColumns[i - 1]
    }
    private func nextStatus(of s: String) -> String? {
        guard let i = vm.statusColumns.firstIndex(of: s), i < vm.statusColumns.count - 1 else { return nil }
        return vm.statusColumns[i + 1]
    }
}

struct ApplicationRow: View {
    let app: Application
    let prev: String?
    let next: String?
    let onMove: (String) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(app.title ?? "Untitled").font(.headline)
            Text(app.company ?? "").font(.subheadline).foregroundStyle(.secondary)
            HStack(spacing: 14) {
                if let prev {
                    Button("← \(prev.humanized)") { onMove(prev) }
                        .font(.subheadline).buttonStyle(.borderless)
                }
                if let next {
                    Button("→ \(next.humanized)") { onMove(next) }
                        .font(.subheadline).buttonStyle(.borderless).tint(Palette.brand)
                }
            }
        }
        .cardStyle()
        .padding(.vertical, 4)
    }
}
