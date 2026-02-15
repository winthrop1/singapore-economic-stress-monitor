import { useLatestData, useHistoryData, useIndicatorsData, useBackendWakeup } from "@/hooks/useProjectData";
import { Hero } from "@/components/stress-monitor/Hero";
import { MetricCards } from "@/components/stress-monitor/MetricCards";
import { StressChart } from "@/components/stress-monitor/StressChart";
import { DriversPanel } from "@/components/stress-monitor/DriversPanel";
import { Methodology } from "@/components/stress-monitor/Methodology";
import { SourcesFooter } from "@/components/stress-monitor/SourcesFooter";

const SingaporeStressMonitor = () => {
  useBackendWakeup();
  const latest = useLatestData();
  const history = useHistoryData();
  const indicators = useIndicatorsData();
  const hasError = latest.isError || history.isError || indicators.isError;

  return (
    <div className="min-h-screen bg-background">
      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        <Hero
          summary={latest.data?.summary}
          lastUpdated={latest.data?.lastUpdated}
          githubUrl={latest.data?.githubUrl}
          isLoading={latest.isLoading}
        />
        {hasError && (
          <div className="rounded-md border border-amber-300 bg-amber-50 text-amber-800 px-4 py-3 text-sm mb-6">
            Some data could not be loaded. Showing available values.
          </div>
        )}
        <MetricCards
          stressScore={latest.data?.stressScore}
          stressBand={latest.data?.stressBand}
          oneMonthChange={latest.data?.oneMonthChange}
          threeMonthChange={latest.data?.threeMonthChange}
          lastUpdated={latest.data?.lastUpdated}
          isLoading={latest.isLoading}
        />
        <StressChart data={history.data} isLoading={history.isLoading} />
        <DriversPanel drivers={indicators.data?.drivers} isLoading={indicators.isLoading} />
        <Methodology
          summary={indicators.data?.methodology?.summary}
          details={indicators.data?.methodology?.details}
          isLoading={indicators.isLoading}
        />
        <SourcesFooter
          sources={indicators.data?.sources}
          githubUrl={latest.data?.githubUrl}
          isLoading={indicators.isLoading}
        />
      </main>
    </div>
  );
};

export default SingaporeStressMonitor;
