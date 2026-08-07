import en from '../i18n/en.json';
import hi from '../i18n/hi.json';
import ta from '../i18n/ta.json';
import ml from '../i18n/ml.json';
import { useLanguage } from './useLanguage';

type Dict = { [key: string]: string | Dict };

const DICTS: Record<string, Dict> = { en, hi, ta, ml };

function lookup(dict: Dict, path: string): string | undefined {
  let node: string | Dict | undefined = dict;
  for (const part of path.split('.')) {
    if (typeof node !== 'object' || node === null) return undefined;
    node = node[part];
  }
  return typeof node === 'string' ? node : undefined;
}

/** Static UI-chrome translation — every label/button/header baked into the
 * app itself (not data fetched from the backend, which stays in whatever
 * language it was recorded/generated in — see AIChat.vue for that separate,
 * live-translated path). Dictionaries are pre-generated (see
 * backend/data/generate_i18n.py) rather than translated on the fly, so
 * switching languages is instant and never flashes untranslated text while
 * a network call resolves.
 *
 * t() reads currentLanguage.value internally, so calling it from a template
 * or a computed() still tracks the dependency correctly — no need for t()
 * itself to be reactive. */
export function useI18n() {
  const { currentLanguage } = useLanguage();

  function t(key: string, vars?: Record<string, string | number>): string {
    const dict = DICTS[currentLanguage.value] ?? DICTS.en;
    let text = lookup(dict, key) ?? lookup(DICTS.en, key) ?? key;
    if (vars) {
      for (const [k, v] of Object.entries(vars)) {
        text = text.replaceAll(`{${k}}`, String(v));
      }
    }
    return text;
  }

  return { t, currentLanguage };
}

/** Looks up the canonical English string regardless of the current display
 * language — for cases like the NLQ suggested-query chips, which are shown
 * translated but must still be submitted to the backend in English (same
 * rule as typed/spoken input — see AIChat.vue, MapShell.vue's mic handler). */
export function tEnglish(key: string): string {
  return lookup(DICTS.en, key) ?? key;
}
