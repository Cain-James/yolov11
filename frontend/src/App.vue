<template>
  <div class="app-container">
    <el-container>
      <el-header>
        <h1 class="main-title">建筑图纸识别</h1>
      </el-header>
      <el-main>
        <detection-panel />
      </el-main>
      <el-footer>
        <p>© 2025 建筑图纸识别系统</p>
      </el-footer>
    </el-container>
  </div>
</template>

<script>
import { defineComponent } from 'vue'
import DetectionPanel from './components/DetectionPanel.vue'

export default defineComponent({
  name: 'App',
  components: {
    DetectionPanel
  }
})
</script>

<style>
.app-container {
  min-height: 100vh;
  background: #f5f7fa;
}

.el-header {
  background: linear-gradient(135deg, #409EFF 0%, #2c3e50 100%);
  color: white;
  text-align: center;
  line-height: 60px;
  padding: 0;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.1);
}

.main-title {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  letter-spacing: 1px;
}

.el-main {
  padding: 20px;
}

.el-footer {
  text-align: center;
  color: #909399;
  padding: 20px;
  background: #ffffff;
  box-shadow: 0 -2px 12px 0 rgba(0,0,0,0.05);
}
</style>