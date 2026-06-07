import AppKit
import SwiftUI

enum AppBrand {
    static let repoURL = URL(string: "https://github.com/Vlad-1618M/web_audit")!

    enum Support {
        static let contactEmailAddress = "contact@muzar.io"
        static let documentation = URL(
            string: "https://github.com/Vlad-1618M/web_audit/blob/v.tools_main/v2_python_core/docs/getting_started_plain.md"
        )!
        static let swiftAppGuide = URL(
            string: "https://github.com/Vlad-1618M/web_audit/blob/v.tools_main/macos/WebAuditMac/SWIFT_APP_GUIDE.md"
        )!
        static let uiDesignMocks = URL(
            string: "https://github.com/Vlad-1618M/web_audit/tree/v.tools_main/designs/swift"
        )!
        static let muzarHome = URL(string: "https://muzar.io/")!
        /// Published Mac .dmg downloads (tag `macos-v*` when released).
        static let macInstallReleases = URL(string: "https://github.com/Vlad-1618M/web_audit/releases")!
        static let issueTracker = URL(string: "https://github.com/Vlad-1618M/web_audit/issues")!
        static let dockerPackage = URL(
            string: "https://github.com/Vlad-1618M/web_audit/pkgs/container/webaudit"
        )!
        static let dockerPullImage = "ghcr.io/vlad-1618m/webaudit:latest"

        static var licenseNotice: String { AppDistribution.licenseNotice }

        static func openBundledInstallGuide() {
            guard let url = bundledResourceURL(name: "INSTALL", ext: "txt") else { return }
            NSWorkspace.shared.open(url)
        }

        private static func bundledResourceURL(name: String, ext: String) -> URL? {
            resourceURL(name: name, ext: ext)
        }
    }

    private static let spmResourceBundleName = "WebAuditMac_WebAuditMac"

    /// SPM executable resources ship as a sibling `.bundle` under Contents/Resources/.
    /// Never use `Bundle.module` — it fatals when that bundle is absent from the .app.
    private static var spmResourceBundle: Bundle? {
        guard let url = Bundle.main.url(
            forResource: spmResourceBundleName,
            withExtension: "bundle"
        ) else { return nil }
        return Bundle(url: url)
    }

    private static var resourceBundles: [Bundle] {
        var bundles = [Bundle.main]
        if let spm = spmResourceBundle {
            bundles.append(spm)
        }
        return bundles
    }

    private static func resourceURL(name: String, ext: String) -> URL? {
        for bundle in resourceBundles {
            if let url = bundle.url(forResource: name, withExtension: ext) {
                return url
            }
        }
        return nil
    }

    /// Web Audit shell version V1 — bash script for users who prefer Terminal.
    enum ShellEdition {
        static let label = "Web Audit shell version V1"
        static let docs = URL(string: "https://github.com/Vlad-1618M/web_audit#v1-audit-lite--bash-quick-start")!
        static let readmeV1 = docs
        static let readScript = URL(string: "https://github.com/Vlad-1618M/web_audit/blob/v.tools_main/web_audit.sh")!
        static let downloadScript = URL(string: "https://raw.githubusercontent.com/Vlad-1618M/web_audit/v.tools_main/web_audit.sh")!
        static let reportComparison = URL(
            string: "https://github.com/Vlad-1618M/web_audit/blob/v.tools_main/v2_python_core/README.md#report-examples---v1-shell-based-vs-v2-python-core"
        )!

        static func openDocs() {
            NSWorkspace.shared.open(docs)
        }

        static func openReadScript() {
            NSWorkspace.shared.open(readScript)
        }

        static func openDownloadScript() {
            NSWorkspace.shared.open(downloadScript)
        }
    }

    static var trademarkImage: NSImage? {
        loadImage(named: "vtool-trademark")
            ?? loadImage(named: "webaudit")
    }

    private static func loadImage(named name: String) -> NSImage? {
        for bundle in resourceBundles {
            if let url = bundle.url(forResource: name, withExtension: "png"),
               let image = NSImage(contentsOf: url) {
                return image
            }
        }
        if let repo = ProcessInfo.processInfo.environment["WEBAUDIT_REPO"] {
            for path in ["\(repo)/png/\(name).png", "\(repo)/png/vtool-trademark.png"] {
                if let image = NSImage(contentsOfFile: path) {
                    return image
                }
            }
        }
        return nil
    }
}

/// Vtools trademark — footer only; opens the GitHub repo when clicked.
struct TrademarkLink: View {
    var size: CGFloat = 32

    var body: some View {
        Link(destination: AppBrand.repoURL) {
            Group {
                if let logo = AppBrand.trademarkImage {
                    Image(nsImage: logo)
                        .resizable()
                        .interpolation(.high)
                        .scaledToFit()
                } else {
                    Image(systemName: "lock.shield.fill")
                        .font(.system(size: size * 0.5))
                        .foregroundStyle(ReportTheme.cyan)
                }
            }
            .frame(width: size, height: size)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .help("Vtools — open Web Audit repository on GitHub")
    }
}

/// Generic app mark for chrome & hero — globe + shield, report palette (not the Vtools trademark).
struct WebAuditMark: View {
    var size: CGFloat = 40

    var body: some View {
        ZStack {
            Circle()
                .fill(
                    LinearGradient(
                        colors: [
                            ReportTheme.surface2,
                            ReportTheme.cyan.opacity(0.12),
                        ],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
            Circle()
                .stroke(
                    LinearGradient(
                        colors: [ReportTheme.cyan.opacity(0.7), ReportTheme.lime.opacity(0.5)],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    ),
                    lineWidth: max(1.5, size * 0.04)
                )
            Image(systemName: "network.badge.shield.half.filled")
                .font(.system(size: size * 0.44, weight: .semibold))
                .symbolRenderingMode(.palette)
                .foregroundStyle(ReportTheme.cyan, ReportTheme.lime)
        }
        .frame(width: size, height: size)
        .shadow(color: ReportTheme.cyan.opacity(0.2), radius: size * 0.12)
        .accessibilityLabel("Web Audit")
    }
}
