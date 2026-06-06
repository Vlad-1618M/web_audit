import AppKit
import SwiftUI

/// Switch between saved reports or return to the home screen.
struct SavedReportsPicker: View {
    let scans: [CompletedScan]
    let currentReportDir: URL
    var metrics: LayoutMetrics = LayoutMetrics(width: 720)
    let onSelect: (CompletedScan) -> Void
    let onReturnHome: () -> Void

    @State private var hoveredScanID: String?

    /// Keeps the picker compact; full list scrolls inside this cap.
    private var reportListMaxHeight: CGFloat {
        min(CGFloat(scans.count) * 76, 280)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 12) {
                Button {
                    onReturnHome()
                } label: {
                    Label("All saved reports", systemImage: "house.fill")
                        .font(.system(size: 14, weight: .semibold))
                }
                .buttonStyle(ReportSecondaryButtonStyle())
                .help("Return to home — pick another report or start a new scan")

                Spacer()

                Text("\(scans.count) saved")
                    .font(metrics.captionFont)
                    .foregroundStyle(ReportTheme.muted)
            }

            if scans.count > 1 {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Switch report")
                        .font(.system(size: 13, weight: .semibold))
                        .foregroundStyle(ReportTheme.muted)
                    ScrollView {
                        LazyVStack(alignment: .leading, spacing: 8) {
                            ForEach(scans) { scan in
                                savedReportRow(scan)
                            }
                        }
                    }
                    .frame(maxHeight: reportListMaxHeight)
                }
            }
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(ReportTheme.surface2.opacity(0.6))
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(ReportTheme.cyan.opacity(0.25), lineWidth: 1)
        )
    }

    @ViewBuilder
    private func savedReportRow(_ scan: CompletedScan) -> some View {
        let isCurrent = scan.reportDir == currentReportDir
        let isHovered = hoveredScanID == scan.id
        let rowOpacity: CGFloat = isCurrent ? 1 : (isHovered ? 0.9 : 0.7)

        Button {
            guard !isCurrent else { return }
            onSelect(scan)
        } label: {
            HStack(spacing: 10) {
                Image(systemName: isCurrent ? "checkmark.circle.fill" : "doc.text.magnifyingglass")
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundStyle(isCurrent ? ReportTheme.lime : ReportTheme.cyan)
                VStack(alignment: .leading, spacing: 2) {
                    HStack(spacing: 6) {
                        Text(scan.hostLabel)
                            .font(metrics.rowTitle)
                            .foregroundStyle(ReportTheme.text)
                        if isCurrent {
                            Text("Viewing")
                                .font(.system(size: 11, weight: .bold))
                                .foregroundStyle(ReportTheme.lime)
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(ReportTheme.lime.opacity(0.22))
                                .clipShape(Capsule())
                        }
                    }
                    HStack(spacing: 8) {
                        VerdictPill(label: scan.verdictLabel, tone: scan.verdictTone)
                        ScanDateLabels(date: scan.completedAt, metrics: metrics)
                    }
                }
                Spacer(minLength: 0)
                if !isCurrent {
                    Image(systemName: "chevron.right")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(ReportTheme.muted)
                }
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 10)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(rowBackground(isCurrent: isCurrent, isHovered: isHovered))
            .clipShape(RoundedRectangle(cornerRadius: 10))
            .overlay(
                RoundedRectangle(cornerRadius: 10)
                    .stroke(
                        rowBorderColor(isCurrent: isCurrent, isHovered: isHovered),
                        lineWidth: isCurrent ? 1.5 : (isHovered ? 1.25 : 1)
                    )
            )
            .shadow(
                color: isCurrent ? ReportTheme.lime.opacity(0.12) : .clear,
                radius: isCurrent ? 8 : 0
            )
            .opacity(rowOpacity)
            .contentShape(RoundedRectangle(cornerRadius: 10))
        }
        .buttonStyle(.plain)
        .allowsHitTesting(!isCurrent)
        .animation(.easeOut(duration: 0.14), value: isHovered)
        .animation(.easeOut(duration: 0.14), value: isCurrent)
        .onHover { hovering in
            guard !isCurrent else { return }
            hoveredScanID = hovering ? scan.id : nil
            if hovering {
                NSCursor.pointingHand.push()
            } else {
                NSCursor.pop()
            }
        }
    }

    private func rowBackground(isCurrent: Bool, isHovered: Bool) -> Color {
        if isCurrent {
            return ReportTheme.surface2
        }
        if isHovered {
            return ReportTheme.surface.opacity(0.72)
        }
        return ReportTheme.surface.opacity(0.28)
    }

    private func rowBorderColor(isCurrent: Bool, isHovered: Bool) -> Color {
        if isCurrent {
            return ReportTheme.lime.opacity(0.62)
        }
        if isHovered {
            return ReportTheme.cyan.opacity(0.38)
        }
        return Color.white.opacity(0.07)
    }
}
