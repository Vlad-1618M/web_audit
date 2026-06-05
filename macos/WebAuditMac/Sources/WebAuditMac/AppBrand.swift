import AppKit
import SwiftUI

enum AppBrand {
    static let repoURL = URL(string: "https://github.com/Vlad-1618M/web_audit")!

    /// v1 Audit Lite — for users who prefer to read or download the shell script.
    enum ShellEdition {
        static let readmeV1 = URL(string: "https://github.com/Vlad-1618M/web_audit#v1-audit-lite--bash-quick-start")!
        static let readScript = URL(string: "https://github.com/Vlad-1618M/web_audit/blob/v.tools_main/web_audit.sh")!
        static let downloadScript = URL(string: "https://raw.githubusercontent.com/Vlad-1618M/web_audit/v.tools_main/web_audit.sh")!
        static let reportComparison = URL(
            string: "https://github.com/Vlad-1618M/web_audit/blob/v.tools_main/v2_python_core/README.md#report-examples---v1-shell-based-vs-v2-python-core"
        )!

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
        for bundle in [Bundle.main, Bundle.module] {
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
