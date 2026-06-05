import AppKit
import Foundation

/// Contact support — copyable address + Apple Mail when available (avoids browser-only mailto handlers).
enum DeveloperContactHelper {
    static let emailAddress = AppBrand.Support.contactEmailAddress

    static func copyEmailAddress() {
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(emailAddress, forType: .string)
    }

    @MainActor
    static func openEmailComposer() {
        if openAppleMailCompose() { return }
        if openSharingServiceCompose() { return }
        if let url = URL(string: "mailto:\(emailAddress)") {
            NSWorkspace.shared.open(url)
        }
    }

    @discardableResult
    private static func openAppleMailCompose() -> Bool {
        guard EmailShareHelper.isAppleMailInstalled else { return false }
        let script = """
        tell application "Mail"
            activate
            set newMessage to make new outgoing message with properties {subject:"Web Audit Pro support", visible:true}
            tell newMessage
                make new to recipient at end of to recipients with properties {address:"\(appleScriptEscape(emailAddress))"}
            end tell
        end tell
        """
        var errorInfo: NSDictionary?
        guard let scriptObject = NSAppleScript(source: script) else { return false }
        scriptObject.executeAndReturnError(&errorInfo)
        return errorInfo == nil
    }

    @MainActor
    @discardableResult
    private static func openSharingServiceCompose() -> Bool {
        guard let service = NSSharingService(named: .composeEmail) else { return false }
        service.recipients = [emailAddress]
        service.subject = "Web Audit Pro support"
        service.perform(withItems: [""])
        return true
    }

    private static func appleScriptEscape(_ value: String) -> String {
        value
            .replacingOccurrences(of: "\\", with: "\\\\")
            .replacingOccurrences(of: "\"", with: "\\\"")
    }
}
