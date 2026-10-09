import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { api, friendlyErrorMessage } from "@/lib/api";
import type { ReportDetail, LabParameter } from "@/lib/types";
import { useAppSettings } from "@/hooks/useAppSettings";
import { ModeSwitcher } from "@/components/ModeSwitcher";
import { ExplanationLanguageSwitcher } from "@/components/ExplanationLanguageSwitcher";
import { ParameterCard } from "@/components/ParameterCard";
import { Card, CardContent } from "@/components/ui/card";
import { useT } from "@/i18n";

/** Verified parameters first, unverified/unknown last — per product requirement. */
function sortParameters(parameters: LabParameter[]): LabParameter[] {
  return [...parameters].sort((a, b) => {
    if (a.loinc_verified === b.loinc_verified) return 0;
    return a.loinc_verified ? -1 : 1;
  });
}

export function IndividualTestAnalysisPage() {
  const { reportId } = useParams<{ reportId: string }>();
  const { mode, explanationLanguage } = useAppSettings();
  const t = useT();
  const [report, setReport] = useState<ReportDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!reportId) return;
    setLoading(true);
    api.getReport(reportId).then(setReport).catch((e) => setError(friendlyErrorMessage(e))).finally(() => setLoading(false));
  }, [reportId]);

  const updateParameter = (updated: LabParameter) => {
    setReport((prev) =>
      prev ? { ...prev, parameters: prev.parameters.map((p) => (p.id === updated.id ? updated : p)) } : prev
    );
  };

  if (loading) {
    return <div className="flex justify-center py-24"><Loader2 className="h-6 w-6 animate-spin text-brand-700" /></div>;
  }
  if (error && !report) {
    return <Card className="mx-auto max-w-lg p-6 text-center text-attention-600">{error}</Card>;
  }
  if (!report) return null;

  const sorted = sortParameters(report.parameters);

  return (
    <div className="mx-auto max-w-4xl">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold text-brand-900 dark:text-paper md:text-3xl">{t("tests.title")}</h1>
          <p className="mt-1 text-sm text-unknown-600">{t("tests.subtitle")}</p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <ModeSwitcher />
          <ExplanationLanguageSwitcher />
        </div>
      </div>

      <div className="mt-6">
        {sorted.length === 0 ? (
          <Card><CardContent className="py-8 text-center text-sm text-unknown-600">{t("tests.noParameters")}</CardContent></Card>
        ) : (
          <div className="space-y-3">
            {sorted.map((p) => (
              <ParameterCard key={p.id} parameter={p} mode={mode} language={explanationLanguage} onUpdate={updateParameter} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
