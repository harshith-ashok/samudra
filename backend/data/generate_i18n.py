"""One-off script that translates frontend/src/i18n/en.json into Hindi, Tamil,
and Malayalam via Google Translate (same free deep-translator path as
services/translate.py), producing hi.json/ta.json/ml.json alongside it.

Run with: uv run backend/data/generate_i18n.py

`{placeholder}` tokens (e.g. "{count} stations live") get mangled by Google
Translate if sent through as-is — it translates the words inside the braces
too. They're swapped for translation-safe __PH0__/__PH1__/... tokens before
the call and restored (as the original, untranslated placeholder text) after.
"""

import json
import os
import re
import time

from deep_translator import GoogleTranslator

I18N_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "src", "i18n")
SOURCE = os.path.join(I18N_DIR, "en.json")
TARGET_LANGS = ["hi", "ta", "ml"]

PLACEHOLDER_RE = re.compile(r"\{[^{}]+\}")


def translate_value(translator: GoogleTranslator, text: str) -> str:
    placeholders = PLACEHOLDER_RE.findall(text)
    tokenized = text
    for i, ph in enumerate(placeholders):
        tokenized = tokenized.replace(ph, f"__PH{i}__", 1)

    translated = translator.translate(tokenized) or tokenized

    for i, ph in enumerate(placeholders):
        translated = translated.replace(f"__PH{i}__", ph)
    return translated


def translate_tree(node, translator: GoogleTranslator):
    if isinstance(node, dict):
        return {k: translate_tree(v, translator) for k, v in node.items()}
    if isinstance(node, str):
        result = translate_value(translator, node)
        time.sleep(0.05)  # be polite to the free endpoint
        return result
    return node


# Keys to leave untranslated in every locale — proper nouns/brand identity,
# not general UI copy. Google Translate happily transliterates "SAMUDRA" into
# each script (e.g. Hindi "समुद्र"), which is linguistically reasonable but
# wrong for a brand name that should read identically everywhere.
PINNED_KEYS = {"app.brand"}


def apply_pins(tree: dict, en: dict, prefix: str = ""):
    for k, v in tree.items():
        path = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            apply_pins(v, en[k], path)
        elif path in PINNED_KEYS:
            tree[k] = en[k]


def main():
    with open(SOURCE) as f:
        en = json.load(f)

    for lang in TARGET_LANGS:
        print(f"translating -> {lang}...")
        translator = GoogleTranslator(source="en", target=lang)
        translated = translate_tree(en, translator)
        apply_pins(translated, en)
        out_path = os.path.join(I18N_DIR, f"{lang}.json")
        with open(out_path, "w") as f:
            json.dump(translated, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"  wrote {out_path}")


if __name__ == "__main__":
    main()
