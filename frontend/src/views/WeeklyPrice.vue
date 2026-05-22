<template>
  <div>
    <div class="page-shell compact">
      <PageHeader eyebrow="每周报价" title="在一个看板里切换两条每周报价流程" tone="orange">
        <template #actions>
          <button
            type="button"
            class="workflow-tab"
            :class="{ 'is-active': activeWorkflow === 'update' }"
            @click="activeWorkflow = 'update'"
          >
            <span class="workflow-tab__badge">流程 A</span>
            <span class="workflow-tab__title">参考价更新</span>
          </button>
          <button
            type="button"
            class="workflow-tab"
            :class="{ 'is-active': activeWorkflow === 'summary' }"
            @click="activeWorkflow = 'summary'"
          >
            <span class="workflow-tab__badge">流程 B</span>
            <span class="workflow-tab__title">新报价汇总</span>
          </button>
        </template>
      </PageHeader>
    </div>

    <WeeklyPriceUpdateWorkflow v-show="activeWorkflow === 'update'" />
    <WeeklyQuoteSummaryWorkflow
      v-if="summaryWorkflowMounted"
      v-show="activeWorkflow === 'summary'"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import PageHeader from '../components/PageHeader.vue'
import WeeklyPriceUpdateWorkflow from '../features/weekly-price/components/WeeklyPriceUpdateWorkflow.vue'
import WeeklyQuoteSummaryWorkflow from '../features/weekly-price/components/WeeklyQuoteSummaryWorkflow.vue'

const activeWorkflow = ref<'update' | 'summary'>('update')
const summaryWorkflowMounted = ref(false)

watch(
  activeWorkflow,
  (workflow) => {
    if (workflow === 'summary') {
      summaryWorkflowMounted.value = true
    }
  },
  { immediate: true },
)
</script>

<style scoped>
.workflow-tab {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border: 1px solid rgba(34, 42, 53, 0.14);
  border-radius: 8px;
  background: #ffffff;
  cursor: pointer;
  transition:
    border-color 0.22s ease,
    background 0.22s ease,
    box-shadow 0.22s ease;
}

.workflow-tab:hover {
  border-color: var(--color-border-highlight);
  background: var(--color-surface-card);
}

.workflow-tab.is-active {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
}

.workflow-tab__badge {
  padding: 2px 7px;
  border-radius: 999px;
  background: rgba(34, 42, 53, 0.08);
  color: var(--color-muted-soft);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.workflow-tab.is-active .workflow-tab__badge {
  background: var(--color-primary);
  color: #ffffff;
}

.workflow-tab__title {
  color: var(--color-text);
  font-family: var(--font-heading);
  font-size: 13px;
  font-weight: 700;
}

@media (max-width: 600px) {
  .workflow-tab__title {
    display: none;
  }
}
</style>
