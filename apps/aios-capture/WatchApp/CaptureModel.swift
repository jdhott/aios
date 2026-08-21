import AIOSCaptureCore
import Foundation

@MainActor
final class CaptureModel: ObservableObject {
    @Published var draftText = "• "
    @Published var statusMessage = ""
    @Published var isSending = false
    @Published var needsSetup = false

    @Published var setupBaseURL = CaptureConfiguration.defaultProductionBaseURL.absoluteString
    @Published var setupUsername = "aios"
    @Published var setupPassword = ""

    private let settingsStore: any CaptureSettingsStore

    init(settingsStore: (any CaptureSettingsStore)? = nil) {
        self.settingsStore = settingsStore ?? KeychainCaptureSettingsStore()
        refreshSetupState()
    }

    func refreshSetupState() {
        do {
            needsSetup = (try settingsStore.load()?.isConfigured != true)
        } catch {
            needsSetup = true
            statusMessage = error.localizedDescription
        }
    }

    func saveSetup() {
        guard let baseURL = URL(string: setupBaseURL.trimmingCharacters(in: .whitespacesAndNewlines)) else {
            statusMessage = "Enter a valid AIOS web URL."
            return
        }

        let settings = CaptureSettings(
            baseURL: baseURL,
            username: setupUsername.trimmingCharacters(in: .whitespacesAndNewlines),
            password: setupPassword
        )

        guard settings.isConfigured else {
            statusMessage = "Enter your AIOS username and password."
            return
        }

        do {
            try settingsStore.save(settings)
            needsSetup = false
            statusMessage = "Saved."
        } catch {
            statusMessage = error.localizedDescription
        }
    }

    func send() async {
        guard !isSending else { return }

        let normalized = BrainDumpFormatter.normalizedDraft(draftText)
        draftText = normalized

        guard BrainDumpFormatter.hasMeaningfulCaptureText(normalized) else {
            statusMessage = CaptureClientError.emptyInput.localizedDescription
            return
        }

        guard let settings = try? settingsStore.load(), settings.isConfigured else {
            needsSetup = true
            statusMessage = "Set up AIOS sign-in first."
            return
        }

        isSending = true
        statusMessage = "Sending…"
        defer { isSending = false }

        do {
            let client = CaptureClient(configuration: settings.makeConfiguration())
            let result = try await client.submit(text: normalized)
            draftText = "• "
            statusMessage = result.sent == 1 ? "1 item sent." : "\(result.sent) items sent."
        } catch {
            statusMessage = error.localizedDescription
        }
    }
}
