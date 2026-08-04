import SwiftUI

@main
struct JobHunterApp: App {
    @StateObject private var vm = AppViewModel()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(vm)
                .tint(Palette.brand)
        }
    }
}
