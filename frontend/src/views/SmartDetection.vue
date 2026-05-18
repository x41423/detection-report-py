<template>
  <div class="smart-detection">
    <el-card class="header-card">
      <div class="header-row">
        <h2>智能检测工作台</h2>
        <span class="inspector">检查员: {{ inspectorName }}</span>
      </div>
      <el-radio-group v-model="dataSource" class="source-switch">
        <el-radio-button value="auto">自动推荐</el-radio-button>
        <el-radio-button value="manual">完全手动</el-radio-button>
      </el-radio-group>
    </el-card>

    <el-alert v-if="gaps && gaps.total_missing > 0" type="warning" :closable="false" show-icon style="margin-bottom:12px">
      <template #title>
        发现 {{ gaps.total_missing }} 天遗漏检测:
        {{ gaps.missing_dates.slice(0, 3).join(', ') }}{{ gaps.missing_dates.length > 3 ? '...' : '' }}
        <el-button type="warning" size="small" @click="showBackfillDialog">批量补做</el-button>
      </template>
    </el-alert>

    <el-skeleton v-if="loading" :rows="6" animated />

    <div v-else class="panels" :class="{ 'manual-mode': dataSource === 'manual' }">
      <div v-if="dataSource === 'auto'" class="panel">
        <div class="panel-header">
          <span>今日进货需检 ({{ todayIntakeItems.length }} 种)</span>
          <div class="panel-actions">
            <el-button size="small" text @click="selectAllToday">全选</el-button>
            <el-button size="small" text @click="deselectAllToday">反选</el-button>
          </div>
        </div>
        <div class="veg-list">
          <el-checkbox
            v-for="item in todayIntakeItems"
            :key="item.name"
            :model-value="selectedToday.has(item.name)"
            @change="toggleToday(item.name)"
          >
            {{ item.name }}
          </el-checkbox>
        </div>
        <div v-if="todayIntakeItems.length === 0" class="empty-hint">暂无今日点货数据</div>
      </div>

      <div v-if="dataSource === 'auto'" class="panel">
        <div class="panel-header">
          <span>昨日库存未检 ({{ yesterdayInventoryItems.length }} 种)</span>
          <div class="panel-actions">
            <el-button size="small" text @click="selectAllYesterday">全选</el-button>
            <el-button size="small" text @click="deselectAllYesterday">反选</el-button>
          </div>
        </div>
        <div class="veg-list">
          <el-checkbox
            v-for="item in yesterdayInventoryItems"
            :key="item.name"
            :model-value="selectedYesterday.has(item.name)"
            @change="toggleYesterday(item.name)"
          >
            {{ item.name }}
            <el-tag size="small" type="warning" style="margin-left:4px">未检</el-tag>
          </el-checkbox>
        </div>
        <div v-if="yesterdayInventoryItems.length === 0" class="empty-hint">昨日均已检测</div>
      </div>

      <div class="panel manual-panel">
        <div class="panel-header">
          <span>手动补充 ({{ manualAdditions.length }} 种)</span>
        </div>
        <div class="manual-input">
          <el-input v-model="newVegName" placeholder="输入蔬菜名称" size="small" @keyup.enter="addManualVeg">
            <template #append>
              <el-button @click="addManualVeg">添加</el-button>
            </template>
          </el-input>
        </div>
        <el-tag
          v-for="(name, idx) in manualAdditions"
          :key="idx"
          closable
          class="manual-tag"
          @close="removeManual(idx)"
        >
          {{ name }}
        </el-tag>
      </div>
    </div>

    <div v-if="!loading" class="action-bar">
      <div class="action-info">
        <span>检测日期: <strong>{{ detectionDate }}</strong></span>
        <span>已选 <strong>{{ selectedCount }}</strong> 种蔬菜</span>
        <span>模板: 自动匹配</span>
      </div>
      <div class="action-buttons">
        <el-button type="primary" size="large" :loading="executing" @click="runDetection">
          一键生成报告
        </el-button>
        <el-button size="large" :loading="executing" @click="runDetectionWithPdf">
          生成并导出 PDF
        </el-button>
      </div>
    </div>

    <el-card v-if="lastResult" class="result-card">
      <template #header>检测结果</template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="状态">
          <el-tag :type="lastResult.success ? 'success' : 'danger'">
            {{ lastResult.success ? '成功' : '失败' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="检测日期">{{ detectionDate }}</el-descriptions-item>
        <el-descriptions-item label="蔬菜数量">{{ lastResult.summary?.total_varieties || 0 }} 种</el-descriptions-item>
        <el-descriptions-item label="检测员">{{ lastResult.summary?.inspector || inspectorName }}</el-descriptions-item>
      </el-descriptions>

      <el-alert
        v-if="lastResult.low_stock_alerts && lastResult.low_stock_alerts.length > 0"
        type="warning"
        :closable="false"
        show-icon
        style="margin-top: 12px"
      >
        <template #title>
          库存低量提醒:
          <el-tag
            v-for="a in lastResult.low_stock_alerts"
            :key="a.item_name"
            size="small"
            type="warning"
            style="margin-left: 4px"
          >
            {{ a.item_name }} ({{ a.balance }}{{ a.unit }})
          </el-tag>
        </template>
      </el-alert>
    </el-card>

    <el-alert v-if="smartError" :title="smartError" type="error" show-icon style="margin-top:12px" />

    <el-dialog v-model="backfillDialogVisible" title="批量补做遗漏检测" width="500px">
      <el-form label-width="100px">
        <el-form-item label="日期范围">
          <el-date-picker
            v-model="backfillDateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="backfillDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="backfilling" @click="runBackfill">开始补做</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useSmartDetection } from '../features/smart-detection/composables/useSmartDetection'
import { useGapDetection } from '../features/smart-detection/composables/useGapDetection'

const inspectorName = ref('检测员')
const dataSource = ref<'auto' | 'manual'>('auto')
const detectionDate = ref(new Date().toISOString().split('T')[0])
const newVegName = ref('')

const {
  todayIntakeItems, yesterdayInventoryItems, manualAdditions,
  selectedToday, selectedYesterday,
  loading, executing, lastResult,
  selectedCount, error: smartError,
  loadRecommendations, toggleToday, toggleYesterday,
  selectAllToday, deselectAllToday, selectAllYesterday, deselectAllYesterday,
  addManual, removeManual, execute,
} = useSmartDetection()

const { gaps, backfilling, checkGaps, backfill } = useGapDetection()

const backfillDialogVisible = ref(false)
const backfillDateRange = ref<[string, string] | null>(null)

function addManualVeg() {
  if (newVegName.value.trim()) {
    addManual(newVegName.value.trim())
    newVegName.value = ''
  }
}

async function runDetection() {
  await execute({
    date: detectionDate.value, big_template: '', small_template: '',
    output_dir: '', inspector_name: inspectorName.value, export_format: 'docx',
  })
}

async function runDetectionWithPdf() {
  await execute({
    date: detectionDate.value, big_template: '', small_template: '',
    output_dir: '', inspector_name: inspectorName.value, export_format: 'both',
  })
}

function showBackfillDialog() {
  backfillDateRange.value = null
  backfillDialogVisible.value = true
}

async function runBackfill() {
  if (!backfillDateRange.value) {
    ElMessage.warning('请选择日期范围')
    return
  }
  await backfill(backfillDateRange.value[0], backfillDateRange.value[1], inspectorName.value)
  backfillDialogVisible.value = false
  ElMessage.success('补做完成')
}

onMounted(() => {
  loadRecommendations(detectionDate.value)
  checkGaps(7)
})
</script>

<style scoped>
.smart-detection { padding: 16px; max-width: 1400px; margin: 0 auto; }
.header-card { margin-bottom: 12px; }
.header-row { display: flex; justify-content: space-between; align-items: center; }
.header-row h2 { margin: 0; font-size: 20px; }
.inspector { color: #909399; font-size: 14px; }
.source-switch { margin-top: 8px; }

.panels { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin: 16px 0; }
.panels.manual-mode { grid-template-columns: 1fr; }
.panel { background: #fff; border: 1px solid #ebeef5; border-radius: 8px; padding: 12px; }
.panel-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; font-weight: 600; }
.panel-actions { display: flex; gap: 4px; }
.veg-list { display: flex; flex-direction: column; gap: 6px; max-height: 400px; overflow-y: auto; }
.empty-hint { color: #c0c4cc; font-size: 13px; text-align: center; padding: 20px 0; }
.manual-input { margin-bottom: 8px; }
.manual-tag { margin: 2px; }

.action-bar { display: flex; justify-content: space-between; align-items: center; padding: 16px; background: #fff; border-radius: 8px; border: 1px solid #ebeef5; margin: 12px 0; }
.action-info { display: flex; gap: 20px; color: #606266; }
.action-buttons { display: flex; gap: 8px; }

.result-card { margin-top: 16px; }
</style>
