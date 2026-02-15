import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Skeleton } from "@/components/ui/skeleton";

interface MethodologyProps {
  summary?: string;
  details?: string;
  isLoading: boolean;
}

export function Methodology({ summary, details, isLoading }: MethodologyProps) {
  return (
    <section id="methodology" className="py-8 scroll-mt-24">
      <h2 className="text-2xl font-semibold text-foreground mb-4">Methodology</h2>
      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-5 w-full" />
          <Skeleton className="h-5 w-3/4" />
        </div>
      ) : summary ? (
        <>
          <p className="text-muted-foreground leading-relaxed mb-4">{summary}</p>
          {details && (
            <Accordion type="single" collapsible>
              <AccordionItem value="details">
                <AccordionTrigger className="text-sm font-medium">
                  Technical Details
                </AccordionTrigger>
                <AccordionContent>
                  <div className="prose prose-sm max-w-none text-muted-foreground whitespace-pre-line">
                    {details}
                  </div>
                </AccordionContent>
              </AccordionItem>
            </Accordion>
          )}
        </>
      ) : (
        <p className="text-muted-foreground">Methodology information unavailable.</p>
      )}
    </section>
  );
}
