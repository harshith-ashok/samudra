import { ref } from 'vue';

export type VoiceRecorderState = 'idle' | 'recording' | 'transcribing' | 'error';

const MAX_RECORD_MS = 12000;

export interface VoiceRecorderMessages {
  transcribeError: () => string;
  micDenied: () => string;
}

const DEFAULT_MESSAGES: VoiceRecorderMessages = {
  transcribeError: () => "Couldn't transcribe — is the backend running?",
  micDenied: () => 'Microphone access denied or unavailable.',
};

/** Wraps the browser MediaRecorder state machine (permissions, MIME
 * detection, auto-stop, cleanup) so callers just supply how to transcribe a
 * blob and what to do with the resulting text — used by both the NLQ search
 * bar and the AI Assistant mic (MapShell.vue, AIChat.vue). `messages` lets
 * each caller pass already-translated (t()) error text — as getters, not
 * plain strings, since MapShell mounts once for the whole session: a plain
 * string would freeze in whatever language was active at mount, not update
 * when the user switches languages later. Defaults to English getters. */
export function useVoiceRecorder(
  transcribe: (blob: Blob) => Promise<string>,
  onTranscribed: (text: string) => void,
  messages: VoiceRecorderMessages = DEFAULT_MESSAGES
) {
  const state = ref<VoiceRecorderState>('idle');
  const errorMsg = ref('');
  let mediaRecorder: MediaRecorder | null = null;
  let audioChunks: Blob[] = [];
  let autoStopTimer: number | undefined;

  function stop() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop();
  }

  async function toggle() {
    if (state.value === 'recording') {
      stop();
      return;
    }
    if (state.value === 'transcribing') return;

    errorMsg.value = '';
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : '';
      mediaRecorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);
      audioChunks = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunks.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        window.clearTimeout(autoStopTimer);
        if (!audioChunks.length) {
          state.value = 'idle';
          return;
        }
        state.value = 'transcribing';
        try {
          const blob = new Blob(audioChunks, {
            type: mediaRecorder?.mimeType || 'audio/webm',
          });
          const text = await transcribe(blob);
          if (text) onTranscribed(text);
          state.value = 'idle';
        } catch {
          errorMsg.value = messages.transcribeError();
          state.value = 'error';
          window.setTimeout(() => (state.value = 'idle'), 2500);
        }
      };

      mediaRecorder.start();
      state.value = 'recording';
      autoStopTimer = window.setTimeout(stop, MAX_RECORD_MS);
    } catch {
      errorMsg.value = messages.micDenied();
      state.value = 'error';
      window.setTimeout(() => (state.value = 'idle'), 2500);
    }
  }

  function dispose() {
    window.clearTimeout(autoStopTimer);
    if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop();
  }

  return { state, errorMsg, toggle, dispose };
}
