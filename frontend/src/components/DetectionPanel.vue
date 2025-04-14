<template>
  <div class="detection-container">
      <el-container>
        <!-- 左侧文件树 -->
        <el-aside width="280px" class="file-tree-container">
          <el-card class="file-tree-card">
            <template #header>
              <div class="card-header">
                <span class="section-title">文件列表</span>
                <input
                  type="file"
                  ref="folderInput"
                  @change="handleFolderSelect"
                  style="display: none"
                  webkitdirectory
                  directory>
                <el-button type="primary" class="upload-btn" @click="triggerFolderSelect">
                  <el-icon><folder-add /></el-icon>
                  选择文件夹
                </el-button>
              </div>
            </template>
            
            <div class="tree-wrapper">
              <el-tree
                ref="fileTree"
                :data="fileTreeData"
                :props="{ label: 'name' }"
                @node-click="handleFileSelect"
                node-key="path"
                :filter-node-method="filterNode"
                class="file-tree">
                <template #default="{ node, data }">
                  <div class="custom-tree-node">
                    <el-icon><document v-if="data.type === 'file'" /><folder v-else /></el-icon>
                    <el-tooltip 
                      :content="node.label" 
                      placement="right" 
                      :show-after="1000"
                      :hide-after="2000">
                      <span class="node-label">{{ node.label }}</span>
                    </el-tooltip>
                  </div>
                </template>
              </el-tree>
            </div>
          </el-card>
        </el-aside>

        <!-- 主要内容区域 -->
        <el-main class="main-content">
          <!-- 操作按钮区 -->
          <el-row class="action-bar" :gutter="24">
            <el-col :span="8">
              <el-button 
                type="primary" 
                @click="handleDetect()" 
                :loading="detecting" 
                :disabled="!currentFile" 
                class="action-btn material-btn material-btn-primary">
                <el-icon><video-play /></el-icon>
                开始检测
              </el-button>
            </el-col>
            <el-col :span="8">
              <el-button 
                type="success" 
                @click="downloadResults" 
                :disabled="!detectionResult" 
                class="action-btn material-btn material-btn-success">
                <el-icon><download /></el-icon>
                导出结果
              </el-button>
            </el-col>
            <el-col :span="8">
              <el-button 
                type="warning" 
                @click="clearResults" 
                class="action-btn material-btn material-btn-warning">
                <el-icon><delete /></el-icon>
                清除结果
              </el-button>
            </el-col>
          </el-row>

          <!-- 图片展示区域 -->
          <el-row :gutter="24" class="image-display-area">
            <!-- 原图 -->
            <el-col :span="12">
              <el-card class="image-card material-card">
                <template #header>
                  <div class="card-header">
                    <span class="section-title">原始图片</span>
                    <span v-if="currentFile" class="file-name">{{ currentFile.name }}</span>
                    <div class="image-navigation">
                      <el-button 
                        type="primary" 
                        @click="showPreviousImage"
                        :disabled="!hasPreviousImage"
                        class="nav-button material-btn">
                        <el-icon><arrow-left /></el-icon>
                        上一张
                      </el-button>
                      <el-button 
                        type="primary" 
                        @click="showNextImage"
                        :disabled="!hasNextImage"
                        class="nav-button material-btn">
                        <el-icon><arrow-right /></el-icon>
                        下一张
                      </el-button>
                    </div>
                  </div>
                </template>
                <div class="image-container">
                  <el-image 
                    v-if="originalImage"
                    :src="originalImage"
                    :preview-src-list="[originalImage]"
                    fit="contain"
                    :initial-index="0"
                    :zoom-rate="1.2"
                    :preview-teleported="true"
                    class="display-image image-display" />
                  <div v-else class="empty-image">
                    <el-icon><picture-icon /></el-icon>
                    <span>请选择图片</span>
                  </div>
                </div>
              </el-card>
            </el-col>

            <!-- 检测结果 -->
            <el-col :span="12">
              <el-card class="image-card material-card">
                <template #header>
                  <div class="card-header">
                    <span class="section-title">检测结果</span>
                  </div>
                </template>
                <div class="image-container">
                  <template v-if="detecting">
                    <div class="loading-container">
                      <div class="loading-animation">
                        <el-icon class="loading-icon"><loading /></el-icon>
                        <div class="loading-text">
                          <span>正在检测中</span>
                          <span class="dots">...</span>
                        </div>
                        <div class="progress-bar">
                          <div class="progress-inner"></div>
                        </div>
                      </div>
                    </div>
                  </template>
                  <template v-else>
                    <div class="detected-image-wrapper" ref="imageContainer">
                      <el-image 
                        v-if="detectedImage"
                        ref="detectedImageRef"
                        :src="detectedImage"
                        :preview-src-list="[detectedImage]"
                        fit="contain"
                        :initial-index="0"
                        :zoom-rate="1.2"
                        :preview-teleported="true"
                        class="display-image image-display" 
                        @load="handleImageLoad" />

                      <div v-if="detectedImage && selectedBbox" class="bbox-overlay">
                        <div class="bbox-highlight" 
                             :style="{
                               left: bboxLeft,
                               top: bboxTop,
                               width: bboxWidth,
                               height: bboxHeight,
                               borderColor: currentBboxColor
                             }"></div>
                      </div>
                      
                      <div v-else-if="!detectedImage" class="empty-image">
                        <el-icon><picture-filled /></el-icon>
                        <span>等待检测</span>
                      </div>
                    </div>
                  </template>
                </div>
              </el-card>
            </el-col>
          </el-row>

          <!-- 检测信息 -->
          <el-row v-if="detectionResult" class="detection-info-area">
            <el-col :span="24">
              <el-card class="info-card">
                <template #header>
                  <div class="card-header">
                    <span class="section-title">检测信息</span>
                    <div class="download-buttons">
                      <el-button type="primary" @click="exportAsJson" class="download-btn json-btn">
                        <el-icon><document /></el-icon>
                        导出JSON
                      </el-button>
                      <el-button type="success" @click="downloadImageResult" class="download-btn">
                        <el-icon><download /></el-icon>
                        导出图片
                      </el-button>
                    </div>
                  </div>
                </template>
                <el-descriptions :column="2" border class="info-descriptions">
                  <el-descriptions-item label="检测目标数量">
                    <span class="info-value">{{ detectionData?.length || 0 }}</span>
                  </el-descriptions-item>
                  <el-descriptions-item label="处理时间">
                    <span class="info-value">{{ processingTime }}ms</span>
                  </el-descriptions-item>
                </el-descriptions>

                <!-- 分类检测结果表格 -->
                <div class="categorized-results-section">
                  <h3>分类检测结果</h3>
                  <el-tabs type="border-card" class="detection-tabs" v-model="activeTabName">
                  <!-- 垂直运输机械 -->
                  <el-tab-pane v-if="getCategoryItems('垂直运输机械').length > 0" label="垂直运输机械" name="vertical_transport">
                    <div class="category-description">塔吊等垂直运输设备</div>
                    <el-table 
                      :data="getCategoryItems('垂直运输机械')" 
                      stripe 
                      style="width: 100%" 
                      :row-class-name="tableRowClassName"
                      :virtual-scrolling="virtualScrollEnabled"
                      :row-height="itemHeight"
                      @scroll="handleScroll">
                        <el-table-column prop="class" label="设备名称" />
                      <el-table-column prop="confidence" label="置信度" width="100">
                        <template #default="scope">
                          {{ (scope.row.confidence * 100).toFixed(2) }}%
                        </template>
                      </el-table-column>
                      <el-table-column label="位置" width="120">
                          <template #default="scope">
                          <el-button 
                            size="small" 
                            type="primary" 
                            @click="showBoundingBox(scope.row.bbox, '垂直运输机械')">
                            <el-icon><location /></el-icon>
                            查看位置
                          </el-button>
                          </template>
                        </el-table-column>
                    </el-table>
                  </el-tab-pane>
                  
                  <!-- 施工机械 -->
                  <el-tab-pane v-if="getCategoryItems('施工机械').length > 0" label="施工机械" name="machinery">
                    <div class="category-description">起重机、挖掘机、搅拌机等施工现场使用的机械设备</div>
                    <el-table 
                      :data="getCategoryItems('施工机械')" 
                      stripe 
                      style="width: 100%" 
                      :row-class-name="tableRowClassName"
                      :virtual-scrolling="virtualScrollEnabled"
                      :row-height="itemHeight"
                      @scroll="handleScroll">
                      <el-table-column prop="class" label="设备名称" />
                        <el-table-column label="位置" width="120">
                          <template #default="scope">
                          <el-button 
                            size="small" 
                            type="primary" 
                            @click="showBoundingBox(scope.row.bbox, '施工机械')">
                              <el-icon><location /></el-icon>
                              查看位置
                            </el-button>
                          </template>
                        </el-table-column>
                      </el-table>
                    </el-tab-pane>
                    
                    <!-- 临时设施-生活及办公区 -->
                    <el-tab-pane v-if="getCategoryItems('临时设施-生活及办公区').length > 0" label="生活及办公区" name="living">
                      <div class="category-description">宿舍、办公室、厕所等工地上的临时生活与办公设施</div>
                    <el-table 
                      :data="getCategoryItems('临时设施-生活及办公区')" 
                      stripe 
                      style="width: 100%" 
                      :row-class-name="tableRowClassName"
                      :virtual-scrolling="virtualScrollEnabled"
                      :row-height="itemHeight"
                      @scroll="handleScroll">
                        <el-table-column prop="class" label="设施名称" />
                        <el-table-column label="位置" width="120">
                          <template #default="scope">
                          <el-button 
                            size="small" 
                            type="primary" 
                            @click="showBoundingBox(scope.row.bbox, '临时设施-生活及办公区')">
                              <el-icon><location /></el-icon>
                              查看位置
                            </el-button>
                          </template>
                        </el-table-column>
                      </el-table>
                    </el-tab-pane>
                    
                    <!-- 临时设施-生产加工区 -->
                    <el-tab-pane v-if="getCategoryItems('临时设施-生产加工区').length > 0" label="生产加工区" name="production">
                      <div class="category-description">钢筋加工厂等材料加工场地</div>
                    <el-table 
                      :data="getCategoryItems('临时设施-生产加工区')" 
                      stripe 
                      style="width: 100%" 
                      :row-class-name="tableRowClassName"
                      :virtual-scrolling="virtualScrollEnabled"
                      :row-height="itemHeight"
                      @scroll="handleScroll">
                        <el-table-column prop="class" label="设施名称" />
                        <el-table-column label="位置" width="120">
                          <template #default="scope">
                          <el-button 
                            size="small" 
                            type="primary" 
                            @click="showBoundingBox(scope.row.bbox, '临时设施-生产加工区')">
                              <el-icon><location /></el-icon>
                              查看位置
                            </el-button>
                          </template>
                        </el-table-column>
                      </el-table>
                    </el-tab-pane>
                    
                    <!-- 临时设施-辅助设施 -->
                    <el-tab-pane v-if="getCategoryItems('临时设施-辅助设施').length > 0" label="辅助设施" name="auxiliary">
                      <div class="category-description">楼梯等临时通行和辅助设施</div>
                    <el-table 
                      :data="getCategoryItems('临时设施-辅助设施')" 
                      stripe 
                      style="width: 100%" 
                      :row-class-name="tableRowClassName"
                      :virtual-scrolling="virtualScrollEnabled"
                      :row-height="itemHeight"
                      @scroll="handleScroll">
                        <el-table-column prop="class" label="设施名称" />
                        <el-table-column label="位置" width="120">
                          <template #default="scope">
                          <el-button 
                            size="small" 
                            type="primary" 
                            @click="showBoundingBox(scope.row.bbox, '临时设施-辅助设施')">
                              <el-icon><location /></el-icon>
                              查看位置
                            </el-button>
                          </template>
                        </el-table-column>
                      </el-table>
                    </el-tab-pane>
                    
                    <!-- 基础设施 -->
                    <el-tab-pane v-if="getCategoryItems('基础设施').length > 0" label="基础设施" name="infrastructure">
                      <div class="category-description">大门、红线、道路等基础设施</div>
                    <el-table 
                      :data="getCategoryItems('基础设施')" 
                      stripe 
                      style="width: 100%" 
                      :row-class-name="tableRowClassName"
                      :virtual-scrolling="virtualScrollEnabled"
                      :row-height="itemHeight"
                      @scroll="handleScroll">
                        <el-table-column prop="class" label="设施名称" />
                        <el-table-column label="位置" width="120">
                          <template #default="scope">
                          <el-button 
                            size="small" 
                            type="primary" 
                            @click="showBoundingBox(scope.row.bbox, '基础设施')">
                              <el-icon><location /></el-icon>
                              查看位置
                            </el-button>
                          </template>
                        </el-table-column>
                      </el-table>
                    </el-tab-pane>
                    
                    <!-- 其他未归类物体 -->
                    <el-tab-pane v-if="getCategoryItems('其他').length > 0" label="其他物体" name="others">
                      <div class="category-description">其他未归类的检测物体</div>
                    <el-table 
                      :data="getCategoryItems('其他')" 
                      stripe 
                      style="width: 100%" 
                      :row-class-name="tableRowClassName"
                      :virtual-scrolling="virtualScrollEnabled"
                      :row-height="itemHeight"
                      @scroll="handleScroll">
                        <el-table-column prop="class" label="物体名称" />
                        <el-table-column label="位置" width="120">
                          <template #default="scope">
                          <el-button 
                            size="small" 
                            type="primary" 
                            @click="showBoundingBox(scope.row.bbox, '其他')">
                              <el-icon><location /></el-icon>
                              查看位置
                            </el-button>
                          </template>
                        </el-table-column>
                      </el-table>
                    </el-tab-pane>
                  </el-tabs>
                </div>
                
                <!-- 检测结果统计 -->
                <div v-if="detectionResult?.data?.class_counts" class="detection-summary-section">
                  <h3>检测结果统计</h3>
                  <el-row :gutter="10" class="summary-grid">
                    <el-col v-for="(category, categoryName) in detectionResult.data.class_counts" :key="categoryName" 
                           :xs="12" :sm="8" :md="6" :lg="4">
                      <el-card shadow="hover" class="summary-card">
                        <div class="summary-item">
                          <span class="summary-category">{{ categoryName }}</span>
                          <span class="summary-count">{{ category.count }}个</span>
                          <div class="summary-items">
                            {{ category.items.join('、') }}
                          </div>
                        </div>
                      </el-card>
                    </el-col>
                  </el-row>
                </div>

              <!-- 规则检查结果放在最下方 -->
              <div v-if="detectionResult?.data?.rules_check_results" class="rules-check-section">
                <h3>规则检查结果</h3>
                <rules-check-result :results="detectionResult.data.rules_check_results" />
                </div>
              </el-card>
            </el-col>
          </el-row>
        </el-main>
      </el-container>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watchEffect, onMounted, onUnmounted, nextTick } from 'vue'
