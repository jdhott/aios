import Foundation

public struct CaptureService: Sendable {
    private let settingsStore: any CaptureSettingsStore
    private let urlSession: URLSession

    public init(
        settingsStore: any CaptureSettingsStore,
        urlSession: URLSession = .shared
    ) {
        self.settingsStore = settingsStore
        self.urlSession = urlSession
    }

    public func submit(
        text: String,
        captureInterface: String = "watchos_v1"
    ) async throws -> CaptureSubmitResult {
        guard let settings = try settingsStore.load(), settings.isConfigured else {
            throw CaptureClientError.notConfigured
        }

        let normalized = BrainDumpFormatter.normalizedDraft(text)
        guard BrainDumpFormatter.hasMeaningfulCaptureText(normalized) else {
            throw CaptureClientError.emptyInput
        }

        let client = CaptureClient(
            configuration: settings.makeConfiguration(captureInterface: captureInterface),
            urlSession: urlSession
        )
        return try await client.submit(text: normalized)
    }
}
