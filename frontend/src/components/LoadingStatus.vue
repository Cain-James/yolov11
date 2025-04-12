<template>
  <div class="loading-status">
    <el-icon class="loading-icon"><Loading /></el-icon>
    <span class="loading-text">正在加载模型...</span>
  </div>
</template>

<script setup lang="ts">
import { Loading } from '@element-plus/icons-vue'
</script>

<style scoped>
.loading-status {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 20px;
}

.loading-icon {
  font-size: 48px;
  color: var(--el-color-primary);
  animation: rotate 2s linear infinite;
}

.loading-text {
  margin-top: 16px;
  font-size: 16px;
  color: var(--el-text-color-secondary);
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style> 