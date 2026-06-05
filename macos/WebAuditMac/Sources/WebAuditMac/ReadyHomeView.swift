import SwiftUI

struct ReadyHomeView: View {
    @ObservedObject var viewModel: ScanViewModel
    var onSubmit: () -> Void
    var onPreferShell: () -> Void

    @State private var contentWidth: CGFloat = 720

    private static let features: [FeatureItem] = [
        FeatureItem(id: "scores", icon: "gauge.with.dots.needle.67percent", color: ReportTheme.cyan, title: "Hygiene & exposure scores", detail: "Configuration quality vs. public leak risk — higher is better."),
        FeatureItem(id: "summary", icon: "doc.richtext", color: ReportTheme.lime, title: "Executive summary", detail: "Plain verdict, fix-first list, and full report in your browser."),
        FeatureItem(id: "dns", icon: "globe.americas.fill", color: ReportTheme.violet, title: "DNS & email protection", detail: "SPF, DKIM, DMARC, and DNS records that affect deliverability and spoofing."),
        FeatureItem(id: "email", icon: "envelope.badge.shield.half.filled", color: ReportTheme.cyan, title: "Email authentication signals", detail: "Whether your domain looks protected against impersonation."),
        FeatureItem(id: "tls", icon: "lock.shield.fill", color: ReportTheme.lime, title: "TLS & certificates", detail: "HTTPS setup, cert expiry, and common transport misconfigurations."),
        FeatureItem(id: "headers", icon: "checkmark.shield.fill", color: ReportTheme.gold, title: "Security headers", detail: "CSP, HSTS, framing, and other browser-side protections."),
        FeatureItem(id: "plugins", icon: "puzzlepiece.extension.fill", color: ReportTheme.gold, title: "Plugins, themes & stack", detail: "WordPress plugins, theme hints, and detected framework surface."),
        FeatureItem(id: "paths", icon: "eye.trianglebadge.exclamationmark", color: ReportTheme.coral, title: "Public paths & sensitive files", detail: "What strangers could reach — admin paths, backups, config leaks."),
        FeatureItem(id: "local", icon: "folder.fill", color: ReportTheme.muted, title: "Saved on this Mac", detail: "Reports in ~/Documents/WebAudit — nothing uploaded unless you share."),
    ]

