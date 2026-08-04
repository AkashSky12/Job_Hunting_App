import SwiftUI

struct InboxView: View {
    @EnvironmentObject var vm: AppViewModel
    @State private var subject = ""
    @State private var emailBody = ""
    @State private var result: ClassifyResult?

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Text(vm.stats.gmailEnabled
                         ? "Gmail configured on server."
                         : "Paste a recruiter email to classify and auto-update the matching application.")
                    .font(.subheadline).foregroundStyle(.secondary)
                }
                .listRowBackground(Palette.surface.opacity(0.6))
                Section("Email") {
                    TextField("Subject", text: $subject)
                    TextField("Body", text: $emailBody, axis: .vertical).lineLimit(5...10)
                    Button("Classify & update") {
                        vm.classifyEmail(subject: subject, body: emailBody) { result = $0 }
                    }
                    .tint(Palette.brand)
                    .disabled(subject.isEmpty && emailBody.isEmpty)
                }
                .listRowBackground(Palette.surface.opacity(0.6))
                if let r = result {
                    Section("Result") {
                        LabeledContent("Status", value: r.classification?.status ?? "—")
                        LabeledContent("Company", value: r.classification?.company ?? "—")
                        if let next = r.classification?.nextAction, !next.isEmpty {
                            LabeledContent("Next", value: next)
                        }
                        Text(r.updated != nil
                             ? "Updated \(r.updated?.company ?? "") → \(r.updated?.status ?? "")"
                             : "No matching application found")
                        .font(.subheadline)
                        .foregroundStyle(r.updated != nil ? Palette.brand : .secondary)
                    }
                    .listRowBackground(Palette.surface.opacity(0.6))
                }
            }
            .scrollContentBackground(.hidden)
            .background(ScreenBackground())
            .navigationTitle("Inbox")
        }
        .onAppear { if vm.stats.jobs == 0 { vm.loadOverview() } }
    }
}
