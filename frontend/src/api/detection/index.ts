import request from '@/utils/request'

// 图片检测
export function detectImage(data: FormData) {
    return request({
        url: '/api/detection/detect',
        method: 'post',
        data,
        headers: {
            'Content-Type': 'multipart/form-data'
        }
    })
}

// 图片分析
export function analyzeImage(data: FormData) {
    return request({
        url: '/api/detection/analyze',
        method: 'post',
        data,
        headers: {
            'Content-Type': 'multipart/form-data'
        }
    })
}

// 获取模型状态
export function getModelStatus() {
    return request({
        url: '/api/detection/model/status',
        method: 'get'
    })
} 