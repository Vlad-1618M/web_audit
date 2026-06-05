import AppKit
import Foundation

struct EmailShareOption: Identifiable {
    let id: String
    let title: String
    let subtitle: String
    let icon: NSImage?
    let systemSymbol: String
}

enum EmailShareError: LocalizedError {
    case appleMailFailed(String)
    case gmailOpenFailed

    var errorDescription: String? {
        switch self {
        case .appleMailFailed(let detail):
            return "Could not open Apple Mail: \(detail)"
        case .gmailOpenFailed:
            return "Could not open Gmail in your browser."
        }
    }
}

/// Email paths that actually support zip attachments (macOS ``composeEmail`` cannot when Chrome is the default handler).
enum EmailShareHelper {
    static func availableOptions() -> [EmailShareOption] {
        var options: [EmailShareOption] = []

        if isAppleMailInstalled {
            options.append(
                EmailShareOption(
                    id: "apple-mail",
                    title: "Apple Mail",
                    subtitle: "New message with zip attached",
                    icon: NSWorkspace.shared.icon(forFile: "/Applications/Mail.app"),
                    systemSymbol: "envelope.fill"
                )
            )
        }

        options.append(
            EmailShareOption(
                id: "gmail",
                title: "Gmail in browser",
                subtitle: gmailBrowserHint(),
                icon: nil,
                systemSymbol: "globe"
            )
        )

        if let handler = defaultMailHandlerName(), handler != "Mail" {
            options.append(
                EmailShareOption(
                    id: "system-default",
                    title: "Default email app (\(handler))",
                    subtitle: "May open browser only — attachments often do not work",
                    icon: defaultMailHandlerIcon(),
                    systemSymbol: "arrow.up.forward.app"
                )
            )
        }

        return options
    }

    static func composeWithAppleMail(
        zipURL: URL,
        hostLabel: String,
        body: String
    ) throws {
        let subject = "Web Audit report — \(hostLabel)"
        let script = """
        tell application "Mail"
            activate
            set newMessage to make new outgoing message with properties {subject:"\(appleScriptEscape(subject))", content:"\(appleScriptEscape(body))", visible:true}
            tell newMessage
                make new attachment with properties {file name: POSIX file "\(appleScriptEscape(zipURL.path))"} at after the last paragraph
            end tell
        end tell
        """

        var errorInfo: NSDictionary?
        guard let scriptObject = NSAppleScript(source: script) else {
            throw EmailShareError.appleMailFailed("Could not build Mail script.")
        }
        scriptObject.executeAndReturnError(&errorInfo)
        if let errorInfo {
            let message = (errorInfo[NSAppleScript.errorMessage] as? String) ?? "Unknown AppleScript error"
            throw EmailShareError.appleMailFailed(message)
        }
    }

    @MainActor
    static func openGmailCompose(
        zipURL: URL,
        hostLabel: String,
        body: String
    ) throws {
        let subject = "Web Audit report — \(hostLabel)"
        var components = URLComponents(string: "https://mail.google.com/mail/")!
        components.queryItems = [
            URLQueryItem(name: "view", value: "cm"),
            URLQueryItem(name: "fs", value: "1"),
            URLQueryItem(name: "su", value: subject),
            URLQueryItem(name: "body", value: body + "\n\nAttach the Web Audit zip from Finder (shown automatically)."),
        ]
        guard let url = components.url else {
            throw EmailShareError.gmailOpenFailed
        }

        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(zipURL.path, forType: .string)

        NSWorkspace.shared.activateFileViewerSelecting([zipURL])
        guard NSWorkspace.shared.open(url) else {
            throw EmailShareError.gmailOpenFailed
        }
    }

    @MainActor
    static func openSystemDefaultEmail(zipURL: URL, hostLabel: String, body: String) {
        guard let service = NSSharingService(named: .composeEmail) else { return }
        service.subject = "Web Audit report — \(hostLabel)"
        service.perform(withItems: [zipURL])
    }

    static var isAppleMailInstalled: Bool {
        NSWorkspace.shared.urlForApplication(withBundleIdentifier: "com.apple.mail") != nil
    }

    static func defaultMailHandlerName() -> String? {
        guard let mailto = URL(string: "mailto:"),
              let appURL = NSWorkspace.shared.urlForApplication(toOpen: mailto) else {
            return nil
        }
        return FileManager.default.displayName(atPath: appURL.path)
            .replacingOccurrences(of: ".app", with: "")
    }

    private static func defaultMailHandlerIcon() -> NSImage? {
        guard let mailto = URL(string: "mailto:"),
              let appURL = NSWorkspace.shared.urlForApplication(toOpen: mailto) else {
            return nil
        }
        return NSWorkspace.shared.icon(forFile: appURL.path)
    }

    private static func gmailBrowserHint() -> String {
        if let handler = defaultMailHandlerName(), handler.localizedCaseInsensitiveContains("chrome") {
            return "Opens Gmail compose in Chrome · zip shown in Finder to attach"
        }
        return "Opens Gmail compose · zip shown in Finder to attach"
    }

    private static func appleScriptEscape(_ value: String) -> String {
        value
            .replacingOccurrences(of: "\\", with: "\\\\")
            .replacingOccurrences(of: "\"", with: "\\\"")
    }
}