import type { ElTree } from 'element-plus'
import type { AxiosError } from 'axios'
import { 
  FolderAdd, 
  Document, 
  Folder, 
  VideoPlay, 
  Download, 
  Delete, 
  Picture as PictureIcon, 
  PictureFilled, 
  Location, 
  Loading,
  ArrowLeft,
  ArrowRight,
  Search
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'
import LoadingStatus from './LoadingStatus.vue'
import RulesCheckResult from './RulesCheckResult.vue'
import { debounce } from 'lodash-es'
import type { UploadFile } from 'element-plus'

interface FileNode {
  name: string
  path: string
  type: 'file' | 'directory'
  children?: FileNode[]
  raw?: File
}

interface DetectionItem {
  class: string
  confidence: number
  bbox: number[]
  category?: string
}

interface CategoryDetections {
  [category: string]: DetectionItem[]
}

interface DetectionResultData {
  original_image?: string
  detected_image?: string
  detections?: DetectionItem[]
  categorized_detections?: CategoryDetections
  class_summary?: Array<{class: string, count: number}>
  rules_check_results?: any[]
  rules_json_path?: string
}

interface ApiError {
  response?: {
    status: number
    data: {
      error?: string
    }
  }
  request?: any
  message: string
}

interface DetectionResult {
  success: boolean
  data: {
    detections: Array<{
      class: string
      confidence: number
      bbox: number[]
      category: string
    }>
    detected_image: string
    rules_check_results: any[]
    [key: string]: any
  }
}

interface DetectionResponse {
  success: boolean
  data: DetectionResult['data']
  error?: string
}

// UI 相关的状态变量
const selectedBbox = ref<number[] | null>(null)
const imageContainer = ref<HTMLElement | null>(null)
const detectedImageRef = ref<any>(null)
const imageLoaded = ref(false)
const fileTree = ref<InstanceType<typeof ElTree> | null>(null)
const folderInput = ref<HTMLInputElement | null>(null)
const fileTreeData = ref<FileNode[]>([])
const imageFiles = ref<FileNode[]>([])
const currentImageIndex = ref(-1)
const isModelReady = ref(true)  // 修改为默认就绪状态

// 检测相关的状态变量
const currentFile = ref<UploadFile | null>(null)
const detecting = ref(false)
const processingTime = ref(0)
const detectionResult = ref<DetectionResult | null>(null)
const originalImage = ref<string>('')
const detectedImage = ref<string>('')
const detectionData = ref<DetectionResult['data']['detections']>([])
const rulesCheckResults = ref<any[]>([])

// 模型选择相关
const availableModels = ref<ModelInfo[]>([])
const selectedModel = ref<string | null>(null)

// 在ref声明部分添加activeTabName变量
const activeTabName = ref('machinery')

// 在ref声明部分添加变量
const currentBboxColor = ref('#FF4500') // 默认颜色

// 为不同类别定义边界框颜色
const categoryColors: Record<string, string> = {
  '施工机械': '#FF4500',          // 橙红色
  '临时设施-生活及办公区': '#4CAF50', // 绿色
  '临时设施-生产加工区': '#2196F3', // 蓝色
  '临时设施-辅助设施': '#9C27B0',  // 紫色
  '基础设施': '#FFC107',         // 琥珀色
  '其他': '#607D8B'             // 蓝灰色
}

// 在ref声明部分添加
// 移除定时查询相关变量
const MODEL_STATUS_CACHE_DURATION = 30000 // 30秒缓存

// 在ref声明部分添加
const virtualScrollEnabled = ref(true)
const itemHeight = ref(50)
const visibleItems = ref(10)
const scrollTop = ref(0)

// 添加计算属性
const totalHeight = computed(() => {
  if (!detectionResult.value?.data?.categorized_detections) return 0
  return Object.values(detectionResult.value.data.categorized_detections)
    .reduce((acc, items) => acc + items.length, 0) * itemHeight.value
})

const visibleRange = computed(() => {
  const start = Math.floor(scrollTop.value / itemHeight.value)
  const end = Math.min(start + visibleItems.value, Math.ceil(totalHeight.value / itemHeight.value))
  return { start, end }
})

// 添加滚动处理函数
const handleScroll = (event: Event) => {
  const target = event.target as HTMLElement
  scrollTop.value = target.scrollTop
}

// 优化图片加载
const loadImage = (src: string) => {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = reject
    img.src = src
  })
}

