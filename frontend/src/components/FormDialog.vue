<template>
  <el-dialog
    :model-value="visible"
    :title="title"
    :width="width"
    :close-on-click-modal="false"
    @update:model-value="$emit('update:visible', $event)"
  >
    <el-form
      ref="formRef"
      :model="localModel"
      :rules="rules"
      label-width="100px"
      @submit.prevent="handleSubmit"
    >
      <el-form-item
        v-for="field in fields"
        :key="field.key"
        :label="field.label"
        :prop="field.key"
        :required="field.required"
      >
        <!-- 文本 -->
        <el-input
          v-if="field.type === 'text' || !field.type"
          v-model="localModel[field.key]"
          :placeholder="field.placeholder"
          :disabled="field.disabled"
        />
        <!-- 数字 -->
        <el-input-number
          v-else-if="field.type === 'number'"
          v-model="localModel[field.key]"
          :min="field.min ?? 0"
          :precision="field.precision ?? 2"
          :placeholder="field.placeholder"
          :style="{ width: '100%' }"
        />
        <!-- 下拉 -->
        <el-select
          v-else-if="field.type === 'select'"
          v-model="localModel[field.key]"
          :placeholder="field.placeholder || '请选择'"
          :style="{ width: '100%' }"
        >
          <el-option
            v-for="opt in field.options"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
        <!-- 日期 -->
        <el-date-picker
          v-else-if="field.type === 'date'"
          v-model="localModel[field.key]"
          type="date"
          :placeholder="field.placeholder"
          value-format="YYYY-MM-DD"
          :style="{ width: '100%' }"
        />
        <!-- 文本域 -->
        <el-input
          v-else-if="field.type === 'textarea'"
          v-model="localModel[field.key]"
          type="textarea"
          :rows="field.rows || 3"
          :placeholder="field.placeholder"
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="$emit('update:visible', false)">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">
        {{ submitText }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'

export interface FormField {
  key: string
  label: string
  type?: 'text' | 'number' | 'select' | 'date' | 'textarea'
  required?: boolean
  placeholder?: string
  disabled?: boolean
  min?: number
  precision?: number
  rows?: number
  options?: { value: string | number; label: string }[]
}

const props = withDefaults(defineProps<{
  visible: boolean
  title: string
  fields: FormField[]
  initialData?: Record<string, any>
  submitting?: boolean
  submitText?: string
  width?: string
}>(), {
  submitting: false,
  submitText: '保存',
  width: '560px',
})

const emit = defineEmits<{
  'update:visible': [value: boolean]
  'submit': [data: Record<string, any>]
}>()

const localModel = reactive<Record<string, any>>({})

watch(() => props.visible, (val) => {
  if (val && props.initialData) {
    Object.assign(localModel, props.initialData)
  } else if (val) {
    Object.keys(localModel).forEach(k => delete localModel[k])
  }
}, { immediate: true })

const rules: FormRules = {}
props.fields.forEach(f => {
  if (f.required) {
    rules[f.key] = [{ required: true, message: `请输入${f.label}`, trigger: 'blur' }]
  }
})

function handleSubmit() {
  const formRef = (document.querySelector('.el-form') as any)?.__vueParentComponent
  emit('submit', { ...localModel })
}
</script>
