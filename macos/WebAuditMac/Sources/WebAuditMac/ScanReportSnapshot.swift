import Foundation

enum MetricChipTone: String, Equatable {
    case critical, high, medium, verify, expected, leak, seo, plugins
}

struct MetricChipSnapshot: Equatable, Identifiable {
    let label: String
    let count: Int
    let tone: MetricChipTone
    let sub: String?

    var id: String { label }
}

struct ActionFindingPreview: Equatable, Identifiable {
    let category: String
    let item: String
    let detail: String
    let severity: String

    var id: String { "\(category)-\(item)-\(detail)" }
}

/// Subset of audit_run.json for the in-app “report ready” screen (mirrors executive HTML report).
struct ScanReportSnapshot: Equatable {
    let targetURL: String
    let hostLabel: String
    let framework: String
    let frameworkConfidence: String
    let scannedAt: String
    let hygiene: Int
    let exposure: Int
    let verdict: String
    let actionFindings: [ActionFindingPreview]
    let actionCount: Int
    let metricChips: [MetricChipSnapshot]
    let pagesScanned: Int?
    let probeCount: Int?
    let certDaysLeft: Int?

    var verdictLabel: String {
        switch verdict {
        case "PASS": return "Pass"
        case "NEEDS_ATTENTION": return "Needs attention"
        case "AT_RISK": return "At risk"
        default: return verdict.replacingOccurrences(of: "_", with: " ").capitalized
        }
    }

    var verdictIcon: String {
        switch verdict {
        case "PASS": return "checkmark.circle.fill"
        case "AT_RISK": return "xmark.octagon.fill"
        default: return "exclamationmark.triangle.fill"
        }
    }

    var summaryLine: String {
        if exposure >= 75 && actionCount > 0 {
            return "No obvious sensitive files were publicly readable, but several standard protections need attention."
        }
        switch verdict {
        case "PASS":
            return "Configuration and exposure look good from this external scan."
        case "AT_RISK":
            return "Critical issues were detected — treat remediation as urgent."
        default:
            return "Review the priority fixes below and share the full report with whoever maintains the site."
        }
    }

    var hygieneBand: ScoreBand { ScoreBand.forHygiene(hygiene) }
    var exposureBand: ScoreBand { ScoreBand.forHygiene(exposure) }
    var verdictTone: ReportTone { ReportTone.forVerdict(verdict) }

    static func load(from runDir: URL) -> ScanReportSnapshot? {
        let jsonURL = runDir.appendingPathComponent("audit_run.json")
        guard let data = try? Data(contentsOf: jsonURL),
              let root = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            return nil
        }

        let meta = root["meta"] as? [String: Any] ?? [:]
        let scores = root["scores"] as? [String: Any] ?? [:]
        let artifacts = root["artifacts"] as? [String: Any] ?? [:]
        let inventory = artifacts["inventory"] as? [String: Any] ?? [:]
        let html = inventory["html"] as? [String: Any] ?? [:]
        let paths = inventory["paths"] as? [String: Any] ?? [:]
        let tls = artifacts["tls"] as? [String: Any] ?? [:]
        let cert = tls["certificate"] as? [String: Any] ?? [:]
        let frameworkObj = inventory["framework"] as? [String: Any] ?? [:]

        let targetURL = meta["target_url"] as? String ?? ""
        let host = URL(string: targetURL)?.host ?? targetURL

        let findingsRaw = root["findings"] as? [[String: Any]] ?? []
        let actionRows: [ActionFindingPreview] = findingsRaw.compactMap { row in
            guard (row["class"] as? String) == "ACTION" else { return nil }
            return ActionFindingPreview(
                category: row["category"] as? String ?? "—",
                item: row["item"] as? String ?? "Issue",
                detail: row["detail"] as? String ?? "",
                severity: row["severity"] as? String ?? "MEDIUM"
            )
        }

        let extensionsArt = artifacts["extensions"] as? [String: Any] ?? artifacts["plugins"] as? [String: Any] ?? [:]
        let extensionList = extensionsArt["extensions"] as? [[String: Any]] ?? []
        let metricChips = Self.buildMetricChips(
            from: findingsRaw,
            extensionDetectedCount: extensionList.count
        )

