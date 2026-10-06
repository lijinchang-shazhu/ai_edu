import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 180000,
})

export default {
  meta: () => api.get('/meta'),

  // 知识库
  kbUpload: (formData) =>
    api.post('/kb/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),
  kbList: (collection, teacher) => api.get('/kb/list', { params: { collection, teacher } }),
  kbSearch: (q, collection, k = 5, teacher) => api.get('/kb/search', { params: { q, collection, k, teacher } }),
  kbChat: (payload) => api.post('/kb/chat', payload),
  kbDelete: (id) => api.delete(`/kb/delete/${id}`),

  // 工作流
  runWorkflow: (payload) => api.post('/workflow/run', payload),

  // 对话
  chat: (message, history) => api.post('/chat', { message, history }),

  // 学情
  learningClass: () => api.get('/learning/class'),
  learningStudents: () => api.get('/learning/students'),
  learningStatistics: () => api.get('/learning/statistics'),
  learningInteractions: () => api.get('/learning/interactions'),
  learningUpdate: (topic) => api.post('/learning/update', { topic }),
  learningMemories: () => api.get('/learning/memories'),
  learningReport: (topic) => api.get('/learning/report', { params: { topic } }),

  // 素材
  materials: () => api.get('/materials'),
  material: (id) => api.get(`/materials/${id}`),
  updateMaterial: (id, content) => api.put(`/materials/${id}`, { content }),
  saveMaterial: (payload) => api.post('/materials/save', payload),
  materialVersions: (id) => api.get(`/materials/${id}/versions`),
  refineMaterial: (id, instruction) => api.post(`/materials/${id}/refine`, { instruction }),
  deleteMaterial: (id) => api.delete(`/materials/${id}`),

  // 课件
  coursewareUrl: (id) => `/api/courseware/${id}`,
  coursewarePptxUrl: (id) => `/api/courseware/${id}/export/pptx`,
  downloadUrl: (id) => `/api/materials/${id}/download`,
  reportDownloadUrl: (topic) => `/api/learning/report/download?topic=${encodeURIComponent(topic)}`,
}
