import { useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { LatestData, HistoryEntry, IndicatorsData, StressBand } from "@/types/stress-monitor";

const STATIC_BASE = import.meta.env.VITE_STATIC_DATA_BASE || "/projects/singapore-economic-stress-monitor/data";
const API_BASE = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/+$/, "");
const DEFAULT_GITHUB_URL = import.meta.env.VITE_PROJECT_GITHUB_URL || "";
const BACKEND_WAKE_EVENT = "stress-monitor:backend-ready";
const API_TIMEOUT_MS = 4000;
const WAKE_TIMEOUT_MS = 55000;

let backendReady = false;
let wakePromise: Promise<void> | null = null;
const RESOURCE_PATHS = {
  latest: {
    api: "/api/stress-monitor/latest",
    static: "latest.json",
  },
  history: {
    api: "/api/stress-monitor/history",
    static: "history.json",
  },
  indicators: {
    api: "/api/stress-monitor/indicators",
    static: "indicators.json",
  },
} as const;

async function fetchFromUrl<T>(url: string, timeoutMs = API_TIMEOUT_MS): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, { signal: controller.signal });
    if (!res.ok) throw new Error(`Failed to fetch ${url}`);
    return res.json();
  } finally {
    clearTimeout(timeout);
  }
}

async function wakeBackendIfNeeded(): Promise<void> {
  if (!API_BASE || backendReady) return;
  if (wakePromise) return wakePromise;

  wakePromise = (async () => {
    try {
      await fetchFromUrl(`${API_BASE}/healthz`, WAKE_TIMEOUT_MS);
      backendReady = true;
      if (typeof window !== "undefined") {
        window.dispatchEvent(new Event(BACKEND_WAKE_EVENT));
      }
    } catch (error) {
      console.warn("Backend wake-up request failed. Continuing on static fallback.", error);
    } finally {
      wakePromise = null;
    }
  })();

  return wakePromise;
}

async function fetchResourceJson<T>(resource: keyof typeof RESOURCE_PATHS): Promise<T> {
  const resourcePath = RESOURCE_PATHS[resource];
  const fallbackUrl = `${STATIC_BASE}/${resourcePath.static}`;

  if (!API_BASE) {
    return fetchFromUrl<T>(fallbackUrl);
  }

  if (!backendReady) {
    void wakeBackendIfNeeded();
    return fetchFromUrl<T>(fallbackUrl);
  }

  try {
    return await fetchFromUrl<T>(`${API_BASE}${resourcePath.api}`);
  } catch (apiError) {
    console.warn(`API fetch failed for ${resource}. Falling back to static data.`, apiError);
    return fetchFromUrl<T>(fallbackUrl);
  }
}

type RawLatestData = Partial<LatestData> & {
  stress_score?: {
    value?: number;
    band?: StressBand;
  };
  changes?: {
    mom?: number;
    qoq?: number;
  };
  last_updated_at?: string;
};

type RawHistoryData =
  | HistoryEntry[]
  | {
      series?: Array<{
        date?: string;
        score?: number;
        stress_score?: number;
      }>;
      regimes?: Array<{
        label?: string;
        start?: string;
        end?: string;
      }>;
    };

type RawIndicatorsData = Partial<IndicatorsData> & {
  drivers?: Array<{
    name?: string;
    label?: string;
    contribution?: number;
    direction?: "positive" | "negative" | "up" | "down";
  }>;
  sources?: Array<{
    name?: string;
    url?: string;
    lastUpdated?: string;
    as_of_date?: string;
  }>;
};

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function normalizeBand(value?: string): StressBand {
  if (value === "Low" || value === "Moderate" || value === "Elevated" || value === "High") {
    return value;
  }
  return "Moderate";
}

function normalizeLatestData(raw: RawLatestData): LatestData {
  return {
    stressScore: isFiniteNumber(raw.stressScore)
      ? raw.stressScore
      : isFiniteNumber(raw.stress_score?.value)
        ? raw.stress_score.value
        : 0,
    stressBand: normalizeBand(raw.stressBand ?? raw.stress_score?.band),
    oneMonthChange: isFiniteNumber(raw.oneMonthChange)
      ? raw.oneMonthChange
      : isFiniteNumber(raw.changes?.mom)
        ? raw.changes.mom
        : 0,
    threeMonthChange: isFiniteNumber(raw.threeMonthChange)
      ? raw.threeMonthChange
      : isFiniteNumber(raw.changes?.qoq)
        ? raw.changes.qoq
        : 0,
    lastUpdated: raw.lastUpdated ?? raw.last_updated_at ?? "",
    githubUrl: raw.githubUrl ?? DEFAULT_GITHUB_URL ?? "",
    summary: raw.summary ?? "A composite indicator tracking financial stress in Singapore's economy.",
  };
}