// 修改边界框位置更新函数
const updateBBoxPosition = debounce(() => {
  if (!selectedBbox.value || !imageContainer.value || !detectedImageRef.value) return
  
  const container = imageContainer.value
  const image = detectedImageRef.value.$el.querySelector('img')
  if (!image) return
  
  const containerRect = container.getBoundingClientRect()
  const imageRect = image.getBoundingClientRect()
  
  // 计算图片在容器中的实际显示尺寸和位置
  const scaleX = imageRect.width / 100 // 假设原始图片宽度为100
  const scaleY = imageRect.height / 100 // 假设原始图片高度为100
  
  // 计算边界框在图片中的相对位置
  const left = selectedBbox.value[0] * scaleX
  const top = selectedBbox.value[1] * scaleY
  const width = (selectedBbox.value[2] - selectedBbox.value[0]) * scaleX
  const height = (selectedBbox.value[3] - selectedBbox.value[1]) * scaleY
  
  // 更新边界框位置
  bboxLeft.value = `${left}px`
  bboxTop.value = `${top}px`
  bboxWidth.value = `${width}px`
  bboxHeight.value = `${height}px`
}, 100)

// 修改图片加载处理函数
const handleImageLoad = () => {
  imageLoaded.value = true
  if (selectedBbox.value) {
    nextTick(() => {
      updateBBoxPosition()
    })
  }
}

