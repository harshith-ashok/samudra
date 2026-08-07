import { ref, watch } from 'vue';

export interface LanguageOption {
  code: 'en' | 'hi' | 'ta' | 'ml';
  glyph: string;
  label: string;
}

// Order matches the app's coastal footprint, English first as the base/default.
export const LANGUAGES: LanguageOption[] = [
  { code: 'en', glyph: 'A', label: 'English' },
  { code: 'ta', glyph: 'அ', label: 'Tamil' },
  { code: 'ml', glyph: 'അ', label: 'Malayalam' },
  { code: 'hi', glyph: 'अ', label: 'Hindi' },
];

const STORAGE_KEY = 'samudra_language';

// Module-level singleton, same pattern as useGlossary — every LanguageToggle
// instance (topbar + per chat message) shares one source of truth for the
// system-wide default, so changing it in the topbar is felt everywhere at once.
const currentLanguage = ref<LanguageOption['code']>(
  (localStorage.getItem(STORAGE_KEY) as LanguageOption['code'] | null) ?? 'en'
);

watch(currentLanguage, (lang) => {
  localStorage.setItem(STORAGE_KEY, lang);
});

export function useLanguage() {
  function setLanguage(code: LanguageOption['code']) {
    currentLanguage.value = code;
  }
  return { currentLanguage, setLanguage, LANGUAGES };
}
