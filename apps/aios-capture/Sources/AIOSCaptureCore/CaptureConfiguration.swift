import Foundation

public struct CaptureConfiguration: Sendable, Equatable {
    public var baseURL: URL
    public var username: String
    public let password: String
    public var captureInterface: String

    public init(
        baseURL: URL,
        username: String,
        password: String,
        captureInterface: String = "watchos_v1"
    ) {
        self.baseURL = baseURL
        self.username = username
        self.password = password
        self.captureInterface = captureInterface
    }

    public static let defaultProductionBaseURL = URL(
        string: "https://aios-web-fcfzjohmmq-nn.a.run.app"
    )!

    public var submitURL: URL {
        baseURL.appendingPathComponent("capture/submit")
    }
}
