import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'

// 创建axios实例
const service: AxiosInstance = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'http://localhost:5000',
    timeout: 30000
})

// 请求拦截器
service.interceptors.request.use(
    (config: AxiosRequestConfig) => {
        // 在这里可以添加token等认证信息
        return config
    },
    (error) => {
        console.error('请求错误:', error)
        return Promise.reject(error)
    }
)

// 响应拦截器
service.interceptors.response.use(
    (response: AxiosResponse) => {
        const res = response.data

        if (!res.success) {
            ElMessage.error(res.error || '请求失败')
            return Promise.reject(new Error(res.error || '请求失败'))
        }

        return res
    },
    (error) => {
        console.error('响应错误:', error)
        ElMessage.error(error.message || '请求失败')
        return Promise.reject(error)
    }
)

export default service 