    private var metrics: LayoutMetrics { LayoutMetrics(width: contentWidth) }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18 * metrics.scale) {
                heroCard
                scanEntryCard
                infoColumns
                if !viewModel.completedScans.isEmpty {
                    sessionHistorySection
                }
            }
            .padding(.bottom, 8)
            .frame(maxWidth: .infinity, alignment: .topLeading)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .trackContentWidth($contentWidth)
    }

    private var heroCard: some View {
        HStack(alignment: .center, spacing: 16 * metrics.scale) {
            WebAuditMark(size: metrics.heroMarkSize)
                .shadow(color: ReportTheme.cyan.opacity(0.35), radius: 16)
            VStack(alignment: .leading, spacing: 6) {
                Text("How well is your site built — and what does the public see?")
                    .font(metrics.heroTitle)
                    .foregroundStyle(ReportTheme.text)
                Text("Read-only security scan · plain-English report · saved on this Mac")
                    .font(metrics.bodyFont)
                    .foregroundStyle(ReportTheme.muted)
                    .fixedSize(horizontal: false, vertical: true)
            }
            Spacer(minLength: 0)
        }
        .padding(metrics.cardPadding)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(ReportTheme.surface)
        .overlay(
            RoundedRectangle(cornerRadius: 14)
                .stroke(
                    LinearGradient(
                        colors: [ReportTheme.cyan.opacity(0.45), ReportTheme.violet.opacity(0.25)],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    ),
                    lineWidth: 1
                )
        )
        .clipShape(RoundedRectangle(cornerRadius: 14))
    }

    private var scanEntryCard: some View {
        VStack(alignment: .leading, spacing: 12 * metrics.scale) {
            Text("Your website address")
                .font(metrics.rowTitle)
                .foregroundStyle(ReportTheme.muted)
            MacURLTextField(
                text: $viewModel.urlText,
                placeholder: "https://your-flower-shop.com",
                isEnabled: !viewModel.isScanning,
                focusOnAppear: true,
                onSubmit: onSubmit
            )
            .frame(maxWidth: .infinity, minHeight: 34 * metrics.scale)
            Button("Scan my website") {
                viewModel.startScan()
            }
            .buttonStyle(ReportPrimaryButtonStyle())
            .controlSize(.large)
            .keyboardShortcut(.defaultAction)
            .disabled(viewModel.urlText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            Text("Only scan websites you own or have permission to test.")
                .font(metrics.captionFont)
                .foregroundStyle(ReportTheme.muted)
        }
        .padding(metrics.cardPadding)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(ReportTheme.surface2)
        .clipShape(RoundedRectangle(cornerRadius: 14))
        .overlay(RoundedRectangle(cornerRadius: 14).stroke(Color.white.opacity(0.08)))
    }

    @ViewBuilder
    private var infoColumns: some View {
        if metrics.isTwoColumn {
            HStack(alignment: .top, spacing: metrics.columnSpacing) {
                whatYouGetCard
                    .layoutPriority(1)
                aboutPanel
                    .layoutPriority(1)
            }
            .frame(maxWidth: .infinity, alignment: .topLeading)
        } else {
            VStack(alignment: .leading, spacing: metrics.columnSpacing) {
                whatYouGetCard
                aboutPanel
            }
            .frame(maxWidth: .infinity, alignment: .topLeading)
        }
    }

    private var aboutPanel: some View {
        AboutDisclaimerPanel(metrics: metrics) {
            viewModel.showHelp = true
        } onPreferShell: {
            onPreferShell()
        }
    }

    private var whatYouGetCard: some View {
        VStack(alignment: .leading, spacing: 10 * metrics.scale) {
            Text("What you get")
                .font(metrics.sectionTitle)
                .foregroundStyle(ReportTheme.text)
            Text("One read-only scan — same depth as the HTML report.")
                .font(metrics.bodyFont)
                .foregroundStyle(ReportTheme.muted)

            LazyVGrid(
                columns: Array(
                    repeating: GridItem(.flexible(minimum: 220), spacing: 12 * metrics.scale),
                    count: metrics.featureColumns
                ),
                alignment: .leading,
                spacing: 12 * metrics.scale
            ) {
                ForEach(Self.features) { feature in
                    featureRow(feature)
                }
            }
        }
        .padding(metrics.cardPadding)
        .frame(maxWidth: .infinity, alignment: .topLeading)
        .background(ReportTheme.surface.opacity(0.65))
        .clipShape(RoundedRectangle(cornerRadius: 14))
    }

    private func featureRow(_ feature: FeatureItem) -> some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: feature.icon)
                .font(.system(size: 20 * metrics.scale))
                .foregroundStyle(feature.color)
                .frame(width: 28 * metrics.scale)
            VStack(alignment: .leading, spacing: 2) {
                Text(feature.title)
                    .font(metrics.rowTitle)
                    .foregroundStyle(ReportTheme.text)
                Text(feature.detail)
                    .font(metrics.bodyFont)
                    .foregroundStyle(ReportTheme.muted)
                    .fixedSize(horizontal: false, vertical: true)
            }
            Spacer(minLength: 0)
        }
        .frame(maxWidth: .infinity, alignment: .topLeading)
    }

    private var sessionHistorySection: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("This session")
                    .font(metrics.sectionTitle)
                    .foregroundStyle(ReportTheme.text)
                Spacer()
                Text("\(viewModel.completedScans.count) report\(viewModel.completedScans.count == 1 ? "" : "s")")
                    .font(metrics.captionFont)
                    .foregroundStyle(ReportTheme.muted)
            }
            if metrics.isTwoColumn {
                LazyVGrid(
                    columns: [GridItem(.flexible()), GridItem(.flexible())],
                    alignment: .leading,
                    spacing: 12
                ) {
                    ForEach(viewModel.completedScans) { scan in
                        ScanHistoryRow(scan: scan, metrics: metrics) {
                            viewModel.reopenScan(scan)
                        }
                    }
                }
            } else {
                ForEach(viewModel.completedScans) { scan in
                    ScanHistoryRow(scan: scan, metrics: metrics) {
                        viewModel.reopenScan(scan)
                    }
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

struct ScanHistoryRow: View {
    let scan: CompletedScan
    var metrics: LayoutMetrics = LayoutMetrics(width: 720)
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 0) {
                RoundedRectangle(cornerRadius: 2)
                    .fill(ReportTheme.toneAccent(scan.verdictTone))
                    .frame(width: 4)
                    .padding(.vertical, 4)

                VStack(alignment: .leading, spacing: 8) {
                    HStack(alignment: .firstTextBaseline) {
                        Text(scan.hostLabel)
                            .font(metrics.rowTitle)
                            .foregroundStyle(ReportTheme.text)
                        Spacer()
                        Text(scan.completedAt, style: .relative)
                            .font(metrics.captionFont)
                            .foregroundStyle(ReportTheme.muted)
                    }
                    HStack(spacing: 8) {
                        VerdictPill(label: scan.verdictLabel, tone: scan.verdictTone)
                        ScoreMiniPill(label: "Hygiene", value: scan.hygiene, band: ScoreBand.forHygiene(scan.hygiene))
                        ScoreMiniPill(label: "Exposure", value: scan.exposure, band: ScoreBand.forHygiene(scan.exposure))
                    }
                }
                .padding(.leading, 12)
                .padding(.vertical, 12)
                .padding(.trailing, 8)

                Image(systemName: "chevron.right")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(ReportTheme.muted)
                    .padding(.trailing, 12)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(ReportTheme.surface)
            .clipShape(RoundedRectangle(cornerRadius: 12))
            .overlay(
                RoundedRectangle(cornerRadius: 12)
                    .stroke(ReportTheme.toneAccent(scan.verdictTone).opacity(0.35), lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
    }
}

struct VerdictPill: View {
    let label: String
    let tone: ReportTone

    var body: some View {
        Text(label)
            .font(.system(size: 13, weight: .semibold))
            .foregroundStyle(ReportTheme.toneAccent(tone))
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(ReportTheme.toneAccent(tone).opacity(0.15))
            .clipShape(Capsule())
            .overlay(Capsule().stroke(ReportTheme.toneAccent(tone).opacity(0.35)))
    }
}

struct ScoreMiniPill: View {
    let label: String
    let value: Int
    let band: ScoreBand

    var body: some View {
        HStack(spacing: 4) {
            Text(label)
                .foregroundStyle(ReportTheme.muted)
            Text("\(value)")
                .foregroundStyle(ReportTheme.bandColor(band))
                .fontWeight(.bold)
        }
        .font(.system(size: 12, weight: .medium))
        .padding(.horizontal, 8)
        .padding(.vertical, 4)
        .background(Color.white.opacity(0.05))
        .clipShape(Capsule())
    }
}

struct SessionHistoryStrip: View {
    let scans: [CompletedScan]
    let currentReportDir: URL
    let onSelect: (CompletedScan) -> Void

    var body: some View {
        let others = scans.filter { $0.reportDir != currentReportDir }
        if !others.isEmpty {
            VStack(alignment: .leading, spacing: 8) {
                Text("Other reports this session")
                    .font(.system(size: 15, weight: .semibold))
                    .foregroundStyle(ReportTheme.muted)
                ForEach(others.prefix(4)) { scan in
                    ScanHistoryRow(scan: scan) {
                        onSelect(scan)
                    }
                }
            }
        }
    }
}
