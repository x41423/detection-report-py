<template>
  <div class="page-shell category-page">
    <PageHero title="分类管理" subtitle="维护商品分类树，支持三级结构。" />

    <el-card shadow="never">
      <div class="toolbar-row">
        <span class="soft-note">共 {{ flatCategories.length }} 条分类</span>
        <el-button type="primary" @click="openCreate(null)">
          <el-icon><Plus /></el-icon>
          新增一级分类
        </el-button>
      </div>

      <el-table
        :data="treeData"
        row-key="id"
        v-loading="loading"
        stripe
        size="small"
        default-expand-all
        :tree-props="{ children: 'children', hasChildren: 'hasChildren' }"
        style="margin-top: 12px"
      >
        <el-table-column prop="name" label="分类名称" min-width="200" />
        <el-table-column prop="level" label="层级" width="80" align="center" />
        <el-table-column prop="sort_order" label="排序" width="80" align="center" />
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openCreate(row)">添加子级</el-button>
            <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
            <el-popconfirm title="确定删除？" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button link type="danger" size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Form Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑分类' : '新增分类'"
      width="480px"
      destroy-on-close
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" label-width="80px">
        <el-form-item label="名称">
          <el-input v-model="form.name" placeholder="输入分类名称" maxlength="30" />
        </el-form-item>
        <el-form-item label="上级分类">
          <el-tree-select
            v-model="form.parent_id"
            :data="parentOptions"
            :props="{ value: 'id', label: 'name', children: 'children' }"
            placeholder="无（一级分类）"
            clearable
            check-strictly
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort_order" :min="0" :max="999" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import PageHero from '../components/PageHero.vue'
import {
  getCategories,
  createCategory,
  updateCategory,
  deleteCategory,
  type Category,
} from '../api/product'

// ── State ──
const flatCategories = ref<Category[]>([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const { data } = await getCategories()
    flatCategories.value = (data as any).items ?? data.items ?? []
  } finally {
    loading.value = false
  }
}

// ── Tree ──
function buildTree(items: Category[]): Category[] {
  const map = new Map<number, Category>()
  const roots: Category[] = []
  for (const item of items) {
    map.set(item.id, { ...item, children: [] })
  }
  for (const node of map.values()) {
    if (node.parent_id && map.has(node.parent_id)) {
      map.get(node.parent_id)!.children!.push(node)
    } else {
      roots.push(node)
    }
  }
  return roots
}

const treeData = computed(() => buildTree(flatCategories.value))

// ── Parent options (exclude self + descendants) ──
const parentOptions = ref<Category[]>([])

function refreshParentOptions(excludeId?: number) {
  const excludeIds = new Set<number>()
  if (excludeId) {
    excludeIds.add(excludeId)
    gatherDescendants(flatCategories.value, excludeId, excludeIds)
  }
  const filtered = flatCategories.value.filter(c => !excludeIds.has(c.id))
  parentOptions.value = buildTree(filtered)
}

function gatherDescendants(items: Category[], parentId: number, out: Set<number>) {
  for (const item of items) {
    if (item.parent_id === parentId) {
      out.add(item.id)
      gatherDescendants(items, item.id, out)
    }
  }
}

// ── Form ──
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const form = reactive({ name: '', parent_id: undefined as number | undefined, sort_order: 0 })

function resetForm() {
  editingId.value = null
  form.name = ''
  form.parent_id = undefined
  form.sort_order = 0
}

function openCreate(parent: Category | null) {
  resetForm()
  form.parent_id = parent?.id
  refreshParentOptions()
  dialogVisible.value = true
}

function openEdit(row: Category) {
  editingId.value = row.id
  form.name = row.name
  form.parent_id = row.parent_id ?? undefined
  form.sort_order = row.sort_order
  refreshParentOptions(row.id)
  dialogVisible.value = true
}

async function submit() {
  if (!form.name.trim()) { ElMessage.warning('请输入名称'); return }
  const payload = {
    name: form.name.trim(),
    parent_id: form.parent_id ?? 0,
    sort_order: form.sort_order,
  }
  try {
    if (editingId.value) {
      await updateCategory(editingId.value, payload)
      ElMessage.success('已更新')
    } else {
      await createCategory(payload)
      ElMessage.success('已创建')
    }
    dialogVisible.value = false
    await load()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  }
}

async function handleDelete(id: number) {
  try {
    await deleteCategory(id)
    flatCategories.value = flatCategories.value.filter(c => c.id !== id)
    ElMessage.success('已删除')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

onMounted(load)
</script>

<style scoped>
.toolbar-row {
  display: flex; align-items: center; justify-content: space-between;
}
.soft-note { color: var(--el-text-color-secondary); font-size: 13px; }
</style>
