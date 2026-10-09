import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Loader2, MessageSquare, ListChecks, Stethoscope, Gavel, ShieldCheck, ShieldAlert, ShieldQuestion,
  Lightbulb, AlertTriangle, Apple, Activity, HeartPulse, CalendarClock, Eye, Quote,
} from "lucide-react";
import { api, friendlyErrorMessage } from "@/lib/api";
import type { ReportDetail, ReportSummary, KeyFindings } from "@/lib/types";
import { useAppSettings } from "@/hooks/useAppSettings";
import { ModeSwitcher } from "@/components/ModeSwitcher";
import { ExplanationLanguageSwitcher } from "@/components/ExplanationLanguageSwitcher";
import { Card } from "@/components/ui/card";
import { SourceTag, sourceTagKind } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useT } from "@/i18n";

const RECOMMENDATION_META: { key: keyof ReportSummary; labelKey: string; icon: typeof Lightbulb }[] = [
  { key: "suggestions", labelKey: "overview.suggestions", icon: Lightbulb },
  { key: "precautions", labelKey: "overview.precautions", icon: AlertTriangle },
  { key: "diet_recommendations", labelKey: "overview.dietRecommendations", icon: Apple },
  { key: "lifestyle_advice", labelKey: "overview.lifestyleAdvice", icon: HeartPulse },
  { key: "exercise_suggestions", labelKey: "overview.exerciseSuggestions", icon: Activity },
  { key: "followup_advice", labelKey: "overview.followupAdvice", icon: CalendarClock },
  { key: "doctor_consultation_advice", labelKey: "overview.doctorConsultation", icon: Stethoscope },
  { key: "monitoring_advice", labelKey: "overview.monitoringAdvice", icon: Eye },
];

const fadeUp = {
  hidden: { opacity: 0, y: 14 },
  show: (i: number = 0) => ({ opacity: 1, y: 0, transition: { duration: 0.45, delay: i * 0.06, ease: "easeOut" } }),
};

