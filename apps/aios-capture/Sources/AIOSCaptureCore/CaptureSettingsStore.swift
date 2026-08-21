import Foundation
import Security

public struct CaptureSettings: Sendable, Equatable {
    public var baseURL: URL
    public var username: String
    public var password: String

    public init(baseURL: URL, username: String, password: String) {
        self.baseURL = baseURL
        self.username = username
        self.password = password
    }

    public var isConfigured: Bool {
        !username.isEmpty && !password.isEmpty
    }

    public func makeConfiguration(captureInterface: String = "watchos_v1") -> CaptureConfiguration {
        CaptureConfiguration(
            baseURL: baseURL,
            username: username,
            password: password,
            captureInterface: captureInterface
        )
    }
}

public protocol CaptureSettingsStore: Sendable {
    func load() throws -> CaptureSettings?
    func save(_ settings: CaptureSettings) throws
    func clear() throws
}

public enum CaptureSettingsStoreError: LocalizedError {
    case keychain(OSStatus)

    public var errorDescription: String? {
        switch self {
        case .keychain(let status):
            return "Keychain error (\(status))."
        }
    }
}

/// Keychain-backed settings for watch-first v1.
/// Later: swap the access group for an App Group shared with an iOS companion app.
public struct KeychainCaptureSettingsStore: CaptureSettingsStore {
    public static let service = "com.aios.capture.settings"
    public static let account = "default"

    private let service: String
    private let account: String
    private let accessGroup: String?

    public init(
        service: String = KeychainCaptureSettingsStore.service,
        account: String = KeychainCaptureSettingsStore.account,
        accessGroup: String? = nil
    ) {
        self.service = service
        self.account = account
        self.accessGroup = accessGroup
    }

    public func load() throws -> CaptureSettings? {
        var query = baseQuery()
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne

        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)
        if status == errSecItemNotFound {
            return nil
        }
        guard status == errSecSuccess else {
            throw CaptureSettingsStoreError.keychain(status)
        }

        guard
            let data = item as? Data,
            let decoded = try? JSONDecoder().decode(StoredCaptureSettings.self, from: data)
        else {
            return nil
        }

        return CaptureSettings(
            baseURL: decoded.baseURL,
            username: decoded.username,
            password: decoded.password
        )
    }

    public func save(_ settings: CaptureSettings) throws {
        let payload = StoredCaptureSettings(settings)
        let data = try JSONEncoder().encode(payload)

        if (try? load()) != nil {
            let query = baseQuery()
            let attributes = [kSecValueData as String: data]
            let status = SecItemUpdate(query as CFDictionary, attributes as CFDictionary)
            guard status == errSecSuccess else {
                throw CaptureSettingsStoreError.keychain(status)
            }
            return
        }

        var query = baseQuery()
        query[kSecValueData as String] = data
        query[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlock

        let status = SecItemAdd(query as CFDictionary, nil)
        guard status == errSecSuccess else {
            throw CaptureSettingsStoreError.keychain(status)
        }
    }

    public func clear() throws {
        let status = SecItemDelete(baseQuery() as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw CaptureSettingsStoreError.keychain(status)
        }
    }

    private func baseQuery() -> [String: Any] {
        var query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
        ]
        if let accessGroup {
            query[kSecAttrAccessGroup as String] = accessGroup
        }
        return query
    }
}

private struct StoredCaptureSettings: Codable {
    var baseURL: URL
    var username: String
    var password: String

    init(_ settings: CaptureSettings) {
        baseURL = settings.baseURL
        username = settings.username
        password = settings.password
    }
}
