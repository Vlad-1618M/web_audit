import SwiftUI

struct BrandingFooterView: View {
    var onDarkBackground: Bool = false

    var body: some View {
        HStack(alignment: .center, spacing: 12) {
            TrademarkLink(size: onDarkBackground ? 36 : 32)
            VStack(alignment: .leading, spacing: 4) {
                HStack(spacing: 4) {
                    Text("Powered by")
                        .foregroundStyle(onDarkBackground ? ReportTheme.muted : .secondary)
                    Link("muzar.io", destination: URL(string: "https://muzar.io/")!)
                        .foregroundStyle(onDarkBackground ? ReportTheme.cyan : .accentColor)
                    Text("·")
                        .foregroundStyle(onDarkBackground ? ReportTheme.muted : .secondary)
                    Link("GitHub", destination: AppBrand.repoURL)
                        .foregroundStyle(onDarkBackground ? ReportTheme.cyan : .accentColor)
                }
                .font(.caption)
                Text("© 2026 Vtools. All rights reserved.")
                    .font(.caption)
                    .foregroundStyle(onDarkBackground ? ReportTheme.muted.opacity(0.8) : Color.secondary.opacity(0.8))
            }
            Spacer(minLength: 0)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.top, 8)
    }
}
