<template>
  <el-card shadow="never" class="panel-card panel-card--emphasis file-source-panel">
    <div class="panel-heading">
      <div>
        <div class="panel-heading__eyebrow">文件来源</div>
        <h2 class="panel-heading__title">{{ heading }}</h2>
      </div>
      <slot name="header-actions" />
    </div>

    <!-- 模式切换 radio -->
    <el-radio-group
      v-if="modes.length > 0"
      :model-value="modelValue"
      style="margin-bottom: 16px"
      @change="(v: string) => $emit('update:modelValue', v)"
    >
      <el-radio-button
        v-for="m in modes"
        :key="m.value"
        :value="m.value"
      >
        {{ m.label }}
      </el-radio-button>
    </el-radio-group>

    <el-form label-position="top">
      <!-- 路径锁定模式 -->
      <template v-if="modelValue === pathLockValue">
        <div class="field-grid two-up">
          <el-form-item
            v-for="slot in slots"
            :key="'lock-' + slot.key"
            :label="slot.label + '目录'"
          >
            <el-input
              :model-value="paths[slot.key] || ''"
              placeholder="点击右侧浏览"
              readonly
            >
              <template #append>
                <el-button @click="$emit('browse', slot.key)">
                  浏览
                </el-button>
              </template>
            </el-input>
          </el-form-item>
        </div>

        <el-button
          type="primary"
          :loading="locking"
          :disabled="!canLock"
          @click="$emit('lock')"
        >
          {{ lockLabel || '锁定模板路径' }}
        </el-button>

        <span
          v-if="lockMessage"
          :class="pathLocked ? 'soft-note' : 'soft-note text--error'"
          style="margin-left: 12px"
        >
          {{ lockMessage }}
        </span>

        <!-- 锁定后显示找到的文件 -->
        <div v-if="pathLocked && lockedFiles && lockedFiles.length > 0" class="soft-note" style="margin-top: 8px">
          <div v-for="f in lockedFiles" :key="f.key">
            {{ f.label }}: {{ f.path }}
          </div>
        </div>

        <slot name="after-lock" />
      </template>

      <!-- 文件选择模式（默认） -->
      <template v-else>
        <slot name="before-slots" />

        <div class="field-grid two-up">
          <el-form-item
            v-for="slot in slots"
            :key="'upload-' + slot.key"
            :label="slot.label"
          >
            <div style="display: flex; align-items: center; gap: 8px">
              <el-button size="small" @click="$emit('browse', slot.key)">
                浏览
              </el-button>
              <span class="soft-note">
                {{ paths[slot.key] || '未选择' }}
              </span>
            </div>
          </el-form-item>
        </div>
      </template>

      <!-- 输出目录 -->
      <template v-if="showOutputDir">
        <el-divider />
        <el-form-item label="输出目录（留空则弹下载）">
          <el-input
            :model-value="outputDir || ''"
            placeholder="点击右侧浏览选择输出目录"
            readonly
          >
            <template #append>
              <el-button @click="$emit('browse-output')">
                浏览
              </el-button>
            </template>
          </el-input>
        </el-form-item>
      </template>
    </el-form>

    <!-- 扩展区域：模板管理 -->
    <slot name="template-actions" />

    <!-- 扩展区域：页面特有内容（如 DataTransfer 文件勾选） -->
    <slot name="extra" />
  </el-card>
</template>

<script setup lang="ts">
export interface FileSourceMode {
  value: string
  label: string
}

export interface FileSlot {
  key: string
  label: string
}

export interface LockedFile {
  key: string
  label: string
  path: string
}

withDefaults(
  defineProps<{
    heading?: string
    modes?: FileSourceMode[]
    modelValue?: string
    pathLockValue?: string
    slots?: FileSlot[]
    paths?: Record<string, string>
    lockedFiles?: LockedFile[]
    pathLocked?: boolean
    locking?: boolean
    lockMessage?: string
    lockLabel?: string
    canLock?: boolean
    showOutputDir?: boolean
    outputDir?: string
  }>(),
  {
    heading: '选择文件',
    modes: () => [],
    modelValue: '',
    pathLockValue: 'path-lock',
    slots: () => [],
    paths: () => ({}),
    lockedFiles: () => [],
    pathLocked: false,
    locking: false,
    lockMessage: '',
    lockLabel: '锁定模板路径',
    canLock: false,
    showOutputDir: false,
    outputDir: '',
  },
)

defineEmits<{
  'update:modelValue': [value: string]
  browse: [key: string]
  lock: []
  'browse-output': []
}>()
</script>

<style scoped>
.file-source-panel {
  margin-bottom: 0;
}
</style>