// 优化类别切换
const handleCategoryChange = (category: string) => {
  activeTabName.value = category
  // 重置滚动位置
  scrollTop.value = 0
}

// 优化检测结果处理
const processDetectionResult = debounce((result: any) => {
  if (!result?.data) return
  
  detectionResult.value = result
  // 触发虚拟滚动更新
  nextTick(() => {
    updateVirtualScroll()
  })
}, 100)

// 更新虚拟滚动
const updateVirtualScroll = () => {
  if (!virtualScrollEnabled.value) return
  
  const { start, end } = visibleRange.value
  // 更新可见数据
  // ... 实现虚拟滚动逻辑
}

// 优化组件卸载
onUnmounted(() => {
  window.removeEventListener('resize', updateBBoxPosition)
  if (modelStatusCheckInterval.value !== null) {
    clearInterval(modelStatusCheckInterval.value)
  }
  // 清理图片资源
  if (originalImage.value) {
    URL.revokeObjectURL(originalImage.value)
  }
  if (detectedImage.value) {
    URL.revokeObjectURL(detectedImage.value)
  }
})

// 添加计算属性
const hasPreviousImage = computed(() => currentImageIndex.value > 0)
const hasNextImage = computed(() => currentImageIndex.value < imageFiles.value.length - 1)

