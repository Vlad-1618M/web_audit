import SwiftUI

/// Branded scan spinner — gradient arc + pulsing globe (replaces default ProgressView).
struct ScanProgressIndicator: View {
    @State private var rotation: Double = 0
    @State private var pulse = false

    var size: CGFloat = 48

    var body: some View {
        ZStack {
            Circle()
                .stroke(Color.secondary.opacity(0.2), lineWidth: 3.5)
                .frame(width: size, height: size)

            Circle()
                .trim(from: 0.08, to: 0.82)
                .stroke(
                    AngularGradient(
                        colors: [
                            ReportTheme.cyan.opacity(0.15),
                            ReportTheme.cyan,
                            ReportTheme.lime,
                            ReportTheme.violet.opacity(0.85),
                            ReportTheme.cyan.opacity(0.15),
                        ],
                        center: .center
                    ),
                    style: StrokeStyle(lineWidth: 3.5, lineCap: .round)
                )
                .frame(width: size, height: size)
                .rotationEffect(.degrees(rotation))
                .shadow(color: ReportTheme.cyan.opacity(0.35), radius: 6)

            Circle()
                .fill(
                    RadialGradient(
                        colors: [ReportTheme.cyan.opacity(pulse ? 0.22 : 0.08), .clear],
                        center: .center,
                        startRadius: 0,
                        endRadius: size * 0.45
                    )
                )
                .frame(width: size * 0.7, height: size * 0.7)

            Image(systemName: "globe.americas.fill")
                .font(.system(size: size * 0.34, weight: .semibold))
                .symbolRenderingMode(.palette)
                .foregroundStyle(ReportTheme.cyan, ReportTheme.lime.opacity(0.85))
                .scaleEffect(pulse ? 1.06 : 0.94)
        }
        .frame(width: size, height: size)
        .onAppear { startAnimations() }
    }

    private func startAnimations() {
        rotation = 0
        withAnimation(.linear(duration: 1.35).repeatForever(autoreverses: false)) {
            rotation = 360
        }
        withAnimation(.easeInOut(duration: 1.5).repeatForever(autoreverses: true)) {
            pulse = true
        }
    }
}
