import Foundation

enum ReportBundleError: LocalizedError {
    case missingHTML
    case zipFailed

    var errorDescription: String? {
        switch self {
        case .missingHTML:
            return "report.html was not found in the scan folder."
        case .zipFailed:
            return "Could not create a zip archive for the report."
        }
    }
}

/// Packages report.html + report.css (+ short instructions) so shared copies render correctly.
enum ReportBundleExporter {
    static func defaultZipName(hostLabel: String) -> String {
        let safe = hostLabel
            .replacingOccurrences(of: "/", with: "-")
            .replacingOccurrences(of: ":", with: "-")
        return "WebAudit-\(safe)-report.zip"
    }

    static func readmeText() -> String {
        """
        Web Audit report package

        1. Unzip this folder (double-click the .zip if needed).
        2. Keep report.html and report.css in the SAME folder.
        3. Double-click report.html to open the full report in your browser.

        Do not move report.html without report.css — the page needs both files.

        You can email this whole zip to your developer or hosting company.
        """
    }

    /// Builds a zip in the system temp directory. Caller may delete when done.
    static func createShareableZip(from runDir: URL, hostLabel: String) throws -> URL {
        let fm = FileManager.default
        let html = runDir.appendingPathComponent("report.html")
        guard fm.fileExists(atPath: html.path) else {
            throw ReportBundleError.missingHTML
        }

        let staging = fm.temporaryDirectory
            .appendingPathComponent("webaudit-export-\(UUID().uuidString)", isDirectory: true)
        try fm.createDirectory(at: staging, withIntermediateDirectories: true)
        defer { try? fm.removeItem(at: staging) }

        try fm.copyItem(at: html, to: staging.appendingPathComponent("report.html"))

        let css = runDir.appendingPathComponent("report.css")
        if fm.fileExists(atPath: css.path) {
            try fm.copyItem(at: css, to: staging.appendingPathComponent("report.css"))
        }

        let readme = staging.appendingPathComponent("HOW-TO-OPEN.txt")
        try readmeText().write(to: readme, atomically: true, encoding: .utf8)

        let zipURL = fm.temporaryDirectory.appendingPathComponent(defaultZipName(hostLabel: hostLabel))
        if fm.fileExists(atPath: zipURL.path) {
            try fm.removeItem(at: zipURL)
        }

        try zipDirectory(staging, to: zipURL)
        return zipURL
    }

    private static func zipDirectory(_ directory: URL, to zipURL: URL) throws {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/zip")
        process.currentDirectoryURL = directory
        process.arguments = ["-rq", zipURL.path, "."]
        try process.run()
        process.waitUntilExit()
        guard process.terminationStatus == 0 else {
            throw ReportBundleError.zipFailed
        }
    }
}
