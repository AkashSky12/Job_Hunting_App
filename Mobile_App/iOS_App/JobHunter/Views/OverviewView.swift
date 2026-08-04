import Charts
import SwiftUI

struct OverviewView: View {
    @EnvironmentObject var vm: AppViewModel

    private var interviews: Int {
        (vm.stats.funnel["interview"] ?? 0) + (vm.stats.funnel["phone_screen"] ?? 0)
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    HStack(spacing: 12) {
                        Button("Ingest jobs") { vm.ingest() }
                            .buttonStyle(.borderedProminent)
                        Button("Run matching") { vm.runMatching() }
                            .buttonStyle(.bordered)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)

                    LazyVGrid(columns: [GridItem(.adaptive(minimum: 150), spacing: 12)], spacing: 12) {
                        KpiCard(label: "Jobs", value: vm.stats.jobs, icon: "number")
                        KpiCard(label: "Matches", value: vm.stats.matches, icon: "sparkles")
                        KpiCard(label: "Applications", value: vm.stats.applications, icon: "tray.full")
                        KpiCard(label: "Interviews", value: interviews, icon: "phone")
                    }

                    trendCard
                    funnelCard
                }
                .padding()
            }
            .background(ScreenBackground())
            .navigationTitle("Overview")
            .refreshable { vm.loadOverview() }
        }
        .onAppear { vm.loadOverview() }
    }

    private var trendCard: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Activity — last 30 days").font(.title3.bold())
            if vm.trend.isEmpty {
                Text("No data yet").foregroundStyle(.secondary).frame(height: 120)
            } else {
                Chart {
                    ForEach(vm.trend) { p in
                        lineMarks(day: p.day, value: p.applied, series: "Applied", color: Palette.brand)
                        lineMarks(day: p.day, value: p.interviews, series: "Interviews", color: Palette.indigo)
                        lineMarks(day: p.day, value: p.offers, series: "Offers", color: Palette.amber)
                    }
                }
                .chartForegroundStyleScale([
                    "Applied": Palette.brand, "Interviews": Palette.indigo, "Offers": Palette.amber,
                ])
                .chartXAxis(.hidden)
                .frame(height: 170)
            }
        }
        .cardStyle()
    }

    @ChartContentBuilder
    private func lineMarks(day: String, value: Int, series: String, color: Color) -> some ChartContent {
        LineMark(x: .value("Day", day), y: .value("Count", value))
            .foregroundStyle(by: .value("Series", series))
            .interpolationMethod(.catmullRom)
            .lineStyle(StrokeStyle(lineWidth: 2.5))
        AreaMark(x: .value("Day", day), y: .value("Count", value))
            .foregroundStyle(
                LinearGradient(colors: [color.opacity(0.30), color.opacity(0.0)],
                               startPoint: .top, endPoint: .bottom)
            )
            .foregroundStyle(by: .value("Series", series))
            .interpolationMethod(.catmullRom)
    }

    private var funnelCard: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Application funnel").font(.title3.bold())
            if vm.stats.funnel.isEmpty {
                Text("No applications yet.").foregroundStyle(.secondary)
            } else {
                ForEach(vm.stats.funnel.sorted(by: { $0.key < $1.key }), id: \.key) { k, v in
                    HStack {
                        Circle().fill(funnelColor(k)).frame(width: 9, height: 9)
                        Text(k.humanized).foregroundStyle(.secondary)
                        Spacer()
                        Text("\(v)").fontWeight(.semibold)
                    }
                }
            }
        }
        .cardStyle()
    }

    private func funnelColor(_ key: String) -> Color {
        switch key {
        case "applied": return Palette.brand
        case "viewed": return Palette.brand2
        case "phone_screen": return Palette.accent
        case "interview": return Palette.emerald
        case "offer": return Palette.amber
        case "rejected": return Palette.rose
        default: return Palette.brand2
        }
    }
}

struct KpiCard: View {
    let label: String
    let value: Int
    var icon: String = "number"
    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            RoundedRectangle(cornerRadius: 2)
                .fill(Palette.brandGradient)
                .frame(height: 3)
            HStack {
                Text(label).font(.subheadline).foregroundStyle(.secondary)
                Spacer()
                Image(systemName: icon)
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundStyle(Palette.brand)
                    .frame(width: 40, height: 40)
                    .background(Palette.chipGradient)
                    .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
            }
            Text("\(value)").font(.system(size: 34, weight: .heavy))
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .cardStyle()
    }
}
