import { Moon, Sun, Languages } from "lucide-react";
import { useAppSettings } from "@/hooks/useAppSettings";

export function TopControls() {
  const { interfaceLanguage, setInterfaceLanguage, theme, toggleTheme } = useAppSettings();

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={() => setInterfaceLanguage(interfaceLanguage === "en" ? "te" : "en")}
        className="inline-flex items-center gap-1.5 rounded-pill border border-border bg-white px-3 py-1.5 text-sm font-medium text-brand-700 hover:border-brand-300 dark:bg-surface-dark dark:text-paper dark:border-borderDark"
        aria-label="Toggle interface language"
        title="App interface language"
      >
        <Languages className="h-4 w-4" />
        {interfaceLanguage === "en" ? "English" : "తెలుగు"}
      </button>
      <button
        onClick={toggleTheme}
        className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-border bg-white text-brand-700 hover:border-brand-300 dark:bg-surface-dark dark:text-paper dark:border-borderDark"
        aria-label="Toggle dark mode"
      >
        {theme === "light" ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
      </button>
    </div>
  );
}
