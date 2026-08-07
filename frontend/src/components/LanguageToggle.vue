<script setup lang="ts">
import { LANGUAGES, type LanguageOption } from '../composables/useLanguage';

defineProps<{
  modelValue: LanguageOption['code'];
  size?: 'normal' | 'small';
}>();
const emit = defineEmits<{ (e: 'update:modelValue', code: LanguageOption['code']): void }>();
</script>

<template>
  <div class="lang-toggle" :class="size ?? 'normal'">
    <button
      v-for="l in LANGUAGES"
      :key="l.code"
      type="button"
      class="lang-btn"
      :class="{ active: l.code === modelValue }"
      :title="l.label"
      :aria-label="l.label"
      @click="emit('update:modelValue', l.code)"
    >
      {{ l.glyph }}
    </button>
  </div>
</template>

<style scoped>
.lang-toggle {
  display: inline-flex;
  align-items: center;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 2px;
  gap: 1px;
}
.lang-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: none;
  border-radius: 6px;
  color: var(--muted);
  cursor: pointer;
  font-family: var(--font-body);
  line-height: 1;
}
.lang-btn:hover {
  color: var(--teal);
}
.lang-btn.active {
  background: var(--teal);
  color: #fff;
}

.lang-toggle.normal .lang-btn {
  width: 26px;
  height: 26px;
  font-size: 13px;
}
.lang-toggle.small .lang-btn {
  width: 19px;
  height: 19px;
  font-size: 10.5px;
}
</style>
