<template>
  <div class="rules-check-container">
    <el-card class="rules-card">
      <template #header>
        <div class="card-header">
          <span class="section-title">施工规范检查结果</span>
          <el-button type="primary" class="export-btn" @click="exportResults">
            <el-icon><download /></el-icon>
            导出规则检查结果
          </el-button>
        </div>
      </template>
      
      <div v-if="!results || results.length === 0" class="empty-result">
        <el-icon><document-checked /></el-icon>
        <span>暂无规则检查结果</span>
      </div>
      
      <div v-else class="result-content">
        <el-alert
          title="规范检查总结"
          :type="alertType"
          :description="alertDescription"
          :closable="false"
          show-icon
          class="summary-alert"
        />
        
        <el-table :data="results" style="width: 100%" :row-class-name="tableRowClassName">
          <el-table-column prop="rule_id" label="规则编号" width="100">
            <template #default="scope">
              {{ formatRuleId(scope.row.rule_id) }}
            </template>
          </el-table-column>
          <el-table-column prop="category" label="类别" width="100" />
          <el-table-column label="规则描述" min-width="300">
            <template #default="scope">
              <div class="rule-description">
                {{ getFullRuleDescription(scope.row) }}
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="severity" label="重要程度" width="100">
            <template #default="scope">
              <el-tag :type="getSeverityType(scope.row.severity)">
                {{ scope.row.severity }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100">
            <template #default="scope">
              <el-tag :type="getStatusType(scope.row.status)">
                {{ scope.row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="message" label="结果说明" min-width="200" />
          <el-table-column label="扣分" width="100">
            <template #default="scope">
              <span :class="{ 'deduction-text': calculateDeduction(scope.row.severity, scope.row.status) > 0 }">
                {{ calculateDeduction(scope.row.severity, scope.row.status) }}
              </span>
            </template>
          </el-table-column>
        </el-table>
        
        <div class="total-score">
          <span class="total-label">总分：</span>
          <span class="total-value">{{ totalScore }}</span>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Document, DocumentChecked, Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  results: {
    type: Array,
    default: () => []
  }
})

// 计算总分
const totalScore = computed(() => {
  if (!props.results || props.results.length === 0) {
    return 100
  }
  
  const totalDeduction = props.results.reduce((sum, result) => {
    return sum + calculateDeduction(result.severity, result.status)
  }, 0)
  
  return Math.max(0, 100 - totalDeduction)
})

// 统计规则检查结果
const complianceStats = computed(() => {
  if (!props.results || props.results.length === 0) {
    return { compliant: 0, nonCompliant: 0, undetectable: 0, failed: 0, total: 0 }
  }
  
  const stats = {
    compliant: 0,
    nonCompliant: 0,
    undetectable: 0,
    failed: 0,
    total: props.results.length
  }
  
  props.results.forEach(result => {
    if (result.status === '合规') {
      stats.compliant++
    } else if (result.status === '不合规') {
      stats.nonCompliant++
    } else if (result.status === '无法检测') {
      stats.undetectable++
    } else {
      stats.failed++
    }
  })
  
  return stats
})

// 根据检查结果设置提示类型
const alertType = computed(() => {
  if (complianceStats.value.nonCompliant > 0) {
    return 'warning'
  } else if (complianceStats.value.compliant > 0 && complianceStats.value.nonCompliant === 0) {
    return 'success'
  } else {
    return 'info'
  }
})

// 生成提示描述
const alertDescription = computed(() => {
  const { compliant, nonCompliant, undetectable, failed, total } = complianceStats.value
  
  if (total === 0) {
    return '暂无规则检查结果'
  }
  
  return `总共检查了 ${total} 条规则，其中 ${compliant} 条合规，${nonCompliant} 条不合规，${undetectable} 条无法自动检测，${failed} 条检查失败。`
})

// 根据状态获取行样式
const tableRowClassName = ({ row }) => {
  if (row.status === '不合规') {
    return 'warning-row'
  } else if (row.status === '合规') {
    return 'success-row'
  }
  return ''
}

// 根据严重程度获取标签类型
const getSeverityType = (severity) => {
  switch (severity) {
    case '严重':
      return 'danger'
    case '重要':
      return 'warning'
    case '一般':
      return 'info'
    default:
      return ''
  }
}

// 根据状态获取标签类型
const getStatusType = (status) => {
  switch (status) {
    case '合规':
      return 'success'
    case '不合规':
      return 'danger'
    case '无法检测':
      return 'info'
    case '检查失败':
      return 'warning'
    default:
      return ''
  }
}

// 格式化规则编号
const formatRuleId = (ruleId) => {
  if (!ruleId) return ''
  
  // 将规则编号转换为标准格式
  // 例如：1.5.1.1 -> 1.5.1.1
  // 例如：1.5.1 -> 1.5.1
  return ruleId.toString()
}

// 获取完整的规则描述
const getFullRuleDescription = (rule) => {
  if (!rule) return ''
  
  // 构建完整的规则描述
  let description = ''
  
  // 添加主规则编号和描述
  if (rule.rule_id) {
    description += `${formatRuleId(rule.rule_id)} `
  }
  
  // 添加规则描述
  if (rule.description) {
    description += rule.description
  }
  
  // 添加子规则（如果有）
  if (rule.sub_rules && rule.sub_rules.length > 0) {
    rule.sub_rules.forEach((subRule, index) => {
      description += `\n${formatRuleId(subRule.rule_id)} ${subRule.description}`
    })
  }
  
  return description
}

// 根据严重程度和状态计算扣分
const calculateDeduction = (severity, status) => {
  if (status !== '不合规') {
    return 0
  }
  
  switch (severity) {
    case '严重':
      return 10
    case '重要':
      return 5
    case '一般':
      return 2
    default:
      return 0
  }
}

// 导出结果
const exportResults = () => {
  if (!props.results || props.results.length === 0) {
    ElMessage.warning('暂无规则检查结果可导出')
    return
  }
  
  try {
    // 准备CSV内容
    const headers = ['规则编号', '类别', '规则描述', '重要程度', '状态', '扣分', '结果说明']
    let csvContent = headers.join(',') + '\n'
    
    props.results.forEach(result => {
      const deduction = calculateDeduction(result.severity, result.status)
      const row = [
        formatRuleId(result.rule_id),
        result.category,
        `"${getFullRuleDescription(result).replace(/"/g, '""')}"`,
        result.severity,
        result.status,
        deduction,
        `"${result.message.replace(/"/g, '""')}"`
      ]
      csvContent += row.join(',') + '\n'
    })
    
    // 添加总分行
    const totalDeduction = props.results.reduce((sum, result) => {
      return sum + calculateDeduction(result.severity, result.status)
    }, 0)
    const totalScore = Math.max(0, 100 - totalDeduction)
    csvContent += `总分,${totalScore}\n`
    
    // 创建Blob并下载
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    
    link.setAttribute('href', url)
    link.setAttribute('download', `规范检查结果_${new Date().toISOString().slice(0, 10)}.csv`)
    link.style.visibility = 'hidden'
    
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    
    ElMessage.success('规则检查结果导出成功')
  } catch (error) {
    console.error('导出结果失败:', error)
    ElMessage.error('导出失败，请重试')
  }
}
</script>

<style scoped>
.rules-check-container {
  margin-top: 24px;
}

.rules-card {
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  border-radius: 8px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-title {
  font-size: 18px;
  font-weight: 500;
  color: #303133;
}

.empty-result {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 0;
  color: #909399;
}

.empty-result .el-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.result-content {
  padding: 16px 0;
}

.summary-alert {
  margin-bottom: 20px;
}

:deep(.el-table .warning-row) {
  background: #fef8e8;
}

:deep(.el-table .success-row) {
  background: #f0f9eb;
}

.export-btn {
  display: flex;
  align-items: center;
}

.export-btn .el-icon {
  margin-right: 4px;
}

.deduction-text {
  color: #f56c6c;
  font-weight: bold;
}

.total-score {
  margin-top: 20px;
  padding: 16px;
  background-color: #f5f7fa;
  border-radius: 4px;
  text-align: right;
}

.total-label {
  font-size: 16px;
  font-weight: 500;
  color: #606266;
  margin-right: 8px;
}

.total-value {
  font-size: 20px;
  font-weight: bold;
  color: #409eff;
}

.rule-description {
  white-space: pre-line;
  line-height: 1.5;
  font-size: 14px;
  color: #606266;
}
</style> 