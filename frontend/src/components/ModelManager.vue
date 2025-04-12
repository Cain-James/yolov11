<template>
  <div class="model-manager">
    <el-card class="model-card">
      <template #header>
        <div class="card-header">
          <span class="section-title">模型管理</span>
          <el-button type="primary" @click="refreshModelStatus">
            <el-icon><refresh /></el-icon>
            刷新状态
          </el-button>
        </div>
      </template>

      <!-- 模型状态信息 -->
      <el-descriptions :column="2" border>
        <el-descriptions-item label="当前模型">
          <el-tag :type="currentModel ? 'success' : 'warning'">
            {{ currentModel?.name || '未加载模型' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="模型状态">
          <el-tag :type="isModelLoaded ? 'success' : 'warning'">
            {{ isModelLoaded ? '已加载' : '未加载' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="可用模型数量">
          <el-tag>{{ availableModels.length }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="最后更新时间">
          <el-tag>{{ lastUpdateTime }}</el-tag>
        </el-descriptions-item>
      </el-descriptions>

      <!-- 模型列表 -->
      <div class="model-list">
        <h3>可用模型列表</h3>
        <el-table :data="availableModels" style="width: 100%" stripe>
          <el-table-column prop="name" label="模型名称" />
          <el-table-column prop="size" label="大小" width="120" />
          <el-table-column prop="last_modified" label="最后修改时间" width="180" />
          <el-table-column label="操作" width="150">
            <template #default="scope">
              <el-button
                type="primary"
                size="small"
                :disabled="scope.row.path === currentModel?.path"
                @click="switchModel(scope.row.path)"
              >
                {{ scope.row.path === currentModel?.path ? '当前模型' : '切换模型' }}
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 模型加载状态 -->
      <div class="model-status">
        <h3>模型加载状态</h3>
        <el-steps :active="modelLoadStep" finish-status="success">
          <el-step title="检查模型" />
          <el-step title="加载模型" />
          <el-step title="初始化" />
        </el-steps>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import axios from 'axios'

interface ModelInfo {
  path: string
  name: string
  size: string
  last_modified: string
}

interface ModelStatus {
  available_models: Record<string, ModelInfo>
  current_model: string | null
  model_loaded: boolean
  total_models: number
}

interface ApiResponse {
  success: boolean
  status?: ModelStatus
  message?: string
  error?: string
}

// 状态变量
const availableModels = ref<ModelInfo[]>([])
const currentModel = ref<ModelInfo | null>(null)
const isModelLoaded = ref(false)
const lastUpdateTime = ref('')
const modelLoadStep = ref(0)

// 获取模型状态
const fetchModelStatus = async () => {
  try {
    const response = await axios.get<ApiResponse>('/api/detection/model/status')
    const data = response.data
    
    if (data.success && data.status) {
      availableModels.value = Object.values(data.status.available_models)
      if (data.status.current_model) {
        currentModel.value = availableModels.value.find(
          model => model.path === data.status?.current_model
        ) || null
      }
      isModelLoaded.value = data.status.model_loaded
      lastUpdateTime.value = new Date().toLocaleString()
    } else {
      ElMessage.error('获取模型状态失败：' + (data.message || data.error))
    }
  } catch (error) {
    console.error('获取模型状态出错：', error)
    ElMessage.error('获取模型状态出错')
  }
}

// 切换模型
const switchModel = async (modelPath: string) => {
  try {
    const modelName = modelPath.split('/').pop() || ''
    const response = await axios.post<ApiResponse>('/api/detection/model/switch', {
      model_name: modelName
    })
    
    if (response.data.success) {
      ElMessage.success(response.data.message || '切换模型成功')
      await fetchModelStatus()
    } else {
      ElMessage.error(response.data.error || '切换模型失败')
    }
  } catch (error) {
    console.error('切换模型失败:', error)
    ElMessage.error('切换模型失败')
  }
}

// 刷新模型状态
const refreshModelStatus = async () => {
  modelLoadStep.value = 0
  await fetchModelStatus()
  modelLoadStep.value = isModelLoaded.value ? 2 : 1
}

// 组件挂载时获取模型状态
onMounted(() => {
  fetchModelStatus()
})
</script>

<style scoped>
.model-manager {
  padding: 20px;
}

.model-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-title {
  font-size: 18px;
  font-weight: 500;
}

.model-list {
  margin-top: 20px;
}

.model-status {
  margin-top: 20px;
}

h3 {
  margin: 16px 0;
  font-size: 16px;
  font-weight: 500;
  color: #303133;
}

:deep(.el-descriptions) {
  margin: 20px 0;
}

:deep(.el-table) {
  margin-top: 16px;
}

:deep(.el-steps) {
  margin-top: 16px;
}
</style> 