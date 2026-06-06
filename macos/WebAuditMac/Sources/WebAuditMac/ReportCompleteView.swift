import AppKit
import SwiftUI

struct ReportCompleteView: View {
    /// Scroll target for ``ContentView`` when switching reports.
    static let resultsScrollAnchor = "webaudit-report-results"

    let snapshot: ScanReportSnapshot
    let reportDir: URL
    @ObservedObject var viewModel: ScanViewModel

    @State private var contentWidth: CGFloat = 720

    private var metrics: LayoutMetrics { LayoutMetrics(width: contentWidth) }
    private var chipColumnCount: Int {
        if contentWidth >= 920 { return 4 }
        if contentWidth >= 560 { return 2 }
        return 2
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 16 * metrics.scale) {
            SavedReportsPicker(
                scans: viewModel.completedScans,
                currentReportDir: reportDir,
                metrics: metrics,
                onSelect: { viewModel.reopenScan($0) },
                onReturnHome: { viewModel.returnToHome() }
            )
            siteHero
                .id(Self.resultsScrollAnchor)
            verdictBanner
            scoreCards
            findingStatusSection
            fixFirstSection
            actionButtons
            Text(reportDir.path)
                .font(metrics.finePrintFont)
                .foregroundStyle(ReportTheme.muted)
                .lineLimit(2)
                .textSelection(.enabled)
            HStack(spacing: 12) {
                Button("Back to home") { viewModel.returnToHome() }
                    .buttonStyle(ReportSecondaryButtonStyle())
                Button("Scan another website") { viewModel.resetForAnotherScan() }
                    .buttonStyle(ReportPrimaryButtonStyle())
            }
        }
        .frame(maxWidth: .infinity, alignment: .topLeading)
        .trackContentWidth($contentWidth)
    }

    private var siteHero: some View {
        VStack(alignment: .leading, spacing: 8 * metrics.scale) {
            HStack(alignment: .center, spacing: 10 * metrics.scale) {
                ZStack {
                    Circle()
                        .fill(
                            LinearGradient(
                                colors: [ReportTheme.lime.opacity(0.9), ReportTheme.cyan.opacity(0.85)],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            )
                        )
                        .frame(width: 32 * metrics.scale, height: 32 * metrics.scale)
                    Image(systemName: "checkmark")
                        .font(.system(size: 14 * metrics.scale, weight: .bold))
                        .foregroundStyle(.white)
                }

                HStack(alignment: .firstTextBaseline, spacing: 8 * metrics.scale) {
                    Text("Report ready")
                        .font(metrics.sectionTitle)
                        .foregroundStyle(ReportTheme.text)
                    Text("·")
                        .font(metrics.sectionTitle)
                        .foregroundStyle(ReportTheme.muted.opacity(0.55))
                    Text(snapshot.hostLabel)
                        .font(.system(size: 18 * metrics.scale, weight: .semibold))
                        .foregroundStyle(ReportTheme.cyan)
                        .lineLimit(1)
                        .minimumScaleFactor(0.85)
                }

                Spacer(minLength: 0)
            }

            ScannedTargetLink(urlString: snapshot.targetURL, metrics: metrics)

            Text("Framework: \(snapshot.framework) (\(snapshot.frameworkConfidence)) · Scanned \(formatScannedAt(snapshot.scannedAt))")
                .font(metrics.captionFont)
                .foregroundStyle(ReportTheme.muted)
        }
    }

    private var verdictBanner: some View {
        HStack(alignment: .top, spacing: 14) {
            Image(systemName: snapshot.verdictIcon)
                .font(.system(size: 28))
                .foregroundStyle(ReportTheme.toneAccent(snapshot.verdictTone))
            VStack(alignment: .leading, spacing: 6) {
                Text(snapshot.verdictLabel)
                    .font(metrics.phaseHeadline)
                    .foregroundStyle(ReportTheme.text)
                Text(snapshot.summaryLine)
                    .font(metrics.bodyFont)
                    .foregroundStyle(ReportTheme.text.opacity(0.88))
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(ReportTheme.surface2)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(ReportTheme.toneAccent(snapshot.verdictTone).opacity(0.45), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private var scoreCards: some View {
        HStack(spacing: 14) {
            ScoreCardView(
                title: "Configuration (Hygiene)",
                hint: "Headers, TLS, DNS — higher is better",
                score: snapshot.hygiene,
                band: snapshot.hygieneBand
            )
            ScoreCardView(
                title: "Leak score (Exposure)",
                hint: "Sensitive paths & public exposure",
                score: snapshot.exposure,
                band: snapshot.exposureBand
            )
        }
    }

    private var findingStatusSection: some View {
        VStack(alignment: .leading, spacing: 10 * metrics.scale) {
            Text("Finding status")
                .font(metrics.captionFont.weight(.semibold))
                .foregroundStyle(ReportTheme.muted)
                .textCase(.uppercase)
                .tracking(0.4)

            LazyVGrid(
                columns: Array(
                    repeating: GridItem(.flexible(minimum: 120), spacing: 10 * metrics.scale),
                    count: chipColumnCount
                ),
                alignment: .leading,
                spacing: 10 * metrics.scale
            ) {
                ForEach(snapshot.metricChips) { chip in
                    ReportMetricChip(chip: chip, metrics: metrics)
                }
            }

            if let meta = scanMetaLine {
                Text(meta)
                    .font(metrics.captionFont)
                    .foregroundStyle(ReportTheme.muted.opacity(0.9))
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var scanMetaLine: String? {
        var parts: [String] = []
        if let pages = snapshot.pagesScanned {
            parts.append("\(pages) page\(pages == 1 ? "" : "s") scanned")
        }
        if let probes = snapshot.probeCount {
            parts.append("\(probes) probes")
        }
        if let days = snapshot.certDaysLeft {
            parts.append("\(days)d cert")
        }
        guard !parts.isEmpty else { return nil }
        return parts.joined(separator: " · ")
    }

    @ViewBuilder
    private var fixFirstSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("What to fix first")
                .font(metrics.phaseHeadline)
                .foregroundStyle(ReportTheme.text)
            if snapshot.actionFindings.isEmpty {
                findingRow(icon: "checkmark.seal.fill", tone: ReportTheme.lime, title: "No scored action items", detail: "Keep monitoring with regular scans.")
            } else {
                ForEach(snapshot.actionFindings.prefix(5)) { finding in
                    findingRow(
                        icon: "wrench.and.screwdriver.fill",
                        tone: ReportTheme.gold,
                        title: "\(finding.item) (\(finding.category))",
                        detail: finding.detail
                    )
                }
            }
            if snapshot.exposure == 100 {
                findingRow(
                    icon: "lock.shield.fill",
                    tone: ReportTheme.lime,
                    title: "No sensitive path leaks",
                    detail: "Detected in this scan."
                )
            }
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(ReportTheme.surface)
        .overlay(RoundedRectangle(cornerRadius: 12).stroke(Color.white.opacity(0.08)))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private func findingRow(icon: String, tone: Color, title: String, detail: String) -> some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: icon)
                .foregroundStyle(tone)
                .frame(width: 18)
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(metrics.rowTitle)
                    .foregroundStyle(ReportTheme.text)
                if !detail.isEmpty {
                    Text(detail)
                        .font(metrics.captionFont)
                        .foregroundStyle(ReportTheme.muted)
                }
            }
        }
    }

    private var actionButtons: some View {
        VStack(alignment: .leading, spacing: 10) {
            Button("Open report in browser") { viewModel.openReportInBrowser() }
                .buttonStyle(ReportAccentButtonStyle())
                .controlSize(.large)
            Button("Save report to share…") { viewModel.downloadReport() }
                .buttonStyle(ReportSecondaryButtonStyle())
            Text("Zip includes report.html + report.css + how-to-open instructions.")
                .font(metrics.finePrintFont)
                .foregroundStyle(ReportTheme.muted)
            HStack(spacing: 10) {
                Button("Show in Finder") { viewModel.revealInFinder() }
                    .buttonStyle(ReportSecondaryButtonStyle())
                Button("Share with…") { viewModel.shareReport() }
                    .buttonStyle(ReportSecondaryButtonStyle())
            }
        }
    }

    private func formatScannedAt(_ raw: String) -> String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let date = formatter.date(from: raw) ?? ISO8601DateFormatter().date(from: raw) {
            return date.formatted(date: .abbreviated, time: .shortened)
        }
        return raw
    }
}

private struct ScoreCardView: View {
    let title: String
    let hint: String
    let score: Int
    let band: ScoreBand

    var body: some View {
        VStack(spacing: 8) {
            Text(title.uppercased())
                .font(.system(size: 12, weight: .semibold))
                .foregroundStyle(ReportTheme.muted)
                .multilineTextAlignment(.center)
            ZStack {
                Circle()
                    .stroke(Color.white.opacity(0.1), lineWidth: 7)
                Circle()
                    .trim(from: 0, to: CGFloat(min(max(score, 0), 100)) / 100)
                    .stroke(
                        ReportTheme.bandColor(band),
                        style: StrokeStyle(lineWidth: 7, lineCap: .round)
                    )
                    .rotationEffect(.degrees(-90))
                Text("\(score)")
                    .font(.system(size: 36, weight: .bold, design: .rounded))
                    .foregroundStyle(ReportTheme.bandColor(band))
            }
            .frame(width: 96, height: 96)
            Text(hint)
                .font(.system(size: 12))
                .foregroundStyle(ReportTheme.muted)
                .multilineTextAlignment(.center)
        }
        .padding(14)
        .frame(maxWidth: .infinity)
        .background(ReportTheme.surface)
        .overlay(RoundedRectangle(cornerRadius: 12).stroke(Color.white.opacity(0.08)))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }
}

private struct ReportMetricChip: View {
    let chip: MetricChipSnapshot
    let metrics: LayoutMetrics

    private var accent: Color { ReportTheme.metricChipColor(chip.tone) }

    var body: some View {
        VStack(spacing: 4 * metrics.scale) {
            Text("\(chip.count)")
                .font(.system(size: 28 * metrics.scale, weight: .bold, design: .rounded))
                .foregroundStyle(accent)
                .shadow(color: accent.opacity(0.35), radius: 8)
            Text(chip.label)
                .font(.system(size: 11.5 * metrics.scale, weight: .medium))
                .foregroundStyle(ReportTheme.muted)
                .textCase(.uppercase)
                .multilineTextAlignment(.center)
                .lineLimit(2)
                .minimumScaleFactor(0.85)
            if let sub = chip.sub, !sub.isEmpty {
                Text(sub)
                    .font(.system(size: 11 * metrics.scale))
                    .foregroundStyle(ReportTheme.muted.opacity(0.9))
                    .multilineTextAlignment(.center)
                    .lineLimit(2)
            }
        }
        .padding(.horizontal, 12 * metrics.scale)
        .padding(.vertical, 12 * metrics.scale)
        .frame(maxWidth: .infinity, minHeight: 72 * metrics.scale)
        .background(ReportTheme.surface)
        .overlay(
            RoundedRectangle(cornerRadius: 10)
                .stroke(Color.white.opacity(0.1), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: 10))
    }
}

/// Full-width scanned URL — clear hover affordance and reliable click target on macOS.
private struct ScannedTargetLink: View {
    let urlString: String
    let metrics: LayoutMetrics

    @State private var isHovered = false
    @Environment(\.openURL) private var openURL

    private var destination: URL {
        URL(string: urlString) ?? URL(string: "https://example.com")!
    }

    var body: some View {
        Button {
            openURL(destination)
        } label: {
            HStack(spacing: 10 * metrics.scale) {
                Image(systemName: "link")
                    .font(.system(size: 13 * metrics.scale, weight: .semibold))
                    .foregroundStyle(isHovered ? ReportTheme.cyan : ReportTheme.muted)
                Text(urlString)
                    .font(.system(size: 15 * metrics.scale, weight: isHovered ? .semibold : .medium))
                    .foregroundStyle(isHovered ? ReportTheme.text : ReportTheme.cyan.opacity(0.88))
                    .lineLimit(1)
                    .truncationMode(.middle)
                Spacer(minLength: 0)
                Image(systemName: "arrow.up.right")
                    .font(.system(size: 12 * metrics.scale, weight: .semibold))
                    .foregroundStyle(ReportTheme.cyan)
                    .opacity(isHovered ? 1 : 0.35)
            }
            .padding(.horizontal, 12 * metrics.scale)
            .padding(.vertical, 10 * metrics.scale)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(
                RoundedRectangle(cornerRadius: 10)
                    .fill(isHovered ? ReportTheme.surface2 : ReportTheme.surface.opacity(0.65))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 10)
                    .stroke(
                        ReportTheme.cyan.opacity(isHovered ? 0.65 : 0.22),
                        lineWidth: isHovered ? 1.5 : 1
                    )
            )
            .shadow(color: ReportTheme.cyan.opacity(isHovered ? 0.18 : 0), radius: isHovered ? 10 : 0)
        }
        .buttonStyle(.plain)
        .contentShape(RoundedRectangle(cornerRadius: 10))
        .animation(.easeOut(duration: 0.16), value: isHovered)
        .onHover { hovering in
            isHovered = hovering
            if hovering {
                NSCursor.pointingHand.push()
            } else {
                NSCursor.pop()
            }
        }
        .accessibilityLabel("Open scanned site")
        .accessibilityHint(urlString)
    }
}

