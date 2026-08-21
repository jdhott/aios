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
    private let captureService: CaptureService

    init(settingsStore: (any CaptureSettingsStore)? = nil) {
        let store = settingsStore ?? KeychainCaptureSettingsStore()
        self.settingsStore = store
        self.captureService = CaptureService(settingsStore: store)
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

        isSending = true
        statusMessage = "Sending…"
        defer { isSending = false }

        do {
            let result = try await captureService.submit(text: normalized)
            draftText = "• "
            statusMessage = result.sent == 1 ? "1 item sent." : "\(result.sent) items sent."
        } catch let error as CaptureClientError where error == .notConfigured {
            needsSetup = true
            statusMessage = error.localizedDescription
        } catch {
            statusMessage = error.localizedDescription
        }
    }
}
