import SwiftUI

/// Updates every minute so “3 hours ago” stays current while the app is open.
struct LiveRelativeDateLabel: View {
    let date: Date
    var font: Font = .system(size: 12)

    var body: some View {
        TimelineView(.periodic(from: .now, by: 60)) { _ in
            Text(date, style: .relative)
                .font(font)
                .foregroundStyle(ReportTheme.muted)
        }
    }
}

struct ScanDateLabels: View {
    let date: Date
    var metrics: LayoutMetrics = LayoutMetrics(width: 720)

    private var absolute: String {
        date.formatted(date: .abbreviated, time: .shortened)
    }

    var body: some View {
        VStack(alignment: .trailing, spacing: 2) {
            Text(absolute)
                .font(metrics.captionFont)
                .foregroundStyle(ReportTheme.muted)
            LiveRelativeDateLabel(date: date, font: metrics.captionFont)
        }
    }
}
