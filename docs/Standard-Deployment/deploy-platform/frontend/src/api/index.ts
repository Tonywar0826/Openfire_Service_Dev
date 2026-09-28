import axios from 'axios'

/** 后端 API 客户端（开发阶段经 vite 代理转发到 FastAPI:8000）。 */
const http = axios.create({
  baseURL: '/',
  timeout: 30000,
})

// 部署
export const deployApi = {
  deploy: (data: Record<string, unknown>) => http.post('/api/deploy', data),
  stop: () => http.post('/api/deploy/stop'),
}

// 备份/恢复
export const backupApi = {
  backup: () => http.post('/api/backup'),
  list: () => http.get('/api/backups'),
  restore: (backupId: string) => http.post('/api/restore', null, { params: { backup_id: backupId } }),
}

// 目标服务器
export const targetsApi = {
  list: () => http.get('/api/targets'),
  add: (data: Record<string, unknown>) => http.post('/api/targets', data),
  remove: (name: string) => http.delete(`/api/targets/${name}`),
  test: (name: string) => http.post(`/api/targets/${name}/test`),
}

// 状态
export const statusApi = {
  status: () => http.get('/api/status'),
}

export default http
