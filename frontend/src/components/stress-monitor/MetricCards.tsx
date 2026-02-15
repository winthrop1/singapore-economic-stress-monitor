import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowDown, ArrowUp, TrendingUp, TrendingDown } from "lucide-react";
import { isDataStale } from "@/hooks/useProjectData";
import type { StressBand } from "@/types/stress-monitor";
import type { ReactNode } from "react";

interface MetricCardsProps {
  stressScore?: number;
  stressBand?: StressBand;
  oneMonthChange?: number;
  threeMonthChange?: number;
  lastUpdated?: string;
  isLoading: boolean;
}

const bandColor: Record<string, string> = {
  Low: "text-emerald-600",
  Moderate: "text-amber-600",
  Elevated: "text-orange-600",
  High: "text-red-600",
};

const bandBg: Record<string, string> = {
  Low: "bg-emerald-50 border-emerald-200",
  Moderate: "bg-amber-50 border-amber-200",
  Elevated: "bg-orange-50 border-orange-200",
  High: "bg-red-50 border-red-200",
};

function scoreColor(score: number) {
  if (score <= 25) return "text-emerald-600";
  if (score <= 50) return "text-amber-600";
  if (score <= 75) return "text-orange-600";
  return "text-red-600";
}

function renderChange(
  value: number | undefined,
  positiveIcon: ReactNode,
  negativeIcon: ReactNode,
  positiveClass: string,
  negativeClass: string,
) {
  if (typeof value !== "number") {
    return <span className="text-2xl font-semibold text-muted-foreground">—</span>;
  }

  if (value === 0) {
    return <span className="text-2xl font-semibold text-muted-foreground">0.0</span>;
  }

  const isPositive = value > 0;
  return (
    <span className={`flex items-center gap-1 text-2xl font-semibold ${isPositive ? positiveClass : negativeClass}`}>
      {isPositive ? positiveIcon : negativeIcon}
      {Math.abs(value).toFixed(1)}
    </span>
  );
}

export function MetricCards({ stressScore, stressBand, oneMonthChange, threeMonthChange, lastUpdated, isLoading }: MetricCardsProps) {
  const stale = lastUpdated ? isDataStale(lastUpdated) : true;

  const cards = [
    {
      label: "Stress Score",
      value: isLoading ? null : (
        <span className={`text-3xl font-bold tabular-nums ${scoreColor(stressScore ?? 0)}`}>
          {typeof stressScore === "number" ? stressScore.toFixed(1) : "—"}
        </span>
      ),
      sub: "out of 100",
    },
    {
      label: "Stress Band",
      value: isLoading ? null : (
        <span className={`text-2xl font-semibold ${bandColor[stressBand ?? "Moderate"]}`}>
          {stressBand ?? "—"}
        </span>
      ),
    },
    {
      label: "1-Month Change",
      value: isLoading
        ? null
        : renderChange(
            oneMonthChange,
            <ArrowUp className="h-5 w-5" />,
            <ArrowDown className="h-5 w-5" />,
            "text-red-600",
            "text-emerald-600",
          ),
    },
    {
      label: "3-Month Trend",
      value: isLoading
        ? null
        : renderChange(
            threeMonthChange,
            <TrendingUp className="h-5 w-5" />,
            <TrendingDown className="h-5 w-5" />,
            "text-red-600",
            "text-emerald-600",
          ),
    },
    {
      label: "Data Freshness",
      value: isLoading ? null : (
        <span className="flex items-center gap-2 text-lg font-medium">
          <span className={`inline-block h-3 w-3 rounded-full ${stale ? "bg-amber-400" : "bg-emerald-500"}`} />
          {lastUpdated ? (stale ? "Stale" : "Fresh") : "Unknown"}
        </span>
      ),
    },
  ];

  return (
    <section aria-label="Key metrics" className="py-8">
      <h2 className="text-2xl font-semibold text-foreground mb-6">Key Results</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {cards.map((card) => (
          <Card
            key={card.label}
            className={card.label === "Stress Band" && stressBand ? bandBg[stressBand] : ""}
          >
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground mb-2">{card.label}</p>
              {card.value ?? <Skeleton className="h-8 w-20" />}
              {card.sub && <p className="text-xs text-muted-foreground mt-1">{card.sub}</p>}
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  );
}
