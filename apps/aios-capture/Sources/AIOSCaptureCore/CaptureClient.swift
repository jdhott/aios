import Foundation

public struct CaptureSubmitResult: Sendable, Equatable {
    public let sent: Int
}

public enum CaptureClientError: LocalizedError, Sendable, Equatable {
    case emptyInput
    case invalidResponse
    case unauthorized
    case server(message: String)
    case transport(String)

    public var errorDescription: String? {
        switch self {
        case .emptyInput:
            return "Enter something to capture."
        case .invalidResponse:
            return "AIOS returned an unexpected response."
        case .unauthorized:
            return "Sign-in failed. Check your AIOS username and password."
        case .server(let message):
            return message
        case .transport(let message):
            return message
        }
    }
}

public struct CaptureClient: Sendable {
    private let configuration: CaptureConfiguration
    private let urlSession: URLSession

    public init(configuration: CaptureConfiguration, urlSession: URLSession = .shared) {
        self.configuration = configuration
        self.urlSession = urlSession
    }

    public func submit(text: String) async throws -> CaptureSubmitResult {
        let lines = BrainDumpFormatter.split(text)
        guard !lines.isEmpty else {
            throw CaptureClientError.emptyInput
        }

        var request = URLRequest(url: configuration.submitURL)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(basicAuthHeaderValue(), forHTTPHeaderField: "Authorization")

        let payload: [String: String] = [
            "text": text,
            "capture_interface": configuration.captureInterface,
        ]
        request.httpBody = try JSONSerialization.data(withJSONObject: payload)

        let (data, response): (Data, URLResponse)
        do {
            (data, response) = try await urlSession.data(for: request)
        } catch {
            throw CaptureClientError.transport(error.localizedDescription)
        }

        guard let http = response as? HTTPURLResponse else {
            throw CaptureClientError.invalidResponse
        }

        switch http.statusCode {
        case 200:
            break
        case 401:
            throw CaptureClientError.unauthorized
        default:
            throw CaptureClientError.server(message: parseErrorMessage(from: data) ?? "Capture failed (\(http.statusCode)).")
        }

        guard
            let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
            (object["ok"] as? Bool) == true
        else {
            throw CaptureClientError.invalidResponse
        }

        let sent = object["sent"] as? Int ?? lines.count
        return CaptureSubmitResult(sent: sent)
    }

    private func basicAuthHeaderValue() -> String {
        let credentials = "\(configuration.username):\(configuration.password)"
        let encoded = Data(credentials.utf8).base64EncodedString()
        return "Basic \(encoded)"
    }

    private func parseErrorMessage(from data: Data) -> String? {
        guard
            let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
            let detail = object["detail"] as? String,
            !detail.isEmpty
        else {
            return nil
        }
        return detail
    }
}
