<script setup lang="ts">
import InfoTip from './InfoTip.vue';
import type { Vessel } from '../api/types';

defineProps<{ vessel: Vessel | null }>();
</script>

<template>
  <div v-if="vessel">
    <span class="stat-badge" :class="{ violation: vessel.in_violation }">
      {{ vessel.in_violation ? 'VIOLATION' : vessel.type.toUpperCase() }}
    </span>
    <h3 class="stat-name">
      {{ vessel.name }}<InfoTip glossary-key="vessel_tracking" />
    </h3>
    <div class="stat-readout">
      <b>ID {{ vessel.id }}</b
      ><br />
      <b>Type {{ vessel.type }}</b
      ><br />
      <b>Speed {{ vessel.speed_knots }} kn</b><br />
      <b>Heading {{ vessel.heading_deg }}°</b>
    </div>
    <div v-if="vessel.in_violation" class="violation-note">
      Currently inside <b>{{ vessel.violation_zone }}</b> — a protected zone
      where fishing/extractive activity is restricted.
    </div>
    <p class="source-note">
      Position updates from a simulated AIS-like track (see /api/vessels) — real
      tracking would come from Global Fishing Watch once an API key is
      configured.
    </p>
  </div>
</template>

<style scoped>
.stat-badge {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: 9.5px;
  padding: 4px 9px;
  border-radius: 5px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  color: var(--teal);
  margin-bottom: 12px;
  font-weight: 600;
}
.stat-badge.violation {
  color: var(--coral);
  background: var(--coral-soft);
  border-color: #f0c4b4;
}
.stat-name {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 19px;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
}
.stat-readout {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 9px;
  padding: 14px;
  margin: 12px 0;
  font-family: var(--font-mono);
  font-size: 11.5px;
  color: var(--muted);
  line-height: 1.9;
}
.stat-readout b {
  color: var(--text);
  font-family: var(--font-body);
  font-weight: 600;
}
.violation-note {
  background: var(--coral-soft);
  border: 1px solid #f0c4b4;
  border-radius: 9px;
  padding: 12px 14px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--text);
  margin-bottom: 12px;
}
.source-note {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--muted);
  margin-top: 8px;
  line-height: 1.5;
}
</style>