function isDateInRange(date: string, start?: string, end?: string): boolean {
  const dateValue = new Date(date).getTime();
  const startValue = start ? new Date(start).getTime() : Number.NEGATIVE_INFINITY;
  const endValue = end ? new Date(end).getTime() : Number.POSITIVE_INFINITY;

  if (Number.isNaN(dateValue) || Number.isNaN(startValue) || Number.isNaN(endValue)) {
    return false;
  }

  return dateValue >= startValue && dateValue <= endValue;
}

function normalizeHistoryData(raw: RawHistoryData): HistoryEntry[] {
  if (Array.isArray(raw)) {
    return raw
      .filter((entry) => typeof entry.date === "string" && isFiniteNumber(entry.score))
      .map((entry) => ({
        date: entry.date,
        score: entry.score,
        regime: entry.regime,
      }));
  }

  const series = raw.series ?? [];
  const regimes = raw.regimes ?? [];

  return series
    .filter((entry) => typeof entry.date === "string")
    .map((entry) => {
      const date = entry.date as string;
      const matchingRegime = regimes.find((regime) => isDateInRange(date, regime.start, regime.end));

      return {
        date,
        score: isFiniteNumber(entry.score) ? entry.score : isFiniteNumber(entry.stress_score) ? entry.stress_score : 0,
        regime: matchingRegime?.label,
      };
    });
}

function normalizeIndicatorsData(raw: RawIndicatorsData): IndicatorsData {
  const drivers = (raw.drivers ?? [])
    .filter((driver) => typeof driver.contribution === "number")
    .map((driver) => {
      const contribution = driver.contribution as number;
      const normalizedDirection =
        driver.direction === "positive" || driver.direction === "negative"
          ? driver.direction
          : contribution < 0 || driver.direction === "down"
            ? "positive"
            : "negative";

      return {
        name: driver.name ?? driver.label ?? "Unnamed indicator",
        contribution,
        direction: normalizedDirection,
      };
    });

  const sources = (raw.sources ?? [])
    .filter((source) => source.name && source.url)
    .map((source) => ({
      name: source.name as string,
      url: source.url as string,
      lastUpdated: source.lastUpdated ?? source.as_of_date ?? "",
    }));

  return {
    drivers,
    methodology: {
      summary: raw.methodology?.summary ?? "",
      details: raw.methodology?.details ?? "",
    },
    sources,
  };
}

export function useLatestData() {
  return useQuery<LatestData>({
    queryKey: ["stress-monitor", "latest"],
    queryFn: async () => normalizeLatestData(await fetchResourceJson<RawLatestData>("latest")),
    staleTime: 1000 * 60 * 10,
  });
}

export function useBackendWakeup() {
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!API_BASE) return;

    const refreshFromApi = () => {
      queryClient.invalidateQueries({ queryKey: ["stress-monitor"] });
    };

    if (typeof window !== "undefined") {
      window.addEventListener(BACKEND_WAKE_EVENT, refreshFromApi);
    }

    void wakeBackendIfNeeded().then(refreshFromApi);

    return () => {
      if (typeof window !== "undefined") {
        window.removeEventListener(BACKEND_WAKE_EVENT, refreshFromApi);
      }
    };
  }, [queryClient]);
}

export function useHistoryData() {
  return useQuery<HistoryEntry[]>({
    queryKey: ["stress-monitor", "history"],
    queryFn: async () => normalizeHistoryData(await fetchResourceJson<RawHistoryData>("history")),
    staleTime: 1000 * 60 * 10,
  });
}

export function useIndicatorsData() {
  return useQuery<IndicatorsData>({
    queryKey: ["stress-monitor", "indicators"],
    queryFn: async () => normalizeIndicatorsData(await fetchResourceJson<RawIndicatorsData>("indicators")),
    staleTime: 1000 * 60 * 10,
  });
}

export function isDataStale(lastUpdated: string, thresholdDays = 45): boolean {
  const updated = new Date(lastUpdated);
  if (Number.isNaN(updated.getTime())) return true;
  const now = new Date();
  const diffMs = now.getTime() - updated.getTime();
  return diffMs > thresholdDays * 24 * 60 * 60 * 1000;
}
