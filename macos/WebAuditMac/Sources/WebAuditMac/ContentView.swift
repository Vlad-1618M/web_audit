import SwiftUI

struct ContentView: View {
    @StateObject private var viewModel = ScanViewModel()
    @State private var showShellEditionChoice = false

    var body: some View {
        ZStack {
            if usesReportChrome {
                ReportAmbientBackground()
            }
            VStack(alignment: .leading, spacing: 14) {
                header
                phaseContent
                    .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
                if !usesReportChrome {
                    BrandingFooterView(onDarkBackground: false)
                } else {
                    BrandingFooterView(onDarkBackground: true)
                }
            }
            .padding(28)
            .frame(minWidth: 580, minHeight: 520)
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .sheet(isPresented: $viewModel.showHelp) {
            HelpSheet()
        }
        .sheet(item: $viewModel.shareContext) { context in
            ReportShareSheet(context: context) {
                viewModel.dismissShareSheet()
            }
        }
        .onAppear { viewModel.refreshEngineInfo() }
        .confirmationDialog(
            "Web Audit v1 — Audit Lite",
            isPresented: $showShellEditionChoice,
            titleVisibility: .visible
        ) {
            Button("Read web_audit.sh on GitHub") {
                AppBrand.ShellEdition.openReadScript()
            }
            Button("Download web_audit.sh") {
                AppBrand.ShellEdition.openDownloadScript()
            }
            Button("v1 vs v2 report examples") {
                NSWorkspace.shared.open(AppBrand.ShellEdition.reportComparison)
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("Don't trust this Mac app? The v1 shell edition is one script — read the source on GitHub first, or download and run it in Terminal. No Docker, no installer.")
        }
    }

    private var usesReportChrome: Bool {
        switch viewModel.phase {
        case .ready, .scanning, .complete: return true
        default: return false
        }
    }

    private var isCompletePhase: Bool {
        if case .complete = viewModel.phase { return true }
        return false
    }

    private func submitScanIfReady() {
        guard !viewModel.urlText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return }
        viewModel.startScan()
    }

    @ViewBuilder
    private var header: some View {
        HStack(spacing: 12) {
            VStack(alignment: .leading, spacing: 2) {
                Text("Web Audit Pro")
                    .font(.system(size: 24, weight: .bold))
                    .foregroundStyle(usesReportChrome ? ReportTheme.text : .primary)
                Text("Check your website's public security")
                    .font(.system(size: 16))
                    .foregroundStyle(usesReportChrome ? ReportTheme.muted : .secondary)
            }
            Spacer()
            if usesReportChrome {
                Button("Quit") { viewModel.quitApp() }
                    .buttonStyle(ReportSecondaryButtonStyle())
                    .keyboardShortcut("q", modifiers: .command)
            } else {
                Button("Quit") { viewModel.quitApp() }
                    .buttonStyle(.bordered)
                    .keyboardShortcut("q", modifiers: .command)
            }
        }
    }

    @ViewBuilder
    private var phaseContent: some View {
        switch viewModel.phase {
        case .ready:
            VStack(alignment: .leading, spacing: 12) {
                ReadyHomeView(
                    viewModel: viewModel,
                    onSubmit: submitScanIfReady,
                    onPreferShell: { showShellEditionChoice = true }
                )
                footerLinks
            }
        case .scanning:
            scanningView
        case .complete(let dir, let summary):
            completeView(dir: dir, summary: summary)
        case .error(let message):
            errorView(message: message)
        }
    }

    private var scanningView: some View {
        VStack(alignment: .leading, spacing: 12) {
            scanningStatusCard
            Text("Live progress")
                .font(.system(size: 13, weight: .semibold))
                .foregroundStyle(ReportTheme.muted)
            LiveLogView(lines: viewModel.logLines)
                .frame(minHeight: 560, maxHeight: .infinity)
            Button("Cancel scan") { viewModel.cancelScan() }
                .buttonStyle(.bordered)
            footerLinks
        }
    }

    private var scanningStatusCard: some View {
        HStack(alignment: .center, spacing: 16) {
            ScanProgressIndicator(size: 52)
            VStack(alignment: .leading, spacing: 8) {
                Text("Checking your site…")
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundStyle(ReportTheme.text)
                if let target = scanningTargetURL {
                    Link(destination: target) {
                        HStack(spacing: 6) {
                            Image(systemName: "arrow.up.right.square")
                                .font(.system(size: 13, weight: .semibold))
                            Text(scanningURLDisplay)
                                .font(.system(size: 15, design: .monospaced))
                                .lineLimit(2)
                                .multilineTextAlignment(.leading)
                        }
                    }
                    .foregroundStyle(ReportTheme.cyan)
                    .help("Open this site in your browser while the scan continues")
                } else {
                    Text(viewModel.urlText)
                        .font(.system(size: 15, design: .monospaced))
                        .foregroundStyle(ReportTheme.muted)
                        .lineLimit(2)
                }
                Text("Passive read-only checks — you can open the site above anytime")
                    .font(.system(size: 12))
                    .foregroundStyle(ReportTheme.muted)
            }
            Spacer(minLength: 0)
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(ReportTheme.surface2)
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(
                    LinearGradient(
                        colors: [ReportTheme.cyan.opacity(0.45), ReportTheme.violet.opacity(0.25)],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    ),
                    lineWidth: 1
                )
        )
    }

    private var scanningURLDisplay: String {
        viewModel.urlText.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private var scanningTargetURL: URL? {
        let raw = scanningURLDisplay
        guard !raw.isEmpty, let url = URL(string: raw),
              let scheme = url.scheme?.lowercased(),
              scheme == "http" || scheme == "https" else {
            return nil
        }
        return url
    }

    private func completeView(dir: URL, summary: String?) -> some View {
        ScrollView {
            if let snapshot = viewModel.activeReport {
                ReportCompleteView(
                    snapshot: snapshot,
                    reportDir: dir,
                    viewModel: viewModel
                )
            } else {
                legacyCompleteView(dir: dir, summary: summary)
            }
            footerLinks
                .padding(.top, 8)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private func legacyCompleteView(dir: URL, summary: String?) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Label("Report ready", systemImage: "checkmark.circle.fill")
                .font(.system(size: 18, weight: .semibold))
                .foregroundStyle(.green)
            if let summary {
                Text(summary)
                    .font(.system(size: 15))
            }
            Button("Open report in browser") { viewModel.openReportInBrowser() }
                .buttonStyle(.borderedProminent)
            Button("Scan another website") { viewModel.resetForAnotherScan() }
                .buttonStyle(.borderedProminent)
        }
    }

    private func errorView(message: String) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Label("Something went wrong", systemImage: "exclamationmark.triangle.fill")
                .font(.system(size: 18, weight: .semibold))
                .foregroundStyle(.red)
            Text(message)
                .font(.system(size: 15))
                .foregroundStyle(.secondary)
            if !viewModel.logLines.isEmpty {
                LiveLogView(lines: viewModel.logLines)
                    .frame(minHeight: 320, maxHeight: .infinity)
            }
            MacURLTextField(
                text: $viewModel.urlText,
                placeholder: "https://…",
                focusOnAppear: true,
                onSubmit: submitScanIfReady
            )
            .frame(maxWidth: .infinity, minHeight: 32)
            Button("Try again") {
                viewModel.startScan()
            }
            .buttonStyle(.borderedProminent)
            .keyboardShortcut(.defaultAction)
            footerLinks
        }
    }

