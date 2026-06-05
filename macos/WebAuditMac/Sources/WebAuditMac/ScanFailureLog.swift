import Foundation

/// Writes a plain-text diagnostic file when a scan fails or the engine errors out.
enum ScanFailureLogWriter {
    static let logsFolderName = "Logs"

    static var defaultLogsDirectory: URL {
        ScanRunner.outputRoot.appendingPathComponent(logsFolderName, isDirectory: true)
    }

    struct Context: Sendable {
        let scannedURL: String
        let errorMessage: String
        let logLines: [String]
        let engine: ScanEngineInfo
        let startedAt: Date
        let failedAt: Date
    }

    static func write(_ context: Context, logsDirectory: URL? = nil) throws -> URL {
        let dir = logsDirectory ?? defaultLogsDirectory
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)

        let hostSlug = filenameHost(from: context.scannedURL)
        let stamp = filenameTimestamp(context.failedAt)
        let fileName = "scan-failure-\(stamp)-\(hostSlug).txt"
        let fileURL = dir.appendingPathComponent(fileName)

        let body = format(context)
        try body.write(to: fileURL, atomically: true, encoding: .utf8)
        return fileURL
    }

    static func format(_ context: Context) -> String {
        let iso = ISO8601DateFormatter()
        iso.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        iso.timeZone = TimeZone.current

        let local = DateFormatter()
        local.locale = Locale(identifier: "en_US_POSIX")
        local.timeZone = TimeZone.current
        local.dateFormat = "yyyy-MM-dd HH:mm:ss zzz"

        var lines: [String] = []
        lines.append("Web Audit Pro — scan failure log")
        lines.append(String(repeating: "=", count: 40))
        lines.append("")
        lines.append("Date and time (local): \(local.string(from: context.failedAt))")
        lines.append("Date and time (UTC):   \(iso.string(from: context.failedAt))")
        lines.append("Scan started:          \(local.string(from: context.startedAt))")
        lines.append("Scanned URL:           \(context.scannedURL)")
        lines.append("")
        lines.append("App version:           \(Bundle.main.appVersionLabel)")
        lines.append("macOS:                 \(ProcessInfo.processInfo.operatingSystemVersionString)")
        lines.append("Engine policy:         \(ScanRunner.enginePolicy().rawValue)")
        lines.append("Engine kind:           \(context.engine.kind.rawValue)")
        lines.append("Engine path:           \(context.engine.path.isEmpty ? "—" : context.engine.path)")
        lines.append("")
        lines.append("Error")
        lines.append("-----")
        lines.append(context.errorMessage)
        lines.append("")
        lines.append("Scan output")
        lines.append("-----------")
        if context.logLines.isEmpty {
            lines.append("(no output captured)")
        } else {
            lines.append(contentsOf: context.logLines)
        }
        lines.append("")
        lines.append("--- end of log ---")
        lines.append("")
        lines.append("Send this file to the developer:")
        lines.append("  \(AppBrand.repoURL.absoluteString)/issues")
        lines.append("")
        return lines.joined(separator: "\n")
    }

    private static func filenameTimestamp(_ date: Date) -> String {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.timeZone = TimeZone.current
        f.dateFormat = "yyyy-MM-dd_HHmmss"
        return f.string(from: date)
    }

    private static func filenameHost(from urlString: String) -> String {
        let host = URL(string: urlString)?.host ?? "unknown-host"
        let slug = host.lowercased()
            .replacingOccurrences(of: ":", with: "-")
            .replacingOccurrences(of: "/", with: "-")
        let safe = slug.filter { $0.isLetter || $0.isNumber || $0 == "." || $0 == "-" }
        return safe.isEmpty ? "unknown-host" : String(safe.prefix(48))
    }
}

private extension Bundle {
    var appVersionLabel: String {
        let short = object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "unknown"
        let build = object(forInfoDictionaryKey: "CFBundleVersion") as? String ?? "?"
        return "\(short) (\(build))"
    }
}
