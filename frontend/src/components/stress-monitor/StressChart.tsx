import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceArea,
} from "recharts";
import { Skeleton } from "@/components/ui/skeleton";
import type { HistoryEntry } from "@/types/stress-monitor";

interface StressChartProps {
  data?: HistoryEntry[];
  isLoading: boolean;
}

function formatDateLabel(rawDate: string): string {
  const normalized = /^\d{4}-\d{2}$/.test(rawDate) ? `${rawDate}-01` : rawDate;
  const parsed = new Date(normalized);
  if (Number.isNaN(parsed.getTime())) return rawDate;
  return parsed.toLocaleDateString("en-SG", { year: "numeric", month: "short" });
}

function getRegimeRegions(data: HistoryEntry[]) {
  const regions: { start: string; end: string; regime: string }[] = [];
  let current: { start: string; regime: string } | null = null;

  for (const entry of data) {
    if (entry.regime) {
      if (!current || current.regime !== entry.regime) {
        if (current) regions.push({ ...current, end: entry.date });
        current = { start: entry.date, regime: entry.regime };
      }
    } else if (current) {
      regions.push({ ...current, end: entry.date });
      current = null;
    }
  }
  if (current) regions.push({ ...current, end: data[data.length - 1].date });
  return regions;
}

export function StressChart({ data, isLoading }: StressChartProps) {
  if (isLoading) {
    return (
      <section className="py-8">
        <h2 className="text-2xl font-semibold text-foreground mb-6">Historical Trend</h2>
        <Skeleton className="h-72 w-full rounded-lg" />
      </section>
    );
  }

  if (!data?.length) {
    return (
      <section className="py-8">
        <h2 className="text-2xl font-semibold text-foreground mb-6">Historical Trend</h2>
        <p className="text-muted-foreground">No historical data available.</p>
      </section>
    );
  }

  const regions = getRegimeRegions(data);

  return (
    <section className="py-8">
      <h2 className="text-2xl font-semibold text-foreground mb-6">Historical Trend</h2>
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
            <XAxis
              dataKey="date"
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(value) => formatDateLabel(String(value))}
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              width={36}
            />
            <Tooltip
              contentStyle={{
                borderRadius: "8px",
                border: "1px solid hsl(var(--border))",
                boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
              }}
              labelFormatter={(label) => `Date: ${formatDateLabel(String(label))}`}
              formatter={(value: number | string) => [typeof value === "number" ? value.toFixed(1) : value, "Stress Score"]}
            />
            {regions.map((r, i) => (
              <ReferenceArea
                key={`${r.start}-${r.end}-${r.regime}-${i}`}
                x1={r.start}
                x2={r.end}
                fill="hsl(var(--destructive))"
                fillOpacity={0.08}
                strokeOpacity={0}
              />
            ))}
            <Line
              type="monotone"
              dataKey="score"
              stroke="hsl(var(--primary))"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 5, stroke: "hsl(var(--primary))", strokeWidth: 2, fill: "hsl(var(--background))" }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
