<template>
  <section class="page-header" :class="[`tone-${tone}`]">
    <div class="page-header__row">
      <div class="page-header__copy">
        <span v-if="eyebrow" class="page-header__eyebrow">{{ eyebrow }}</span>
        <h1 class="page-header__title">{{ title }}</h1>
      </div>
      <div v-if="$slots.actions" class="page-header__actions">
        <slot name="actions" />
      </div>
    </div>
    <div v-if="$slots.aside" class="page-header__stats">
      <slot name="aside" />
    </div>
  </section>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    eyebrow?: string
    title: string
    tone?: 'teal' | 'orange' | 'green' | 'sun'
  }>(),
  {
    eyebrow: '',
    tone: 'teal',
  },
)
</script>

<style scoped>
.page-header {
  padding: 14px 24px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}

.page-header__row {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  min-width: 0;
}

.page-header__copy {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex: 1;
}

.page-header__eyebrow {
  flex-shrink: 0;
  padding: 3px 0;
  border-radius: 999px;
  background: transparent;
  color: var(--color-muted);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  white-space: nowrap;
}

.page-header__title {
  margin: 0;
  color: var(--color-text);
  font-family: var(--font-heading);
  font-size: 20px;
  font-weight: 600;
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.page-header__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-left: auto;
  flex-shrink: 0;
}

.page-header__stats {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border);
}

/* Override hero-metric-grid to display as a horizontal strip inside PageHeader */
.page-header__stats :deep(.hero-metric-grid) {
  display: flex;
  gap: 0;
  flex-wrap: wrap;
  width: 100%;
}

.page-header__stats :deep(.hero-metric) {
  flex: 1;
  min-width: 110px;
  min-height: auto;
  padding: 6px 16px 8px;
  border-radius: 0;
  border: none;
    border-right: 1px solid var(--color-border);
  background: transparent;
  box-shadow: none;
}

.page-header__stats :deep(.hero-metric:first-child) {
  padding-left: 0;
}

.page-header__stats :deep(.hero-metric:last-child) {
  border-right: none;
}

.page-header__stats :deep(.hero-metric__label) {
  margin-bottom: 4px;
  font-size: 10px;
  letter-spacing: 0.14em;
}

.page-header__stats :deep(.hero-metric__value) {
  font-size: 18px;
  line-height: 1.2;
}

.page-header__stats :deep(.hero-metric__note) {
  margin-top: 3px;
  font-size: 11px;
  line-height: 1.45;
}

.tone-teal,
.tone-green,
.tone-orange,
.tone-sun {
  background: var(--color-surface);
}

@media (max-width: 900px) {
  .page-header__stats :deep(.hero-metric-grid) {
    flex-wrap: wrap;
  }

  .page-header__stats :deep(.hero-metric) {
    min-width: 50%;
    border-right: none;
    border-bottom: 1px solid rgba(34, 42, 53, 0.07);
    padding: 8px 0;
  }

  .page-header__stats :deep(.hero-metric:last-child),
  .page-header__stats :deep(.hero-metric:nth-last-child(2):nth-child(odd)) {
    border-bottom: none;
  }
}

@media (max-width: 600px) {
  .page-header {
    padding: 12px 16px;
  }

  .page-header__copy {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .page-header__title {
    font-size: 18px;
    white-space: normal;
    overflow: visible;
    text-overflow: clip;
  }

  .page-header__row {
    gap: 10px;
  }

  .page-header__actions {
    gap: 6px;
    width: 100%;
    margin-left: 0;
  }
}
</style>
