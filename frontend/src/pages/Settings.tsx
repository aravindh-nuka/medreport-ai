import { useAppSettings } from "@/hooks/useAppSettings";
import { ModeSwitcher } from "@/components/ModeSwitcher";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Languages, Sparkles, Moon } from "lucide-react";
import { useT } from "@/i18n";

export function SettingsPage() {
  const { explanationLanguage, setExplanationLanguage, interfaceLanguage, setInterfaceLanguage, theme, toggleTheme } = useAppSettings();
  const t = useT();

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <h1 className="font-display text-2xl font-semibold text-brand-900 dark:text-paper">{t("settings.title")}</h1>

      <Card>
        <CardHeader><CardTitle>{t("settings.explanationMode")}</CardTitle></CardHeader>
        <CardContent>
          <p className="mb-3 text-sm text-unknown-600">{t("settings.explanationModeBody")}</p>
          <ModeSwitcher />
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>{t("settings.explanationLanguage")}</CardTitle></CardHeader>
        <CardContent className="flex items-center justify-between gap-4">
          <p className="flex items-center gap-2 text-sm text-unknown-600">
            <Sparkles className="h-4 w-4 shrink-0" /> {t("settings.explanationLanguageBody")}
          </p>
          <button
            onClick={() => setExplanationLanguage(explanationLanguage === "en" ? "te" : "en")}
            className="shrink-0 rounded-pill border border-border px-4 py-1.5 text-sm font-medium text-brand-700 dark:text-paper dark:border-borderDark"
          >
            {explanationLanguage === "en" ? "English" : "తెలుగు"}
          </button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>{t("settings.interfaceLanguage")}</CardTitle></CardHeader>
        <CardContent className="flex items-center justify-between gap-4">
          <p className="flex items-center gap-2 text-sm text-unknown-600">
            <Languages className="h-4 w-4 shrink-0" /> {t("settings.interfaceLanguageBody")}
          </p>
          <button
            onClick={() => setInterfaceLanguage(interfaceLanguage === "en" ? "te" : "en")}
            className="shrink-0 rounded-pill border border-border px-4 py-1.5 text-sm font-medium text-brand-700 dark:text-paper dark:border-borderDark"
          >
            {interfaceLanguage === "en" ? "English" : "తెలుగు"}
          </button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>{t("settings.appearance")}</CardTitle></CardHeader>
        <CardContent className="flex items-center justify-between">
          <p className="flex items-center gap-2 text-sm text-unknown-600"><Moon className="h-4 w-4" /> {t("settings.darkMode")}</p>
          <button
            onClick={toggleTheme}
            className="rounded-pill border border-border px-4 py-1.5 text-sm font-medium text-brand-700 dark:text-paper dark:border-borderDark"
          >
            {theme === "light" ? t("settings.off") : t("settings.on")}
          </button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>{t("settings.aboutPrivacy")}</CardTitle></CardHeader>
        <CardContent className="space-y-2 text-sm leading-relaxed text-unknown-600">
          <p>{t("settings.privacyBody")}</p>
          <p className="font-medium text-brand-900 dark:text-paper">{t("settings.privacyDisclaimer")}</p>
        </CardContent>
      </Card>
    </div>
  );
}
