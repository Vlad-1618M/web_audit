import SwiftUI

struct AboutDisclaimerPanel: View {
    var metrics: LayoutMetrics

    var body: some View {
        VStack(alignment: .leading, spacing: 12 * metrics.scale) {
            Text("About this scan")
                .font(metrics.sectionTitle)
                .foregroundStyle(ReportTheme.text)

            Text(
                "A passive, external hygiene snapshot — what a visitor or opportunistic attacker could observe without logging in. Written for site owners first; full evidence is in the HTML report."
            )
            .font(metrics.bodyFont)
            .foregroundStyle(ReportTheme.muted)
            .fixedSize(horizontal: false, vertical: true)

            disclaimerSection(
                title: "What it is",
                icon: "checkmark.circle.fill",
                tint: ReportTheme.lime,
                items: [
                    "An outside-in check after deploys, DNS, or cert changes.",
                    "Catches obvious misconfigurations — headers, TLS, email auth, exposed paths, plugins.",
                    "A conversation starter: urgent fixes vs. what can wait.",
                ]
            )

            disclaimerSection(
                title: "What it is not",
                icon: "xmark.circle.fill",
                tint: ReportTheme.coral,
                items: [
                    "Not a penetration test — no exploitation or login bypass.",
                    "Not authenticated testing — no member areas or admin consoles.",
                    "Not a CDN/WAF dashboard — edge rules may hide or block what we see.",
                    "Not compliance certification (PCI, HIPAA, SOC 2, ISO).",
                ]
            )

            Text("Passive external scan only — not a substitute for authenticated testing or CDN/WAF review. Open Learn more below for documentation, contact, and other resources.")
                .font(metrics.finePrintFont)
                .foregroundStyle(ReportTheme.muted.opacity(0.9))
                .fixedSize(horizontal: false, vertical: true)
                .padding(.top, 4)
        }
        .padding(metrics.cardPadding)
        .frame(maxWidth: .infinity, alignment: .topLeading)
        .background(ReportTheme.surface.opacity(0.65))
        .overlay(
            RoundedRectangle(cornerRadius: 14)
                .stroke(ReportTheme.gold.opacity(0.25), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: 14))
    }

    private func disclaimerSection(title: String, icon: String, tint: Color, items: [String]) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Label(title, systemImage: icon)
                .font(metrics.rowTitle)
                .foregroundStyle(tint)
            ForEach(items, id: \.self) { item in
                HStack(alignment: .top, spacing: 8) {
                    Text("·")
                        .foregroundStyle(ReportTheme.muted)
                    Text(item)
                        .font(metrics.bodyFont)
                        .foregroundStyle(ReportTheme.text.opacity(0.9))
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
    }
}
