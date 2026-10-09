import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { FileText, Upload, ShieldCheck, Languages, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import type { ReportOut } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useT } from "@/i18n";

export function HomePage() {
  const t = useT();
  const [reports, setReports] = useState<ReportOut[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listReports().then(setReports).finally(() => setLoading(false));
  }, []);

  const PILLARS = [
    { icon: ShieldCheck, title: t("home.pillar1Title"), body: t("home.pillar1Body") },
    { icon: Sparkles, title: t("home.pillar2Title"), body: t("home.pillar2Body") },
    { icon: Languages, title: t("home.pillar3Title"), body: t("home.pillar3Body") },
  ];

  return (
    <div className="mx-auto max-w-5xl">
      {/* Hero */}
      <motion.section
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative overflow-hidden rounded-card border border-border bg-white px-6 py-12 dark:bg-surface-dark dark:border-borderDark md:px-12 md:py-16"
      >
        <div className="pointer-events-none absolute -right-16 -top-16 h-64 w-64 rounded-full bg-brand-50 dark:bg-white/5" />
        <div className="relative max-w-2xl">
          <span className="mb-4 inline-block rounded-pill bg-verified-50 px-3 py-1 font-mono text-xs uppercase tracking-wide text-verified-700">
            {t("home.badge")}
          </span>
          <h1 className="font-display text-3xl font-semibold leading-tight text-brand-900 dark:text-paper md:text-5xl">
            {t("home.title")}
          </h1>
          <p className="mt-4 text-base leading-relaxed text-unknown-600 md:text-lg">
            {t("home.subtitle")}
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/upload">
              <Button size="lg">
                <Upload className="h-4 w-4" /> {t("home.uploadCta")}
              </Button>
            </Link>
            {reports.length > 0 && (
              <Link to={`/reports/${reports[0].id}`}>
                <Button size="lg" variant="secondary">
                  <FileText className="h-4 w-4" /> {t("home.viewLast")}
                </Button>
              </Link>
            )}
          </div>
        </div>
      </motion.section>

      {/* Pillars */}
      <section className="mt-10 grid gap-4 md:grid-cols-3">
        {PILLARS.map((p, i) => (
          <motion.div
            key={p.title}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1 * i }}
          >
            <Card className="h-full p-5">
              <p.icon className="h-5 w-5 text-brand-700 dark:text-brand-300" />
              <h3 className="mt-3 font-display text-base font-semibold text-brand-900 dark:text-paper">{p.title}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-unknown-600">{p.body}</p>
            </Card>
          </motion.div>
        ))}
      </section>

      {/* Recent reports */}
      <section className="mt-10">
        <h2 className="mb-4 font-display text-xl font-semibold text-brand-900 dark:text-paper">{t("home.yourReports")}</h2>
        {loading ? (
          <p className="text-sm text-unknown-600">{t("common.loading")}</p>
        ) : reports.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
              <FileText className="h-8 w-8 text-unknown-400" />
              <p className="text-sm text-unknown-600">{t("home.noReports")}</p>
              <Link to="/upload"><Button variant="secondary">{t("home.uploadCta")}</Button></Link>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-3 md:grid-cols-2">
            {reports.map((r) => (
              <Link key={r.id} to={`/reports/${r.id}`}>
                <Card className="p-4 transition-shadow hover:shadow-cardHover">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-display font-semibold text-brand-900 dark:text-paper">{r.report_type}</p>
                      <p className="mt-0.5 text-xs text-unknown-600">{r.original_filename}</p>
                    </div>
                    <span className="rounded-pill bg-brand-50 px-2.5 py-1 font-mono text-[10px] text-brand-700 dark:bg-white/5 dark:text-brand-300">
                      {new Date(r.uploaded_at).toLocaleDateString()}
                    </span>
                  </div>
                  {r.patient_name && (
                    <p className="mt-3 text-sm text-unknown-600">{r.patient_name}</p>
                  )}
                </Card>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
