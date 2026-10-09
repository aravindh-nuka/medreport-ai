import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, ShieldCheck, ShieldQuestion, Loader2 } from "lucide-react";
import type { LabParameter, Mode, Lang } from "@/lib/types";
import { StatusBadge, SourceTag, sourceTagKind, statusKind } from "@/components/ui/badge";
import { api, friendlyErrorMessage } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useT } from "@/i18n";

const STRIPE_COLOR: Record<string, string> = {
  normal: "text-verified-600",
  high: "text-attention-600",
  low: "text-attention-600",
  critical: "text-attention-700",
  unknown: "text-unknown-400",
};

export function ParameterCard({
  parameter, mode, language, onUpdate, defaultOpen = false,
}: {
  parameter: LabParameter;
  mode: Mode;
  language: Lang;
  onUpdate: (p: LabParameter) => void;
  defaultOpen?: boolean;
}) {
  const t = useT();
  const [open, setOpen] = useState(defaultOpen);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const kind = statusKind(parameter.status);

  const handleToggle = async () => {
    setOpen((o) => !o);
    if (!open && !parameter.explanation) {
      setLoading(true);
      setError(null);
      try {
        const updated = await api.explainParameter(parameter.id, mode, language);
        onUpdate(updated);
      } catch (e) {
        setError(friendlyErrorMessage(e));
      } finally {
        setLoading(false);
      }
    }
  };

  return (
    <div className={cn("ledger-stripe overflow-hidden rounded-card border border-border bg-white dark:bg-surface-dark dark:border-borderDark", STRIPE_COLOR[kind])}>
      <button onClick={handleToggle} className="flex w-full items-center justify-between gap-4 p-4 text-left">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-display font-semibold text-brand-900 dark:text-paper">
              {parameter.test_name_normalized || parameter.test_name_raw}
            </p>
            {parameter.loinc_verified ? (
              <ShieldCheck className="h-3.5 w-3.5 text-verified-600" aria-label={t("common.verified")} />
            ) : (
              <ShieldQuestion className="h-3.5 w-3.5 text-unknown-400" aria-label={t("common.unverified")} />
            )}
          </div>
          <p className="mt-1 font-mono text-sm text-unknown-600">
            {parameter.value ?? "Unknown"} {parameter.unit ?? ""}
            {parameter.reference_range && <span className="ml-2 text-unknown-400">ref {parameter.reference_range}</span>}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge status={parameter.status} />
          <ChevronDown className={cn("h-4 w-4 shrink-0 text-unknown-400 transition-transform", open && "rotate-180")} />
        </div>
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
          >
            <div className="border-t border-border px-4 pb-4 pt-4 dark:border-borderDark">
              <SourceTag kind={sourceTagKind(parameter.explanation?.source_of_truth)} />
              {loading && (
                <div className="mt-3 flex items-center gap-2 text-sm text-unknown-600">
                  <Loader2 className="h-4 w-4 animate-spin" /> {t("common.generating")}
                </div>
              )}
              {error && <p className="mt-3 text-sm text-attention-600">{error}</p>}
              {parameter.explanation && !loading && (
                <div className="mt-3 space-y-3 font-display text-sm leading-relaxed text-brand-900 dark:text-paper/90">
                  <Field label={t("tests.whatItMeasures")} text={parameter.explanation.what_it_measures} />
                  <Field label={t("tests.whyItMatters")} text={parameter.explanation.why_it_matters} />
                  <Field label={t("tests.clinicalSignificance")} text={parameter.explanation.clinical_significance} />
                  {kind === "high" && <Field label={t("tests.highReasons")} text={parameter.explanation.high_value_reasons} />}
                  {kind === "low" && <Field label={t("tests.lowReasons")} text={parameter.explanation.low_value_reasons} />}
                  {(kind === "unknown" || kind === "normal" || kind === "critical") && (
                    <>
                      <Field label={t("tests.ifHigh")} text={parameter.explanation.high_value_reasons} />
                      <Field label={t("tests.ifLow")} text={parameter.explanation.low_value_reasons} />
                    </>
                  )}
                  <Field label={t("tests.lifestyleSuggestions")} text={parameter.explanation.lifestyle_suggestions} />
                  <Field label={t("tests.educationalNotes")} text={parameter.explanation.educational_notes} />
                  <Field label={t("tests.whenToConsult")} text={parameter.explanation.when_to_consult_doctor} emphasize />
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function Field({ label, text, emphasize }: { label: string; text: string; emphasize?: boolean }) {
  return (
    <div>
      <p className="font-sans text-xs font-semibold uppercase tracking-wide text-unknown-600">{label}</p>
      <p className={cn("mt-1", emphasize && "text-attention-700")}>{text}</p>
    </div>
  );
}
