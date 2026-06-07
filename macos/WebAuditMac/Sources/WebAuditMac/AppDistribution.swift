import Foundation

/// How this `.app` was packaged — set in `Info.plist` at bundle time (`WEBAUDITDistributionChannel`).
enum AppDistribution {
    enum Channel: String {
        case unsigned
        case release
    }

    static var channel: Channel {
        guard let raw = Bundle.main.infoDictionary?["WEBAUDITDistributionChannel"] as? String,
              let value = Channel(rawValue: raw) else {
            return .unsigned
        }
        return value
    }

    static var isReleaseBuild: Bool { channel == .release }

    /// Advanced footer line (Help → Advanced).
    static var advancedFooterNotice: String {
        switch channel {
        case .release:
            return "Release build — Developer ID signed and notarized. Install from the official GitHub Releases DMG."
        case .unsigned:
            return "Beta (unsigned) — first launch may require Right-click → Open on Web Audit"
        }
    }

    /// Learn more / about copy.
    static var licenseNotice: String {
        switch channel {
        case .release:
            return """
            Web Audit Pro — each scan includes JavaScript rendering (--js) \
            and GraphQL/OpenAPI checks (--api). This build is Developer ID signed and notarized for macOS.
            """
        case .unsigned:
            return """
            Web Audit Pro — beta (unsigned build). Each scan includes JavaScript rendering (--js) \
            and GraphQL/OpenAPI checks (--api).

            If macOS blocks the app on first launch, open Applications, right-click Web Audit, \
            choose Open, then confirm Open once. The signed release on GitHub Releases skips this step.
            """
        }
    }
}
