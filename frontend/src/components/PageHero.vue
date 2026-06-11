<template>
  <section class="page-hero" :class="[`tone-${tone}`]">
    <div class="page-hero__copy">
      <div v-if="eyebrow" class="page-hero__eyebrow">{{ eyebrow }}</div>
      <h1 class="page-hero__title">{{ title }}</h1>
      <p class="page-hero__description">{{ subtitle || description }}</p>

      <div v-if="$slots.actions" class="page-hero__actions">
        <slot name="actions" />
      </div>
    </div>

    <div class="page-hero__side">
      <slot name="aside" />
    </div>
  </section>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    eyebrow?: string
    title: string
    description?: string
    subtitle?: string
    tone?: 'teal' | 'orange' | 'green' | 'sun'
  }>(),
  {
    eyebrow: '',
    description: '',
    subtitle: '',
    tone: 'teal',
  },
)
</script>

<style scoped>
.page-hero {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(240px, 0.6fr);
  gap: 24px;
  padding: 28px;
  border-radius: var(--radius-xl);
  border-left: 3px solid var(--color-primary);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}

.page-hero__copy,
.page-hero__side {
  position: relative;
  z-index: 1;
}

.page-hero__copy {
  display: grid;
  gap: 12px;
  align-content: start;
}

.page-hero__eyebrow {
  color: var(--color-muted);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.page-hero__title {
  max-width: 780px;
  margin: 0;
  color: var(--color-text);
  font-family: var(--font-heading);
  font-size: clamp(28px, 3vw, 38px);
  font-weight: 600;
  line-height: 1.12;
  letter-spacing: 0;
}

.page-hero__description {
  max-width: 760px;
  margin: 0;
  color: var(--color-body);
  font-size: 15px;
  line-height: 1.6;
}

.page-hero__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 2px;
}

.page-hero__side {
  display: flex;
  align-items: stretch;
  justify-content: stretch;
}

.page-hero__side :deep(.hero-metric-grid) {
  align-self: stretch;
}

.tone-teal,
.tone-orange,
.tone-green,
.tone-sun {
  background: var(--color-surface);
}

@media (max-width: 1080px) {
  .page-hero {
    grid-template-columns: 1fr;
    gap: 18px;
  }
}

@media (max-width: 900px) {
  .page-hero {
    padding: 22px 20px;
  }

  .page-hero__title {
    font-size: clamp(24px, 6vw, 32px);
  }

  .page-hero__description {
    font-size: 14px;
    line-height: 1.7;
  }
}

@media (max-width: 720px) {
  .page-hero {
    padding: 20px 16px;
    border-radius: var(--radius-lg);
  }

  .page-hero__title {
    font-size: 24px;
  }

  .page-hero__actions {
    display: grid;
    grid-template-columns: 1fr;
  }
}

@media (max-width: 430px) {
  .page-hero {
    padding: 18px 16px;
  }

  .page-hero__title {
    font-size: 22px;
  }

  .page-hero__description {
    font-size: 13px;
  }
}
</style>
