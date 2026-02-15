export type StressBand = "Low" | "Moderate" | "Elevated" | "High";

export interface LatestData {
  stressScore: number;
  stressBand: StressBand;
  oneMonthChange: number;
  threeMonthChange: number;
  lastUpdated: string;
  githubUrl: string;
  summary: string;
}

export interface HistoryEntry {
  date: string;
  score: number;
  regime?: string;
}

export interface Indicator {
  name: string;
  contribution: number;
  direction: "positive" | "negative";
}

export interface IndicatorsData {
  drivers: Indicator[];
  methodology: {
    summary: string;
    details: string;
  };
  sources: {
    name: string;
    url: string;
    lastUpdated: string;
  }[];
}
