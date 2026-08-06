<script setup lang="ts">
import { nextTick, ref } from "vue";
import { postChat } from "../api";
import type { StationDetail } from "../api/types";

const props = defineProps<{ stationContext: StationDetail | null }>();

interface LogEntry {
  role: "user" | "ai";
  text: string;
  sources?: string[];
  pending?: boolean;
}

const log = ref<LogEntry[]>([
  {
    role: "ai",
    text: "Hi, I'm the SAMUDRA research assistant. Ask about a region, species, or advisory — I query ocean sensor, fisheries and eDNA records together.",
  },
]);
const input = ref("");
const logEl = ref<HTMLDivElement | null>(null);

const presets = [
  "Why is sardine catch declining off Kerala?",
  "Show coral bleaching risk near Lakshadweep",
  "Which species were newly detected via eDNA this month?",
];

async function scrollToBottom() {
  await nextTick();
  if (logEl.value) logEl.value.scrollTop = logEl.value.scrollHeight;
}

async function send(text?: string) {
  const message = (text ?? input.value).trim();
  if (!message) return;
  log.value.push({ role: "user", text: message });
  input.value = "";
  log.value.push({ role: "ai", text: "···", pending: true });
  const pendingIndex = log.value.length - 1;
  await scrollToBottom();

  try {
    const result = await postChat(message, props.stationContext ?? undefined);
    log.value[pendingIndex].text = result.answer;
    log.value[pendingIndex].sources = result.sources;
  } catch {
    log.value[pendingIndex].text =
      "Couldn't reach the SAMUDRA backend / gpt-oss model. Make sure the backend is running (uv run main.py) and Ollama has gpt-oss:120b-cloud available.";
  } finally {
    log.value[pendingIndex].pending = false;
    await scrollToBottom();
  }
}

function askPreset(q: string) {
  send(q);
}

defineExpose({ send });
</script>

<template>
  <div>
    <div class="chat-log" ref="logEl">
      <div v-for="(entry, i) in log" :key="i" class="msg" :class="entry.role">
        <span v-if="entry.pending">···</span>
        <template v-else>
          {{ entry.text }}
          <div v-if="entry.sources?.length" class="cite">Sources: {{ entry.sources.join(" · ") }}</div>
        </template>
      </div>
    </div>
    <div class="chip" v-for="q in presets" :key="q" @click="askPreset(q)">{{ q }}</div>
    <div class="chat-input-row">
      <input v-model="input" placeholder="Type a question..." @keydown.enter="send()" />
      <button @click="send()">Ask</button>
    </div>
  </div>
</template>

<style scoped>
.chat-log {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 14px;
  max-height: 50vh;
  overflow-y: auto;
}
.msg {
  padding: 11px 14px;
  border-radius: 10px;
  font-size: 13px;
  line-height: 1.55;
  max-width: 92%;
  white-space: pre-wrap;
}
.msg.user {
  align-self: flex-end;
  background: var(--surface-2);
  border: 1px solid var(--border);
}
.msg.ai {
  background: var(--teal-soft);
  border: 1px solid #bfe3dc;
}
.msg.ai .cite {
  display: block;
  margin-top: 8px;
  font-family: var(--font-mono);
  font-size: 9.5px;
  color: var(--teal);
  border-top: 1px dashed #bfe3dc;
  padding-top: 6px;
  white-space: normal;
}
.chip {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 9px 11px;
  font-size: 11.5px;
  color: var(--muted);
  cursor: pointer;
  margin-bottom: 7px;
  font-weight: 500;
}
.chip:hover {
  color: var(--teal);
  border-color: var(--teal);
}
.chat-input-row {
  display: flex;
  gap: 8px;
  position: sticky;
  bottom: 0;
  background: var(--surface);
  padding-top: 8px;
}
.chat-input-row input {
  flex: 1;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 13px;
  color: var(--text);
  font-size: 12.5px;
  outline: none;
}
.chat-input-row button {
  background: var(--teal);
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 0 14px;
  font-weight: 700;
  font-size: 12px;
  cursor: pointer;
}
</style>
