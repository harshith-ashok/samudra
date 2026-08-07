<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref } from 'vue';
import { postChat, postSttTranscribe, postTranslate } from '../api';
import type { StationDetail } from '../api/types';
import type { LanguageOption } from '../composables/useLanguage';
import { useI18n, tEnglish } from '../composables/useI18n';
import { useVoiceRecorder } from '../composables/useVoiceRecorder';
import LanguageToggle from './LanguageToggle.vue';

const props = defineProps<{
  stationContext: StationDetail | null;
  speciesContext?: unknown | null;
}>();

const { t, currentLanguage } = useI18n();

interface LogEntry {
  role: 'user' | 'ai';
  text: string;
  sources?: string[];
  pending?: boolean;
  // AI entries only — the raw gpt-oss answer plus a per-language cache, so
  // switching a past message's display language is a translate call at
  // worst, never a re-run of the chat pipeline.
  originalText?: string;
  translations?: Partial<Record<LanguageOption['code'], string>>;
  displayLang?: LanguageOption['code'];
}

// The welcome bubble isn't part of the actual conversation, so it's kept out
// of `log` and rendered separately via t() in the template — that way it
// re-translates immediately if the language toggle changes, rather than
// freezing in whatever language was active when the component first
// mounted. Keeping it out of `log` also avoids an off-by-one index shift for
// switchMessageLang(), which indexes directly into `log`.
const log = ref<LogEntry[]>([]);
const input = ref('');
const logEl = ref<HTMLDivElement | null>(null);

// Displayed translated, but always submitted to /api/chat in English — same
// rule as the NLQ suggested-query chips (see MapShell.vue's tEnglish usage).
const presetKeys = ['chat.preset1', 'chat.preset2', 'chat.preset3'];

async function scrollToBottom() {
  await nextTick();
  if (logEl.value) logEl.value.scrollTop = logEl.value.scrollHeight;
}

/** displayMessage is what appears in the user's own chat bubble (whatever
 * they actually typed/spoke, or the preset chip's translated label);
 * englishMessage is what actually goes to /api/chat — the RAG pipeline
 * reasons over English seed data, same rule as everywhere else. */
async function sendMessage(displayMessage: string, englishMessage: string) {
  log.value.push({ role: 'user', text: displayMessage });
  log.value.push({ role: 'ai', text: '···', pending: true });
  const pendingIndex = log.value.length - 1;
  await scrollToBottom();

  try {
    const result = await postChat(
      englishMessage,
      props.stationContext ?? undefined,
      props.speciesContext ?? undefined
    );
    const entry = log.value[pendingIndex];
    entry.originalText = result.answer;
    entry.translations = { en: result.answer };
    entry.sources = result.sources;
    if (currentLanguage.value === 'en') {
      entry.text = result.answer;
      entry.displayLang = 'en';
    } else {
      const translated = await postTranslate(
        result.answer,
        currentLanguage.value,
        'en'
      );
      entry.translations[currentLanguage.value] = translated;
      entry.text = translated;
      entry.displayLang = currentLanguage.value;
    }
  } catch {
    log.value[pendingIndex].text = t('chat.unreachable');
  } finally {
    log.value[pendingIndex].pending = false;
    await scrollToBottom();
  }
}

async function send(text?: string) {
  const message = (text ?? input.value).trim();
  if (!message) return;
  input.value = '';
  const englishMessage =
    currentLanguage.value === 'en'
      ? message
      : await postTranslate(message, 'en', currentLanguage.value);
  await sendMessage(message, englishMessage);
}

function askPreset(key: string) {
  sendMessage(t(key), tEnglish(key));
}

async function switchMessageLang(index: number, lang: LanguageOption['code']) {
  const entry = log.value[index];
  if (entry.pending || !entry.originalText) return;
  if (!entry.translations) entry.translations = {};
  if (!entry.translations[lang]) {
    entry.translations[lang] =
      lang === 'en'
        ? entry.originalText
        : await postTranslate(entry.originalText, lang, 'en');
  }
  entry.text = entry.translations[lang]!;
  entry.displayLang = lang;
}

const {
  state: micState,
  errorMsg: micErrorMsg,
  toggle: toggleMic,
  dispose: disposeMic,
} = useVoiceRecorder(
  (blob) => postSttTranscribe(blob, currentLanguage.value),
  (text) => send(text),
  {
    transcribeError: () => t('chat.micError'),
    micDenied: () => t('chat.micDenied'),
  }
);

onBeforeUnmount(disposeMic);

defineExpose({ send });
</script>

<template>
  <div>
    <div class="chat-log" ref="logEl">
      <div class="msg ai">{{ t('chat.welcome') }}</div>
      <div v-for="(entry, i) in log" :key="i" class="msg" :class="entry.role">
        <span v-if="entry.pending">···</span>
        <template v-else>
          {{ entry.text }}
          <div
            v-if="entry.role === 'ai' && entry.originalText"
            class="msg-lang-row"
          >
            <LanguageToggle
              :model-value="entry.displayLang ?? 'en'"
              size="small"
              @update:model-value="(l) => switchMessageLang(i, l)"
            />
          </div>
          <div v-if="entry.sources?.length" class="cite">
            {{ t('chat.sources', { sources: entry.sources.join(' · ') }) }}
          </div>
        </template>
      </div>
    </div>
    <div
      class="chip"
      v-for="key in presetKeys"
      :key="key"
      @click="askPreset(key)"
    >
      {{ t(key) }}
    </div>
    <div class="chat-input-row">
      <input
        v-model="input"
        :placeholder="
          micState === 'recording'
            ? t('chat.placeholderListening')
            : micState === 'transcribing'
              ? t('chat.placeholderTranscribing')
              : t('chat.placeholderTyping')
        "
        @keydown.enter="send()"
      />
      <button
        type="button"
        class="mic-btn"
        :class="micState"
        :disabled="micState === 'transcribing'"
        :title="micErrorMsg || t('chat.micTitle')"
        @mousedown.prevent="toggleMic"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <rect x="9" y="2" width="6" height="12" rx="3" />
          <path d="M5 11a7 7 0 0 0 14 0" />
          <path d="M12 18v4M8 22h8" />
        </svg>
      </button>
      <button @click="send()">{{ t('chat.ask') }}</button>
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
.msg-lang-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
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
.mic-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  flex-shrink: 0;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface-2);
  color: var(--muted);
  cursor: pointer;
}
.mic-btn:hover:not(:disabled) {
  color: var(--teal);
  border-color: var(--teal);
}
.mic-btn svg {
  width: 15px;
  height: 15px;
}
.mic-btn.recording {
  color: var(--coral);
  background: var(--coral-soft);
  border-color: var(--coral);
  animation: mic-pulse 1.4s ease-in-out infinite;
}
.mic-btn.transcribing {
  color: var(--teal);
  cursor: default;
}
.mic-btn.error {
  color: var(--coral);
}
@keyframes mic-pulse {
  0%,
  100% {
    box-shadow: 0 0 0 0 rgba(214, 81, 45, 0.35);
  }
  50% {
    box-shadow: 0 0 0 5px rgba(214, 81, 45, 0);
  }
}
</style>