        return ScanReportSnapshot(
            targetURL: targetURL,
            hostLabel: host,
            framework: meta["framework"] as? String ?? frameworkObj["name"] as? String ?? "auto",
            frameworkConfidence: frameworkObj["confidence"] as? String ?? "—",
            scannedAt: (meta["finished_at"] as? String) ?? (meta["started_at"] as? String) ?? "—",
            hygiene: scores["hygiene"] as? Int ?? 0,
            exposure: scores["exposure"] as? Int ?? 0,
            verdict: scores["verdict"] as? String ?? "NEEDS_ATTENTION",
            actionFindings: Array(actionRows.prefix(6)),
            actionCount: actionRows.count,
            metricChips: metricChips,
            pagesScanned: html["pages_scanned"] as? Int,
            probeCount: paths["probe_count"] as? Int,
            certDaysLeft: cert["days_left"] as? Int
        )
    }

    /// When audit_run.json is missing fields, still show a usable summary screen.
    static func fallback(url: String, summary: String?, runDir: URL) -> ScanReportSnapshot {
        var hygiene = 0
        var exposure = 0
        var verdict = "NEEDS_ATTENTION"
        if let summary {
            let parts = summary.split(separator: "·").map { $0.trimmingCharacters(in: .whitespaces) }
            if let first = parts.first { verdict = first.replacingOccurrences(of: " ", with: "_").uppercased() }
            for part in parts {
                if part.hasPrefix("Hygiene "), let n = Int(part.dropFirst(8)) { hygiene = n }
                if part.hasPrefix("Exposure "), let n = Int(part.dropFirst(9)) { exposure = n }
            }
        }
        let host = URL(string: url)?.host ?? url
        return ScanReportSnapshot(
            targetURL: url,
            hostLabel: host,
            framework: "—",
            frameworkConfidence: "—",
            scannedAt: runDir.lastPathComponent,
            hygiene: hygiene,
            exposure: exposure,
            verdict: verdict,
            actionFindings: [],
            actionCount: 0,
            metricChips: Self.emptyMetricChips(),
            pagesScanned: nil,
            probeCount: nil,
            certDaysLeft: nil
        )
    }

    static func parseDate(_ raw: String) -> Date? {
        let withFraction = ISO8601DateFormatter()
        withFraction.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let date = withFraction.date(from: raw) { return date }
        let plain = ISO8601DateFormatter()
        plain.formatOptions = [.withInternetDateTime]
        return plain.date(from: raw)
    }

    private static let extensionCategories: Set<String> = [
        "PLUGIN", "PLUGIN_VERIFY", "PLUGIN_INFO",
        "PACKAGE", "PACKAGE_VERIFY", "PACKAGE_INFO",
        "GEM", "GEM_VERIFY", "GEM_INFO",
    ]

    static func emptyMetricChips() -> [MetricChipSnapshot] {
        buildMetricChips(from: [], extensionDetectedCount: 0)
    }

    /// Mirrors ``webaudit.render.report_metrics.build_metric_chips``.
    static func buildMetricChips(from findings: [[String: Any]], extensionDetectedCount: Int) -> [MetricChipSnapshot] {
        func cls(_ row: [String: Any]) -> String { (row["class"] as? String ?? "").uppercased() }
        func cat(_ row: [String: Any]) -> String { row["category"] as? String ?? "" }
        func status(_ row: [String: Any]) -> String { (row["status"] as? String ?? "").uppercased() }
        func severity(_ row: [String: Any]) -> String { (row["severity"] as? String ?? "").uppercased() }
        func item(_ row: [String: Any]) -> String { row["item"] as? String ?? "" }

        func countAction(_ sev: String) -> Int {
            findings.filter { cls($0) == "ACTION" && severity($0) == sev }.count
        }

        let verify = findings.filter { cls($0) == "VERIFY" }
        let expected = findings.filter { cls($0) == "EXPECTED" }
        let seo = findings.filter { cat($0) == "SEO_SURFACE" }
        let extensions = findings.filter { extensionCategories.contains(cat($0)) }

        let pluginCount: Int
        if extensionDetectedCount > 0 {
            pluginCount = extensionDetectedCount
        } else {
            pluginCount = extensions.filter {
                status($0) != "NONE_OBSERVED" && !item($0).hasPrefix("Framework ")
            }.count
        }

        let sensitive = findings.filter {
            cat($0) == "PATHS" && cls($0) == "ACTION" && ["OPEN", "LEAKING"].contains(status($0))
        }

        let extStale = extensions.filter { ["STALE", "UNKNOWN", "NO_VERSION"].contains(status($0)) }
        let pluginSub = extStale.isEmpty ? nil : "\(extStale.count) need version review"

        return [
            MetricChipSnapshot(label: "Critical", count: countAction("CRITICAL"), tone: .critical, sub: nil),
            MetricChipSnapshot(label: "High action", count: countAction("HIGH"), tone: .high, sub: nil),
            MetricChipSnapshot(label: "Medium", count: countAction("MEDIUM"), tone: .medium, sub: nil),
            MetricChipSnapshot(label: "Verify", count: verify.count, tone: .verify, sub: nil),
            MetricChipSnapshot(label: "Expected", count: expected.count, tone: .expected, sub: nil),
            MetricChipSnapshot(label: "Sensitive leaks", count: sensitive.count, tone: .leak, sub: nil),
            MetricChipSnapshot(label: "SEO checks", count: seo.count, tone: .seo, sub: nil),
            MetricChipSnapshot(label: "Plugins", count: pluginCount, tone: .plugins, sub: pluginSub),
        ]
    }
}

enum ScoreBand: Equatable {
    case good, fair, poor, critical

    static func forHygiene(_ score: Int) -> ScoreBand {
        if score >= 90 { return .good }
        if score >= 70 { return .fair }
        if score >= 50 { return .poor }
        return .critical
    }
}

enum ReportTone: Equatable {
    case pass, attention, risk

    static func forVerdict(_ verdict: String) -> ReportTone {
        switch verdict {
        case "PASS": return .pass
        case "AT_RISK": return .risk
        default: return .attention
        }
    }
}
