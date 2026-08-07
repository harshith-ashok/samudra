<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue';
import gsap from 'gsap';
import { useI18n } from '../composables/useI18n';

const emit = defineEmits<{ (e: 'done'): void }>();
const { t } = useI18n();

interface Step {
  selector: string;
  textKey: string;
}

const STEPS: Step[] = [
  { selector: '#map', textKey: 'guidedIntro.step1' },
  { selector: '.layer-panel', textKey: 'guidedIntro.step2' },
  { selector: '.fab-stack .fab', textKey: 'guidedIntro.step3' },
  { selector: '.scrubber-bar', textKey: 'guidedIntro.step4' },
];
const STEP_DURATION_MS = 2500;

const visible = ref(true);
const stepIndex = ref(0);
const spotlightEl = ref<HTMLDivElement | null>(null);
const captionEl = ref<HTMLDivElement | null>(null);
const captionAbove = ref(false);
let advanceTimer: number | undefined;

function positionFor(step: Step) {
  const target = document.querySelector(step.selector);
  if (!target) return null;
  return target.getBoundingClientRect();
}

function showStep(index: number) {
  const step = STEPS[index];
  const rect = positionFor(step);
  if (!rect || !spotlightEl.value || !captionEl.value) {
    // target not in the DOM yet (e.g. scrubber still loading) — skip to the next step
    if (index < STEPS.length - 1) {
      stepIndex.value = index + 1;
      showStep(stepIndex.value);
    } else {
      finish();
    }
    return;
  }
  const CAPTION_HEIGHT = 110;
  captionAbove.value = rect.bottom + 14 + CAPTION_HEIGHT > window.innerHeight;
  gsap.to(spotlightEl.value, {
    left: rect.left - 6,
    top: rect.top - 6,
    width: rect.width + 12,
    height: rect.height + 12,
    duration: 0.5,
    ease: 'power2.inOut',
  });
  gsap.fromTo(
    captionEl.value,
    { opacity: 0, y: 8 },
    { opacity: 1, y: 0, duration: 0.35, delay: 0.15 }
  );
  const rawTop = captionAbove.value
    ? rect.top - 14 - CAPTION_HEIGHT
    : rect.bottom + 14;
  gsap.to(captionEl.value, {
    left: Math.min(Math.max(rect.left, 16), window.innerWidth - 336),
    top: Math.min(
      Math.max(rawTop, 16),
      window.innerHeight - CAPTION_HEIGHT - 16
    ),
    duration: 0.5,
    ease: 'power2.inOut',
  });
}

function next() {
  window.clearTimeout(advanceTimer);
  if (stepIndex.value >= STEPS.length - 1) {
    finish();
    return;
  }
  stepIndex.value += 1;
  showStep(stepIndex.value);
  advanceTimer = window.setTimeout(next, STEP_DURATION_MS);
}

function finish() {
  window.clearTimeout(advanceTimer);
  gsap.to([spotlightEl.value, captionEl.value], {
    opacity: 0,
    duration: 0.3,
    onComplete: () => {
      visible.value = false;
      localStorage.setItem('samudra_intro_seen', '1');
      emit('done');
    },
  });
}

onMounted(() => {
  showStep(0);
  advanceTimer = window.setTimeout(next, STEP_DURATION_MS);
});

onBeforeUnmount(() => window.clearTimeout(advanceTimer));
</script>

<template>
  <div v-if="visible" class="intro-root">
    <div ref="spotlightEl" class="spotlight"></div>
    <div ref="captionEl" class="caption">
      <div class="caption-step">{{ stepIndex + 1 }} / {{ STEPS.length }}</div>
      <p>{{ t(STEPS[stepIndex].textKey) }}</p>
      <button class="skip-btn" @click="finish">{{ t('guidedIntro.skipTour') }}</button>
    </div>
  </div>
</template>

<style scoped>
.intro-root {
  position: fixed;
  inset: 0;
  z-index: 90;
  pointer-events: none;
}
.spotlight {
  position: fixed;
  border: 2px solid var(--teal);
  border-radius: 12px;
  box-shadow: 0 0 0 9999px rgba(15, 38, 32, 0.6);
  pointer-events: none;
}
.caption {
  position: fixed;
  width: 320px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 16px;
  box-shadow: var(--shadow);
  pointer-events: auto;
}
.caption-step {
  font-family: var(--font-mono);
  font-size: 9.5px;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 6px;
}
.caption p {
  font-size: 13px;
  line-height: 1.5;
  color: var(--text);
  margin-bottom: 10px;
}
.skip-btn {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 5px 10px;
  font-size: 11px;
  color: var(--muted);
  cursor: pointer;
}
.skip-btn:hover {
  color: var(--coral);
  border-color: var(--coral);
}
</style>
