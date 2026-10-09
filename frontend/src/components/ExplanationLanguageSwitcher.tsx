import { useAppSettings } from "@/hooks/useAppSettings";

/**
 * Toggles the language of AI-generated content only (Explanation Language).
 * Deliberately separate from the app's Interface Language (see TopControls) —
 * these two are independent settings by design.
 */
export function ExplanationLanguageSwitcher() {
  const { explanationLanguage, setExplanationLanguage } = useAppSettings();
  return (
    <button
      onClick={() => setExplanationLanguage(explanationLanguage === "en" ? "te" : "en")}
      className="inline-flex items-center gap-1.5 rounded-pill border border-border bg-white px-3 py-1.5 text-sm font-medium text-brand-700 hover:border-brand-300 dark:bg-surface-dark dark:text-paper dark:border-borderDark"
      title="AI explanation language"
    >
      {explanationLanguage === "en" ? "AI: English" : "AI: తెలుగు"}
    </button>
  );
}
