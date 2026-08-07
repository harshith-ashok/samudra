<script setup lang="ts">
export interface ModuleDef {
  key: string;
  label: string;
  iconPaths: string[];
}

defineProps<{ modules: ModuleDef[]; activePanel: string | null }>();
const emit = defineEmits<{ (e: 'open', key: string): void }>();
</script>

<template>
  <div class="fab-stack">
    <div
      v-for="m in modules"
      :key="m.key"
      class="fab"
      :class="{ active: activePanel === m.key }"
      @click="emit('open', m.key)"
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.7"
      >
        <path v-for="(d, i) in m.iconPaths" :key="i" :d="d" />
      </svg>
      {{ m.label }}
    </div>
  </div>
</template>

<style scoped>
.fab-stack {
  position: fixed;
  left: 20px;
  top: 150px;
  z-index: 25;
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 186px;
}
.fab {
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 9px;
  padding: 11px 13px;
  cursor: pointer;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text);
  box-shadow: var(--shadow);
  transition:
    border-color 0.12s,
    color 0.12s;
}
.fab svg {
  width: 15px;
  height: 15px;
  flex-shrink: 0;
  color: var(--muted);
}
.fab:hover {
  border-color: var(--teal);
}
.fab.active {
  background: var(--teal);
  color: #fff;
  border-color: var(--teal);
}
.fab.active svg {
  color: #fff;
}
</style>
