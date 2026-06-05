import SwiftUI

struct ContentWidthKey: PreferenceKey {
    static var defaultValue: CGFloat = 720

    static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) {
        value = nextValue()
    }
}

struct LayoutMetrics {
    let width: CGFloat

    var scale: CGFloat { min(1.4, max(1.0, width / 880)) }
    var isTwoColumn: Bool { width >= 860 }
    var cardWidth: CGFloat { isTwoColumn ? (width - columnSpacing) / 2 : width }
    var featureColumns: Int { cardWidth >= 420 ? 2 : 1 }
    var heroMarkSize: CGFloat { 48 * scale }
    var sectionTitle: Font { .system(size: 19 * scale, weight: .semibold) }
    var rowTitle: Font { .system(size: 16 * scale, weight: .semibold) }
    var bodyFont: Font { .system(size: 15 * scale) }
    var captionFont: Font { .system(size: 13 * scale) }
    var finePrintFont: Font { .system(size: 12 * scale) }
    var heroTitle: Font { .system(size: 22 * scale, weight: .bold) }
    var phaseHeadline: Font { .system(size: 18 * scale, weight: .semibold) }
    var logFont: Font { .system(size: 14 * scale, design: .monospaced) }
    var cardPadding: CGFloat { 16 * scale }
    var columnSpacing: CGFloat { 16 * scale }
}

struct FeatureItem: Identifiable {
    let id: String
    let icon: String
    let color: Color
    let title: String
    let detail: String
}

extension View {
    func trackContentWidth(_ width: Binding<CGFloat>) -> some View {
        background {
            GeometryReader { geometry in
                Color.clear
                    .preference(key: ContentWidthKey.self, value: geometry.size.width)
            }
        }
        .onPreferenceChange(ContentWidthKey.self) { width.wrappedValue = $0 }
    }
}