// 修改 showPreviousImage 和 showNextImage 函数
const showPreviousImage = () => {
  if (hasPreviousImage.value) {
    currentImageIndex.value--
    const file = imageFiles.value[currentImageIndex.value]
    if (file) {
      handleFileSelect(file)
    }
  }
}

const showNextImage = () => {
  if (hasNextImage.value) {
    currentImageIndex.value++
    const file = imageFiles.value[currentImageIndex.value]
    if (file) {
      handleFileSelect(file)
    }
  }
}

// 修改 handleFileSelect 函数
const handleFileSelect = async (data: FileNode) => {
  if (data.type === 'file' && data.raw) {
    // 创建一个新的 File 对象，添加 uid 属性
    const rawFile = new File([data.raw], data.raw.name, {
      type: data.raw.type,
      lastModified: data.raw.lastModified
    }) as any
    rawFile.uid = Date.now()

    // 创建符合 UploadFile 接口的对象
    const uploadFile: UploadFile = {
      name: data.name,
      raw: rawFile,
      uid: rawFile.uid,
      status: 'success'
    }
    currentFile.value = uploadFile
    currentImageIndex.value = imageFiles.value.findIndex(file => file.path === data.path)
    
    // 更新文件树选中状态
    if (fileTree.value) {
      fileTree.value.setCurrentKey(data.path)
    }
    
    try {
      clearResults()  // 清除之前的结果
      originalImage.value = URL.createObjectURL(data.raw)
      await handleDetect()
    } catch (error) {
      console.error('Failed to process image:', error)
      ElMessage.error('图片处理失败')
    }
  }
}

