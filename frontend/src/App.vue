<template>
  <el-config-provider>
    <!-- DirBrowserV2 单例：全局唯一 DOM 实例，由 provide 暴露给所有页面 -->
    <DirBrowserV2 ref="dirBrowserRef" />
    <Layout />
  </el-config-provider>
</template>

<script setup lang="ts">
import { provide, ref } from 'vue'
import Layout from './layout/Layout.vue'
import DirBrowserV2 from './components/DirBrowserV2.vue'
import { DIR_BROWSER_KEY } from './features/shared/dirBrowser'

const dirBrowserRef = ref()

provide(DIR_BROWSER_KEY, dirBrowserRef)
</script>
