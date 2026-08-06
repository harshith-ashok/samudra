<script setup lang="ts">
import { computed, ref } from "vue";
import { useGlossary } from "../composables/useGlossary";

const props = defineProps<{ glossaryKey: string }>();
const { byKey } = useGlossary();
const entry = computed(() => byKey(props.glossaryKey));
const open = ref(false);

function toggle() {
  open.value = !open.value;
}
function close() {
  open.value = false;
}
</script>

<template>
  <span class="info-tip" v-if="entry" @mouseenter="open = true" @mouseleave="close">
    <button class="info-tip-icon" type="button" @click.stop="toggle" :aria-label="`About ${entry.title}`">i</button>
    <div class="info-tip-popover" v-if="open" @click.stop>
      <div class="info-tip-title">{{ entry.title }}</div>
      <p class="info-tip-body">{{ entry.what_it_is }}</p>
      <p class="info-tip-why"><b>Why it matters:</b> {{ entry.why_it_matters }}</p>
    </div>
  </span>
</template>

<style scoped>
.info-tip {
  position: relative;
  display: inline-flex;
  align-items: center;
  margin-left: 5px;
}
.info-tip-icon {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 1px solid var(--border-strong);
  background: var(--surface-2);
  color: var(--muted);
  font-family: var(--font-mono);
  font-size: 9px;
  font-style: italic;
  line-height: 1;
  padding: 0;
  cursor: help;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.info-tip-icon:hover {
  border-color: var(--teal);
  color: var(--teal);
}
.info-tip-popover {
  position: absolute;
  bottom: calc(100% + 8px);
  left: 50%;
  transform: translateX(-50%);
  width: 240px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 9px;
  box-shadow: var(--shadow);
  padding: 11px 13px;
  z-index: 60;
  font-family: var(--font-body);
  text-align: left;
}
.info-tip-title {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 12.5px;
  margin-bottom: 5px;
}
.info-tip-body {
  font-size: 11px;
  line-height: 1.5;
  color: var(--text);
  margin-bottom: 6px;
}
.info-tip-why {
  font-size: 10.5px;
  line-height: 1.5;
  color: var(--muted);
}
.info-tip-why b {
  color: var(--text);
  font-weight: 600;
}
</style>
