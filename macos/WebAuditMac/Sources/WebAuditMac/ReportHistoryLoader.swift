import Foundation

/// Discovers completed scan folders under ``ScanRunner/outputRoot``.
enum ReportHistoryLoader {
    static let logsFolderName = ScanFailureLogWriter.logsFolderName
    static let lastRunMarkerName = ".webaudit-last-run"
    static let maxLoadedScans = 100

    static func loadScans(from root: URL = ScanRunner.outputRoot) -> [CompletedScan] {
        let runner = ScanRunner()
        let summaryLoader: (URL) -> String? = { runner.loadVerdictSummary(from: $0) }
        let fm = FileManager.default
        guard let entries = try? fm.contentsOfDirectory(
            at: root,
            includingPropertiesForKeys: [.isDirectoryKey, .contentModificationDateKey],
            options: [.skipsHiddenFiles]
        ) else {
            return []
        }

        var scans: [CompletedScan] = []
        for entry in entries {
            guard isReportDirectory(entry) else { continue }
            guard let scan = completedScan(from: entry, summaryLoader: summaryLoader) else { continue }
            scans.append(scan)
        }

        scans.sort { $0.completedAt > $1.completedAt }
        if scans.count > maxLoadedScans {
            scans = Array(scans.prefix(maxLoadedScans))
        }
        return scans
    }

    static func listReportDirectories(from root: URL = ScanRunner.outputRoot) -> [URL] {
        let fm = FileManager.default
        guard let entries = try? fm.contentsOfDirectory(
            at: root,
            includingPropertiesForKeys: [.isDirectoryKey],
            options: [.skipsHiddenFiles]
        ) else {
            return []
        }
        return entries.filter { isReportDirectory($0) }
    }

    static func isReportDirectory(_ url: URL) -> Bool {
        var isDir: ObjCBool = false
        guard FileManager.default.fileExists(atPath: url.path, isDirectory: &isDir), isDir.boolValue else {
            return false
        }
        let name = url.lastPathComponent
        if name == logsFolderName { return false }
        let html = url.appendingPathComponent("report.html")
        let json = url.appendingPathComponent("audit_run.json")
        return FileManager.default.fileExists(atPath: html.path)
            || FileManager.default.fileExists(atPath: json.path)
    }

    private static func completedScan(
        from runDir: URL,
        summaryLoader: (URL) -> String?
    ) -> CompletedScan? {
        let snapshot = ScanReportSnapshot.load(from: runDir)
        let summary = summaryLoader(runDir)

        let url: String
        if let snapshot, !snapshot.targetURL.isEmpty {
            url = snapshot.targetURL
        } else if let inferred = inferURL(from: runDir) {
            url = inferred
        } else {
            url = "https://\(runDir.lastPathComponent)"
        }

        let completedAt: Date
        if let snapshot, let parsed = ScanReportSnapshot.parseDate(snapshot.scannedAt) {
            completedAt = parsed
        } else if let mod = try? runDir.resourceValues(forKeys: [.contentModificationDateKey]).contentModificationDate {
            completedAt = mod
        } else {
            completedAt = .distantPast
        }

        return CompletedScan(
            url: url,
            reportDir: runDir,
            summary: summary,
            completedAt: completedAt,
            verdict: snapshot?.verdict ?? "NEEDS_ATTENTION",
            hygiene: snapshot?.hygiene ?? 0,
            exposure: snapshot?.exposure ?? 0,
            hostLabel: snapshot?.hostLabel ?? URL(string: url)?.host ?? runDir.lastPathComponent
        )
    }

    private static func inferURL(from runDir: URL) -> String? {
        let jsonURL = runDir.appendingPathComponent("audit_run.json")
        guard let data = try? Data(contentsOf: jsonURL),
              let root = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let meta = root["meta"] as? [String: Any],
              let target = meta["target_url"] as? String,
              !target.isEmpty else {
            return nil
        }
        return target
    }
}
