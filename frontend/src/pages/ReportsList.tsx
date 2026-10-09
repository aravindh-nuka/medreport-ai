import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { FileText } from "lucide-react";
import { api } from "@/lib/api";
import type { ReportOut } from "@/lib/types";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useT } from "@/i18n";

export function ReportsListPage() {
  const t = useT();
  const [reports, setReports] = useState<ReportOut[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listReports().then(setReports).finally(() => setLoading(false));
  }, []);

  return (
    <div className="mx-auto max-w-4xl">
      <h1 className="font-display text-2xl font-semibold text-brand-900 dark:text-paper">{t("home.yourReports")}</h1>
      {loading ? (
        <p className="mt-6 text-sm text-unknown-600">{t("common.loading")}</p>
      ) : reports.length === 0 ? (
        <Card className="mt-6">
          <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
            <FileText className="h-8 w-8 text-unknown-400" />
            <p className="text-sm text-unknown-600">{t("home.noReports")}</p>
            <Link to="/upload"><Button variant="secondary">{t("home.uploadCta")}</Button></Link>
          </CardContent>
        </Card>
      ) : (
        <div className="mt-6 grid gap-3 md:grid-cols-2">
          {reports.map((r) => (
            <Link key={r.id} to={`/reports/${r.id}`}>
              <Card className="p-4 transition-shadow hover:shadow-cardHover">
                <p className="font-display font-semibold text-brand-900 dark:text-paper">{r.report_type}</p>
                <p className="mt-0.5 text-xs text-unknown-600">{r.original_filename}</p>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
