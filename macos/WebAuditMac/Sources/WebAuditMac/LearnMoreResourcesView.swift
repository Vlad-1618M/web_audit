import SwiftUI

/// Single “Learn more” menu — docs, install, shell V1, dev resources, contact, license.
struct LearnMoreResourcesView: View {
    @ObservedObject var viewModel: ScanViewModel
    var onDarkBackground: Bool
    var onShowShellEdition: () -> Void
    @Binding var isExpanded: Bool

    @State private var showLicenseNotice = false
    @State private var contactCopied = false

    private var linkColor: Color { onDarkBackground ? ReportTheme.cyan : .accentColor }
    private var accentGold: Color { onDarkBackground ? ReportTheme.gold : .orange }
    private var itemFont: Font { .system(size: 14) }
    private var sectionFont: Font { .system(size: 12, weight: .semibold) }

    var body: some View {
        ExpandableSection(
            title: "Learn more",
            subtitle: "Documentation, install, shell V1, developers, contact",
            systemImage: "book.fill",
            onDarkBackground: onDarkBackground,
            isExpanded: $isExpanded
        ) {
            VStack(alignment: .leading, spacing: 14) {
                resourceSection("About this app") {
                    resourceButton("What is this app for?") { viewModel.showHelp = true }
                    resourceLink("Documentation on GitHub", url: AppBrand.Support.documentation)
                    resourceLink("UI design reference (mockups)", url: AppBrand.Support.uiDesignMocks)
                    resourceLink("Mac app architecture guide", url: AppBrand.Support.swiftAppGuide)
                }
                resourceSection("Install & updates") {
                    resourceButton("Release notes & install guide (INSTALL.txt)") {
                        AppBrand.Support.openBundledInstallGuide()
                    }
                    resourceLink("Get new install (GitHub Releases)", url: AppBrand.Support.macInstallReleases)
                    resourceLink("Project home (muzar.io)", url: AppBrand.Support.muzarHome)
                }
                resourceSection("Web Audit shell V1") {
                    resourceButton("Shell V1 options…") { onShowShellEdition() }
                        .foregroundStyle(accentGold)
                    resourceLink("V1 documentation", url: AppBrand.ShellEdition.docs)
                        .foregroundStyle(accentGold)
                    resourceLink("V1 script source", url: AppBrand.ShellEdition.readScript)
                        .foregroundStyle(accentGold)
                    resourceLink("v1 vs v2 report examples", url: AppBrand.ShellEdition.reportComparison)
                        .foregroundStyle(accentGold)
                }
                resourceSection("Developers") {
                    resourceLink("Docker image (GHCR package)", url: AppBrand.Support.dockerPackage)
                    Text(AppBrand.Support.dockerPullImage)
                        .font(.system(size: 12, design: .monospaced))
                        .foregroundStyle(.secondary)
                        .textSelection(.enabled)
                    resourceLink("Report an issue on GitHub", url: AppBrand.Support.issueTracker)
                }
                contactSection
                resourceButton("License") { showLicenseNotice = true }
            }
            .padding(.top, 2)
        }
        .alert("License", isPresented: $showLicenseNotice) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(AppBrand.Support.licenseNotice)
        }
    }

    private var contactSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Contact developers")
                .font(sectionFont)
                .foregroundStyle(onDarkBackground ? ReportTheme.muted : .secondary)
            Text(DeveloperContactHelper.emailAddress)
                .font(.system(size: 15, weight: .medium, design: .monospaced))
                .foregroundStyle(linkColor)
                .textSelection(.enabled)
            Text("Select the address above to copy, or use the buttons below.")
                .font(.system(size: 12))
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
            HStack(spacing: 10) {
                Button("Open in Mail") {
                    DeveloperContactHelper.openEmailComposer()
                }
                .buttonStyle(.bordered)
                Button(contactCopied ? "Copied!" : "Copy email address") {
                    DeveloperContactHelper.copyEmailAddress()
                    contactCopied = true
                    DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                        contactCopied = false
                    }
                }
                .buttonStyle(.bordered)
            }
        }
    }

    private func resourceSection<Content: View>(_ title: String, @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title.uppercased())
                .font(.system(size: 11, weight: .bold))
                .tracking(0.6)
                .foregroundStyle(onDarkBackground ? ReportTheme.muted : .secondary)
            VStack(alignment: .leading, spacing: 5) {
                content()
            }
            .padding(.leading, 4)
        }
        .padding(.vertical, 4)
    }

    private func resourceButton(_ title: String, action: @escaping () -> Void) -> some View {
        Button(title, action: action)
            .buttonStyle(.link)
            .font(itemFont)
            .foregroundStyle(linkColor)
    }

    private func resourceLink(_ title: String, url: URL) -> some View {
        Link(title, destination: url)
            .font(itemFont)
            .foregroundStyle(linkColor)
    }
}

/// Compact contact row for error screens and help sheet.
struct DeveloperContactRow: View {
    @State private var copied = false

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Contact developers")
                .font(.system(size: 13, weight: .semibold))
            Text(DeveloperContactHelper.emailAddress)
                .font(.system(size: 14, design: .monospaced))
                .textSelection(.enabled)
            HStack(spacing: 10) {
                Button("Open in Mail") {
                    DeveloperContactHelper.openEmailComposer()
                }
                .buttonStyle(.bordered)
                Button(copied ? "Copied!" : "Copy email") {
                    DeveloperContactHelper.copyEmailAddress()
                    copied = true
                    DispatchQueue.main.asyncAfter(deadline: .now() + 2) { copied = false }
                }
                .buttonStyle(.bordered)
                Link("GitHub issues", destination: AppBrand.Support.issueTracker)
                    .font(.system(size: 13))
            }
        }
    }
}
