import SwiftUI

/// Shared premium palette matching the web dashboard / Android app.
enum Palette {
    static let brand = Color(red: 0x22 / 255, green: 0xD3 / 255, blue: 0xEE / 255)   // cyan
    static let brand2 = Color(red: 0x81 / 255, green: 0x8C / 255, blue: 0xF8 / 255)  // indigo
    static let accent = Color(red: 0xF4 / 255, green: 0x72 / 255, blue: 0xB6 / 255)  // pink
    static let indigo = brand2
    static let amber = Color(red: 0xFB / 255, green: 0xBF / 255, blue: 0x24 / 255)
    static let emerald = Color(red: 0x34 / 255, green: 0xD3 / 255, blue: 0x99 / 255)
    static let rose = Color(red: 0xF8 / 255, green: 0x71 / 255, blue: 0x71 / 255)

    static let ink0 = Color(red: 0x06 / 255, green: 0x07 / 255, blue: 0x0D / 255)
    static let ink1 = Color(red: 0x0B / 255, green: 0x0D / 255, blue: 0x18 / 255)
    static let surface = Color(red: 0x15 / 255, green: 0x1A / 255, blue: 0x2C / 255)
    static let stroke = Color.white.opacity(0.10)
    static let textMuted = Color(red: 0x9A / 255, green: 0xA3 / 255, blue: 0xB8 / 255)

    static let brandGradient = LinearGradient(
        colors: [brand, brand2, accent],
        startPoint: .topLeading, endPoint: .bottomTrailing
    )
    static let chipGradient = LinearGradient(
        colors: [brand.opacity(0.28), brand2.opacity(0.28)],
        startPoint: .topLeading, endPoint: .bottomTrailing
    )
}

extension String {
    /// "phone_screen" -> "phone screen"
    var humanized: String { replacingOccurrences(of: "_", with: " ") }
}

/// Full-screen gradient mesh background with soft brand glow orbs.
struct ScreenBackground: View {
    var body: some View {
        ZStack {
            LinearGradient(
                colors: [Palette.ink0, Palette.ink1, Palette.ink0],
                startPoint: .topLeading, endPoint: .bottomTrailing
            )
            .ignoresSafeArea()

            RadialGradient(
                colors: [Palette.brand2.opacity(0.20), .clear],
                center: .topLeading, startRadius: 5, endRadius: 420
            )
            .ignoresSafeArea()

            RadialGradient(
                colors: [Palette.accent.opacity(0.16), .clear],
                center: .bottomTrailing, startRadius: 5, endRadius: 480
            )
            .ignoresSafeArea()
        }
    }
}

/// Gradient icon/avatar chip used for KPIs, match & source cards.
struct GradientChip: View {
    let text: String
    var size: CGFloat = 48
    var body: some View {
        Text(text)
            .font(.system(size: size * 0.42, weight: .bold))
            .foregroundStyle(Palette.brand)
            .frame(width: size, height: size)
            .background(Palette.chipGradient)
            .clipShape(RoundedRectangle(cornerRadius: size / 3, style: .continuous))
    }
}

extension View {
    /// Glassy elevated card surface used across all screens.
    func cardStyle() -> some View {
        self
            .padding(18)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Palette.surface.opacity(0.75))
            .background(.ultraThinMaterial)
            .clipShape(RoundedRectangle(cornerRadius: 22, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 22, style: .continuous)
                    .strokeBorder(Palette.stroke, lineWidth: 1)
            )
            .shadow(color: .black.opacity(0.45), radius: 18, x: 0, y: 12)
    }
}