export function ReportOverviewPage() {
  const { reportId } = useParams<{ reportId: string }>();
  const { mode, explanationLanguage } = useAppSettings();
  const t = useT();
  const [report, setReport] = useState<ReportDetail | null>(null);
  const [summary, setSummary] = useState<ReportSummary | null>(null);
  const [findings, setFindings] = useState<KeyFindings | null>(null);
  const [loadingReport, setLoadingReport] = useState(true);
  const [loadingSummary, setLoadingSummary] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!reportId) return;
    setLoadingReport(true);
    Promise.all([api.getReport(reportId), api.getKeyFindings(reportId)])
      .then(([r, f]) => { setReport(r); setFindings(f); })
      .catch((e) => setError(friendlyErrorMessage(e)))
      .finally(() => setLoadingReport(false));
  }, [reportId]);

  useEffect(() => {
    if (!reportId) return;
    setLoadingSummary(true);
    setSummary(null);
    api.getOverview(reportId, mode, explanationLanguage)
      .then(setSummary)
      .catch((e) => setError(friendlyErrorMessage(e)))
      .finally(() => setLoadingSummary(false));
  }, [reportId, mode, explanationLanguage]);

  if (loadingReport) {
    return <div className="flex justify-center py-24"><Loader2 className="h-6 w-6 animate-spin text-brand-700" /></div>;
  }
  if (error && !report) {
    return <Card className="mx-auto max-w-lg p-6 text-center text-attention-600">{error}</Card>;
  }
  if (!report) return null;

  const hasAbnormal = (findings?.verified_abnormal.length ?? 0) > 0;

  return (
    <div className="mx-auto max-w-4xl">
      {/* Header + Report Title */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <span className="inline-block rounded-pill bg-brand-50 px-3 py-1 font-mono text-xs uppercase tracking-wide text-brand-700 dark:bg-white/5 dark:text-brand-300">
            {report.report_type}
          </span>
          <h1 className="mt-2 font-display text-2xl font-semibold text-brand-900 dark:text-paper md:text-3xl">
            {report.patient_name || "Unnamed patient"}
          </h1>
          <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-sm text-unknown-600">
            {report.patient_age && <span>Age: {report.patient_age}</span>}
            {report.patient_sex && <span>Sex: {report.patient_sex}</span>}
            {report.sample_date && <span>{report.sample_date}</span>}
            {report.hospital_name && <span>{report.hospital_name}</span>}
          </div>
        </div>
        <div className="flex flex-col items-end gap-2">
          <ModeSwitcher />
          <ExplanationLanguageSwitcher />
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-3">
        <Link to={`/reports/${reportId}/tests`}><Button variant="secondary" size="sm"><ListChecks className="h-4 w-4" /> {t("nav.tests")}</Button></Link>
        <Link to={`/reports/${reportId}/chat`}><Button variant="secondary" size="sm"><MessageSquare className="h-4 w-4" /> {t("common.askAboutReport")}</Button></Link>
      </div>

      {loadingSummary ? (
        <div className="mt-10 flex items-center gap-2 py-8 text-sm text-unknown-600">
          <Loader2 className="h-4 w-4 animate-spin" /> {t("overview.generatingOverview", { mode })}
        </div>
      ) : summary ? (
        <>
          {/* Short Summary — hero pull-quote */}
          <motion.section variants={fadeUp} initial="hidden" animate="show" custom={0} className="mt-8">
            <div className="relative overflow-hidden rounded-card border border-brand-100 bg-gradient-to-br from-brand-50 via-white to-white p-6 dark:border-borderDark dark:from-white/5 dark:via-surface-dark dark:to-surface-dark md:p-8">
              <Quote className="absolute -right-2 -top-2 h-20 w-20 text-brand-100 dark:text-white/5" strokeWidth={1} />
              <div className="relative flex items-center justify-between">
                <p className="font-mono text-xs uppercase tracking-wide text-brand-700 dark:text-brand-300">{t("overview.shortSummary")}</p>
                <SourceTag kind={sourceTagKind(summary.source_of_truth)} />
              </div>
              <p className="relative mt-3 font-display text-lg font-medium leading-[1.7] text-brand-900 dark:text-paper md:text-xl">
                {summary.short_summary}
              </p>
            </div>
          </motion.section>

          {/* Detailed Doctor Explanation — narrative timeline */}
          <motion.section variants={fadeUp} initial="hidden" animate="show" custom={1} className="mt-8">
            <div className="mb-3 flex items-center gap-2">
              <Stethoscope className="h-4 w-4 text-brand-700 dark:text-brand-300" />
              <h2 className="font-display text-lg font-semibold text-brand-900 dark:text-paper">{t("overview.detailedExplanation")}</h2>
              <SourceTag kind={sourceTagKind(summary.source_of_truth)} />
            </div>
            <Card className="p-6">
              <p className="font-display text-[15px] leading-[1.9] text-brand-900 dark:text-paper/90">
                {summary.detailed_explanation}
              </p>
            </Card>
          </motion.section>

          {/* Final Verdict — prominent banner */}
          <motion.section variants={fadeUp} initial="hidden" animate="show" custom={2} className="mt-8">
            <div
              className={`flex items-start gap-4 rounded-card border p-6 ${
                hasAbnormal
                  ? "border-attention-400/40 bg-attention-50 dark:bg-attention-600/10"
                  : "border-verified-400/40 bg-verified-50 dark:bg-verified-600/10"
              }`}
            >
              <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-full ${hasAbnormal ? "bg-attention-600" : "bg-verified-600"}`}>
                <Gavel className="h-5 w-5 text-white" />
              </div>
              <div>
                <p className={`font-mono text-xs uppercase tracking-wide ${hasAbnormal ? "text-attention-700" : "text-verified-700"}`}>
                  {t("overview.finalVerdict")}
                </p>
                <p className="mt-1.5 font-display text-base font-medium leading-[1.75] text-brand-900 dark:text-paper">
                  {summary.final_verdict}
                </p>
              </div>
            </div>
          </motion.section>

          {/* Key Findings — stat cards */}
          {findings && (
            <motion.section variants={fadeUp} initial="hidden" animate="show" custom={3} className="mt-8">
              <h2 className="mb-3 font-display text-lg font-semibold text-brand-900 dark:text-paper">{t("overview.keyFindings")}</h2>
              <div className="grid gap-4 sm:grid-cols-3">
                <FindingsGroup icon={ShieldAlert} tone="attention" title={t("overview.verifiedAbnormal")} items={findings.verified_abnormal} emptyLabel={t("overview.noFindings")} />
                <FindingsGroup icon={ShieldCheck} tone="verified" title={t("overview.verifiedNormal")} items={findings.verified_normal} emptyLabel={t("overview.noFindings")} />
                <FindingsGroup icon={ShieldQuestion} tone="unknown" title={t("overview.unverifiedFindings")} items={findings.unverified} emptyLabel={t("overview.noFindings")} />
              </div>
            </motion.section>
          )}

          {/* Recommendations — icon-led grid */}
          <motion.section variants={fadeUp} initial="hidden" animate="show" custom={4} className="mt-8 mb-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="font-display text-lg font-semibold text-brand-900 dark:text-paper">{t("overview.recommendations")}</h2>
              <SourceTag kind={sourceTagKind(summary.source_of_truth)} />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              {RECOMMENDATION_META.map(({ key, labelKey, icon: Icon }) => {
                const text = summary[key];
                if (!text) return null;
                return (
                  <Card key={key} className="flex gap-3 p-4">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-50 dark:bg-white/5">
                      <Icon className="h-4 w-4 text-brand-700 dark:text-brand-300" />
                    </div>
                    <div>
                      <p className="font-sans text-xs font-semibold uppercase tracking-wide text-unknown-600">{t(labelKey)}</p>
                      <p className="mt-1 font-display text-sm leading-relaxed text-brand-900 dark:text-paper/90">{text}</p>
                    </div>
                  </Card>
                );
              })}
            </div>
          </motion.section>
        </>
      ) : null}
    </div>
  );
}

function FindingsGroup({
  icon: Icon, tone, title, items, emptyLabel,
}: {
  icon: typeof ShieldCheck;
  tone: "attention" | "verified" | "unknown";
  title: string;
  items: ReportDetail["parameters"];
  emptyLabel: string;
}) {
  const toneStyles = {
    attention: { text: "text-attention-600", ring: "border-attention-400/30", num: "text-attention-700" },
    verified: { text: "text-verified-600", ring: "border-verified-400/30", num: "text-verified-700" },
    unknown: { text: "text-unknown-400", ring: "border-unknown-400/30", num: "text-unknown-600" },
  }[tone];

  return (
    <Card className={`p-4 ${toneStyles.ring}`}>
      <div className="flex items-center justify-between">
        <Icon className={`${toneStyles.text} h-5 w-5`} />
        <span className={`font-mono text-2xl font-semibold ${toneStyles.num}`}>{items.length}</span>
      </div>
      <p className="mt-2 font-display text-sm font-semibold text-brand-900 dark:text-paper">{title}</p>
      {items.length === 0 ? (
        <p className="mt-1 text-xs text-unknown-600">{emptyLabel}</p>
      ) : (
        <ul className="mt-2 space-y-1 border-t border-border pt-2 dark:border-borderDark">
          {items.slice(0, 4).map((p) => (
            <li key={p.id} className="flex items-center justify-between font-mono text-xs">
              <span className="truncate text-brand-900 dark:text-paper/90">{p.test_name_normalized || p.test_name_raw}</span>
              <span className="shrink-0 text-unknown-600">{p.value ?? "—"} {p.unit ?? ""}</span>
            </li>
          ))}
          {items.length > 4 && <li className="text-xs text-unknown-400">+{items.length - 4} more</li>}
        </ul>
      )}
    </Card>
  );
}
