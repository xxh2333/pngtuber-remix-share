import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../stores/user'

const http = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

// 请求拦截：携带 token
http.interceptors.request.use((config) => {
  const userStore = useUserStore()
  if (userStore.token) {
    config.headers.Authorization = `Bearer ${userStore.token}`
  }
  return config
})

// 响应拦截：统一错误处理
http.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status
    const detail = error.response?.data?.detail
    if (status === 401) {
      const userStore = useUserStore()
      userStore.logout()
      ElMessage.error('登录已过期，请重新登录')
      window.location.href = '/login'
    } else if (detail) {
      ElMessage.error(detail)
    } else if (status >= 400) {
      ElMessage.error(`请求失败 (${status})`)
    }
    return Promise.reject(error)
  }
)

// ========== 认证 ==========
export const authApi = {
  register: (username, password) => http.post('/auth/register', { username, password }),
  login: (username, password) => http.post('/auth/login', { username, password }),
  deactivate: () => http.post('/auth/deactivate'),
  me: () => http.get('/auth/me'),
}

// ========== 作品 ==========
export const worksApi = {
  list: (params) => http.get('/works/', { params }),
  hot: (params) => http.get('/works/hot', { params }),
  detail: (id) => http.get(`/works/${id}`),
  create: (formData) => http.post('/works/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  remix: (formData) => http.post('/works/remix', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  mine: (params) => http.get('/works/mine', { params }),
  update: (id, data) => http.put(`/works/${id}`, data),
  replaceFile: (id, formData) => http.put(`/works/${id}/file`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  delete: (id) => http.delete(`/works/${id}`),
  like: (id) => http.post(`/works/${id}/like`),
  downloadUrl: (id) => `/api/works/${id}/download`,
}

export default http
