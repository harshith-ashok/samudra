<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{ confidence: string }>();

// Any confidence string the backend hasn't standardized to low/medium/high yet
// (a few services still emit ad-hoc labels) degrades to the lowest fill rather
// than guessing, so the meter never overstates certainty it can't back up.
const LEVELS: Record<string, { fill: number; label: string }> = {
  low: { fill: 1, label: 'Low confidence' },
  medium: { fill: 2, label: 'Medium confidence' },
  high: { fill: 3, label: 'High confidence' },
};

const level = computed(
  () => LEVELS[props.confidence.toLowerCase()] ?? { fill: 1, label: props.confidence }
);
</script>

<template>
  <span class="confidence-meter" :title="level.label">
    <span
      v-for="n in 3"
      :key="n"
      class="cm-bar"
      :class="{ filled: n <= level.fill, [confidence.toLowerCase()]: n <= level.fill }"
    />
    <span class="cm-label">{{ level.label }}</span>
  </span>
</template>

<style scoped>
.confidence-meter {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.cm-bar {
  display: inline-block;
  width: 6px;
  height: 8px;
  border-radius: 1.5px;
  background: var(--border-strong);
}
.cm-bar:nth-child(2) {
  height: 11px;
}
.cm-bar:nth-child(3) {
  height: 14px;
}
.cm-bar.filled.low {
  background: var(--coral);
}
.cm-bar.filled.medium {
  background: var(--amber);
}
.cm-bar.filled.high {
  background: var(--teal);
}
.cm-label {
  font-family: var(--font-mono);
  font-size: 9.5px;
  color: var(--muted);
  margin-left: 2px;
}
</style>
