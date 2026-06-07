<template>
  <div class="not-found-page">
    <div class="not-found-content">
      <h1>404</h1>
      <p>页面不存在</p>
      <el-button type="primary" @click="$router.push('/')">返回首页</el-button>
    </div>
  </div>
</template>

<style scoped>
.not-found-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
}
.not-found-content {
  text-align: center;
}
.not-found-content h1 {
  font-size: 72px;
  font-weight: 700;
  color: var(--el-text-color-secondary);
  margin: 0;
}
.not-found-content p {
  font-size: 16px;
  color: var(--el-text-color-placeholder);
  margin: 12px 0 24px;
}
</style>