// 修改 handleFolderSelect 函数
const handleFolderSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (!target) return

  const files = Array.from(target.files || [])
  const imageFilesList = files.filter(file => isImageFile(file.name))
  
  if (imageFilesList.length === 0) {
    ElMessage.warning('未找到支持的图片文件')
    return
  }

  const tree = buildFileTree(imageFilesList)
  fileTreeData.value = tree
  imageFiles.value = getAllImageFiles(tree)
  currentImageIndex.value = -1
  currentFile.value = null
  
  // 清除文件树选中状态
  if (fileTree.value) {
    fileTree.value.setCurrentKey('')
  }
  
  ElMessage.success(`已找到 ${imageFilesList.length} 个图片文件`)
  
  target.value = ''
}

const downloadResults = () => {
  ElMessageBox.confirm(
    '请选择导出方式',
    '导出结果',
    {
      confirmButtonText: '导出图片',
      cancelButtonText: '导出JSON',
      distinguishCancelAndClose: true,
      type: 'info',
    }
  )
    .then(() => {
      downloadImageResult()
    })
    .catch(action => {
      if (action === 'cancel') {
        exportAsJson()
      }
    })
}

const showModelNotReadyWarning = () => {
  ElMessageBox.confirm(
    '模型正在加载中，您确定要尝试检测吗？如果模型尚未准备好，检测可能会失败。',
    '模型未就绪提示',
    {
      confirmButtonText: '继续检测',
      cancelButtonText: '等待模型就绪',
      type: 'warning',
    }
  ).then(() => {
    handleDetect()
  }).catch(() => {
    ElMessage.info('已取消检测，请等待模型就绪')
  })
}

const triggerFolderSelect = () => {
  if (folderInput.value) {
    folderInput.value.click()
  }
}

const filterNode = (value: string, data: FileNode) => {
  if (!value) return true
  return data.name.toLowerCase().includes(value.toLowerCase())
}

