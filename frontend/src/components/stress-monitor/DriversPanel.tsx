import { Skeleton } from "@/components/ui/skeleton";
import type { Indicator } from "@/types/stress-monitor";

interface DriversPanelProps {
  drivers?: Indicator[];
  isLoading: boolean;
}

export function DriversPanel({ drivers, isLoading }: DriversPanelProps) {
  if (isLoading) {
    return (
      <section className="py-8">
        <h2 className="text-2xl font-semibold text-foreground mb-6">Stress Drivers</h2>
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-8 w-full" />
          ))}
        </div>
      </section>
    );
  }

  if (!drivers?.length) {
    return (
      <section className="py-8">
        <h2 className="text-2xl font-semibold text-foreground mb-6">Stress Drivers</h2>
        <p className="text-muted-foreground">No driver data available.</p>
      </section>
    );
  }

  const negative = drivers
    .filter((d) => d.direction === "negative")
    .sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution));
  const positive = drivers
    .filter((d) => d.direction === "positive")
    .sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution));
  const maxMagnitude = Math.max(1, ...drivers.map((d) => Math.abs(d.contribution)));

  const BarRow = ({ indicator }: { indicator: Indicator }) => {
    const pct = (Math.abs(indicator.contribution) / maxMagnitude) * 100;
    const isStress = indicator.direction === "negative";
    return (
      <div className="flex items-center gap-3 py-1.5">
        <span className="text-sm text-foreground w-44 shrink-0 truncate">{indicator.name}</span>
        <div className="flex-1 h-5 bg-muted rounded-sm overflow-hidden">
          <div
            className={`h-full rounded-sm ${isStress ? "bg-red-400" : "bg-emerald-400"}`}
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className={`text-sm font-medium tabular-nums w-12 text-right ${isStress ? "text-red-600" : "text-emerald-600"}`}>
          {indicator.contribution > 0 ? "+" : ""}
          {indicator.contribution.toFixed(1)}
        </span>
      </div>
    );
  };

  return (
    <section className="py-8">
      <h2 className="text-2xl font-semibold text-foreground mb-6">Stress Drivers</h2>
      <div className="grid md:grid-cols-2 gap-8">
        <div>
          <h3 className="text-sm font-semibold text-red-600 uppercase tracking-wide mb-3">Top Stressors</h3>
          {negative.map((d) => <BarRow key={d.name} indicator={d} />)}
        </div>
        <div>
          <h3 className="text-sm font-semibold text-emerald-600 uppercase tracking-wide mb-3">Easing Factors</h3>
          {positive.map((d) => <BarRow key={d.name} indicator={d} />)}
        </div>
      </div>
    </section>
  );
}
