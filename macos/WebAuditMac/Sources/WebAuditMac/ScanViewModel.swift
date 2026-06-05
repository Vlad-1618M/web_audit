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

    let runner = ScanRunner()
    private var scanTask: Task<Void, Never>?
    private var shareStagingFiles: [URL] = []

    init() {
        engineInfo = runner.detectEngine()
        NotificationCenter.default.addObserver(
            forName: NSApplication.willTerminateNotification,
            object: nil,
            queue: .main
        ) { [weak self] _ in
            Task { @MainActor in
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
        phase = .scanning
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
                recordCompletedScan(url: trimmed, reportDir: runDir, summary: summary)
                phase = .complete(reportDir: runDir, summary: summary)
            } catch is CancellationError {
                phase = .ready
            } catch {
                phase = .error(message: error.localizedDescription)
            }
        }
    }

    func cancelScan() {
        runner.terminateScan()
        scanTask?.cancel()
        phase = .ready
        logLines.append("Scan cancelled.")
    }

    func resetForAnotherScan() {
        phase = .ready
        logLines = []
        urlText = ""
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

    private func recordCompletedScan(url: String, reportDir: URL, summary: String?) {
        let snapshot = ScanReportSnapshot.load(from: reportDir)
        let completedAt = snapshot.flatMap { ScanReportSnapshot.parseDate($0.scannedAt) } ?? Date()
        let scan = CompletedScan(
            url: url,
            reportDir: reportDir,
            summary: summary,
            completedAt: completedAt,
            verdict: snapshot?.verdict ?? "NEEDS_ATTENTION",
            hygiene: snapshot?.hygiene ?? 0,
            exposure: snapshot?.exposure ?? 0,
            hostLabel: snapshot?.hostLabel ?? URL(string: url)?.host ?? url
        )
        completedScans.removeAll { $0.reportDir == reportDir }
        completedScans.insert(scan, at: 0)
        if completedScans.count > 10 {
            completedScans = Array(completedScans.prefix(10))
        }
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