const exportAsJson = () => {
  if (!detectionResult.value) return
  
  const dataStr = JSON.stringify(detectionResult.value, null, 2)
  const blob = new Blob([dataStr], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `detection_result_${new Date().toISOString()}.json`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

const downloadImageResult = () => {
  if (!detectedImage.value) return
  
  const link = document.createElement('a')
  link.href = detectedImage.value
  link.download = `detection_result_${new Date().toISOString()}.png`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

const getCategoryItems = (category: string): DetectionItem[] => {
  if (!detectionResult.value?.data?.categorized_detections) return []
  const items = detectionResult.value.data.categorized_detections[category] as DetectionItem[] | undefined
  return items ? items.map(item => ({
    class: item.class,
    confidence: item.confidence,
    bbox: item.bbox,
    category: category
  })) : []
}

const tableRowClassName = ({ row }: { row: DetectionItem }) => {
  const category = Object.entries(detectionResult.value?.data?.categorized_detections || {})
    .find(([_, items]) => items.includes(row))?.[0]
  
  if (!category) return ''
  
  switch (category) {
    case '施工机械': return 'machinery-row'
    case '临时设施-生活及办公区': return 'living-row'
    case '临时设施-生产加工区': return 'production-row'
    case '临时设施-辅助设施': return 'auxiliary-row'
    case '基础设施': return 'infrastructure-row'
    case '其他': return 'others-row'
    default: return ''
  }
}

const showBoundingBox = (bbox: number[], category: string) => {
  selectedBbox.value = bbox
  currentBboxColor.value = categoryColors[category] || '#FF4500'
  
  if (imageLoaded.value) {
    updateBBoxPosition()
  }
}

// 添加辅助函数
const supportedImageTypes = ['.jpg', '.jpeg', '.png', '.bmp', '.webp']

const isImageFile = (filename: string): boolean => {
  return supportedImageTypes.some(ext => filename.toLowerCase().endsWith(ext))
}

const buildFileTree = (files: File[]): FileNode[] => {
  const tree: FileNode[] = []
  const map = new Map<string, FileNode>()

  files.forEach(file => {
    const path = file.webkitRelativePath || file.name
    const parts = path.split('/')
    let currentPath = ''
    let parentNode: FileNode | null = null

    parts.forEach((part, index) => {
      currentPath = index === 0 ? part : `${currentPath}/${part}`
      
      if (index === parts.length - 1) {
        // 文件节点
        const fileNode: FileNode = {
          name: part,
          path: currentPath,
          type: 'file',
          raw: file
        }
        map.set(currentPath, fileNode)
        
        if (parentNode) {
          if (!parentNode.children) {
            parentNode.children = []
          }
          parentNode.children.push(fileNode)
    } else {
          tree.push(fileNode)
        }
    } else {
        // 目录节点
        let dirNode = map.get(currentPath)
        if (!dirNode) {
          dirNode = {
            name: part,
            path: currentPath,
            type: 'directory',
            children: []
          }
          map.set(currentPath, dirNode)
          
          if (parentNode) {
            if (!parentNode.children) {
              parentNode.children = []
            }
            parentNode.children.push(dirNode)
  } else {
            tree.push(dirNode)
          }
        }
        parentNode = dirNode
      }
    })
  })

  return tree
}

const getAllImageFiles = (tree: FileNode[]): FileNode[] => {
  const files: FileNode[] = []
  const traverse = (nodes: FileNode[]) => {
    nodes.forEach(node => {
      if (node.type === 'file' && node.raw && isImageFile(node.name)) {
        files.push(node)
      } else if (node.children) {
        traverse(node.children)
      }
    })
  }
  traverse(tree)
  return files
}

// 修改模型状态检查
const checkModelStatus = async () => {
  try {
    const response = await axios.get<ApiResponse>('/api/detection/model/status')
    if (response.data.success && response.data.status) {
      isModelReady.value = response.data.status.loaded
    }
  } catch (error) {
    console.error('检查模型状态失败:', error)
    isModelReady.value = false
  }
}

// 定期检查模型状态
// 移除定时查询启动函数

// 组件挂载时启动模型状态检查
onMounted(() => {
  checkModelStatus()
})

// 添加模型状态相关变量
const loadingProgress = ref(0)
const loadingStatus = ref<'success' | 'exception' | 'warning'>('warning')

// 刷新模型状态
const refreshModelStatus = async () => {
  try {
    const response = await axios.get<ApiResponse>('/api/detection/model/status')
    if (response.data.success && response.data.status) {
      isModelReady.value = response.data.status.loaded
      availableModels.value = Object.values(response.data.status.available_models)
      if (response.data.status.current_model) {
        selectedModel.value = response.data.status.current_model
      }
    }
  } catch (error) {
    console.error('刷新模型状态失败:', error)
    ElMessage.error('刷新模型状态失败')
  }
}

// 添加handleDetect函数
const handleDetect = async () => {
  if (!currentFile.value) {
    ElMessage.warning('请先选择图片')
    return
  }

  try {
    detecting.value = true
    const startTime = Date.now()
    const formData = new FormData()
    formData.append('file', currentFile.value.raw)

    const response = await axios.post('/api/detection/detect', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })

    if (response.data.success) {
      const endTime = Date.now()
      processingTime.value = endTime - startTime
      detectionResult.value = response.data
      detectionData.value = response.data.data.detections
      detectedImage.value = `data:image/png;base64,${response.data.data.detected_image}`
      
      // 处理分类检测结果
      const categorizedDetections = {}
      response.data.data.detections.forEach(detection => {
        if (!categorizedDetections[detection.category]) {
          categorizedDetections[detection.category] = []
        }
        categorizedDetections[detection.category].push(detection)
      })
      detectionResult.value.data.categorized_detections = categorizedDetections
      
      // 发送规则检查请求
      try {
        const rulesResponse = await axios.post('/api/check-rules', {
          detections: response.data.data.detections
        })
        
        if (rulesResponse.data.success) {
          detectionResult.value.data.rules_check_results = rulesResponse.data.results
          ElMessage.success('检测和规则检查完成')
        } else {
          ElMessage.warning('检测完成，但规则检查失败: ' + (rulesResponse.data.error || '未知错误'))
        }
      } catch (rulesError) {
        console.error('规则检查失败:', rulesError)
        ElMessage.warning('检测完成，但规则检查失败')
      }
    } else {
      ElMessage.error(response.data.error || '检测失败')
    }
  } catch (error) {
    console.error('检测失败:', error)
    ElMessage.error('检测失败，请重试')
  } finally {
    detecting.value = false
  }
}

const loading = ref(false)

// 修改handleModelChange函数
const handleModelChange = async (modelName: string) => {
  try {
    loading.value = true
    const response = await axios.post('/api/detection/model/switch', {
      model_name: modelName
    })
    
    if (response.data.success) {
      ElMessage.success('切换模型成功')
      await fetchModelStatus() // 重新获取模型状态
    } else {
      ElMessage.error(response.data.error || '切换模型失败')
    }
  } catch (error) {
    console.error('切换模型失败:', error)
    ElMessage.error('切换模型失败，请重试')
  } finally {
    loading.value = false
  }
}

const clearResults = () => {
  detectedImage.value = null
  detectionResult.value = null
  loadingProgress.value = 0
  loadingStatus.value = 'warning'
  isModelReady.value = false
}

// 修改fetchModelStatus函数
const fetchModelStatus = async () => {
  try {
    const response = await axios.get('/api/detection/model/status')
    if (response.data.success && response.data.status) {
      const status = response.data.status
      currentModel.value = status.current_model
      isModelReady.value = status.loaded
      availableModels.value = Object.values(status.available_models || {})
      lastUpdateTime.value = new Date().toLocaleString()
    } else {
      ElMessage.error(response.data.error || '获取模型状态失败')
    }
  } catch (error) {
    console.error('获取模型状态失败:', error)
    ElMessage.error('获取模型状态失败，请重试')
  }
}
</script>

<style scoped>
/* 统一图片展示区域样式 */
.image-display-area {
  margin-top: 24px;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--el-text-color-secondary);
}

.loading-animation {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.loading-icon {
  font-size: 32px;
  animation: spin 2s linear infinite;
}

.loading-text {
  font-size: 16px;
  display: flex;
  align-items: center;
}

.dots {
  display: inline-block;
  animation: dots 1.5s infinite;
  width: 24px;
}

.progress-bar {
  width: 200px;
  height: 4px;
  background: var(--el-border-color-lighter);
  border-radius: 2px;
  overflow: hidden;
}

.progress-inner {
  width: 40%;
  height: 100%;
  background: var(--el-color-primary);
  border-radius: 2px;
  animation: progress 1.5s ease-in-out infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes dots {
  0%, 20% { content: '.'; }
  40% { content: '..'; }
  60% { content: '...'; }
  80%, 100% { content: ''; }
}

@keyframes progress {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(350%); }
}

.image-card {
  height: 600px; /* 统一卡片高度 */
  display: flex;
  flex-direction: column;
}

.image-container {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  position: relative;
  background-color: #f5f7fa;
  border-radius: 4px;
  height: 500px; /* 统一容器高度 */
  margin: 0;
  padding: 0;
}

.detected-image-wrapper {
  width: 100%;
  height: 100%;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.display-image {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  position: relative;
  z-index: 1;
}

.empty-image {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #909399;
  font-size: 14px;
  gap: 8px;
}

.empty-image .el-icon {
  font-size: 48px;
}

/* 确保图片容器在卡片中居中 */
.el-card__body {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 20px;
}

/* 统一卡片头部样式 */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 8px;
}

.section-title {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
}

.card-header .file-name {
  margin-left: 10px;
  color: #909399;
  font-size: 14px;
}

/* 统一图片导航按钮样式 */
.image-navigation {
  display: flex;
  gap: 8px;
}

.nav-button {
  padding: 8px 16px;
  display: flex;
  align-items: center;
  gap: 4px;
}

/* 模型状态悬浮窗样式 */
.model-status-float {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 1000;
}

.model-status-card {
  width: 300px;
  background-color: rgba(255, 255, 255, 0.95);
  border-radius: 8px;
}

.model-status-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-item .label {
  min-width: 80px;
  color: #606266;
}

.model-info {
  color: #909399;
  font-size: 12px;
  margin-left: 8px;
}

.loading-progress {
  margin-top: 8px;
}

/* 确保悬浮窗不会影响其他内容 */
.detection-container {
  position: relative;
  min-height: 100vh;
}
</style>