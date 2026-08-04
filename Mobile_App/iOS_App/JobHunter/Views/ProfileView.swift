import SwiftUI
import UniformTypeIdentifiers

struct ProfileView: View {
    @EnvironmentObject var vm: AppViewModel
    @State private var showImporter = false

    private let cvTypes: [UTType] = [.pdf, .plainText,
        UTType(filenameExtension: "docx") ?? .data, UTType(filenameExtension: "md") ?? .plainText]

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    Button {
                        showImporter = true
                    } label: {
                        Label("Upload CV (PDF / DOCX / TXT)", systemImage: "doc.badge.plus")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)

                    if let parsed = vm.profile?.parsedJson {
                        VStack(alignment: .leading, spacing: 8) {
                            Text(parsed.name ?? vm.profile?.fullName ?? "").font(.title3.bold())
                            Text(parsed.email ?? vm.profile?.email ?? "")
                                .font(.subheadline).foregroundStyle(.secondary)
                            if let summary = parsed.summary, !summary.isEmpty {
                                Text(summary).font(.body)
                            }
                            if !parsed.skills.isEmpty {
                                SkillChips(skills: parsed.skills)
                            }
                        }
                        .cardStyle()
                    } else {
                        Text("No CV uploaded yet.").foregroundStyle(.secondary)
                    }

                    serverCard
                }
                .padding()
            }
            .background(ScreenBackground())
            .navigationTitle("Profile")
            .refreshable { vm.loadProfile() }
            .fileImporter(isPresented: $showImporter, allowedContentTypes: cvTypes) { result in
                if case .success(let url) = result { vm.uploadCV(url) }
            }
        }
        .onAppear {
            vm.loadProfile()
            if vm.stats.jobs == 0 { vm.loadOverview() }
        }
    }

    private var serverCard: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("Server status").font(.title3.bold())
            Text("AI matching: \(vm.stats.aiEnabled ? "on (LLM)" : "fallback (TF-IDF)")")
                .foregroundStyle(.secondary)
            Text("Adzuna: \(vm.stats.adzunaEnabled ? "enabled" : "off")").foregroundStyle(.secondary)
            Text("Gmail sync: \(vm.stats.gmailEnabled ? "configured" : "off")").foregroundStyle(.secondary)
        }
        .font(.callout)
        .cardStyle()
    }
}

struct SkillChips: View {
    let skills: [String]
    var body: some View {
        // Simple wrapping layout using a flexible grid.
        FlowLayout(spacing: 6) {
            ForEach(skills, id: \.self) { skill in
                Text(skill)
                    .font(.subheadline)
                    .foregroundStyle(Palette.brand2)
                    .padding(.horizontal, 10).padding(.vertical, 5)
                    .background(Palette.brand2.opacity(0.16))
                    .overlay(Capsule().strokeBorder(Palette.brand2.opacity(0.3), lineWidth: 1))
                    .clipShape(Capsule())
            }
        }
    }
}

/// Minimal wrapping layout (chips) using the SwiftUI Layout protocol.
struct FlowLayout: Layout {
    var spacing: CGFloat = 8

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let maxWidth = proposal.width ?? .infinity
        var x: CGFloat = 0, y: CGFloat = 0, rowHeight: CGFloat = 0
        for view in subviews {
            let size = view.sizeThatFits(.unspecified)
            if x + size.width > maxWidth {
                x = 0
                y += rowHeight + spacing
                rowHeight = 0
            }
            x += size.width + spacing
            rowHeight = max(rowHeight, size.height)
        }
        return CGSize(width: maxWidth == .infinity ? x : maxWidth, height: y + rowHeight)
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        var x = bounds.minX, y = bounds.minY, rowHeight: CGFloat = 0
        for view in subviews {
            let size = view.sizeThatFits(.unspecified)
            if x + size.width > bounds.maxX {
                x = bounds.minX
                y += rowHeight + spacing
                rowHeight = 0
            }
            view.place(at: CGPoint(x: x, y: y), proposal: ProposedViewSize(size))
            x += size.width + spacing
            rowHeight = max(rowHeight, size.height)
        }
    }
}
