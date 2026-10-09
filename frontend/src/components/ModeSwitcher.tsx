import { motion } from "framer-motion";
import { useAppSettings } from "@/hooks/useAppSettings";
import type { Mode } from "@/lib/types";
import { cn } from "@/lib/utils";
import { useT } from "@/i18n";

export function ModeSwitcher() {
  const { mode, setMode } = useAppSettings();
  const t = useT();
  const MODES: { value: Mode; label: string }[] = [
    { value: "patient", label: t("common.patient") },
    { value: "student", label: t("common.student") },
    { value: "doctor", label: t("common.doctor") },
  ];

  return (
    <div className="inline-flex items-center rounded-pill border border-border bg-white p-1 dark:bg-surface-dark dark:border-borderDark">
      {MODES.map((m) => (
        <button
          key={m.value}
          onClick={() => setMode(m.value)}
          className={cn(
            "relative rounded-pill px-4 py-1.5 text-sm font-medium transition-colors",
            mode === m.value ? "text-white" : "text-brand-700 hover:text-brand-900 dark:text-paper/80"
          )}
        >
          {mode === m.value && (
            <motion.span
              layoutId="mode-pill"
              className="absolute inset-0 rounded-pill bg-brand-700"
              transition={{ type: "spring", duration: 0.4 }}
            />
          )}
          <span className="relative z-10">{m.label}</span>
        </button>
      ))}
    </div>
  );
}
