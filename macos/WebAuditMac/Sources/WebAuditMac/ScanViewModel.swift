import AppKit
import Foundation
import UniformTypeIdentifiers

@MainActor
final class ScanViewModel: ObservableObject {
    @Published var urlText = ""
    @Published var phase: ScanPhase = .ready
    @Published var logLines: [String] = []
    @Published var showHelp = false
    @Published var showAdvanced = false
    @Published var shareContext: ShareReportContext?
    @Published private(set) var engineInfo: ScanEngineInfo
    @Published private(set) var completedScans: [CompletedScan] = []
    @Published private(set) var activeReport: ScanReportSnapshot?
    @Published private(set) var failureLogURL: URL?
    @Published var statusMessage: String?

    let runner = ScanRunner()
    private var scanTask: Task<Void, Never>?
    private var shareStagingFiles: [URL] = []
    private var scanStartedAt: Date?

    var lastSavedScan: CompletedScan? { completedScans.first }

    init() {
        engineInfo = runner.detectEngine()
        completedScans = ReportHistoryLoader.loadScans()
        NotificationCenter.default.addObserver(
            forName: NSApplication.willTerminateNotification,
            object: nil,
            queue: .main
        ) { [weak self] _ in
            Task { @MainActor [weak self] in
                self?.shutdown()
            }
        }
    }

    func shutdown() {
        runner.terminateScan()
        scanTask?.cancel()
    }

    func quitApp() {
        shutdown()
        NSApplication.shared.terminate(nil)
    }

    func refreshEngineInfo() {
        engineInfo = runner.detectEngine()
    }

    var isScanning: Bool {
        if case .scanning = phase { return true }
        return false
    }

    var reportHTML: URL? {
        guard case .complete(let dir, _) = phase else { return nil }
        let html = dir.appendingPathComponent("report.html")
        return FileManager.default.fileExists(atPath: html.path) ? html : nil
    }

    var reportDirectory: URL? {
        guard case .complete(let dir, _) = phase else { return nil }
        return dir
    }

    func startScan() {
        let trimmed = urlText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard isValidURL(trimmed) else {
            phase = .error(message: "Paste the full website address starting with https:// — for example https://your-site.com")
            return
        }

        scanTask?.cancel()
        logLines = []
        failureLogURL = nil
        phase = .scanning
        scanStartedAt = Date()
        logLines.append("Starting scan for \(trimmed)…")

        scanTask = Task {
            do {
                let runDir = try await runner.runScan(url: trimmed) { [weak self] line in
                    Task { @MainActor in
                        self?.logLines.append(line)
                    }
                }
                let summary = runner.loadVerdictSummary(from: runDir)
                loadReport(from: runDir, scannedURL: trimmed)
                refreshSavedScans()
                phase = .complete(reportDir: runDir, summary: summary)
                failureLogURL = nil
            } catch is CancellationError {
                runner.terminateScan()
                phase = .ready
                failureLogURL = nil
            } catch {
                runner.terminateScan()
                let message = error.localizedDescription
                failureLogURL = recordScanFailure(
                    url: trimmed,
                    message: message,
                    startedAt: scanStartedAt ?? Date()
                )
                phase = .error(message: message)
            }
        }
    }

    func cancelScan() {
        runner.terminateScan()
        scanTask?.cancel()
        phase = .ready
        logLines = []
        failureLogURL = nil
    }

    /// Leave the error screen and return to the home page (keeps the URL for editing).
    func abortFromError() {
        runner.terminateScan()
        scanTask?.cancel()
        phase = .ready
        logLines = []
        failureLogURL = nil
    }

    /// Home screen with saved reports list — keeps history, does not clear URL.
    func returnToHome() {
        phase = .ready
        logLines = []
        failureLogURL = nil
        activeReport = nil
    }

    func resetForAnotherScan() {
        phase = .ready
        logLines = []
        failureLogURL = nil
        urlText = ""
        activeReport = nil
    }

    func refreshSavedScans() {
        completedScans = ReportHistoryLoader.loadScans()
    }

    func revealFailureLogInFinder() {
        guard let failureLogURL else { return }
        NSWorkspace.shared.activateFileViewerSelecting([failureLogURL])
    }

    func copyFailureLogPathToPasteboard() {
        guard let failureLogURL else { return }
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(failureLogURL.path, forType: .string)
    }

    @discardableResult
    private func recordScanFailure(url: String, message: String, startedAt: Date) -> URL? {
        let context = ScanFailureLogWriter.Context(
            scannedURL: url,
            errorMessage: message,
            logLines: logLines,
            engine: engineInfo,
            startedAt: startedAt,
            failedAt: Date()
        )
        if let fileURL = try? ScanFailureLogWriter.write(context) {
            logLines.append("Diagnostic log saved: \(fileURL.path)")
            return fileURL
        }
        logLines.append("Could not save diagnostic log under ~/Documents/WebAudit/Logs/")
        return nil
    }

    func reopenScan(_ scan: CompletedScan) {
        urlText = scan.url
        loadReport(from: scan.reportDir, scannedURL: scan.url)
        phase = .complete(reportDir: scan.reportDir, summary: scan.summary)
    }

