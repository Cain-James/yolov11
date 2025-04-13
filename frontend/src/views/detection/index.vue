<template>
  <div class="detection-container">
    <!-- 左侧文件列表 -->
    <div class="file-list">
      <el-upload
        class="upload-area"
        action="#"
        :auto-upload="false"
        :on-change="handleFileChange"
        :show-file-list="true"
      >
        <template #trigger>
          <el-button type="primary">选择文件</el-button>
        </template>
      </el-upload>
      <div class="file-tree-container">
        <el-scrollbar>
          <el-tree
            :data="fileList"
            :props="{ label: 'name' }"
            @node-click="handleFileSelect"
          />
        </el-scrollbar>
      </div>
    </div>

    <!-- 右侧内容区 -->
    <div class="content-area">
      <!-- 顶部操作栏 -->
      <div class="action-bar">
        <el-button-group>
          <el-button type="primary" @click="handleDetect" :loading="detecting">
            检测
          </el-button>
          <el-button type="success" @click="handleAnalyze" :loading="analyzing">
            分析
          </el-button>
          <el-button @click="handlePrev" :disabled="!hasPrev">上一张</el-button>
          <el-button @click="handleNext" :disabled="!hasNext">下一张</el-button>
        </el-button-group>
      </div>

      <!-- 图片显示区域 -->
      <div class="image-container" v-loading="loading">
        <div class="image-wrapper" v-if="currentImage">
          <el-image :src="currentImage" fit="contain" />
        </div>
        <div class="result-wrapper" v-if="detectionResult">
          <el-image :src="detectionResult" fit="contain" />
        </div>
      </div>

      <!-- 检测结果统计 -->
      <div class="result-stats" v-if="classSummary.length">
        <h3>检测结果统计：</h3>
        <el-table :data="classSummary" stripe>
          <el-table-column prop="class" label="类别" />
          <el-table-column prop="count" label="数量" />
        </el-table>
      </div>

      <!-- 分析结果 -->
      <div class="analysis-result" v-if="analysisResult">
        <h3>分析结果：</h3>
        <el-card class="analysis-card">
          {{ analysisResult }}
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { detectImage, analyzeImage } from '@/api/detetion'

// 状态
const fileList = ref<any[]>([])
const currentFileIndex = ref(-1)
const currentImage = ref('')
const detectionResult = ref('')
const classSummary = ref<any[]>([])
const analysisResult = ref('')
const loading = ref(false)
const detecting = ref(false)
const analyzing = ref(false)

// 计算属性
const hasPrev = computed(() => currentFileIndex.value > 0)
const hasNext = computed(() => currentFileIndex.value < fileList.value.length - 1)

// 文件处理
const handleFileChange = (file: any) => {
  if (!file.raw.type.startsWith('image/')) {
    ElMessage.error('请选择图片文件')
    return
  }
  
  const reader = new FileReader()
  reader.onload = (e) => {
    currentImage.value = e.target?.result as string
    fileList.value.push({
      name: file.name,
      file: file.raw,
      preview: currentImage.value
    })
    currentFileIndex.value = fileList.value.length - 1
  }
  reader.readAsDataURL(file.raw)
}

const handleFileSelect = (data: any) => {
  const index = fileList.value.findIndex(f => f.name === data.name)
  if (index !== -1) {
    currentFileIndex.value = index
    currentImage.value = fileList.value[index].preview
    detectionResult.value = ''
    classSummary.value = []
    analysisResult.value = ''
  }
}

// 导航控制
const handlePrev = () => {
  if (hasPrev.value) {
    currentFileIndex.value--
    const file = fileList.value[currentFileIndex.value]
    currentImage.value = file.preview
    detectionResult.value = ''
    classSummary.value = []
    analysisResult.value = ''
  }
}

const handleNext = () => {
  if (hasNext.value) {
    currentFileIndex.value++
    const file = fileList.value[currentFileIndex.value]
    currentImage.value = file.preview
    detectionResult.value = ''
    classSummary.value = []
    analysisResult.value = ''
  }
}

// 检测和分析
const handleDetect = async () => {
  if (currentFileIndex.value === -1) {
    ElMessage.warning('请先选择图片')
    return
  }

  const file = fileList.value[currentFileIndex.value]
  const formData = new FormData()
  formData.append('file', file.file)

  try {
    detecting.value = true
    const response = await detectImage(formData)
    if (response.success) {
      detectionResult.value = `data:image/png;base64,${response.data.detected_image}`
      classSummary.value = response.data.class_summary
    } else {
      ElMessage.error(response.error || '检测失败')
    }
  } catch (error: any) {
    ElMessage.error(error.message || '检测失败')
  } finally {
    detecting.value = false
  }
}

const handleAnalyze = async () => {
  if (currentFileIndex.value === -1) {
    ElMessage.warning('请先选择图片')
    return
  }

  const file = fileList.value[currentFileIndex.value]
  const formData = new FormData()
  formData.append('file', file.file)

  try {
    analyzing.value = true
    const response = await analyzeImage(formData)
    if (response.success) {
      analysisResult.value = response.analysis
    } else {
      ElMessage.error(response.error || '分析失败')
    }
  } catch (error: any) {
    ElMessage.error(error.message || '分析失败')
  } finally {
    analyzing.value = false
  }
}
</script>

<style scoped>
.detection-container {
  display: flex;
  width: 100%;
  height: 100%;
  background-color: #f5f7fa;
}

.file-list {
  width: 300px;
  height: 100%;
  padding: 20px;
  background-color: #fff;
  border-right: 1px solid #dcdfe6;
  display: flex;
  flex-direction: column;
}

.upload-area {
  margin-bottom: 20px;
}

.file-tree-container {
  flex: 1;
  overflow: hidden;
}

.content-area {
  flex: 1;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  overflow: auto;
}

.action-bar {
  padding: 10px 0;
  border-bottom: 1px solid #dcdfe6;
}

.image-container {
  display: flex;
  gap: 20px;
  flex: 1;
  min-height: 400px;
}

.image-wrapper,
.result-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #fff;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  overflow: hidden;
}

.result-stats {
  background-color: #fff;
  padding: 20px;
  border-radius: 4px;
}

.analysis-result {
  background-color: #fff;
  padding: 20px;
  border-radius: 4px;
}

.analysis-card {
  margin-top: 10px;
}
</style> 