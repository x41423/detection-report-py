---
title: 文件预览统一组件
created: 2026-06-08
updated: 2026-06-08
type: concept
tags: [frontend, vue3, convention]
sources: []
---

# 文件预览统一组件（FilePreviewDialog）

## 设计原则

**一次开发，全局复用。** 任何需要查看文件的业务功能直接调用 `FilePreviewDialog`，禁止各模块重复造轮子。

## 组件路径

```
frontend/src/components/FilePreviewDialog.vue
```

## 依赖

| 包 | 版本 | 用途 |
|----|------|------|
| `@vue-office/docx` | 1.6.3 | Word `.docx` 预览（基于 mammoth.js） |
| `@vue-office/excel` | 1.7.14 | Excel `.xlsx` 预览（基于 SheetJS） |
| `@vue-office/pdf` | 2.0.10 | PDF 预览（基于 pdf.js） |
| `v-viewer` | 3.0.23 | 图片查看器（已安装，待全局注册） |

## 支持格式

| 格式 | 引擎 | 备注 |
|------|------|------|
| `.jpg .png .gif .webp .svg .bmp` | `<img>` | 零依赖 |
| `.pdf` | `@vue-office/pdf` | 内嵌浏览、缩放 |
| `.docx .doc` | `@vue-office/docx` | 转 HTML 渲染 |
| `.xlsx .xls` | `@vue-office/excel` | 前端解析转表格 |
| `.csv` | 内置解析器 | fetch → 自动检测表头 → `el-table` |
| `.txt .log .md .json` | `<pre>` | 暗色代码风格，等宽字体 |
| 其他 | 下载 | 提示下载 |

## 使用方式

```vue
<script setup>
import FilePreviewDialog from '@/components/FilePreviewDialog.vue'

const previewVisible = ref(false)
const previewSrc = ref('')
const previewFileName = ref('')

function openPreview(url: string, name: string) {
  previewSrc.value = url
  previewFileName.value = name
  previewVisible.value = true
}
</script>

<template>
  <FilePreviewDialog
    v-model:visible="previewVisible"
    :src="previewSrc"
    :file-name="previewFileName"
  />
</template>
```

## Props

| Prop | 类型 | 必填 | 说明 |
|------|------|------|------|
| `visible` | boolean | 是 | 控制弹窗显隐 |
| `src` | string | 是 | 文件 URL（支持 HTTP/BLOB） |
| `fileName` | string | 否 | 文件名，用于标题和类型推断 |
| `viewerType` | string | 否 | 强制指定预览器类型，不传则根据后缀自动推断 |

## 首个集成点

[[entities/inspection-report]] 检测报告管理 — 详情弹窗 + 表格行均接入。

## 扩展指南

未来任何模块需要文件预览时：

1. 导入 `FilePreviewDialog`
2. 加 `previewVisible`/`previewSrc`/`previewFileName` 三个 ref
3. 模板中加 `<FilePreviewDialog>` 标签
4. 三行代码完成

**禁止各模块自行实现文件预览。**
