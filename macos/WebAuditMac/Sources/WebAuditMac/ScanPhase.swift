import Foundation

struct CompletedScan: Equatable, Identifiable {
    let url: String
    let reportDir: URL
    let summary: String?
    let completedAt: Date
    let verdict: String
    let hygiene: Int
    let exposure: Int
    let hostLabel: String

    var id: String { reportDir.path }

    var verdictLabel: String {
        switch verdict {
        case "PASS": return "Pass"
        case "NEEDS_ATTENTION": return "Needs attention"
        case "AT_RISK": return "At risk"
        default: return verdict.replacingOccurrences(of: "_", with: " ").capitalized
        }
    }

    var verdictTone: ReportTone { ReportTone.forVerdict(verdict) }

    var displayTitle: String {
        if let summary { return "\(hostLabel) — \(summary)" }
        return hostLabel
    }
}

enum ScanPhase: Equatable {
    case ready
    case scanning
    case complete(reportDir: URL, summary: String?)
    case error(message: String)
}

struct ScanEngineInfo: Equatable {
    enum Kind: String {
        case webauditDocker = "webaudit-docker"
        case webauditCLI = "webaudit"
        case none = "not found"
    }

    let kind: Kind
    let path: String
    let detail: String
}
