<template>
  <div class="status-log">
    <div class="status-log__header">
      <div>
        <div class="status-log__eyebrow">事件流</div>
        <div class="status-log__title">状态日志</div>
      </div>

      <div class="status-log__actions">
        <span class="status-log__count">{{ logs.length }} 条</span>
        <el-button v-if="logs.length > 0" text @click="clear">清空</el-button>
      </div>
    </div>

    <div ref="logBody" class="status-log__body">
      <div v-if="logs.length === 0" class="status-log__empty">
        这里会按时间顺序记录执行过程、成功提示和错误信息。
      </div>

      <div
        v-for="(log, index) in logs"
        :key="index"
        class="status-log__item"
        :class="`status-log__item--${log.type}`"
      >
        <div class="status-log__line" />
        <div class="status-log__marker">
          <el-icon v-if="log.type === 'success'"><CircleCheck /></el-icon>
          <el-icon v-else-if="log.type === 'error'"><CircleClose /></el-icon>
          <el-icon v-else><InfoFilled /></el-icon>
        </div>

        <div class="status-log__content">
          <div class="status-log__meta">
            <span class="status-log__type">{{ typeLabel(log.type) }}</span>
            <span class="status-log__time">{{ log.time }}</span>
          </div>
          <div class="status-log__message">{{ log.msg }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, ref } from 'vue'
import { CircleCheck, CircleClose, InfoFilled } from '@element-plus/icons-vue'

interface LogEntry {
  time: string
  msg: string
  type: 'info' | 'success' | 'error'
}

const logs = ref<LogEntry[]>([])
const logBody = ref<HTMLElement>()

function now(): string {
  return new Date().toLocaleTimeString()
}

function append(msg: string, type: 'info' | 'success' | 'error' = 'info') {
  logs.value.push({ time: now(), msg, type })
  nextTick(() => {
    if (logBody.value) {
      logBody.value.scrollTop = logBody.value.scrollHeight
    }
  })
}

function clear() {
  logs.value = []
}

function typeLabel(type: LogEntry['type']) {
  if (type === 'success') return '成功'
  if (type === 'error') return '失败'
  return '信息'
}

defineExpose({ append, clear })
</script>

<style scoped>
.status-log {
  position: relative;
  border-radius: var(--radius-lg);
  background: #ffffff;
  box-shadow: var(--shadow-glass);
  overflow: hidden;
}

.status-log::before {
  content: none;
}

.status-log__header,
.status-log__body {
  position: relative;
  z-index: 1;
}

.status-log__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
  padding: 18px 20px 14px;
  box-shadow: inset 0 -1px 0 rgba(34, 42, 53, 0.08);
}

.status-log__eyebrow {
  color: var(--color-muted-soft);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.status-log__title {
  margin-top: 4px;
  color: var(--color-text);
  font-family: var(--font-heading);
  font-size: 20px;
  font-weight: 600;
}

.status-log__actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.status-log__count {
  padding: 6px 10px;
  border-radius: 999px;
  background: #fafafa;
  box-shadow: inset 0 0 0 1px rgba(34, 42, 53, 0.08);
  color: var(--color-muted);
  font-size: 12px;
  font-weight: 600;
}

.status-log__body {
  max-height: 360px;
  overflow-y: auto;
  padding: 14px 20px 18px;
}

.status-log__body::-webkit-scrollbar {
  width: 10px;
}

.status-log__body::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(71, 85, 105, 0.24);
}

.status-log__empty {
  padding: 30px 10px;
  color: var(--color-muted);
  font-size: 14px;
  line-height: 1.7;
  text-align: center;
}

.status-log__item {
  position: relative;
  display: grid;
  grid-template-columns: 16px 42px minmax(0, 1fr);
  gap: 12px;
  padding: 10px 0;
}

.status-log__line {
  width: 2px;
  height: calc(100% + 12px);
  margin: 20px auto 0;
  border-radius: 999px;
  background: rgba(34, 42, 53, 0.1);
}

.status-log__item:last-child .status-log__line {
  height: 24px;
}

.status-log__marker {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: var(--radius-md);
  background: #fafafa;
  color: var(--color-text);
  box-shadow: inset 0 0 0 1px rgba(34, 42, 53, 0.08);
}

.status-log__item--success .status-log__marker {
  color: var(--color-success);
  background: rgba(16, 185, 129, 0.08);
}

.status-log__item--error .status-log__marker {
  color: var(--color-danger);
  background: rgba(239, 68, 68, 0.08);
}

.status-log__content {
  padding: 12px 14px;
  border-radius: var(--radius-md);
  background: #ffffff;
  box-shadow: var(--shadow-glass);
}

.status-log__meta {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: baseline;
}

.status-log__type {
  color: var(--color-text);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.status-log__time {
  color: var(--color-muted-soft);
  font-size: 12px;
}

.status-log__message {
  margin-top: 8px;
  color: var(--color-text);
  font-size: 14px;
  line-height: 1.65;
  word-break: break-word;
}

@media (max-width: 720px) {
  .status-log__header,
  .status-log__meta {
    flex-direction: column;
    align-items: flex-start;
  }

  .status-log__item {
    grid-template-columns: 12px 38px minmax(0, 1fr);
  }
}
</style>
