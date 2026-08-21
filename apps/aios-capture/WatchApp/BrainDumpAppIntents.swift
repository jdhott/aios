import AIOSCaptureCore
import AppIntents

/// Sends dictated or spoken task text straight to AIOS without opening the app.
struct BrainDumpCaptureIntent: AppIntent {
    static var title: LocalizedStringResource = "Brain Dump"
    static var description = IntentDescription("Capture tasks to AIOS.")
    static var openAppWhenRun: Bool = false

    @Parameter(
        title: "Tasks",
        requestValueDialog: IntentDialog("What do you want to add to Brain Dump?")
    )
    var text: String

    static var parameterSummary: some ParameterSummary {
        Summary("Add \(\.$text) to Brain Dump")
    }

    func perform() async throws -> some IntentResult & ProvidesDialog {
        let service = CaptureService(settingsStore: KeychainCaptureSettingsStore())
        let result = try await service.submit(
            text: text,
            captureInterface: "watchos_siri_v1"
        )

        let message = result.sent == 1
            ? "Added 1 item to AIOS."
            : "Added \(result.sent) items to AIOS."
        return .result(dialog: IntentDialog(stringLiteral: message))
    }
}

/// Opens the Brain Dump capture screen when you invoke Siri without task text.
struct OpenBrainDumpIntent: AppIntent {
    static var title: LocalizedStringResource = "Brain Dump"
    static var description = IntentDescription("Open the Brain Dump capture screen.")
    static var openAppWhenRun: Bool = true

    func perform() async throws -> some IntentResult {
        .result()
    }
}

struct AIOSCaptureShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        [
            AppShortcut(
                intent: BrainDumpCaptureIntent(),
                phrases: [
                    "Add \(\.$text) to \(.applicationName)",
                    "Put \(\.$text) in \(.applicationName)",
                ],
                shortTitle: "Brain Dump",
                systemImageName: "text.badge.plus"
            ),
            AppShortcut(
                intent: OpenBrainDumpIntent(),
                phrases: [
                    "Open \(.applicationName)",
                    "Start \(.applicationName)",
                ],
                shortTitle: "Brain Dump",
                systemImageName: "square.and.pencil"
            ),
        ]
    }
}
