<template>
  <el-config-provider>
    <!-- 全局 loading 条 -->
    <div class="global-loading-bar" :class="{ 'is-loading': routeLoading.isLoading.value }" />
    <!-- DirBrowserV2 单例：全局唯一 DOM 实例，由 provide 暴露给所有页面 -->
    <DirBrowserV2 ref="dirBrowserRef" />
    <Layout />
  </el-config-provider>
</template>

<script setup lang="ts">
import { onMounted, provide, ref } from 'vue'
import Layout from './layout/Layout.vue'
import DirBrowserV2 from './components/DirBrowserV2.vue'
import { DIR_BROWSER_KEY } from './features/shared/dirBrowser'
import { useRouteLoadingBar } from './composables/useLoadingBar'
import { preloadAllRouteChunks } from './composables/useChunkPreload'

const dirBrowserRef = ref()
const routeLoading = useRouteLoadingBar()

provide(DIR_BROWSER_KEY, dirBrowserRef)

// 首屏渲染完成后，后台预下载所有页面 chunk
onMounted(() => {
  preloadAllRouteChunks()
})
</script>

<style>
/* 全局顶部 loading 条 — 纯 CSS 动画，零依赖 */
.global-loading-bar {
  position: fixed;
  top: 0;
  left: 0;
  height: 3px;
  width: 0%;
  background: linear-gradient(90deg, #409EFF, #67C23A, #409EFF);
  background-size: 200% 100%;
  z-index: 9999;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.15s ease, width 0.3s ease;
  animation: none;
}

.global-loading-bar.is-loading {
  opacity: 1;
  width: 70%;
  animation: loadingBarShimmer 1.2s ease-in-out infinite;
}

@keyframes loadingBarShimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}
</style>
