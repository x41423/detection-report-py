<template>
  <div class="variety-preview">
    <div class="variety-preview__stats">
      <div class="summary-card">
        <span class="summary-card__label">总品种</span>
        <span class="summary-card__value">{{ varieties.length }}</span>
        <span class="summary-card__note">来自已检测到的大表内容。</span>
      </div>

      <div class="summary-card">
        <span class="summary-card__label">已匹配</span>
        <span class="summary-card__value">{{ matchedVarieties.length }}</span>
        <span class="summary-card__note">当前输入菜名或别名已经覆盖。</span>
      </div>

      <div class="summary-card">
        <span class="summary-card__label">待核对</span>
        <span class="summary-card__value">{{ unmatchedVarieties.length }}</span>
        <span class="summary-card__note">仍未被命中的品种，建议重点复核。</span>
      </div>
    </div>

    <div v-if="varieties.length === 0" class="variety-preview__empty">
      先检测大表，再在这里核对品种匹配情况。
    </div>

    <template v-else>
      <section class="variety-preview__group">
        <div class="variety-preview__heading">
          <span class="accent-tag">已匹配</span>
          <span class="soft-note">这些品种已经被当前输入或别名规则命中。</span>
        </div>

        <div class="variety-preview__tags">
          <span
            v-for="name in matchedVarieties"
            :key="`matched-${name}`"
            class="variety-chip variety-chip--matched"
          >
            {{ name }}
          </span>
        </div>
      </section>

      <section class="variety-preview__group">
        <div class="variety-preview__heading">
          <span class="accent-tag warning-tag">待核对</span>
          <span class="soft-note">这些品种尚未被命中，可能是漏填、别名缺失或本次不需要。</span>
        </div>

        <div class="variety-preview__tags">
          <span
            v-for="name in unmatchedVarieties"
            :key="`unmatched-${name}`"
            class="variety-chip"
          >
            {{ name }}
          </span>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  varieties: string[]
  matchedSet: Set<string>
  aliasesMap: Record<string, string[]>
}>()

function normalize(value: string) {
  return value.trim().toLowerCase()
}

const matchedVarietySet = computed(() => {
  const result = new Set<string>()
  const nameToGroup: Record<string, Set<string>> = {}

  for (const [mainName, aliasList] of Object.entries(props.aliasesMap)) {
    const group = new Set([normalize(mainName), ...aliasList.map(normalize)])
    for (const name of group) {
      if (!nameToGroup[name]) {
        nameToGroup[name] = new Set()
      }
      for (const item of group) {
        nameToGroup[name].add(item)
      }
    }
  }

  for (const variety of props.varieties) {
    const normalized = normalize(variety)
    if (props.matchedSet.has(normalized)) {
      result.add(variety)
      continue
    }

    const aliasGroup = nameToGroup[normalized]
    if (!aliasGroup) {
      continue
    }

    for (const alias of aliasGroup) {
      if (props.matchedSet.has(alias)) {
        result.add(variety)
        break
      }
    }
  }

  return result
})

const matchedVarieties = computed(() =>
  props.varieties.filter((name) => matchedVarietySet.value.has(name)),
)

const unmatchedVarieties = computed(() =>
  props.varieties.filter((name) => !matchedVarietySet.value.has(name)),
)
</script>

<style scoped>
.variety-preview {
  display: grid;
  gap: 16px;
}

.variety-preview__stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.variety-preview__empty {
  padding: 28px 18px;
  border-radius: var(--radius-md);
  background: #fafafa;
  box-shadow: inset 0 0 0 1px rgba(34, 42, 53, 0.08);
  color: var(--color-muted);
  text-align: center;
  line-height: 1.7;
}

.variety-preview__group {
  display: grid;
  gap: 12px;
}

.variety-preview__heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.variety-preview__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  max-height: 220px;
  overflow-y: auto;
  padding-right: 4px;
}

.variety-chip {
  padding: 8px 12px;
  border-radius: 999px;
  background: #fafafa;
  border: 1px solid rgba(34, 42, 53, 0.1);
  color: var(--color-muted);
  font-size: 12px;
  line-height: 1;
}

.variety-chip--matched {
  background: rgba(16, 185, 129, 0.08);
  border-color: rgba(16, 185, 129, 0.28);
  color: #047857;
}

.accent-tag {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: 999px;
  background: rgba(34, 42, 53, 0.08);
  color: var(--color-text);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.warning-tag {
  background: rgba(245, 158, 11, 0.12);
  color: #b45309;
}

.soft-note {
  color: var(--color-muted);
  font-size: 12px;
}

@media (max-width: 720px) {
  .variety-preview__stats {
    grid-template-columns: 1fr;
  }
}
</style>
