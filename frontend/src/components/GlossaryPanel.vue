<script setup lang="ts">
import { useGlossary } from '../composables/useGlossary';
import { useI18n } from '../composables/useI18n';

const { entries } = useGlossary();
const { t } = useI18n();
</script>

<template>
  <div class="glossary-list">
    <p class="intro">{{ t('glossaryPanel.intro') }}</p>
    <div class="entry" v-for="e in entries" :key="e.key">
      <div class="entry-title">{{ e.title }}</div>
      <p class="entry-body">{{ e.what_it_is }}</p>
      <p class="entry-why">
        <b>{{ t('glossaryPanel.whyItMatters') }}</b> {{ e.why_it_matters }}
      </p>
      <p v-if="e.details" class="entry-details">
        <b>{{ t('glossaryPanel.details') }}</b> {{ e.details }}
      </p>
    </div>
  </div>
</template>

<style scoped>
.intro {
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 16px;
  line-height: 1.5;
}
.entry {
  padding: 12px 0;
  border-bottom: 1px solid var(--border);
}
.entry:last-child {
  border-bottom: none;
}
.entry-title {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 4px;
}
.entry-body {
  font-size: 12px;
  line-height: 1.55;
  color: var(--text);
  margin-bottom: 5px;
}
.entry-why {
  font-size: 11px;
  line-height: 1.5;
  color: var(--muted);
}
.entry-why b {
  color: var(--text);
  font-weight: 600;
}
.entry-details {
  font-size: 10.5px;
  line-height: 1.5;
  color: var(--muted);
  margin-top: 5px;
  font-family: var(--font-mono);
}
.entry-details b {
  color: var(--text);
  font-weight: 600;
  font-family: var(--font-body);
}
</style>
