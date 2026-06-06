<template>
  <div class="filter-bar">
    <el-form :inline="true" :model="modelValue" class="filter-bar__form">
      <template v-for="filter in filters" :key="filter.key">
        <!-- 文本搜索 -->
        <el-form-item v-if="filter.type === 'search'" :label="filter.label">
          <el-input
            v-model="modelValue[filter.key]"
            :placeholder="filter.placeholder || '输入关键词搜索'"
            clearable
            :style="{ width: filter.width || '200px' }"
            @clear="$emit('update:modelValue', { ...modelValue, [filter.key]: '' })"
          />
        </el-form-item>

        <!-- 下拉选择 -->
        <el-form-item v-else-if="filter.type === 'select'" :label="filter.label">
          <el-select
            v-model="modelValue[filter.key]"
            :placeholder="filter.placeholder || '全部'"
            clearable
            :style="{ width: filter.width || '140px' }"
            @change="$emit('update:modelValue', { ...modelValue, [filter.key]: $event })"
          >
            <el-option
              v-for="opt in filter.options"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
        </el-form-item>

        <!-- 日期范围 -->
        <el-form-item v-else-if="filter.type === 'date-range'" :label="filter.label">
          <el-date-picker
            v-model="modelValue[filter.key]"
            type="daterange"
            range-separator="~"
            :start-placeholder="filter.startPlaceholder || '开始日期'"
            :end-placeholder="filter.endPlaceholder || '结束日期'"
            :style="{ width: filter.width || '260px' }"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>

        <!-- 标签组 -->
        <el-form-item v-else-if="filter.type === 'tags'" :label="filter.label">
          <div class="filter-bar__tags">
            <el-tag
              v-for="tag in filter.options"
              :key="tag.value"
              :type="modelValue[filter.key] === tag.value ? '' : 'info'"
              :effect="modelValue[filter.key] === tag.value ? 'dark' : 'plain'"
              class="filter-bar__tag"
              @click="$emit('update:modelValue', { ...modelValue, [filter.key]: tag.value })"
            >
              {{ tag.label }}
            </el-tag>
          </div>
        </el-form-item>
      </template>

      <el-form-item>
        <el-button type="primary" @click="$emit('search')">
          <el-icon><Search /></el-icon>
          搜索
        </el-button>
        <el-button v-if="showReset" @click="$emit('reset')">重置</el-button>
        <slot name="extra" />
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { Search } from '@element-plus/icons-vue'

export interface FilterOption {
  value: string
  label: string
}

export interface FilterConfig {
  key: string
  label: string
  type: 'search' | 'select' | 'date-range' | 'tags'
  placeholder?: string
  startPlaceholder?: string
  endPlaceholder?: string
  width?: string
  options?: FilterOption[]
}

defineProps<{
  filters: FilterConfig[]
  modelValue: Record<string, any>
  showReset?: boolean
}>()

defineEmits<{
  'update:modelValue': [value: Record<string, any>]
  'search': []
  'reset': []
}>()
</script>

<style scoped>
.filter-bar__form {
  margin-bottom: 0;
}
.filter-bar__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.filter-bar__tag {
  cursor: pointer;
}
</style>
