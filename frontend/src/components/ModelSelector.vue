<template>
  <div class="model-selector" :class="{ 'minimized': true }">
    <div class="toggle-button" @click="toggleMinimize">
      <el-icon><component :is="isMinimized ? 'Expand' : 'Fold'" /></el-icon>
      <span v-if="isMinimized">模型状态</span>
    </div>
    
    <el-card v-show="!isMinimized" class="box-card" size="small">
      <template #header>
        <div class="card-header">
          <span class="header-title">模型选择</span>
          <el-tag size="small" :type="modelLoaded ? 'success' : 'warning'" class="status-tag">
            {{ modelLoaded ? '已加载' : '加载中' }}
          </el-tag>
        </div>
      </template>
      
      <div class="model-list">
        <el-select v-model="selectedModel" placeholder="请选择模型" @change="handleModelChange">
          <el-option
            v-for="model in availableModels"
            :key="model.path"
            :label="model.name"
            :value="model.path"
          >
            <div class="model-option">
              <span>{{ model.name }}</span>
              <span class="model-size">{{ model.size }}</span>
            </div>
          </el-option>
        </el-select>
      </div>

      <div class="model-info" v-if="currentModel">
        <el-descriptions :column="1" size="small" border>
          <el-descriptions-item label="当前模型">
            {{ currentModel }}
          </el-descriptions-item>
          <el-descriptions-item label="修改时间">
            {{ selectedModelInfo?.last_modified || '未知' }}
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import { Expand, Fold } from '@element-plus/icons-vue'

interface ModelInfo {
  name: string
  path: string
  size: string
  last_modified: string
}

const modelLoaded = ref(false)
const currentModel = ref<string>('')
const selectedModel = ref<string>('')
const availableModels = ref<ModelInfo[]>([])
const selectedModelInfo = ref<ModelInfo | null>(null)
const isMinimized = ref(true)

// 切换最小化/展开状态
const toggleMinimize = () => {
  isMinimized.value = !isMinimized.value
}

// 获取模型列表
const fetchModelStatus = async () => {
  try {
    const response = await axios.get('/api/detection/model/status')
    if (response.data.success) {
      const models = Object.values(response.data.status.available_models)
      availableModels.value = models as ModelInfo[]
      currentModel.value = response.data.status.current_model || ''
      modelLoaded.value = response.data.status.loaded || false
      
      if (currentModel.value && !selectedModel.value) {
        selectedModel.value = currentModel.value
        selectedModelInfo.value = availableModels.value.find(m => m.path === currentModel.value) || null
      }
    }
  } catch (error) {
    console.error('获取模型状态失败:', error)
    ElMessage.error('获取模型状态失败')
  }
}

// 处理模型切换
const handleModelChange = async (value: string) => {
  try {
    selectedModel.value = value
    selectedModelInfo.value = availableModels.value.find(m => m.path === value) || null
    
    // 发送切换模型请求到后端
    const response = await axios.post('/api/detection/model/switch', {
      model_name: selectedModelInfo.value?.name || value
    })
    
    if (response.data.success) {
      currentModel.value = value
      ElMessage.success(`已切换到模型：${selectedModelInfo.value?.name || value}`)
    } else {
      ElMessage.error(response.data.error || '切换模型失败')
    }
  } catch (error) {
    console.error('切换模型失败:', error)
    ElMessage.error('切换模型失败')
  }
}

// 初始化
onMounted(async () => {
  await fetchModelStatus()
})
</script>

<style scoped>
.model-selector {
  position: fixed;
  bottom: 20px;
  right: 20px;
  width: 300px;
  z-index: 1000;
  transition: all 0.3s ease;
}

.model-selector.minimized {
  width: auto;
}

.toggle-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background-color: #fff;
  border-radius: 4px;
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.toggle-button:hover {
  background-color: #f5f7fa;
}

.box-card {
  margin-top: 8px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title {
  font-weight: bold;
}

.status-tag {
  margin-left: 8px;
}

.model-list {
  margin: 10px 0;
}

.model-list .el-select {
  width: 100%;
}

.model-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.model-size {
  color: #909399;
  font-size: 12px;
}

.model-info {
  margin-top: 10px;
}
</style> 