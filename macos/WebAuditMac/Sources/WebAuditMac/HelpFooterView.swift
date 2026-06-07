import SwiftUI

/// Footer — consolidated Learn more menu + Advanced technical details.
struct HelpFooterView: View {
    @ObservedObject var viewModel: ScanViewModel
    var onDarkBackground: Bool
    var onShowShellEdition: () -> Void

    @State private var showLearnMore = false

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            LearnMoreResourcesView(
                viewModel: viewModel,
                onDarkBackground: onDarkBackground,
                onShowShellEdition: onShowShellEdition,
                isExpanded: $showLearnMore
            )
            ExpandableSection(
                title: "Advanced",
                subtitle: "Scan engine paths and technical details",
                systemImage: "gearshape.fill",
                onDarkBackground: onDarkBackground,
                isExpanded: $viewModel.showAdvanced
            ) {
                VStack(alignment: .leading, spacing: 6) {
                    advancedRow("Engine", viewModel.engineInfo.kind.rawValue)
                    advancedRow("Path", viewModel.engineInfo.path.isEmpty ? "—" : viewModel.engineInfo.path)
                    advancedRow("Reports", ScanRunner.outputRoot.path)
                    advancedRow("Failure logs", ScanFailureLogWriter.defaultLogsDirectory.path)
                    Text("Beta (unsigned) — first launch may require Right-click → Open on Web Audit")
                        .font(.system(size: 12))
                        .foregroundStyle(onDarkBackground ? ReportTheme.muted : .secondary)
                        .padding(.top, 4)
                }
            }
            .onChange(of: viewModel.showAdvanced) { expanded in
                if expanded { viewModel.refreshEngineInfo() }
            }
        }
    }

    private func advancedRow(_ label: String, _ value: String) -> some View {
        HStack(alignment: .top, spacing: 8) {
            Text(label)
                .font(.system(size: 12, weight: .semibold))
                .foregroundStyle(onDarkBackground ? ReportTheme.muted : .secondary)
                .frame(width: 88, alignment: .leading)
            Text(value)
                .font(.system(size: 12, design: .monospaced))
                .foregroundStyle(onDarkBackground ? ReportTheme.text.opacity(0.9) : .primary)
                .textSelection(.enabled)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}
