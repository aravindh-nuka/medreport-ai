import en from "./en.json";
import te from "./te.json";
import { useAppSettings } from "@/hooks/useAppSettings";

type Dict = typeof en;
const DICTIONARIES: Record<string, Dict> = { en, te: te as Dict };

/**
 * Resolves a dot-path key like "nav.home" against the active dictionary,
 * falling back to English if a key is missing in Telugu (should not happen
 * if te.json is kept in sync with en.json, but this prevents blank UI).
 * Supports simple {placeholder} interpolation.
 */
function resolve(dict: Dict, path: string): string | undefined {
  const parts = path.split(".");
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let node: any = dict;
  for (const part of parts) {
    if (node == null) return undefined;
    node = node[part];
  }
  return typeof node === "string" ? node : undefined;
}

export function translate(interfaceLanguage: string, path: string, vars?: Record<string, string | number>): string {
  const dict = DICTIONARIES[interfaceLanguage] ?? DICTIONARIES.en;
  let value = resolve(dict, path) ?? resolve(DICTIONARIES.en, path) ?? path;
  if (vars) {
    for (const [k, v] of Object.entries(vars)) {
      value = value.replace(`{${k}}`, String(v));
    }
  }
  return value;
}

export function useT() {
  const { interfaceLanguage } = useAppSettings();
  return (path: string, vars?: Record<string, string | number>) => translate(interfaceLanguage, path, vars);
}
