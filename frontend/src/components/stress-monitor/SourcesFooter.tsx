import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { ExternalLink, ArrowLeft } from "lucide-react";

const DEFAULT_GITHUB_URL = import.meta.env.VITE_PROJECT_GITHUB_URL || "";
const PORTFOLIO_URL = import.meta.env.VITE_PORTFOLIO_URL || "https://winthrop-portfolio.vercel.app/";

interface Source {
  name: string;
  url: string;
  lastUpdated: string;
}

interface SourcesFooterProps {
  sources?: Source[];
  githubUrl?: string;
  isLoading: boolean;
}

function formatSourceDate(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "date unavailable";
  return parsed.toLocaleDateString("en-SG", { year: "numeric", month: "short", day: "numeric" });
}

export function SourcesFooter({ sources, githubUrl, isLoading }: SourcesFooterProps) {
  const repositoryUrl = githubUrl || DEFAULT_GITHUB_URL;

  return (
    <>
      {/* Sources */}
      <section className="py-8 border-t border-border">
        <h2 className="text-2xl font-semibold text-foreground mb-4">Data Sources</h2>
        {isLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-5 w-64" />
            ))}
          </div>
        ) : sources?.length ? (
          <ul className="space-y-2">
            {sources.map((s) => (
              <li key={s.name} className="flex flex-wrap items-center gap-2 text-sm">
                <a
                  href={s.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary underline-offset-4 hover:underline font-medium"
                >
                  {s.name}
                </a>
                <span className="text-muted-foreground">
                  — updated {formatSourceDate(s.lastUpdated)}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-muted-foreground">No source information available.</p>
        )}
      </section>

      {/* Footer CTA */}
      <footer className="py-12 border-t border-border bg-muted/30 -mx-4 px-4 sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8 mt-8 rounded-lg">
        <div className="flex flex-wrap justify-center gap-4">
          {repositoryUrl && (
            <Button asChild>
              <a href={repositoryUrl} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="mr-2 h-4 w-4" />
                See Code on GitHub
              </a>
            </Button>
          )}
          <Button variant="outline" asChild>
            <a href={PORTFOLIO_URL}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Portfolio
            </a>
          </Button>
        </div>
      </footer>
    </>
  );
}
