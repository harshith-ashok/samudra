import { ref } from "vue";
import { getGlossary } from "../api";
import type { GlossaryEntry } from "../api/types";

// Module-level singleton: every InfoTip / GlossaryPanel shares one fetch, one cache.
const entries = ref<GlossaryEntry[]>([]);
const loaded = ref(false);
let loadPromise: Promise<void> | null = null;

function ensureLoaded(): Promise<void> {
  if (loaded.value) return Promise.resolve();
  if (!loadPromise) {
    loadPromise = getGlossary()
      .then((data) => {
        entries.value = data;
        loaded.value = true;
      })
      .catch(() => {
        entries.value = [];
      });
  }
  return loadPromise;
}

export function useGlossary() {
  ensureLoaded();
  const byKey = (key: string): GlossaryEntry | undefined => entries.value.find((e) => e.key === key);
  return { entries, loaded, byKey };
}