    func loadReport(from runDir: URL, scannedURL: String) {
        if let snapshot = ScanReportSnapshot.load(from: runDir) {
            activeReport = snapshot
            return
        }
        activeReport = ScanReportSnapshot.fallback(
            url: scannedURL,
            summary: runner.loadVerdictSummary(from: runDir),
            runDir: runDir
        )
    }

    func zipAllSavedReports() {
        let dirs = ReportHistoryLoader.listReportDirectories()
        guard !dirs.isEmpty else {
            statusMessage = "No saved reports to archive."
            return
        }

        let panel = NSSavePanel()
        panel.title = "Archive all saved reports"
        panel.message = "Creates one zip with every scan folder from ~/Documents/WebAudit/. Use this before deleting reports to free disk space."
        panel.nameFieldStringValue = ReportArchiveExporter.defaultArchiveName()
        panel.allowedContentTypes = [.zip]
        panel.canCreateDirectories = true
        guard panel.runModal() == .OK, let dest = panel.url else { return }

        do {
            let zipURL = try ReportArchiveExporter.createArchive(from: dirs)
            defer { try? FileManager.default.removeItem(at: zipURL) }
            let fm = FileManager.default
            if fm.fileExists(atPath: dest.path) {
                try fm.removeItem(at: dest)
            }
            try fm.copyItem(at: zipURL, to: dest)
            statusMessage = "Archived \(dirs.count) report\(dirs.count == 1 ? "" : "s") to \(dest.lastPathComponent)."
            NSWorkspace.shared.activateFileViewerSelecting([dest])
        } catch {
            statusMessage = "Could not create archive: \(error.localizedDescription)"
        }
    }

    func deleteAllSavedReports() {
        let dirs = ReportHistoryLoader.listReportDirectories()
        let fm = FileManager.default
        for dir in dirs {
            try? fm.removeItem(at: dir)
        }
        completedScans = []
        activeReport = nil
        if case .complete = phase {
            phase = .ready
        }
        try? fm.removeItem(at: ScanRunner.outputRoot.appendingPathComponent(".webaudit-last-run"))
        statusMessage = dirs.isEmpty
            ? "No saved reports to delete."
            : "Deleted \(dirs.count) saved report\(dirs.count == 1 ? "" : "s"). Failure logs were kept."
    }

    func otherSessionScans(excluding reportDir: URL) -> [CompletedScan] {
        completedScans.filter { $0.reportDir != reportDir }
    }

    func openReportInBrowser() {
        guard let html = reportHTML else { return }
        NSWorkspace.shared.open(html)
    }

    func revealInFinder() {
        guard let dir = reportDirectory, let html = reportHTML else { return }
        var items = [html]
        let css = dir.appendingPathComponent("report.css")
        if FileManager.default.fileExists(atPath: css.path) {
            items.append(css)
        }
        NSWorkspace.shared.activateFileViewerSelecting(items)
    }

    func downloadReport() {
        guard let runDir = reportDirectory, reportHTML != nil else { return }
        let hostLabel = activeReport?.hostLabel ?? runDir.lastPathComponent

        let panel = NSSavePanel()
        panel.title = "Save report to share"
        panel.message = "Creates a zip with report.html, report.css, and instructions. Unzip, then double-click report.html."
        panel.nameFieldStringValue = ReportBundleExporter.defaultZipName(hostLabel: hostLabel)
        panel.allowedContentTypes = [.zip]
        panel.canCreateDirectories = true
        guard panel.runModal() == .OK, let dest = panel.url else { return }

        do {
            let zipURL = try ReportBundleExporter.createShareableZip(from: runDir, hostLabel: hostLabel)
            defer { try? FileManager.default.removeItem(at: zipURL) }
            let fm = FileManager.default
            if fm.fileExists(atPath: dest.path) {
                try fm.removeItem(at: dest)
            }
            try fm.copyItem(at: zipURL, to: dest)
            NSWorkspace.shared.activateFileViewerSelecting([dest])
        } catch {
            phase = .error(message: "Could not save report: \(error.localizedDescription)")
        }
    }

    func shareReport() {
        guard let runDir = reportDirectory, reportHTML != nil else { return }
        let hostLabel = activeReport?.hostLabel ?? runDir.lastPathComponent

        do {
            clearShareStaging()
            let zipURL = try ReportBundleExporter.createShareableZip(from: runDir, hostLabel: hostLabel)
            shareStagingFiles.append(zipURL)
            shareContext = ShareReportContext(zipURL: zipURL, hostLabel: hostLabel)
        } catch {
            phase = .error(message: "Could not prepare report to share: \(error.localizedDescription)")
        }
    }

    func dismissShareSheet() {
        shareContext = nil
        clearShareStaging()
    }

    private func clearShareStaging() {
        for old in shareStagingFiles {
            try? FileManager.default.removeItem(at: old)
        }
        shareStagingFiles.removeAll()
    }

    private func isValidURL(_ raw: String) -> Bool {
        guard let components = URLComponents(string: raw),
              let scheme = components.scheme?.lowercased(),
              scheme == "https" || scheme == "http",
              let host = components.host, !host.isEmpty else {
            return false
        }
        return true
    }
}
