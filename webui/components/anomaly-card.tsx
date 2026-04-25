import {
  Card,
  CardBody,
  CardHeader,
  CardSubtitle,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ArrowUpRight, BookOpen, Sparkles } from "lucide-react";
import type { AnalysisReport } from "@/lib/api";
import { formatNumber, formatTimestamp } from "@/lib/utils";

const METRIC_TONE: Record<string, "info" | "success" | "warning"> = {
  traffic: "info",
  sales: "success",
  error_rate: "warning",
};

export function AnomalyCard({ report }: { report: AnalysisReport }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center gap-2">
            <Badge tone={METRIC_TONE[report.metric] ?? "neutral"}>
              {report.metric}
            </Badge>
            <Badge tone="danger">{report.status}</Badge>
            <span className="font-mono text-xs text-[var(--color-foreground-muted)]">
              cos d={report.distance.toFixed(3)}
            </span>
          </div>
          <CardTitle className="font-mono">
            value <span className="text-[var(--color-warning)]">{formatNumber(report.value)}</span>
          </CardTitle>
          <CardSubtitle>{formatTimestamp(report.timestamp)}</CardSubtitle>
        </div>
      </CardHeader>

      <CardBody className="space-y-4">
        <section>
          <h4 className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-[var(--color-accent)]">
            <BookOpen className="h-3.5 w-3.5" />
            Matched playbook
          </h4>
          <p className="text-sm leading-relaxed text-[var(--color-foreground)]">
            {report.rule_text}
          </p>
        </section>

        <section>
          <h4 className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-[var(--color-warning)]">
            <ArrowUpRight className="h-3.5 w-3.5" />
            Suggested action
          </h4>
          <p className="text-sm leading-relaxed text-[var(--color-foreground)]">
            {report.suggested_action}
          </p>
        </section>

        <section>
          <h4 className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-[var(--color-foreground-muted)]">
            <Sparkles className="h-3.5 w-3.5" />
            On-call report
          </h4>
          <p className="text-sm leading-relaxed text-[var(--color-foreground-muted)]">
            {report.explanation}
          </p>
        </section>
      </CardBody>
    </Card>
  );
}