struct ReportAccentButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 17, weight: .semibold))
            .frame(maxWidth: .infinity)
            .padding(.vertical, 10)
            .foregroundStyle(ReportTheme.text)
            .background(
                LinearGradient(
                    colors: [ReportTheme.surface2, ReportTheme.surface],
                    startPoint: .top,
                    endPoint: .bottom
                )
            )
            .overlay(
                RoundedRectangle(cornerRadius: 10)
                    .stroke(ReportTheme.cyan.opacity(configuration.isPressed ? 0.9 : 0.55), lineWidth: 1)
            )
            .shadow(color: ReportTheme.cyan.opacity(0.25), radius: configuration.isPressed ? 4 : 12)
            .clipShape(RoundedRectangle(cornerRadius: 10))
    }
}

struct ReportPrimaryButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 17, weight: .semibold))
            .frame(maxWidth: .infinity)
            .padding(.vertical, 10)
            .foregroundStyle(.white)
            .background(
                LinearGradient(
                    colors: [ReportTheme.cyan.opacity(0.85), ReportTheme.violet.opacity(0.75)],
                    startPoint: .leading,
                    endPoint: .trailing
                )
            )
            .opacity(configuration.isPressed ? 0.85 : 1)
            .clipShape(RoundedRectangle(cornerRadius: 10))
    }
}

struct ReportSecondaryButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 15, weight: .medium))
            .frame(maxWidth: .infinity)
            .padding(.vertical, 8)
            .foregroundStyle(ReportTheme.text)
            .background(ReportTheme.surface2)
            .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.white.opacity(0.12)))
            .clipShape(RoundedRectangle(cornerRadius: 8))
            .opacity(configuration.isPressed ? 0.8 : 1)
    }
}
