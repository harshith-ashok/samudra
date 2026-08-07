<script setup lang="ts">
import { ref } from 'vue';
import { useI18n } from '../composables/useI18n';

defineProps<{
  stationCount: number;
  stateCount: number;
  speciesCount: number;
}>();
const collapsed = ref(false);
const { t } = useI18n();
</script>

<template>
  <div class="impact-card" :class="{ collapsed }">
    <button class="collapse-btn" @click="collapsed = !collapsed">
      {{ collapsed ? t('impact.expandLabel') : t('impact.collapseLabel') }}
    </button>
    <template v-if="!collapsed">
      <h4>{{ t('impact.title') }}</h4>
      <div class="row">
        <span>{{ t('impact.coastline') }}</span
        ><b>{{ t('impact.coastlineValue') }}</b>
      </div>
      <div class="row">
        <span>{{ t('impact.stationsTracked') }}</span><b>{{ stationCount }}</b>
      </div>
      <div class="row">
        <span>{{ t('impact.statesCovered') }}</span><b>{{ stateCount }}</b>
      </div>
      <div class="row">
        <span>{{ t('impact.speciesIndexed') }}</span><b>{{ speciesCount }}</b>
      </div>
      <p class="note">{{ t('impact.note') }}</p>
    </template>
  </div>
</template>

<style scoped>
.impact-card {
  position: fixed;
  top: 76px;
  right: 20px;
  z-index: 20;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 16px;
  box-shadow: var(--shadow);
  width: 200px;
}
.impact-card.collapsed {
  width: auto;
  padding: 8px 12px;
}
.collapse-btn {
  position: absolute;
  top: 8px;
  right: 10px;
  background: none;
  border: none;
  color: var(--muted);
  font-size: 12px;
  cursor: pointer;
  font-family: var(--font-mono);
}
.impact-card.collapsed .collapse-btn {
  position: static;
  font-weight: 600;
  color: var(--teal);
}
h4 {
  font-family: var(--font-mono);
  font-size: 9.5px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--muted);
  margin-bottom: 10px;
  padding-right: 16px;
}
.row {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  padding: 4px 0;
}
.row span {
  color: var(--muted);
}
.row b {
  color: var(--text);
  font-weight: 600;
}
.note {
  font-size: 9.5px;
  color: var(--muted);
  line-height: 1.4;
  margin-top: 8px;
  border-top: 1px dashed var(--border);
  padding-top: 8px;
}
</style>
