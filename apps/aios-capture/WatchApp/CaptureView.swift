import AIOSCaptureCore
import SwiftUI

struct CaptureView: View {
    @ObservedObject var model: CaptureModel

    var body: some View {
        NavigationStack {
            Group {
                if model.needsSetup {
                    SetupView(model: model)
                } else {
                    CaptureEditorView(model: model)
                }
            }
            .navigationTitle("Brain Dump")
        }
    }
}

private struct CaptureEditorView: View {
    @ObservedObject var model: CaptureModel
    @FocusState private var isFocused: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("One task per line.")
                .font(.caption2)
                .foregroundStyle(.secondary)

            TextField("Capture", text: $model.draftText, axis: .vertical)
                .lineLimit(3...8)
                .focused($isFocused)

            if !model.statusMessage.isEmpty {
                Text(model.statusMessage)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }

            HStack {
                Button("Clear") {
                    model.draftText = "• "
                    model.statusMessage = ""
                    isFocused = true
                }
                .buttonStyle(.bordered)
                .disabled(model.isSending)

                Spacer()

                Button(model.isSending ? "Sending…" : "Send") {
                    Task { await model.send() }
                }
                .buttonStyle(.borderedProminent)
                .disabled(model.isSending)
            }
        }
        .padding(.horizontal, 4)
        .onAppear { isFocused = true }
    }
}

private struct SetupView: View {
    @ObservedObject var model: CaptureModel

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 10) {
                Text("Sign in once. Credentials stay in Keychain on this watch.")
                    .font(.caption2)
                    .foregroundStyle(.secondary)

                TextField("Web URL", text: $model.setupBaseURL)
                TextField("Username", text: $model.setupUsername)
                SecureField("Password", text: $model.setupPassword)

                Button("Save") {
                    model.saveSetup()
                }
                .buttonStyle(.borderedProminent)

                if !model.statusMessage.isEmpty {
                    Text(model.statusMessage)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
            }
        }
    }
}

#Preview {
    CaptureView(model: CaptureModel(settingsStore: PreviewSettingsStore()))
}

private struct PreviewSettingsStore: CaptureSettingsStore {
    func load() throws -> CaptureSettings? {
        CaptureSettings(
            baseURL: CaptureConfiguration.defaultProductionBaseURL,
            username: "aios",
            password: "preview"
        )
    }

    func save(_ settings: CaptureSettings) throws {}
    func clear() throws {}
}
