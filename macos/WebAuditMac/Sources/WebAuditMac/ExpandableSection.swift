import SwiftUI

/// Full-width expandable row — entire header (text + chevron) toggles open/closed.
struct ExpandableSection<Content: View>: View {
    let title: String
    var subtitle: String? = nil
    var systemImage: String = "info.circle"
    var onDarkBackground: Bool = false
    @Binding var isExpanded: Bool
    @ViewBuilder let content: () -> Content

    private var titleColor: Color { onDarkBackground ? ReportTheme.text : .primary }
    private var subtitleColor: Color { onDarkBackground ? ReportTheme.muted : .secondary }
    private var accentColor: Color { onDarkBackground ? ReportTheme.cyan : .accentColor }
    private var headerBackground: Color {
        onDarkBackground ? ReportTheme.surface2.opacity(0.85) : Color(nsColor: .controlBackgroundColor)
    }
    private var borderColor: Color {
        onDarkBackground ? Color.white.opacity(0.1) : Color.secondary.opacity(0.2)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Button {
                withAnimation(.easeInOut(duration: 0.2)) {
                    isExpanded.toggle()
                }
            } label: {
                HStack(alignment: .center, spacing: 12) {
                    Image(systemName: systemImage)
                        .font(.system(size: 18, weight: .semibold))
                        .foregroundStyle(accentColor)
                        .frame(width: 24)
                    VStack(alignment: .leading, spacing: 3) {
                        Text(title)
                            .font(.system(size: 15, weight: .semibold))
                            .foregroundStyle(titleColor)
                        if let subtitle {
                            Text(subtitle)
                                .font(.system(size: 12))
                                .foregroundStyle(subtitleColor)
                                .multilineTextAlignment(.leading)
                        }
                    }
                    Spacer(minLength: 8)
                    Image(systemName: isExpanded ? "chevron.up.circle.fill" : "chevron.down.circle.fill")
                        .font(.system(size: 20, weight: .medium))
                        .foregroundStyle(accentColor.opacity(0.9))
                        .symbolRenderingMode(.hierarchical)
                }
                .padding(.horizontal, 14)
                .padding(.vertical, 12)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(headerBackground)
                .clipShape(RoundedRectangle(cornerRadius: 10))
                .overlay(
                    RoundedRectangle(cornerRadius: 10)
                        .stroke(borderColor, lineWidth: 1)
                )
                .contentShape(RoundedRectangle(cornerRadius: 10))
            }
            .buttonStyle(.plain)
            .accessibilityAddTraits(.isButton)
            .accessibilityHint(isExpanded ? "Collapse section" : "Expand section")

            if isExpanded {
                content()
                    .padding(.top, 10)
                    .padding(.horizontal, 4)
                    .padding(.bottom, 4)
                    .transition(.opacity.combined(with: .move(edge: .top)))
            }
        }
    }
}
