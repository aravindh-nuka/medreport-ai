import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import type { Mode, Lang } from "@/lib/types";

interface AppSettingsState {
  mode: Mode;
  setMode: (m: Mode) => void;
  /** Controls AI-generated content only (summaries, explanations, chat, flashcards).
   * When "te", the LLM writes directly in natural Telugu — no post-hoc translation. */
  explanationLanguage: Lang;
  setExplanationLanguage: (l: Lang) => void;
  /** Controls the static app UI (nav, buttons, labels) via a pre-built dictionary.
   * Independent of explanationLanguage — no API/LLM calls involved. */
  interfaceLanguage: Lang;
  setInterfaceLanguage: (l: Lang) => void;
  theme: "light" | "dark";
  toggleTheme: () => void;
}

const AppSettingsContext = createContext<AppSettingsState | null>(null);

export function AppSettingsProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<Mode>("patient");
  const [explanationLanguage, setExplanationLanguage] = useState<Lang>("en");
  const [interfaceLanguage, setInterfaceLanguage] = useState<Lang>("en");
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    if (typeof window === "undefined") return "light";
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  });

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [theme]);

  useEffect(() => {
    document.documentElement.lang = interfaceLanguage;
  }, [interfaceLanguage]);

  const toggleTheme = () => setTheme((t) => (t === "light" ? "dark" : "light"));

  return (
    <AppSettingsContext.Provider
      value={{
        mode, setMode,
        explanationLanguage, setExplanationLanguage,
        interfaceLanguage, setInterfaceLanguage,
        theme, toggleTheme,
      }}
    >
      {children}
    </AppSettingsContext.Provider>
  );
}

export function useAppSettings() {
  const ctx = useContext(AppSettingsContext);
  if (!ctx) throw new Error("useAppSettings must be used within AppSettingsProvider");
  return ctx;
}
