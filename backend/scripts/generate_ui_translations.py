"""
Optional helper: draft-translates any NEW keys in frontend/src/i18n/en.json
into frontend/src/i18n/te.json using deep-translator (Google Translate).

The interface language system in this app does NOT call any translation
API at runtime — it reads from the pre-built te.json dictionary directly,
which is why the UI stays fast and works offline once loaded. This script
exists only to help you draft translations when you add new UI strings.

Always review machine-translated output by hand afterward — it tends to
read more formal/literary than the natural, everyday Telugu used
elsewhere in this app, and won't know app-specific context.

Usage:
    cd backend
    python scripts/generate_ui_translations.py
"""
import json
from pathlib import Path

from deep_translator import GoogleTranslator

FRONTEND_I18N = Path(__file__).resolve().parent.parent.parent / "frontend" / "src" / "i18n"
EN_PATH = FRONTEND_I18N / "en.json"
TE_PATH = FRONTEND_I18N / "te.json"


def flatten(d: dict, prefix: str = "") -> dict:
    out = {}
    for k, v in d.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            out.update(flatten(v, key))
        else:
            out[key] = v
    return out


def unflatten(flat: dict) -> dict:
    out: dict = {}
    for key, value in flat.items():
        parts = key.split(".")
        node = out
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value
    return out


def main() -> None:
    en = json.loads(EN_PATH.read_text(encoding="utf-8"))
    te = json.loads(TE_PATH.read_text(encoding="utf-8")) if TE_PATH.exists() else {}

    en_flat = flatten(en)
    te_flat = flatten(te)

    translator = GoogleTranslator(source="en", target="te")
    added = 0
    for key, en_value in en_flat.items():
        if key not in te_flat or not te_flat[key]:
            te_flat[key] = translator.translate(en_value)
            added += 1
            print(f"translated: {key}")

    TE_PATH.write_text(json.dumps(unflatten(te_flat), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nDone. {added} new key(s) drafted into {TE_PATH}. Please review for natural phrasing before shipping.")


if __name__ == "__main__":
    main()
