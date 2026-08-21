import AIOSCaptureCore
import SwiftUI

@main
struct AIOSCaptureWatchApp: App {
    @StateObject private var model = CaptureModel()

    var body: some Scene {
        WindowGroup {
            CaptureView(model: model)
        }
    }
}
