<script setup lang="ts">
import { useGlossary } from "../composables/useGlossary";

const { entries } = useGlossary();
</script>

<template>
  <div class="glossary-list">
    <p class="intro">Plain-language notes on every metric and layer used in SAMUDRA — for a quick skim instead of hunting for the (i) icons.</p>
    <div class="entry" v-for="e in entries" :key="e.key">
      <div class="entry-title">{{ e.title }}</div>
      <p class="entry-body">{{ e.what_it_is }}</p>
      <p class="entry-why"><b>Why it matters:</b> {{ e.why_it_matters }}</p>
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
</style>
