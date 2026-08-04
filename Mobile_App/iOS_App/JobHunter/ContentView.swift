import SwiftUI

struct ContentView: View {
    @EnvironmentObject var vm: AppViewModel

    var body: some View {
        TabView {
            OverviewView()
                .tabItem { Label("Overview", systemImage: "square.grid.2x2") }
            MatchesView()
                .tabItem { Label("Matches", systemImage: "briefcase") }
            ApplicationsView()
                .tabItem { Label("Apps", systemImage: "list.bullet.rectangle") }
            InboxView()
                .tabItem { Label("Inbox", systemImage: "envelope") }
            SourcesView()
                .tabItem { Label("Sources", systemImage: "point.3.connected.trianglepath.dotted") }
            ProfileView()
                .tabItem { Label("Profile", systemImage: "person") }
        }
        .tint(Palette.brand)
        .preferredColorScheme(.dark)
        // Surface view-model messages as a transient banner.
        .overlay(alignment: .bottom) {
            if let message = vm.message {
                Text(message)
                    .font(.subheadline)
                    .padding(.horizontal, 16).padding(.vertical, 10)
                    .background(.ultraThinMaterial)
                    .clipShape(Capsule())
                    .overlay(Capsule().strokeBorder(Palette.stroke, lineWidth: 1))
                    .padding(.bottom, 60)
                    .transition(.move(edge: .bottom).combined(with: .opacity))
                    .task {
                        try? await Task.sleep(nanoseconds: 2_600_000_000)
                        withAnimation { vm.message = nil }
                    }
            }
        }
        .animation(.default, value: vm.message)
    }
}
