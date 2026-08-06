<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { getTimeline } from "../api";
import type { TimelineResponse } from "../api/types";
import InfoTip from "./InfoTip.vue";

export interface TimelineChangePayload {
  metric: string;
  day: number;
  kind: "recorded" | "forecast";
  values: Record<string, number>;
}

const emit = defineEmits<{ (e: "change", payload: TimelineChangePayload): void }>();

const METRICS = [
  { key: "sst", label: "How warm the water is" },
  { key: "chlorophyll", label: "How much plankton is in the water" },
];

const metric = ref("sst");
const timeline = ref<TimelineResponse | null>(null);
const day = ref(0);
const currentKind = ref<"recorded" | "forecast">("recorded");
const playing = ref(false);
let playTimer: number | undefined;

function emitCurrent() {
  if (!timeline.value) return;
  const values: Record<string, number> = {};
  let kind: "recorded" | "forecast" = "recorded";
  for (const [stationId, points] of Object.entries(timeline.value.stations)) {
    const point = points.find((p) => p.day === day.value);
    if (point) {
      values[stationId] = point.value;
      kind = point.kind;
    }
  }
  currentKind.value = kind;
  emit("change", { metric: metric.value, day: day.value, kind, values });
}

async function load() {
  stopPlay();
  timeline.value = await getTimeline(metric.value, 30);
  day.value = 0; // "today" — the boundary between recorded and forecast
  emitCurrent();
}

function stopPlay() {
  playing.value = false;
  window.clearInterval(playTimer);
}

function togglePlay() {
  if (playing.value) {
    stopPlay();
    return;
  }
  if (!timeline.value) return;
  playing.value = true;
  const { min_day, max_day } = timeline.value;
  const totalSteps = max_day - min_day + 1;
  const stepMs = Math.max(150, Math.round(10000 / totalSteps));
  day.value = min_day;
  playTimer = window.setInterval(() => {
    if (!timeline.value) return;
    if (day.value >= timeline.value.max_day) {
      stopPlay();
      return;
    }
    day.value += 1;
  }, stepMs);
}

watch(metric, load);
watch(day, emitCurrent);
onMounted(load);
onBeforeUnmount(stopPlay);

const dayLabel = computed(() => {
  if (!timeline.value) return "";
  const ordinal = day.value - timeline.value.min_day + 1;
  return `Day ${ordinal} of ${timeline.value.days} — ${currentKind.value}`;
});
</script>

<template>
  <div class="scrubber-bar" v-if="timeline">
    <div class="scrubber-head">
      <select v-model="metric" class="metric-select">
        <option v-for="m in METRICS" :key="m.key" :value="m.key">{{ m.label }}</option>
      </select>
      <InfoTip :glossary-key="metric" />
      <button class="play-btn" @click="togglePlay">{{ playing ? "Pause" : "Play" }}</button>
      <span class="day-label" :class="currentKind">{{ dayLabel }}</span>
    </div>
    <input
      type="range"
      class="scrubber-range"
      :min="timeline.min_day"
      :max="timeline.max_day"
      step="1"
      v-model.number="day"
    />
    <div class="scrubber-scale">
      <span>{{ timeline.min_day }}d ago</span>
      <span class="today-mark">today</span>
      <span>+{{ timeline.max_day }}d forecast</span>
    </div>
  </div>
</template>

<style scoped>
.scrubber-bar {
  position: fixed;
  left: 220px;
  right: 250px;
  bottom: 20px;
  z-index: 20;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 10px 16px 8px;
  box-shadow: var(--shadow);
}
.scrubber-head {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}
.metric-select {
  font-family: var(--font-body);
  font-size: 12px;
  font-weight: 600;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 3px 6px;
  background: var(--surface-2);
  color: var(--text);
}
.play-btn {
  background: var(--teal);
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 4px 12px;
  font-size: 11.5px;
  font-weight: 700;
  cursor: pointer;
  margin-left: auto;
}
.day-label {
  font-family: var(--font-mono);
  font-size: 10.5px;
  padding: 3px 8px;
  border-radius: 5px;
  background: var(--surface-2);
  color: var(--muted);
}
.day-label.forecast {
  color: var(--amber);
  background: var(--amber-soft);
}
.scrubber-range {
  width: 100%;
  accent-color: var(--teal);
}
.scrubber-scale {
  display: flex;
  justify-content: space-between;
  font-family: var(--font-mono);
  font-size: 9.5px;
  color: var(--muted);
}
.today-mark {
  font-weight: 600;
  color: var(--text);
}
</style>
