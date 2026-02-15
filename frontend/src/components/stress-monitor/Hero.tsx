import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ExternalLink, FileText } from "lucide-react";
import { isDataStale } from "@/hooks/useProjectData";

const DEFAULT_GITHUB_URL = import.meta.env.VITE_PROJECT_GITHUB_URL || "";

interface HeroProps {
  summary?: string;
  lastUpdated?: string;
  githubUrl?: string;
  isLoading: boolean;
}

export function Hero({ summary, lastUpdated, githubUrl, isLoading }: HeroProps) {
  const stale = lastUpdated ? isDataStale(lastUpdated) : true;
  const repositoryUrl = githubUrl || DEFAULT_GITHUB_URL;
  const formattedDate = lastUpdated
    ? new Date(lastUpdated).toLocaleDateString("en-SG", { year: "numeric", month: "long", day: "numeric" })
    : "Unavailable";

  return (
    <header className="py-16 md:py-24">
      <div className="max-w-3xl">
        <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-foreground mb-4">
          Singapore Economic Stress Monitor
        </h1>
        {isLoading ? (
          <Skeleton className="h-6 w-full max-w-xl mb-6" />
        ) : (
          <p className="text-lg text-muted-foreground mb-6 leading-relaxed">
            {summary ?? "A composite indicator tracking financial stress in Singapore's economy."}
          </p>
        )}
        <div className="flex flex-wrap items-center gap-3 mb-8">
          {isLoading ? (
            <Skeleton className="h-5 w-48" />
          ) : (
            <>
              <span className="text-sm text-muted-foreground">Last updated: {formattedDate}</span>
              {stale && (
                <Badge variant="outline" className="text-amber-600 border-amber-300 bg-amber-50">
                  Data may be stale
                </Badge>
              )}
            </>
          )}
        </div>
        <div className="flex flex-wrap gap-3">
          {repositoryUrl && (
            <Button asChild>
              <a href={repositoryUrl} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="mr-2 h-4 w-4" />
                View GitHub Repo
              </a>
            </Button>
          )}
          <Button variant="outline" asChild>
            <a href="#methodology">
              <FileText className="mr-2 h-4 w-4" />
              Read Methodology
            </a>
          </Button>
        </div>
      </div>
    </header>
  );
}
