<template>
  <div class="data-table">
    <el-table
      :data="data"
      :loading="loading"
      :default-sort="{ prop: defaultSort?.prop, order: defaultSort?.order }"
      stripe
      highlight-current-row
      @sort-change="$emit('sort-change', $event)"
      @selection-change="$emit('selection-change', $event)"
    >
      <el-table-column
        v-if="selectable"
        type="selection"
        width="40"
        fixed="left"
      />
      <el-table-column
        v-for="col in columns"
        :key="col.prop"
        :prop="col.prop"
        :label="col.label"
        :width="col.width"
        :min-width="col.minWidth"
        :sortable="col.sortable ? 'custom' : false"
        :fixed="col.fixed"
        :show-overflow-tooltip="col.tooltip !== false"
      >
        <template v-if="col.slot" #default="scope">
          <slot :name="col.slot" :row="scope.row" :index="scope.$index" />
        </template>
      </el-table-column>
      <el-table-column
        v-if="actions?.length"
        label="操作"
        :width="actionsWidth"
        fixed="right"
      >
        <template #default="scope">
          <slot name="actions" :row="scope.row" :index="scope.$index">
            <el-button
              v-for="act in actions"
              :key="act.key"
              :type="act.type || 'primary'"
              :link="act.link !== false"
              size="small"
              @click="$emit('action', act.key, scope.row)"
            >
              {{ act.label }}
            </el-button>
          </slot>
        </template>
      </el-table-column>
    </el-table>

    <div v-if="showPagination" class="data-table__pagination">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="currentPageSize"
        :page-sizes="pageSizes"
        :total="total"
        :layout="paginationLayout"
        background
        @size-change="$emit('page-change', currentPage, currentPageSize)"
        @current-change="$emit('page-change', currentPage, currentPageSize)"
      />
    </div>

    <div v-if="!loading && (!data || data.length === 0)" class="data-table__empty">
      <slot name="empty">
        <el-empty :description="emptyText" />
      </slot>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

export interface ColumnConfig {
  prop: string
  label: string
  width?: number | string
  minWidth?: number | string
  sortable?: boolean
  fixed?: 'left' | 'right' | boolean
  tooltip?: boolean
  slot?: string
}

export interface ActionConfig {
  key: string
  label: string
  type?: 'primary' | 'success' | 'warning' | 'danger' | 'info'
  link?: boolean
}

export interface SortConfig {
  prop: string
  order: 'ascending' | 'descending'
}

const props = withDefaults(defineProps<{
  columns: ColumnConfig[]
  data: any[]
  loading?: boolean
  total?: number
  selectable?: boolean
  actions?: ActionConfig[]
  actionsWidth?: number | string
  showPagination?: boolean
  pageSizes?: number[]
  paginationLayout?: string
  defaultSort?: SortConfig
  emptyText?: string
}>(), {
  loading: false,
  total: 0,
  selectable: false,
  showPagination: true,
  pageSizes: () => [10, 20, 50, 100],
  paginationLayout: 'total, sizes, prev, pager, next, jumper',
  actionsWidth: 160,
  emptyText: '暂无数据',
})

const currentPage = ref(1)
const currentPageSize = ref(props.pageSizes[0])

defineEmits<{
  'sort-change': [value: any]
  'selection-change': [value: any[]]
  'page-change': [page: number, pageSize: number]
  'action': [key: string, row: any]
}>()
</script>

<style scoped>
.data-table__pagination {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
.data-table__empty {
  padding: 20px 0;
}
</style>
