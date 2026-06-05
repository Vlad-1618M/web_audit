import AppKit
import SwiftUI

struct ShareReportContext: Identifiable, Equatable {
    let id = UUID()
    let zipURL: URL
    let hostLabel: String
}

struct ReportShareSheet: View {
    let context: ShareReportContext
    var onDismiss: () -> Void

    @State private var emailOptions: [EmailShareOption] = []
    @State private var services: [NSSharingService] = []
    @State private var errorMessage: String?

    private var shareItems: [Any] {
        [shareNote, context.zipURL as NSURL]
    }

    private var fileItems: [Any] {
        [context.zipURL as NSURL]
    }

    private var shareNote: String {
        "Web Audit report for \(context.hostLabel). Unzip the attachment, keep report.html and report.css together, then double-click report.html."
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Share report")
                .font(.system(size: 22, weight: .bold))

            Text("Send the zip (HTML + CSS + instructions). For Gmail users, choose Gmail in browser — the generic Mail row cannot attach files through Chrome.")
                .font(.system(size: 15))
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)

            ScrollView {
                VStack(spacing: 8) {
                    if !emailOptions.isEmpty {
                        Text("Email")
                            .font(.system(size: 12, weight: .semibold))
                            .foregroundStyle(.secondary)
                            .textCase(.uppercase)
                            .frame(maxWidth: .infinity, alignment: .leading)

                        ForEach(emailOptions) { option in
                            ShareActionRow(option: option) {
                                performEmailShare(option)
                            }
                        }
                    }

                    if !services.isEmpty {
                        Text("Other apps")
                            .font(.system(size: 12, weight: .semibold))
                            .foregroundStyle(.secondary)
                            .textCase(.uppercase)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(.top, emailOptions.isEmpty ? 0 : 6)

                        ForEach(Array(services.enumerated()), id: \.offset) { _, service in
                            ShareServiceRow(service: service) {
                                performShare(using: service)
                            }
                        }
                    }
                }
            }
            .frame(maxHeight: 320)

            if emailOptions.isEmpty && services.isEmpty {
                emptyState
            }

            Divider()

            Button("More sharing options…") {
                ShareSheetPresenter.showSystemPicker(items: fileItems)
            }
            .buttonStyle(.bordered)

            Text("WhatsApp and social apps only appear if their Mac app registers with macOS Share.")
                .font(.system(size: 12))
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)

            HStack {
                Spacer()
                Button("Cancel") { onDismiss() }
                    .keyboardShortcut(.cancelAction)
            }
        }
        .padding(24)
        .frame(width: 460)
        .onAppear { reloadOptions() }
        .alert("Could not send email", isPresented: Binding(
            get: { errorMessage != nil },
            set: { if !$0 { errorMessage = nil } }
        )) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(errorMessage ?? "")
        }
    }

    @ViewBuilder
    private var emptyState: some View {
        VStack(alignment: .leading, spacing: 10) {
            Label("No other share apps detected", systemImage: "exclamationmark.triangle")
                .font(.system(size: 15, weight: .semibold))
                .foregroundStyle(.orange)
            Text("Use an email option above, More sharing options…, or Save report to share…")
                .font(.system(size: 14))
                .foregroundStyle(.secondary)
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.orange.opacity(0.08))
        .clipShape(RoundedRectangle(cornerRadius: 10))
    }

    private func reloadOptions() {
        emailOptions = EmailShareHelper.availableOptions()
        services = ShareSheetPresenter.availableServices(fileItems: fileItems, fullItems: shareItems)
    }

    private func performEmailShare(_ option: EmailShareOption) {
        do {
            switch option.id {
            case "apple-mail":
                try EmailShareHelper.composeWithAppleMail(
                    zipURL: context.zipURL,
                    hostLabel: context.hostLabel,
                    body: shareNote
                )
            case "gmail":
                try EmailShareHelper.openGmailCompose(
                    zipURL: context.zipURL,
                    hostLabel: context.hostLabel,
                    body: shareNote
                )
            case "system-default":
                EmailShareHelper.openSystemDefaultEmail(
                    zipURL: context.zipURL,
                    hostLabel: context.hostLabel,
                    body: shareNote
                )
            default:
                break
            }
            onDismiss()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func performShare(using service: NSSharingService) {
        service.perform(withItems: shareItems)
        onDismiss()
    }
}

private struct ShareActionRow: View {
    let option: EmailShareOption
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 12) {
                Group {
                    if let icon = option.icon {
                        Image(nsImage: icon)
                            .resizable()
                            .scaledToFit()
                    } else {
                        Image(systemName: option.systemSymbol)
                            .font(.system(size: 20))
                            .foregroundStyle(.secondary)
                    }
                }
                .frame(width: 28, height: 28)

                VStack(alignment: .leading, spacing: 2) {
                    Text(option.title)
                        .font(.system(size: 16, weight: .medium))
                        .foregroundStyle(.primary)
                    Text(option.subtitle)
                        .font(.system(size: 12))
                        .foregroundStyle(.secondary)
                        .multilineTextAlignment(.leading)
                }
                Spacer()
                Image(systemName: "chevron.right")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.tertiary)
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 10)
            .background(Color(nsColor: .controlBackgroundColor))
            .clipShape(RoundedRectangle(cornerRadius: 10))
            .overlay(
                RoundedRectangle(cornerRadius: 10)
                    .stroke(Color.secondary.opacity(0.2), lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
    }
}

