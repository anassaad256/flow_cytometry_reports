import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api'
})

export async function fetchPanels() {
  const res = await api.get('/panels')
  return res.data
}

export async function fetchPanelSchema(panelId) {
  const res = await api.get(`/panel/${panelId}/schema`)
  return res.data
}

export async function fetchEnums() {
  const res = await api.get('/enums')
  return res.data
}

export async function generateReport(caseInput) {
  const res = await api.post('/generate', caseInput)
  return res.data
}
