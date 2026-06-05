import Foundation

enum ReportArchiveError: LocalizedError {
    case noReports
    case zipFailed

    var errorDescription: String? {
        switch self {
        case .noReports:
            return "No saved reports were found to archive."
        case .zipFailed:
            return "Could not create the archive zip."
        }
    }
}

/// Zip many scan run folders into one archive (for backup before delete).
enum ReportArchiveExporter {
    static func defaultArchiveName() -> String {
        let stamp = DateFormatter.archiveStamp.string(from: Date())
        return "WebAudit-all-reports-\(stamp).zip"
    }

    static func createArchive(from reportDirs: [URL]) throws -> URL {
        guard !reportDirs.isEmpty else { throw ReportArchiveError.noReports }

        let fm = FileManager.default
        let staging = fm.temporaryDirectory
            .appendingPathComponent("webaudit-archive-\(UUID().uuidString)", isDirectory: true)
        try fm.createDirectory(at: staging, withIntermediateDirectories: true)
        defer { try? fm.removeItem(at: staging) }

        for dir in reportDirs {
            let folderName = uniqueFolderName(for: dir, used: staging)
            try fm.copyItem(at: dir, to: staging.appendingPathComponent(folderName, isDirectory: true))
        }

        let readme = staging.appendingPathComponent("README-ARCHIVE.txt")
        try archiveReadme(reportCount: reportDirs.count).write(to: readme, atomically: true, encoding: .utf8)

        let zipURL = fm.temporaryDirectory.appendingPathComponent(defaultArchiveName())
        if fm.fileExists(atPath: zipURL.path) {
            try fm.removeItem(at: zipURL)
        }
        try zipDirectory(staging, to: zipURL)
        return zipURL
    }

    private static func archiveReadme(reportCount: Int) -> String {
        """
        Web Audit — archived reports
        ============================

        This zip contains \(reportCount) saved scan folder\(reportCount == 1 ? "" : "s") from ~/Documents/WebAudit/.

        Each subfolder has report.html and report.css (when present). Open report.html in a browser
        to view the full report. Keep each pair in the same folder.

        Created: \(DateFormatter.archiveReadme.string(from: Date()))
        """
    }

    private static func uniqueFolderName(for dir: URL, used staging: URL) -> String {
        let base = dir.lastPathComponent
        var candidate = base
        var suffix = 2
        let fm = FileManager.default
        while fm.fileExists(atPath: staging.appendingPathComponent(candidate).path) {
            candidate = "\(base)-\(suffix)"
            suffix += 1
        }
        return candidate
    }

    private static func zipDirectory(_ directory: URL, to zipURL: URL) throws {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/zip")
        process.currentDirectoryURL = directory
        process.arguments = ["-rq", zipURL.path, "."]
        try process.run()
        process.waitUntilExit()
        guard process.terminationStatus == 0 else {
            throw ReportArchiveError.zipFailed
        }
    }
}

private extension DateFormatter {
    static let archiveStamp: DateFormatter = {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.timeZone = TimeZone.current
        f.dateFormat = "yyyy-MM-dd_HHmmss"
        return f
    }()

    static let archiveReadme: DateFormatter = {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.timeZone = TimeZone.current
        f.dateStyle = .medium
        f.timeStyle = .medium
        return f
    }()
}
