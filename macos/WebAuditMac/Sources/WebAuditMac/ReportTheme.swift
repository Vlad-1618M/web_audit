import SwiftUI

/// Colors aligned with v2 executive report CSS (--cyan, --lime, --gold, --coral).
enum ReportTheme {
    static let canvas = Color(red: 0.01, green: 0.01, blue: 0.024)
    static let surface = Color(red: 0.055, green: 0.055, blue: 0.086)
    static let surface2 = Color(red: 0.078, green: 0.078, blue: 0.122)
    static let text = Color(red: 0.933, green: 0.949, blue: 1.0)
    static let muted = Color(red: 0.545, green: 0.584, blue: 0.69)
    static let cyan = Color(red: 0.0, green: 0.941, blue: 1.0)
    static let lime = Color(red: 0.224, green: 1.0, blue: 0.549)
    static let gold = Color(red: 1.0, green: 0.757, blue: 0.302)
    static let coral = Color(red: 1.0, green: 0.2, blue: 0.333)
    static let violet = Color(red: 0.659, green: 0.333, blue: 0.969)
    static let magenta = Color(red: 1.0, green: 0.0, blue: 0.502)
    static let criticalPink = Color(red: 1.0, green: 0.42, blue: 0.616)

    static func metricChipColor(_ tone: MetricChipTone) -> Color {
        switch tone {
        case .critical: return criticalPink
        case .high, .leak: return coral
        case .medium: return gold
        case .verify, .seo: return cyan
        case .expected: return lime
        case .plugins: return magenta
        }
    }

    static func bandColor(_ band: ScoreBand) -> Color {
        switch band {
        case .good: return lime
        case .fair: return gold
        case .poor: return Color(red: 1.0, green: 0.624, blue: 0.42)
        case .critical: return coral
        }
    }

    static func toneAccent(_ tone: ReportTone) -> Color {
        switch tone {
        case .pass: return lime
        case .attention: return gold
        case .risk: return coral
        }
    }
}

struct ReportAmbientBackground: View {
    var body: some View {
        ZStack {
            ReportTheme.canvas
            RadialGradient(
                colors: [ReportTheme.cyan.opacity(0.14), .clear],
                center: .init(x: 0.5, y: 0.0),
                startRadius: 0,
                endRadius: 420
            )
            RadialGradient(
                colors: [ReportTheme.violet.opacity(0.1), .clear],
                center: .init(x: 1.0, y: 0.85),
                startRadius: 0,
                endRadius: 360
            )
        }
        .ignoresSafeArea()
    }
}
