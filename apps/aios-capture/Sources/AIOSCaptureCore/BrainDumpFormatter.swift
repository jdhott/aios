import Foundation

public enum BrainDumpFormatter {
    /// Split multiline capture text into task lines, mirroring the web Brain Dump splitter.
    public static func split(_ text: String) -> [String] {
        text
            .split(whereSeparator: \.isNewline)
            .map(String.init)
            .map { line in
                var clean = line.trimmingCharacters(in: .whitespacesAndNewlines)
                if let first = clean.first, ["•", "-", "*"].contains(first) {
                    clean = String(clean.dropFirst()).trimmingCharacters(in: .whitespacesAndNewlines)
                }
                return clean
            }
            .filter(hasMeaningfulCaptureText)
    }

    public static func hasMeaningfulCaptureText(_ text: String) -> Bool {
        let clean = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !clean.isEmpty else { return false }
        let stripped = clean
            .replacingOccurrences(of: "•", with: "")
            .replacingOccurrences(of: "-", with: "")
            .replacingOccurrences(of: "*", with: "")
            .trimmingCharacters(in: .whitespacesAndNewlines)
        return !stripped.isEmpty
    }

    public static func normalizedDraft(_ text: String) -> String {
        let lines = text.split(whereSeparator: \.isNewline).map(String.init)
        guard !lines.isEmpty else { return "• " }

        let formatted = lines.map { line -> String in
            let trimmed = line.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !trimmed.isEmpty else { return line }

            let body: String
            if let first = trimmed.first, ["•", "-", "*"].contains(first) {
                body = String(trimmed.dropFirst()).trimmingCharacters(in: .whitespacesAndNewlines)
            } else {
                body = trimmed
            }

            guard !body.isEmpty else { return line }
            let capitalized = body.prefix(1).uppercased() + body.dropFirst()
            return "• \(capitalized)"
        }

        return formatted.joined(separator: "\n")
    }
}
