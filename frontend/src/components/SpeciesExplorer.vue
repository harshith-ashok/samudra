<script setup lang="ts">
import { onMounted, ref } from "vue";
import { getSpecies } from "../api";
import type { Species } from "../api/types";

const species = ref<Species[]>([]);
const hovered = ref<Species | null>(null);
const loading = ref(true);

const statusLabel: Record<string, string> = { LC: "Least Concern", NT: "Near Threatened", VU: "Vulnerable", EN: "Endangered" };
const statusClass: Record<string, string> = { LC: "lc", NT: "nt", VU: "vu", EN: "vu" };

onMounted(async () => {
  try {
    species.value = await getSpecies();
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div>
    <p v-if="loading" class="loading">Loading species table…</p>
    <table v-else>
      <thead>
        <tr>
          <th>Species</th>
          <th>Region</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="s in species"
          :key="s.sci"
          @mouseenter="hovered = s"
          @mouseleave="hovered = null"
        >
          <td><i>{{ s.sci }}</i></td>
          <td>{{ s.region }}</td>
          <td>
            <span v-if="s.status" class="tag" :class="statusClass[s.status]">{{ statusLabel[s.status] }}</span>
            <span v-else>—</span>
          </td>
        </tr>
      </tbody>
    </table>

    <div class="species-hover-card" :class="{ show: hovered }">
      <template v-if="hovered">
        <div class="shc-head">
          <span class="shc-sci">{{ hovered.sci }}</span>
          <span v-if="hovered.status" class="tag" :class="statusClass[hovered.status]">{{ statusLabel[hovered.status] }}</span>
        </div>
        <div class="shc-common">{{ hovered.common }}</div>
        <div class="shc-region">{{ hovered.region }}</div>
        <p class="shc-note">{{ hovered.note }}</p>
      </template>
    </div>
  </div>
</template>

<style scoped>
.loading {
  color: var(--muted);
  font-size: 12.5px;
  font-family: var(--font-mono);
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 11.5px;
}
th {
  text-align: left;
  font-family: var(--font-mono);
  font-size: 9px;
  text-transform: uppercase;
  color: var(--muted);
  padding: 7px 6px;
  border-bottom: 1px solid var(--border);
}
td {
  padding: 8px 6px;
  border-bottom: 1px solid var(--border);
}
.tag {
  font-family: var(--font-mono);
  font-size: 9.5px;
  padding: 2px 7px;
  border-radius: 5px;
  border: 1px solid;
  font-weight: 600;
}
.tag.lc {
  color: #0b7a63;
  background: #e3f5f0;
  border-color: #bfe6dc;
}
.tag.nt {
  color: var(--amber);
  background: var(--amber-soft);
  border-color: #efdba6;
}
.tag.vu {
  color: var(--coral);
  background: var(--coral-soft);
  border-color: #f0c4b4;
}

.species-hover-card {
  position: fixed;
  left: 20px;
  bottom: 20px;
  width: 270px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: var(--shadow);
  padding: 15px 17px;
  z-index: 40;
  opacity: 0;
  transform: translate(-18px, 18px) scale(0.97);
  transition: opacity 0.22s ease, transform 0.22s ease;
  pointer-events: none;
}
.species-hover-card.show {
  opacity: 1;
  transform: translate(0, 0) scale(1);
}
.species-hover-card .shc-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 5px;
}
.species-hover-card .shc-sci {
  font-family: var(--font-display);
  font-size: 14px;
  font-style: italic;
  line-height: 1.3;
}
.species-hover-card .shc-common {
  font-size: 11.5px;
  color: var(--teal);
  font-weight: 600;
  margin-bottom: 3px;
}
.species-hover-card .shc-region {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--muted);
  margin-bottom: 9px;
}
.species-hover-card .shc-note {
  font-size: 11.5px;
  line-height: 1.5;
  color: var(--text);
}
</style>
