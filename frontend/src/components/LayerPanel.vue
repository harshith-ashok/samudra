<script setup lang="ts">
import InfoTip from './InfoTip.vue';

export interface LayerDef {
  key: string;
  label: string;
  color: string;
  glossaryKey?: string;
  visible: boolean;
}
export interface KpiDef {
  label: string;
  value: string | number;
  glossaryKey?: string;
}

defineProps<{ layers: LayerDef[]; kpis: KpiDef[] }>();
const emit = defineEmits<{ (e: 'toggle', key: string): void }>();
</script>

<template>
  <div class="layer-panel">
    <h4>Map Layers</h4>
    <label class="layer-row" v-for="layer in layers" :key="layer.key">
      <input
        type="checkbox"
        :checked="layer.visible"
        @change="emit('toggle', layer.key)"
      />
      <i :style="{ background: layer.color }"></i>
      {{ layer.label }}
      <InfoTip v-if="layer.glossaryKey" :glossary-key="layer.glossaryKey" />
    </label>
    <div class="divider"></div>
    <div class="kpi-mini" v-for="kpi in kpis" :key="kpi.label">
      <span
        >{{ kpi.label
        }}<InfoTip v-if="kpi.glossaryKey" :glossary-key="kpi.glossaryKey"
      /></span>
      <b>{{ kpi.value }}</b>
    </div>
  </div>
</template>

<style scoped>
.layer-panel {
  position: fixed;
  right: 20px;
  bottom: 26px;
  z-index: 20;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 16px;
  box-shadow: var(--shadow);
  width: 210px;
}
.layer-panel h4 {
  font-family: var(--font-mono);
  font-size: 9.5px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--muted);
  margin-bottom: 10px;
}
.layer-row {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 5px 0;
  font-size: 12.5px;
  cursor: pointer;
}
.layer-row input {
  accent-color: var(--teal);
  width: 14px;
  height: 14px;
}
.layer-row i {
  width: 8px;
  height: 8px;
  border-radius: 2px;
  display: inline-block;
}
.layer-panel .divider {
  height: 1px;
  background: var(--border);
  margin: 10px 0;
}
.kpi-mini {
  display: flex;
  justify-content: space-between;
  font-family: var(--font-mono);
  font-size: 10.5px;
  color: var(--muted);
  padding: 3px 0;
}
.kpi-mini span {
  display: inline-flex;
  align-items: center;
}
.kpi-mini b {
  color: var(--text);
  font-weight: 600;
}
</style>