private struct ShareServiceRow: View {
    let service: NSSharingService
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 12) {
                Image(nsImage: service.image)
                    .resizable()
                    .scaledToFit()
                    .frame(width: 28, height: 28)
                Text(service.title)
                    .font(.system(size: 16, weight: .medium))
                    .foregroundStyle(.primary)
                Spacer()
                Image(systemName: "chevron.right")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.tertiary)
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 10)
            .background(Color(nsColor: .controlBackgroundColor))
            .clipShape(RoundedRectangle(cornerRadius: 10))
            .overlay(
                RoundedRectangle(cornerRadius: 10)
                    .stroke(Color.secondary.opacity(0.2), lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
    }
}

/// Presents ``NSSharingServicePicker`` and lists non-email macOS share services.
enum ShareSheetPresenter {
    private static let priority = ["Messages", "AirDrop"]

    @MainActor
    static func availableServices(fileItems: [Any], fullItems: [Any]) -> [NSSharingService] {
        var merged: [NSSharingService] = []
        var seen = Set<String>()

        func add(_ service: NSSharingService?) {
            guard let service, !service.title.isEmpty else { return }
            if service.title.localizedCaseInsensitiveContains("mail") { return }
            if seen.insert(service.title).inserted {
                merged.append(service)
            }
        }

        let standardNames: [NSSharingService.Name] = [
            .composeMessage,
            .sendViaAirDrop,
        ]
        for name in standardNames {
            add(NSSharingService(named: name))
        }

        for service in NSSharingService.sharingServices(forItems: fileItems) {
            add(service)
        }
        for service in NSSharingService.sharingServices(forItems: fullItems) {
            add(service)
        }

        return sorted(merged)
    }

    @MainActor
    static func showSystemPicker(items: [Any]) {
        let picker = NSSharingServicePicker(items: items)

        let windows = [NSApp.keyWindow, NSApp.mainWindow].compactMap { $0 }
            + NSApp.windows.filter { $0.isVisible }

        for window in windows {
            guard let contentView = window.contentView else { continue }
            let anchor = NSRect(
                x: contentView.bounds.midX - 1,
                y: contentView.bounds.midY,
                width: 2,
                height: 2
            )
            picker.show(relativeTo: anchor, of: contentView, preferredEdge: .maxY)
            return
        }
    }

    private static func sorted(_ services: [NSSharingService]) -> [NSSharingService] {
        services.sorted { a, b in
            let ia = priority.firstIndex(where: { a.title.localizedCaseInsensitiveContains($0) }) ?? 999
            let ib = priority.firstIndex(where: { b.title.localizedCaseInsensitiveContains($0) }) ?? 999
            if ia != ib { return ia < ib }
            return a.title.localizedCaseInsensitiveCompare(b.title) == .orderedAscending
        }
    }
}
