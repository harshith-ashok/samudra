<script setup lang="ts">
import DatasetsDashboard from '../components/DatasetsDashboard.vue';
import LanguageToggle from '../components/LanguageToggle.vue';
import { useI18n } from '../composables/useI18n';

const { t, currentLanguage } = useI18n();
</script>

<template>
  <div class="page">
    <div class="topbar">
      <div class="brand">
        {{ t('app.brand') }}
        <small>{{ t('datasets.pageTitle') }}</small>
      </div>
      <div class="actions">
        <router-link to="/" class="back-link">{{ t('datasets.backToMap') }}</router-link>
        <LanguageToggle v-model="currentLanguage" />
      </div>
    </div>
    <div class="body">
      <DatasetsDashboard />
    </div>
  </div>
</template>

<style scoped>
.page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg);
}
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 22px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.brand {
  display: flex;
  align-items: center;
  gap: 9px;
  font-weight: 700;
  font-size: 15.5px;
  letter-spacing: -0.01em;
}
.brand small {
  font-family: var(--font-mono);
  font-size: 9.5px;
  color: var(--muted);
  font-weight: 500;
  letter-spacing: 0.08em;
  margin-left: 3px;
  text-transform: uppercase;
}
.actions {
  display: flex;
  align-items: center;
  gap: 14px;
}
.back-link {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--teal);
  text-decoration: none;
}
.back-link:hover {
  text-decoration: underline;
}
.body {
  flex: 1;
  min-height: 0;
}
</style>