    private var footerLinks: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 16) {
                Button("What is this?") { viewModel.showHelp = true }
                    .buttonStyle(.link)
                    .font(.system(size: 14))
                    .foregroundStyle(usesReportChrome ? ReportTheme.cyan : .accentColor)
                Link("Help on GitHub", destination: URL(string: "https://github.com/Vlad-1618M/web_audit/blob/v.tools_main/v2_python_core/docs/getting_started_plain.md")!)
                    .font(.system(size: 14))
                    .foregroundStyle(usesReportChrome ? ReportTheme.cyan : .accentColor)
                Button("v1 shell edition") { showShellEditionChoice = true }
                    .buttonStyle(.link)
                    .font(.system(size: 14))
                    .foregroundStyle(usesReportChrome ? ReportTheme.gold : .orange)
            }
            DisclosureGroup("Advanced", isExpanded: $viewModel.showAdvanced) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Engine: \(viewModel.engineInfo.kind.rawValue)")
                    Text("Path: \(viewModel.engineInfo.path.isEmpty ? "—" : viewModel.engineInfo.path)")
                    Text("Reports: \(ScanRunner.outputRoot.path)")
                    Text("Notarization: in progress — first open may require Right-click → Open")
                        .foregroundStyle(.secondary)
                }
                .font(.system(size: 13))
                .textSelection(.enabled)
            }
            .font(.system(size: 14))
            .onChange(of: viewModel.showAdvanced) { expanded in
                if expanded { viewModel.refreshEngineInfo() }
            }
        }
    }
}

struct LiveLogView: View {
    let lines: [String]

    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 2) {
                    ForEach(Array(lines.enumerated()), id: \.offset) { index, line in
                        Text(line)
                            .font(.system(size: 14, design: .monospaced))
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .id(index)
                    }
                }
                .padding(8)
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .background(Color(nsColor: .textBackgroundColor))
            .clipShape(RoundedRectangle(cornerRadius: 8))
            .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.secondary.opacity(0.25)))
            .onChange(of: lines.count) { count in
                guard count > 0 else { return }
                withAnimation(.easeOut(duration: 0.15)) {
                    proxy.scrollTo(count - 1, anchor: .bottom)
                }
            }
        }
    }
}

struct HelpSheet: View {
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("What is Web Audit Pro?")
                .font(.system(size: 22, weight: .bold))
            Text("A read-only check of your public website — what a stranger on the internet could see. It is not a penetration test and does not log into your site.")
                .font(.system(size: 15))
                .foregroundStyle(.secondary)
            Text("Reports are saved on this Mac under Documents/WebAudit unless you share them.")
                .font(.system(size: 15))
                .foregroundStyle(.secondary)
            Link("Plain-English guide on GitHub", destination: URL(string: "https://github.com/Vlad-1618M/web_audit/blob/v.tools_main/v2_python_core/docs/getting_started_plain.md")!)
                .font(.system(size: 14))
            Link("v1 shell edition (read or download)", destination: AppBrand.ShellEdition.readScript)
                .font(.system(size: 13))
            Text("Prefer bash? Read web_audit.sh on GitHub before you run anything.")
                .font(.system(size: 13))
                .foregroundStyle(.secondary)
            Spacer()
            Button("OK") { dismiss() }
                .keyboardShortcut(.defaultAction)
        }
        .padding(24)
        .frame(width: 460, height: 300)
    }
}
